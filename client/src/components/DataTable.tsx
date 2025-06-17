import React, {useCallback, useEffect, useRef} from "react";
import {Table, Input, Space} from "antd";
import {observer} from "mobx-react-lite";
import {dataStore} from "../stores/DataStore";
import type {ColumnType, TableProps} from "antd/es/table";
import {SearchOutlined} from "@ant-design/icons";

const DataTable: React.FC = observer(() => {
    const tableRef = useRef<HTMLDivElement>(null);


    useEffect(() => {
        dataStore.fetchData();
    }, []);

    const handleTableChange = useCallback<TableProps<DataItem>["onChange"]>(
        (pagination, filters, sorter) => {
            if (pagination.current !== dataStore.pagination.current) {
                dataStore.setPagination(pagination);
            }

            const newSorts: SortCondition[] = [];
            if (Array.isArray(sorter)) {
                sorter.forEach((sort, index) => {
                    if (sort.field && sort.order) {
                        newSorts.push({
                            column: sort.field as string,
                            direction: sort.order === "ascend" ? "asc" : "desc",
                            priority: index + 1,
                        });
                    }
                });
            } else if (sorter.field && sorter.order) {
                newSorts.push({
                    column: sorter.field as string,
                    direction: sorter.order === "ascend" ? "asc" : "desc",
                    priority: 1,
                });
            }
            dataStore.setSorts(newSorts);

            const newFilters: FilterCondition[] = [];
            for (const [column, value] of Object.entries(filters)) {
                if (value) {
                    newFilters.push({
                        column,
                        operator: "in",
                        value,
                    });
                }
            }
            dataStore.setFilters(newFilters);
        });

    const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
        const {scrollTop, scrollHeight, clientHeight} = e.currentTarget;
        const {pageSize} = dataStore.pagination;

        if (
            scrollHeight - (scrollTop + clientHeight) < 100 &&
            !dataStore.loading &&
            dataStore.data.length < (dataStore.pagination.total || 0)
        ) {
            const nextOffset = dataStore.data.length;
            dataStore.handleScrollLoad(nextOffset, pageSize || 1000);
        }
    };

    const columns: ColumnType<DataItem>[] = [
        {
            title: "ID",
            dataIndex: "id",
            key: "id",
            sorter: true,
        },
        {
            title: "Name",
            dataIndex: "name",
            key: "name",
            sorter: true,
            filterDropdown: ({setSelectedKeys, selectedKeys, confirm}) => (
                <div style={{padding: 8}}>
                    <Input
                        placeholder="Filter name"
                        value={selectedKeys[0]}
                        onChange={(e) =>
                            setSelectedKeys(e.target.value ? [e.target.value] : [])
                        }
                        onPressEnter={confirm}
                        style={{width: 188, marginBottom: 8, display: "block"}}
                    />
                </div>
            ),
            filterIcon: (filtered) => (
                <SearchOutlined style={{color: filtered ? "#1890ff" : undefined}}/>
            ),
            onFilter: (value, record) =>
                record.name.toLowerCase().includes(value.toString().toLowerCase()),
        },
        {
            title: "Version",
            dataIndex: "version",
            key: "version",
            sorter: true,
        },
        {
            title: "Created At",
            dataIndex: "created_at",
            key: "created_at",
            sorter: true,
            render: (date: string) => new Date(date).toLocaleString(),
        },
        {
            title: "Description",
            dataIndex: "description",
            key: "description",
        },
        {
            title: "Country",
            dataIndex: "country",
            key: "country",
            sorter: true,
        },
        {
            title: "Count",
            dataIndex: "count",
            key: "count",
            sorter: true,
        },
        {
            title: "Parent",
            dataIndex: "parent",
            key: "parent",
            sorter: true,
        },
    ];

    return (
        <div style={{padding: "20px"}}>
            <Space direction="vertical" style={{width: "100%"}}>
                <Input
                    placeholder="Global search..."
                    value={dataStore.globalSearch}
                    onChange={(e) => dataStore.setGlobalSearch(e.target.value)}
                    style={{marginBottom: 16}}
                />

                <div
                    ref={tableRef}
                    onScroll={handleScroll}
                    style={{overflow: "auto"}}
                >
                    <Table
                        columns={columns}
                        dataSource={dataStore.data}
                        rowKey="id"
                        loading={dataStore.loading}
                        onChange={handleTableChange}
                        pagination={dataStore.pagination}
                        scroll={{y: "60vh"}}
                        sticky
                    />
                </div>
            </Space>
        </div>
    );
});

export default DataTable;