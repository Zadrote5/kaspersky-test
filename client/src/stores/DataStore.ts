import {makeAutoObservable, runInAction} from "mobx";
import type {TablePaginationConfig} from "antd/es/table";
import {debounce} from "../utils/debounce.ts";

interface DataItem {
    id: number;
    name: string;
    version: string;
    created_at: string;
    desc: string;
    country: number;
    count: number;
    parent: number | null;
}

interface FilterCondition {
    column: string;
    operator: string;
    value: any;
}

interface SortCondition {
    column: string;
    direction: string;
    priority: number;
}

class DataStore {
    data: DataItem[] = [];
    loading = false;
    error: string | null = null;
    pagination: TablePaginationConfig = {
        current: 1,
        pageSize: 1000,
        total: 0,
    };
    filters: FilterCondition[] = [];
    sorts: SortCondition[] = [];
    globalSearch: string = "";
    maxRecords = 3000; // 300% of pageSize

    constructor() {
        makeAutoObservable(this);
    }

    private isFetching = false;

    async fetchData() {
        if (this.isFetching) return;

        this.isFetching = true;
        this.loading = true;
        this.error = null;

        try {
            const {current, pageSize} = this.pagination;
            const offset = ((current || 1) - 1) * (pageSize || 1000);

            const response = await fetch("http://localhost:8000/data", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    offset,
                    limit: pageSize,
                    filters: this.filters,
                    sorts: this.sorts,
                    global_search: this.globalSearch,
                }),
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();

            runInAction(() => {
                this.data = result.data;
                this.pagination.total = result.total;
                this.loading = false;
            });
        } catch (error) {
            runInAction(() => {
                this.error = error instanceof Error ? error.message : "Unknown error";
                this.loading = false;
            });
        } finally {
            runInAction(() => {
                this.isFetching = false;
            });
        }

    }

    setPagination(pagination: TablePaginationConfig) {
        this.pagination = pagination;
        this.fetchData();
    }

    setFilters = debounce((filters: FilterCondition[]) => {
        runInAction(() => {
            this.filters = filters;
            this.pagination.current = 1;
            this.fetchData();
        });
    }, 300);

    setSorts = debounce((sorts: SortCondition[]) => {
        runInAction(() => {
            this.sorts = sorts;
            this.fetchData();
        });
    }, 300);

    setGlobalSearch = debounce((search: string) => {
        runInAction(() => {
            this.globalSearch = search;
            this.pagination.current = 1;
            this.fetchData();
        });
    }, 500);

    async handleScrollLoad(offset: number, limit: number) {
        if (this.data.length >= this.maxRecords) {
            this.data = this.data.slice(-this.maxRecords + limit);
        }

        try {
            const response = await fetch("http://localhost:8000/data", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    offset,
                    limit,
                    filters: this.filters,
                    sorts: this.sorts,
                    global_search: this.globalSearch,
                }),
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();

            runInAction(() => {
                this.data = [...this.data, ...result.data];
                this.pagination.total = result.total;
            });
        } catch (error) {
            console.error("Error loading more data:", error);
        }
    }
}

export const dataStore = new DataStore();