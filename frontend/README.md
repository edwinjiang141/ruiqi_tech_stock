# 前端应用

V1.2 纯量化股票推荐系统前端，使用 Vue3、TypeScript、Vite 和 ECharts。

开发期通过 Vite proxy 将 `/api` 转发到 `http://127.0.0.1:8000`，生产或本机部署时由 FastAPI 挂载 `frontend/dist` 静态文件，不使用 Nginx。
