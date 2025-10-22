# StreamMind - Docker Deployment Guide

## 快速部署

### 1. 准备环境

```bash
# 确认 Docker 已安装
docker --version
docker-compose --version

# 克隆代码
git clone <repo-url>
cd skiuo
```

### 2. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑配置（必须设置以下变量）
nano .env
```

**必须配置的变量：**
```bash
QWEN_API_KEY=sk-ca9c7b9a2f33471d8d092851ccc74b68
JWT_SECRET=$(openssl rand -base64 32)
POSTGRES_PASSWORD=$(openssl rand -base64 16)
```

### 3. 启动服务

```bash
# 构建并启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 检查服务状态
docker-compose ps
```

### 4. 验证部署

```bash
# 检查 Spring Boot 健康状态
curl http://localhost:8080/actuator/health

# 检查 Python AI 服务
curl http://localhost:8000/health

# 查看数据库表
docker exec -it streammind-postgres psql -U streammind -d streammind -c '\dt'
```

---

## Caddy 反向代理配置

### Caddyfile 示例

```caddy
# StreamMind API 域名
api.yourdomain.com {
    # Spring Boot REST API
    handle /api/* {
        reverse_proxy localhost:8080
    }

    # Spring Boot WebSocket
    handle /ws/* {
        reverse_proxy localhost:8080
    }

    # Python AI Docs
    handle /ai-docs {
        reverse_proxy localhost:8000
    }

    # 健康检查
    handle /health {
        reverse_proxy localhost:8080
    }
}

# Node.js Signaling（如果部署在同一服务器）
signaling.yourdomain.com {
    reverse_proxy localhost:3000
}

# Frontend（静态文件或其他前端服务器）
yourdomain.com {
    # 如果前端使用 Nginx 或静态文件服务
    reverse_proxy localhost:5173
}
```

### 重启 Caddy

```bash
sudo systemctl reload caddy
```

---

## 服务间通信说明

### Docker 网络架构

```
streammind-network (172.20.0.0/16)
├── postgres (数据库)
├── redis (缓存)
├── core-service (Spring Boot)
│   ├── REST API: 8080
│   └── gRPC: 9090
└── ai-service (Python)
    └── HTTP/WebSocket: 8000
```

### 服务通信方式

1. **Python → Spring Boot (gRPC)**
   - 地址：`core-service:9090`
   - 用途：发送 AI 分析 Token

2. **Spring Boot → PostgreSQL (JDBC)**
   - 地址：`postgres:5432`
   - 用途：持久化数据

3. **Spring Boot → Redis (Redis Protocol)**
   - 地址：`redis:6379`
   - 用途：缓存和会话

4. **外部 → Spring Boot (REST/WebSocket)**
   - 通过 Caddy 代理
   - 端口：8080

5. **外部 → Python AI (HTTP)**
   - 通过 Caddy 代理（可选）
   - 端口：8000

---

## 日志管理

### 查看日志

```bash
# 查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f core-service
docker-compose logs -f ai-service

# 查看最近 100 行
docker-compose logs --tail=100 core-service

# 查看日志并跟随（实时）
docker-compose logs -f --tail=50 ai-service
```

### 日志配置

所有服务的日志已配置为 JSON 格式，自动轮转：

- **PostgreSQL & Redis**: 10MB × 3 个文件
- **Spring Boot**: 50MB × 5 个文件
- **Python AI**: 50MB × 5 个文件

日志存储位置：
```bash
# Docker 日志路径（宿主机）
/var/lib/docker/containers/<container-id>/<container-id>-json.log
```

### 清理日志

```bash
# 清理所有 Docker 日志
docker system prune --volumes

# 手动删除特定容器日志
truncate -s 0 $(docker inspect --format='{{.LogPath}}' streammind-core)
```

---

## 数据备份

### PostgreSQL 备份

```bash
# 创建备份
docker exec streammind-postgres pg_dump -U streammind streammind > backup_$(date +%Y%m%d_%H%M%S).sql

# 恢复备份
cat backup_20250123_120000.sql | docker exec -i streammind-postgres psql -U streammind streammind
```

### 自动备份（Cron）

```bash
# 创建备份脚本
cat > ~/backup-streammind.sh <<'EOF'
#!/bin/bash
BACKUP_DIR=~/backups/streammind
mkdir -p $BACKUP_DIR
DATE=$(date +%Y%m%d_%H%M%S)
docker exec streammind-postgres pg_dump -U streammind streammind > $BACKUP_DIR/backup_$DATE.sql
find $BACKUP_DIR -name "backup_*.sql" -mtime +7 -delete
EOF

chmod +x ~/backup-streammind.sh

# 添加到 crontab（每天凌晨 2 点）
(crontab -l 2>/dev/null; echo "0 2 * * * ~/backup-streammind.sh") | crontab -
```

---

## 更新部署

### 更新代码

```bash
cd ~/skiuo
git pull

# 重新构建并启动
docker-compose up -d --build

# 查看启动日志
docker-compose logs -f
```

### 仅重启服务（不重新构建）

```bash
docker-compose restart core-service
docker-compose restart ai-service
```

### 更新单个服务

```bash
# 重新构建并重启 Spring Boot
docker-compose up -d --build --no-deps core-service

# 重新构建并重启 Python AI
docker-compose up -d --build --no-deps ai-service
```

---

## 监控和维护

### 查看资源使用

```bash
# 查看容器资源使用情况
docker stats

# 查看特定容器
docker stats streammind-core streammind-ai
```

### 查看容器详情

```bash
# 查看容器配置
docker inspect streammind-core

# 查看容器网络
docker inspect streammind-network
```

### 进入容器

```bash
# 进入 Spring Boot 容器
docker exec -it streammind-core sh

# 进入 Python AI 容器
docker exec -it streammind-ai bash

# 进入 PostgreSQL
docker exec -it streammind-postgres psql -U streammind -d streammind
```

---

## 故障排查

### 服务无法启动

```bash
# 查看详细错误日志
docker-compose logs core-service

# 检查容器状态
docker-compose ps

# 重新构建（清除缓存）
docker-compose build --no-cache core-service
docker-compose up -d core-service
```

### 服务间无法通信

```bash
# 检查网络连接
docker exec streammind-ai ping core-service
docker exec streammind-core ping postgres

# 检查端口监听
docker exec streammind-core netstat -tuln | grep 8080
```

### 数据库连接失败

```bash
# 检查 PostgreSQL 日志
docker-compose logs postgres

# 验证数据库可访问
docker exec streammind-postgres pg_isready -U streammind

# 手动连接测试
docker exec -it streammind-postgres psql -U streammind -d streammind
```

### Python gRPC 连接失败

```bash
# 检查 gRPC 端口
docker exec streammind-core netstat -tuln | grep 9090

# 测试 gRPC 连接（从 Python 容器）
docker exec streammind-ai curl -v telnet://core-service:9090
```

### 查看 Protobuf 生成

```bash
# 检查 Spring Boot 生成的文件
docker exec streammind-core find /app -name "*pb*.java"

# 检查 Python 生成的文件
docker exec streammind-ai ls -la /app/app/generated/
```

---

## 停止和清理

### 停止服务

```bash
# 停止所有服务
docker-compose down

# 停止并删除卷（⚠️ 会删除数据）
docker-compose down -v
```

### 清理镜像

```bash
# 删除未使用的镜像
docker image prune -a

# 删除所有 StreamMind 镜像
docker images | grep streammind | awk '{print $3}' | xargs docker rmi -f
```

---

## 环境变量参考

所有环境变量都在 `.env` 文件中配置：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `QWEN_API_KEY` | **必填** Qwen API 密钥 | - |
| `JWT_SECRET` | **必填** JWT 密钥 | - |
| `POSTGRES_PASSWORD` | **必填** 数据库密码 | - |
| `POSTGRES_DB` | 数据库名 | `streammind` |
| `POSTGRES_USER` | 数据库用户 | `streammind` |
| `CORE_SERVICE_PORT` | Spring Boot 端口 | `8080` |
| `GRPC_PORT` | gRPC 端口 | `9090` |
| `AI_SERVICE_PORT` | Python AI 端口 | `8000` |
| `LOG_LEVEL` | 日志级别 | `INFO` |
| `SPRING_PROFILES_ACTIVE` | Spring 配置文件 | `prod` |

---

## 安全建议

1. **更改默认密码**
   ```bash
   # 生成强密码
   openssl rand -base64 32
   ```

2. **限制端口暴露**
   - 生产环境建议只暴露必要的端口
   - 使用 Caddy 作为反向代理，不直接暴露服务端口

3. **配置 HTTPS**
   - Caddy 自动配置 Let's Encrypt 证书

4. **定期更新**
   ```bash
   docker-compose pull
   docker-compose up -d
   ```

5. **日志监控**
   - 定期检查日志中的错误
   - 设置日志轮转避免磁盘占满

---

## 生产环境清单

- [ ] 已设置 `QWEN_API_KEY`
- [ ] 已生成并设置强 `JWT_SECRET`
- [ ] 已生成并设置强 `POSTGRES_PASSWORD`
- [ ] 已配置 Caddy 反向代理
- [ ] 已配置 HTTPS（Caddy 自动）
- [ ] 已设置数据库备份计划
- [ ] 已配置日志轮转
- [ ] 已测试服务健康检查
- [ ] 已测试 API 端点
- [ ] 已测试 WebSocket 连接

---

完成部署后，访问：
- API 健康检查: `http://your-domain.com/health`
- Swagger 文档: `http://your-domain.com/api-docs`（如果启用）
- Python AI 文档: `http://your-domain.com/ai-docs`
