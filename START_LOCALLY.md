# StreamMind - 本地启动指南

本指南将帮助你在不使用 docker-compose 的情况下，分别启动各个服务进行本地测试。

## ✅ 已完成的准备工作

所有代码修复已完成：
- ✅ Spring Boot 编译成功（JWT API 已更新到 0.12.x）
- ✅ Protobuf 代码已生成（Java 和 Python）
- ✅ Python 导入路径已修复
- ✅ Frontend 依赖已安装

## 📋 启动步骤

### 第 1 步：启动基础设施（PostgreSQL + Redis）

```bash
# 停止并删除旧容器（如果存在）
docker stop streammind-postgres streammind-redis 2>/dev/null
docker rm streammind-postgres streammind-redis 2>/dev/null

# 启动 PostgreSQL
docker run -d \
  --name streammind-postgres \
  -e POSTGRES_DB=streammind \
  -e POSTGRES_USER=streammind \
  -e POSTGRES_PASSWORD=streammind_dev_password \
  -p 5432:5432 \
  -v "$(pwd)/docker/postgres/init.sql:/docker-entrypoint-initdb.d/init.sql" \
  postgres:15-alpine

# 启动 Redis
docker run -d \
  --name streammind-redis \
  -p 6379:6379 \
  redis:7-alpine

# 等待服务启动
sleep 5

# 验证容器状态
docker ps --filter "name=streammind" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

**验证数据库表是否创建成功：**
```bash
docker exec -it streammind-postgres psql -U streammind -d streammind -c '\dt'
```

应该看到：`users`, `sessions`, `analysis_records` 三张表。

---

### 第 2 步：安装 Python 依赖

```bash
cd ai-service

# 安装依赖（包括新添加的 pydantic-settings）
pip3 install -r requirements.txt

# 验证安装成功
python3 -c "from app.config import settings; print('✅ Config OK')"
python3 -c "from app.grpc_client import SpringBootGrpcClient; print('✅ gRPC client OK')"
```

---

### 第 3 步：配置环境变量

**方式 1：导出环境变量（推荐用于测试）**
```bash
# 在项目根目录
export QWEN_API_KEY="你的通义千问API密钥"
export SPRING_BOOT_GRPC_HOST="localhost"
export SPRING_BOOT_GRPC_PORT="9090"
```

**方式 2：创建 .env 文件（已存在）**
```bash
# 编辑根目录的 .env 文件，确保包含：
QWEN_API_KEY=你的通义千问API密钥
SPRING_BOOT_GRPC_HOST=localhost
SPRING_BOOT_GRPC_PORT=9090
```

---

### 第 4 步：启动 Spring Boot Core Service（终端 1）

```bash
cd core-service

# 启动 Spring Boot
mvn spring-boot:run
```

**验证启动成功：**
- 看到日志：`Started CoreServiceApplication in X seconds`
- REST API：http://localhost:8080/api/sessions/status
- gRPC Server：localhost:9090
- WebSocket：ws://localhost:8080/ws/analysis

---

### 第 5 步：启动 Python AI Service（终端 2）

```bash
cd ai-service

# 启动 FastAPI
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

**验证启动成功：**
- 看到日志：`Application startup complete`
- WebSocket endpoint：ws://localhost:8001/ws/analyze/{session_id}
- Swagger 文档：http://localhost:8001/docs

---

### 第 6 步：部署 Node.js Signaling Service（远程服务器）

**⚠️ 重要说明：**
Node.js signaling-service 依赖 `wrtc` 包，该包在 **macOS ARM64 (Apple Silicon)** 上无预编译二进制文件，无法在本地安装。

**推荐方案：部署到 Linux 服务器**

在你的 Linux 服务器上执行：

```bash
# 上传代码到服务器
cd signaling-service

# 安装依赖（Linux 上可以正常安装 wrtc）
npm install

# 配置环境变量
export SPRING_BOOT_API_URL="http://你的本地IP:8080"
export PYTHON_AI_WS_URL="ws://你的本地IP:8001"
export PORT=8002

# 启动服务（建议使用 pm2）
npm install -g pm2
pm2 start src/server.js --name streammind-signaling

# 或直接启动
npm start
```

**验证启动成功：**
- 看到日志：`Signaling server started on port 8002`
- WebSocket endpoint：ws://服务器IP:8002

**本地测试替代方案（不推荐）：**
如果必须在本地测试，可以使用 Docker 部署 signaling-service：
```bash
cd signaling-service
docker build -t streammind-signaling .
docker run -d -p 8002:8002 \
  -e SPRING_BOOT_API_URL="http://host.docker.internal:8080" \
  -e PYTHON_AI_WS_URL="ws://host.docker.internal:8001" \
  streammind-signaling
```

---

### 第 7 步：启动 Frontend（终端 4）

```bash
cd frontend

# 启动开发服务器
npm run dev
```

**验证启动成功：**
- 看到日志：`Local: http://localhost:5173/`
- 浏览器打开：http://localhost:5173

---

## 🔍 完整服务状态检查

启动所有服务后，运行以下命令检查状态：

```bash
# 检查 PostgreSQL
docker exec -it streammind-postgres psql -U streammind -d streammind -c 'SELECT version();'

# 检查 Redis
docker exec -it streammind-redis redis-cli PING

# 检查 Spring Boot
curl http://localhost:8080/actuator/health

# 检查 Python AI Service
curl http://localhost:8001/docs

# 检查 Node.js Signaling
curl http://localhost:8002/health 2>/dev/null || echo "WebSocket only, no HTTP endpoint"

# 检查 Frontend
curl http://localhost:5173
```

---

## 🧪 测试完整流程

### 1. 注册/登录

```bash
# 注册用户
curl -X POST http://localhost:8080/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "password123"
  }'

# 登录获取 JWT
curl -X POST http://localhost:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "password123"
  }'
```

保存返回的 `token` 用于后续请求。

### 2. 创建录制会话

```bash
export TOKEN="你的JWT令牌"

curl -X POST http://localhost:8080/api/sessions/start \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "测试录制",
    "description": "本地测试"
  }'
```

保存返回的 `id`（session_id）。

### 3. 使用浏览器测试完整流程

1. 打开浏览器访问：http://localhost:5173
2. 使用刚才注册的账号登录
3. 点击"开始录制"
4. 允许浏览器访问摄像头和麦克风
5. 观察实时分析文本是否显示
6. 点击"停止录制"

### 4. 查看录制历史

```bash
# 获取所有会话
curl http://localhost:8080/api/sessions \
  -H "Authorization: Bearer $TOKEN"

# 获取特定会话的分析结果
curl http://localhost:8080/api/sessions/{session_id}/analysis \
  -H "Authorization: Bearer $TOKEN"
```

---

## 🐛 常见问题排查

### 问题 1：Spring Boot 启动失败 - 数据库连接错误

**症状：** `Connection refused: localhost:5432`

**解决方案：**
```bash
# 检查 PostgreSQL 容器是否运行
docker ps | grep streammind-postgres

# 查看容器日志
docker logs streammind-postgres

# 如果容器未启动，重新启动
docker start streammind-postgres
```

### 问题 2：Python 服务启动失败 - 模块未找到

**症状：** `ModuleNotFoundError: No module named 'pydantic_settings'`

**解决方案：**
```bash
cd ai-service
pip3 install --upgrade pip
pip3 install -r requirements.txt --force-reinstall
```

### 问题 3：Python gRPC 连接失败

**症状：** `gRPC error: UNAVAILABLE`

**解决方案：**
- 确保 Spring Boot 已经启动（先启动 Spring Boot，再启动 Python）
- 检查端口 9090 是否被占用：`lsof -i :9090`
- 检查 Spring Boot 日志中是否有 "gRPC server started on port 9090"

### 问题 4：Frontend 无法连接 WebSocket

**症状：** 浏览器控制台显示 `WebSocket connection failed`

**解决方案：**
- 检查 Spring Boot 是否启动
- 检查浏览器控制台的具体错误信息
- 确认 JWT token 是否有效（可能已过期）

### 问题 5：WebRTC 无法获取摄像头

**症状：** 浏览器显示 `NotAllowedError: Permission denied`

**解决方案：**
- 浏览器必须使用 HTTPS 或 localhost
- 检查浏览器权限设置（允许摄像头和麦克风访问）
- Chrome：设置 → 隐私和安全 → 网站设置 → 摄像头/麦克风

### 问题 6：Node.js Signaling 连接失败

**症状：** Frontend 日志显示 `Signaling connection failed`

**解决方案：**
```bash
# 检查 Node.js 服务是否运行
curl http://localhost:8002/

# 查看 Node.js 日志
cd signaling-service && npm start
```

---

## 🔧 端口占用检查

如果某个服务启动失败，可能是端口被占用：

```bash
# 检查所有 StreamMind 相关端口
lsof -i :5432    # PostgreSQL
lsof -i :6379    # Redis
lsof -i :8080    # Spring Boot
lsof -i :9090    # gRPC
lsof -i :8001    # Python AI
lsof -i :8002    # Node.js Signaling
lsof -i :5173    # Frontend
```

**杀死占用端口的进程：**
```bash
kill -9 $(lsof -t -i :8080)  # 替换 8080 为需要释放的端口
```

---

## 📝 日志查看

### Spring Boot 日志
```bash
cd core-service
mvn spring-boot:run | tee logs/spring-boot.log
```

### Python 日志
```bash
cd ai-service
uvicorn app.main:app --reload --log-level debug | tee logs/python.log
```

### Node.js 日志
```bash
cd signaling-service
npm start | tee logs/nodejs.log
```

### Frontend 日志
浏览器开发者工具 → Console

---

## 🛑 停止所有服务

```bash
# 停止 Docker 容器
docker stop streammind-postgres streammind-redis

# 停止其他服务
# 在各个终端按 Ctrl+C 停止 Spring Boot、Python、Node.js、Frontend
```

**可选：删除容器和数据**
```bash
docker rm streammind-postgres streammind-redis
docker volume prune  # 删除数据库数据（谨慎操作）
```

---

## ✅ 成功标志

所有服务正常运行时，你应该看到：

1. **4 个 Docker 容器运行中**（PostgreSQL + Redis）
2. **4 个终端分别运行**（Spring Boot + Python + Node.js + Frontend）
3. **浏览器可以访问** http://localhost:5173 并成功登录
4. **点击"开始录制"后：**
   - 摄像头视频显示在界面上
   - 实时分析文本开始显示
   - 数据库中 `sessions` 和 `analysis_records` 表有新记录

---

## 📚 进一步调试

如果遇到问题，请按以下顺序排查：

1. **基础设施层**：PostgreSQL + Redis
2. **后端核心层**：Spring Boot
3. **AI 分析层**：Python AI Service
4. **信令层**：Node.js Signaling
5. **前端层**：React Frontend

每一层都需要依赖前一层正常运行。

**查看详细文档：**
- 架构设计：`doc/dev2.md`
- 项目状态：`PROJECT_STATUS.md`
- API 文档：`README.md`
