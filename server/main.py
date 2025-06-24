from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import asyncpg
import os
from dotenv import load_dotenv

# Загрузка переменных окружения из файла .env
load_dotenv()

# Создание FastAPI приложения
app = FastAPI(
    title="API для работы с данными",
    description="API предоставляет endpoints для работы с таблицей items в PostgreSQL",
    version="1.0.0"
)

# Настройка CORS middleware для кросс-доменных запросов
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Разрешаем запросы со всех доменов
    allow_credentials=True,
    allow_methods=["*"],  # Разрешаем все HTTP методы
    allow_headers=["*"],  # Разрешаем все заголовки
)


# Модели запросов (Pydantic схемы)
class FilterCondition(BaseModel):
    """Модель условия фильтрации данных"""
    column: str  # Название колонки для фильтрации
    operator: str  # Оператор: '=', '!=', '>', '<', '>=', '<=', 'like', 'in', 'not in'
    value: Any  # Значение для фильтрации


class SortCondition(BaseModel):
    """Модель условия сортировки данных"""
    column: str  # Колонка для сортировки
    direction: str  # Направление: 'asc' или 'desc'
    priority: int  # Приоритет сортировки (чем меньше число, тем выше приоритет)


class DataRequest(BaseModel):
    """Основная модель запроса данных"""
    offset: int  # Смещение для пагинации
    limit: int  # Лимит записей на странице
    filters: List[FilterCondition] = []  # Список условий фильтрации
    sorts: List[SortCondition] = []  # Список условий сортировки
    global_search: Optional[str] = None  # Глобальный поиск по текстовым полям


# Утилиты для работы с базой данных
def build_where_clause(filters: List[FilterCondition], global_search: Optional[str]) -> tuple:
    """
    Строит SQL условие WHERE на основе фильтров и глобального поиска

    Args:
        filters: Список условий фильтрации
        global_search: Строка для глобального поиска

    Returns:
        Кортеж из (SQL условие, список параметров)
    """
    where_clauses = []
    params = []

    # Обрабатываем каждый фильтр
    for filter in filters:
        if filter.operator.lower() in ('in', 'not in'):
            # Обработка операторов IN/NOT IN
            placeholders = ', '.join([f'${len(params) + 1 + i}' for i in range(len(filter.value))])
            where_clauses.append(f"{filter.column} {filter.operator} ({placeholders})")
            params.extend(filter.value)
        elif filter.operator.lower() == 'like':
            # Обработка LIKE с добавлением % вокруг значения
            where_clauses.append(f"{filter.column} {filter.operator} ${len(params) + 1}")
            params.append(f"%{filter.value}%")
        else:
            # Обработка стандартных операторов
            where_clauses.append(f"{filter.column} {filter.operator} ${len(params) + 1}")
            params.append(filter.value)

    # Добавляем глобальный поиск по текстовым полям
    if global_search:
        search_clauses = []
        text_columns = ['name', 'version', 'description']
        for col in text_columns:
            search_clauses.append(f"{col} LIKE ${len(params) + 1}")
            params.append(f"%{global_search}%")
        where_clauses.append(f"({' OR '.join(search_clauses)})")

    return (" AND ".join(where_clauses), params) if where_clauses else ("", params)


def build_order_clause(sorts: List[SortCondition]) -> str:
    """
    Строит SQL условие ORDER BY на основе условий сортировки

    Args:
        sorts: Список условий сортировки

    Returns:
        SQL строка для ORDER BY
    """
    if not sorts:
        return "id ASC"  # Сортировка по умолчанию

    # Сортируем условия по приоритету
    sorted_sorts = sorted(sorts, key=lambda x: x.priority)
    order_parts = []
    for sort in sorted_sorts:
        direction = "ASC" if sort.direction.lower() == "asc" else "DESC"
        order_parts.append(f"{sort.column} {direction}")

    return ", ".join(order_parts)


# Обработчики событий приложения
@app.on_event("startup")
async def startup():
    """Инициализация пула соединений с PostgreSQL при старте приложения"""
    app.state.pool = await asyncpg.create_pool(
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        host=os.getenv("DB_HOST"),
        port=5432,
        min_size=5,  # Минимальное количество соединений в пуле
        max_size=20  # Максимальное количество соединений
    )


@app.on_event("shutdown")
async def shutdown():
    """Закрытие пула соединений при завершении работы приложения"""
    await app.state.pool.close()


# Dependency для получения соединения с БД
async def get_db():
    """Генератор соединений с базой данных из пула"""
    async with app.state.pool.acquire() as conn:
        yield conn


# API Endpoints
@app.post("/data", summary="Получение данных с фильтрацией и сортировкой")
async def get_data(request: DataRequest, db=Depends(get_db)):
    """
    Основной endpoint для получения данных с пагинацией, фильтрацией и сортировкой

    Args:
        request: Параметры запроса (DataRequest)
        db: Соединение с базой данных

    Returns:
        Словарь с данными и общим количеством записей
    """
    try:
        # Формируем условия WHERE
        where_clause, where_params = build_where_clause(request.filters, request.global_search)

        # Формируем ORDER BY
        order_clause = build_order_clause(request.sorts)

        # Строим основной запрос
        query = f"""
            SELECT id, name, version, created_at, description, country, count, parent
            FROM items
            {f'WHERE {where_clause}' if where_clause else ''}
            ORDER BY {order_clause}
            LIMIT ${len(where_params) + 1} OFFSET ${len(where_params) + 2}
        """

        # Параметры запроса (фильтры + limit/offset)
        params = where_params + [request.limit, request.offset]

        # Выполняем запрос
        rows = await db.fetch(query, *params)

        # Получаем общее количество записей (для пагинации)
        count_query = f"""
            SELECT COUNT(*) 
            FROM items
            {f'WHERE {where_clause}' if where_clause else ''}
        """
        total = await db.fetchval(count_query, *where_params)

        return {
            "data": rows,
            "total": total
        }
    except Exception as e:
        # В продакшне лучше использовать HTTPException
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/init_db", summary="Инициализация базы данных")
async def init_db(force: bool = False, db=Depends(get_db)):
    """
    Endpoint для инициализации базы данных (создание таблицы и тестовых данных)

    Args:
        force: Принудительное пересоздание таблицы, если она уже существует
        db: Соединение с базой данных

    Returns:
        Сообщение о результате инициализации
    """
    try:
        async with db.transaction():
            # Проверяем существование таблицы
            table_exists = await db.fetchval(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'items')"
            )

            if table_exists and not force:
                return {"message": "Таблица уже существует"}

            # Удаляем и создаем таблицу заново
            await db.execute("""
                DROP TABLE IF EXISTS items;
                CREATE TABLE items (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    version TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    description TEXT,
                    country INTEGER,
                    count INTEGER,
                    parent INTEGER
                );
            """)

            # Генерируем тестовые данные
            from faker import Faker
            import random
            fake = Faker()

            # Пакетная вставка для производительности
            batch_size = 1000
            total_records = 100000
            batches = total_records // batch_size

            for i in range(batches):
                values = []
                for j in range(batch_size):
                    values.append((
                        fake.first_name(),
                        f"{random.randint(1, 20)}.{random.randint(0, 9)}.{random.randint(0, 9)}",
                        fake.date_time_this_decade(),
                        fake.sentence(),
                        random.randint(1, 250),
                        random.randint(1, 1000),
                        random.randint(1, 100) if random.random() > 0.3 else None
                    ))

                await db.executemany("""
                    INSERT INTO items (name, version, created_at, description, country, count, parent)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                """, values)

            # Создаем индексы для ускорения поиска
            await db.execute("""
                -- Расширение для триграммного поиска
                CREATE EXTENSION IF NOT EXISTS pg_trgm;

                -- Индексы
                CREATE INDEX IF NOT EXISTS idx_items_name ON items USING gin(name gin_trgm_ops);
                CREATE INDEX IF NOT EXISTS idx_items_description ON items USING gin(description gin_trgm_ops);
                CREATE INDEX IF NOT EXISTS idx_items_country ON items(country);
                CREATE INDEX IF NOT EXISTS idx_items_count ON items(count);
                CREATE INDEX IF NOT EXISTS idx_items_parent ON items(parent);
            """)

            return {"message": f"База данных инициализирована с {total_records} записями"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Запуск приложения
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8008)