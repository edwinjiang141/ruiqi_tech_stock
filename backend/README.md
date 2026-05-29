# 后端服务

V1.2 纯量化股票推荐系统后端，使用 FastAPI、SQLAlchemy、Alembic 和 PostgreSQL。

## 本地运行

```bash
cd /ruiqi_tech_stock
python3 -m pip install -r backend/requirements.txt
alembic -c backend/alembic.ini upgrade head
scripts/run_backend.sh
```

默认数据库 schema 为 `stock_research_v12`，不会使用已有的 `public` schema。
