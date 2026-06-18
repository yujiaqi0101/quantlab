# QuantLab Deployment

## Docker 部署（推荐）

### 快速启动

```bash
cd deploy/docker
docker compose up -d
```

启动后：
- 前端：http://localhost:5173
- 后端 API：http://localhost:8000
- API 文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/api/v1/health

### 服务说明

| 服务 | 端口 | 说明 |
|------|------|------|
| backend | 8000 | FastAPI 后端 |
| frontend | 5173 | Vite 前端 |
| postgres | 5432 | PostgreSQL（可选） |

### 使用 PostgreSQL

默认使用 SQLite，如需 PostgreSQL：

```bash
docker compose --profile postgres up -d
```

### 数据持久化

| 卷 | 容器路径 | 说明 |
|----|----------|------|
| ../../storage | /app/storage | 数据/产物/数据库 |
| ../../logs | /app/logs | 日志 |
| ../../backups | /app/backups | 备份 |
| ../../config | /app/config | 配置 |
| quantlab_db | /var/lib/postgresql/data | PostgreSQL 数据 |

### 停止

```bash
docker compose down
```

### 查看日志

```bash
docker compose logs -f backend
docker compose logs -f frontend
```

### 重新构建

```bash
docker compose build --no-cache
docker compose up -d
```

## 手动部署

### 后端

```bash
pip install -r deploy/docker/requirements.txt
uvicorn quantlab.api.app:app --host 0.0.0.0 --port 8000
```

### 前端

```bash
cd frontend
npm install
npm run build
npm run preview -- --host 0.0.0.0 --port 5173
```

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| QUANTLAB_ENV | development | 环境名 |
| QUANTLAB_DB_PATH | storage/quantlab.db | 数据库路径 |
