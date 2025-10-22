# StreamMind 服务器部署配置

## 需要在服务器上配置的环境变量

### 1. Docker 服务 (.env 文件)

在服务器的 `~/skiuo/.env` 文件中配置：

```bash
# Qwen API
QWEN_API_KEY=sk-your-actual-qwen-api-key

# Security
JWT_SECRET=your-actual-jwt-secret-32-chars-or-more
POSTGRES_PASSWORD=your-actual-postgres-password

# Database
POSTGRES_DB=streammind
POSTGRES_USER=streammind

# Ports (默认值可以不改)
CORE_SERVICE_PORT=8080
GRPC_PORT=9090
AI_SERVICE_PORT=8000

# Logging
LOG_LEVEL=INFO

# Spring Profile
SPRING_PROFILES_ACTIVE=prod
```

### 2. Node.js Signaling Service 环境变量

在 `~/skiuo/signaling-service/.env` 文件中配置：

```bash
NODE_SERVICE_PORT=3000
SPRING_BOOT_API_URL=http://localhost:8080
PYTHON_AI_WS_URL=ws://localhost:8000
LOG_LEVEL=info
```

### 3. Frontend 环境变量

在 `~/skiuo/frontend/.env.local` 文件中配置：

```bash
VITE_API_URL=https://api.supanx.net
VITE_SIGNALING_WS_URL=wss://signaling.supanx.net
VITE_ANALYSIS_WS_URL=wss://api.supanx.net/ws/analysis
```

## 部署步骤

### 1. 启动 Docker 服务

```bash
cd ~/skiuo
docker compose down
docker compose build
docker compose up -d
```

检查服务状态：
```bash
docker compose ps
docker compose logs -f core-service
docker compose logs -f ai-service
```

### 2. 启动 Node.js Signaling Service

```bash
cd ~/skiuo/signaling-service
pm2 start npm --name streammind-signaling --cwd ~/skiuo/signaling-service -- start
pm2 save
```

### 3. 启动 Frontend

```bash
cd ~/skiuo/frontend
pm2 start npm --name frontend --cwd ~/skiuo/frontend -- run dev
pm2 save
```

## 检查服务

### Docker 服务
```bash
# 检查容器状态
docker compose ps

# 查看日志
docker compose logs -f

# 进入容器
docker exec -it streammind-core bash
docker exec -it streammind-ai bash
```

### PM2 服务
```bash
# 查看所有服务
pm2 list

# 查看日志
pm2 logs frontend
pm2 logs streammind-signaling

# 重启服务
pm2 restart frontend
pm2 restart streammind-signaling
```

## 验证部署

### 1. 检查 API 服务
```bash
curl https://api.supanx.net/actuator/health
```

应该返回：
```json
{"status":"UP"}
```

### 2. 检查前端
访问 https://skiuo.supanx.net，应该能看到登录页面。

### 3. 测试注册
在浏览器中打开开发者工具，尝试注册用户，应该不再有 CORS 错误。

## 常见问题

### 1. CORS 错误
- 检查 SecurityConfig.java 中的 allowedOrigins 配置
- 确保 WebSocketConfig.java 中的 allowedOrigins 配置正确
- 重新构建并重启 core-service 容器

### 2. 容器启动失败
- 检查 .env 文件是否配置正确
- 查看容器日志：`docker compose logs [service-name]`
- 确保数据库初始化成功：`docker compose logs postgres`

### 3. 前端无法连接 API
- 检查 frontend/.env.local 配置
- 确保使用的是子域名而不是 localhost
- 检查 Caddy 配置和 DNS 解析

## Caddy 配置

确保 Caddyfile 配置了所有子域名：

```caddy
{
    email your-email@example.com
}

skiuo.supanx.net {
    reverse_proxy localhost:5173
}

api.supanx.net {
    reverse_proxy localhost:8080
}

ai.supanx.net {
    reverse_proxy localhost:8000
}

signaling.supanx.net {
    reverse_proxy localhost:3000
}
```

重新加载 Caddy：
```bash
sudo systemctl reload caddy
```

## 监控和维护

### 查看资源使用
```bash
# Docker 容器资源
docker stats

# PM2 进程资源
pm2 monit
```

### 日志轮转
Docker 日志已配置自动轮转（max-size: 10m/50m）。

PM2 日志可以手动清理：
```bash
pm2 flush
```

### 数据备份
```bash
# 备份 PostgreSQL
docker exec streammind-postgres pg_dump -U streammind streammind > backup_$(date +%Y%m%d).sql

# 恢复
cat backup_20251023.sql | docker exec -i streammind-postgres psql -U streammind streammind
```
