# 非 Docker 本机运行说明

本项目在 `/ruiqi_tech_stock` 下运行，不使用 Docker、Nginx 或 Python 虚拟环境。

## 初始化

```bash
cd /ruiqi_tech_stock
python3 -m pip install -r backend/requirements.txt
npm install --prefix frontend
alembic -c backend/alembic.ini upgrade head
```

## 启动服务

```bash
scripts/run_backend.sh
scripts/run_frontend.sh
scripts/run_scheduler.sh
```

前端构建后，FastAPI 会自动挂载 `frontend/dist` 静态文件。
