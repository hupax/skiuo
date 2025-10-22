# 重新构建检查清单

## 修改的文件列表

### 1. ✅ Core Service (需要重新构建)

**修改的文件：**
- `core-service/src/main/java/com/skiuo/streammind/security/SecurityConfig.java`
  - 添加了生产环境域名到 CORS allowedOrigins
  - 添加了 `https://skiuo.supanx.net`, `https://api.supanx.net`, `https://ai.supanx.net`, `https://signaling.supanx.net`

- `core-service/src/main/java/com/skiuo/streammind/websocket/WebSocketConfig.java`
  - 将 `setAllowedOrigins("*")` 改为具体的域名列表
  - 添加了生产和开发环境的域名

- `core-service/pom.xml`
  - 添加了 `spring-boot-starter-actuator` 依赖

**是否生效：** ❌ 需要重新构建
```bash
docker compose build core-service
```

---

### 2. ✅ AI Service (需要重新构建)

**修改的文件：**
- `ai-service/Dockerfile`
  - 修改 protobuf 生成路径从 `/app/app/generated` 到 `/app/app/generated/proto`
  - 更改了 `--python_out` 和 `--grpc_python_out` 路径

- `ai-service/app/grpc_client.py`
  - 调整了 import 顺序，优先尝试从 `app.generated` 导入
  - 添加了更多的 fallback import 路径

**是否生效：** ❌ 需要重新构建
```bash
docker compose build ai-service
```

---

### 3. ⚠️ Frontend (需要重启 PM2)

**修改的文件：**
- `frontend/.env.local`
  - `VITE_API_URL=https://api.supanx.net`
  - `VITE_SIGNALING_WS_URL=wss://signaling.supanx.net`
  - `VITE_ANALYSIS_WS_URL=wss://api.supanx.net/ws/analysis`

- `frontend/vite.config.js`
  - 添加了 `host: true`
  - 添加了 `allowedHosts` 配置

**是否生效：** ❌ 需要重启 PM2
```bash
pm2 restart frontend
```

---

### 4. ✅ Signaling Service (无需改动)

**状态：** 无修改

---

## 完整的重新部署步骤

```bash
cd ~/skiuo

# 1. 停止所有 Docker 服务
docker compose down

# 2. 清理旧的无名镜像
docker image prune -f

# 3. 重新构建所有修改过的服务
docker compose build core-service ai-service

# 4. 启动 Docker 服务
docker compose up -d

# 5. 检查服务状态
docker compose ps
docker compose logs -f core-service ai-service

# 6. 重启 Frontend PM2
pm2 restart frontend
pm2 logs frontend

# 7. 验证修改是否生效
# 检查 core-service CORS 配置
docker compose logs core-service | grep -i cors

# 检查 ai-service protobuf 导入
docker compose logs ai-service | grep -i "grpc\|protobuf"

# 检查 ai-service 生成的文件
docker exec streammind-ai find /app/app/generated -name "*.py" -type f
```

---

## 验证清单

### Core Service
- [ ] SecurityConfig 中的 CORS 配置包含生产域名
- [ ] WebSocketConfig 中的 allowedOrigins 不是 "*"
- [ ] Actuator health endpoint 正常工作: `curl https://api.supanx.net/actuator/health`

### AI Service
- [ ] protobuf 文件在 `/app/app/generated/proto/` 或 `/app/app/generated/`
- [ ] gRPC 客户端成功初始化，没有 "protobuf files missing" 错误
- [ ] 能够连接到 core-service:9090

### Frontend
- [ ] 使用 `https://api.supanx.net` 作为 API base URL
- [ ] 没有 CORS 错误
- [ ] 能够成功注册和登录

---

## 当前镜像清理

如果有多个无名镜像，建议清理：

```bash
# 查看所有镜像
docker images

# 删除所有无名镜像（dangling images）
docker image prune -f

# 或者删除所有未使用的镜像
docker image prune -a
```

---

## 常见问题

### 1. 容器使用旧镜像
**原因：** `docker compose build` 只构建镜像，不会自动重新创建容器
**解决：**
```bash
docker compose down
docker compose up -d
```

### 2. 修改没有生效
**原因：** 构建时使用了缓存
**解决：**
```bash
docker compose build --no-cache [service-name]
```

### 3. PM2 前端使用旧代码
**原因：** PM2 没有重启或配置文件没有重新加载
**解决：**
```bash
pm2 restart frontend
# 或强制重启
pm2 delete frontend
cd ~/skiuo/frontend
pm2 start npm --name frontend --cwd ~/skiuo/frontend -- run dev
```
