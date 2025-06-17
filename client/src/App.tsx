// client/src/App.tsx
import React from "react";
import DataTable from "./components/DataTable";
import { ConfigProvider } from "antd";
import "./App.scss";

const App: React.FC = () => {
  return (
    <ConfigProvider
      theme={{
        token: {
          colorPrimary: "#1890ff",
        },
      }}
    >
      <div className="app-container">
        <h1>Тестовое задание для Лаборатории Касперского</h1>
        <DataTable />
      </div>
    </ConfigProvider>
  );
};

export default App;