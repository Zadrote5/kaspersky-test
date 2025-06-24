FROM node:20-alpine

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm install

COPY . .

# Запускаем в dev режиме без сборки
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]