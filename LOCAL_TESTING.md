# StreamMind 本地测试指南

本文档介绍如何在本地环境运行和测试 StreamMind 项目（Canvas 截图方案）。

## 架构概述

```
浏览器前端 (React)
    ↓ Canvas 截图 (1fps)
    ↓ WebSocket /frames/{sessionId}
Node.js Signaling Service
    ↓ 转发 Base64 JPEG
    ↓ WebSocket /ws/analyze/{sessionId}
Python AI Service (FastAPI)
    ↓ 分析结果 (gRPC)
Spring Boot Core Service
    ↓ 广播 Token (WebSocket)
    ↓ /ws/analysis/{sessionId}
浏览器前端 (显示分析)
```

## 前置要求

- **Node.js** 18+ (用于 signaling-service 和 frontend)
- **Python** 3.9+ (用于 ai-service)
- **Java** 17+ (用于 core-service)
- **PostgreSQL** 15+ (数据库)
- **通义千问 API Key** (QWEN_API_KEY)

## 快速启动步骤

### 1. 启动数据库

```bash
# 使用 Docker 启动 PostgreSQL
cd ~/skiuo
docker compose up -d postgres

# 或者使用本地 PostgreSQL
# 确保创建了数据库: streammind
```

### 2. 启动 Spring Boot Core Service

```bash
cd ~/skiuo/core-service

# 确保环境变量配置正确 (.env 或系统环境变量)
export DATABASE_URL=jdbc:postgresql://localhost:5432/streammind
export DATABASE_USERNAME=postgres
export DATABASE_PASSWORD=your_password

# 运行服务
mvn spring-boot:run

# 或者使用 JAR
mvn clean package
java -jar target/core-service-0.0.1-SNAPSHOT.jar
```

**验证**: 访问 http://localhost:8080/actuator/health 应该返回 `{"status":"UP"}`

### 3. 启动 Python AI Service

```bash
cd ~/skiuo/ai-service

# 安装依赖 (首次运行)
pip install -r requirements.txt

# 设置环境变量
export QWEN_API_KEY=your_qwen_api_key_here
export SPRING_BOOT_GRPC_HOST=localhost
export SPRING_BOOT_GRPC_PORT=9090

# 运行服务
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**验证**: 访问 http://localhost:8000/health 应该返回 `{"status":"healthy"}`

### 4. 启动 Node.js Signaling Service

```bash
cd ~/skiuo/signaling-service

# 清理旧依赖并重新安装 (首次运行或更新后)
rm -rf node_modules package-lock.json
npm install

# 确保 .env 配置正确
cat .env
# NODE_SERVICE_PORT=3000
# SPRING_BOOT_API_URL=http://localhost:8080
# PYTHON_AI_WS_URL=ws://localhost:8000
# LOG_LEVEL=info

# 运行服务
npm start

# 或者开发模式 (自动重启)
npm run dev
```

**验证**: 访问 http://localhost:3000/health 应该返回 `{"status":"healthy","service":"signaling-service"}`

### 5. 启动前端

```bash
cd ~/skiuo/frontend

# 安装依赖 (首次运行)
npm install

# 确保使用本地环境变量
# Vite 会自动读取 .env.development

# 运行开发服务器
npm run dev
```

**验证**: 访问 http://localhost:5173 应该看到登录页面

## 完整测试流程

### 1. 注册/登录

1. 打开浏览器访问 http://localhost:5173
2. 点击"注册"创建新账号 (或使用已有账号登录)
3. 登录成功后自动跳转到录制页面

### 2. 开始录制

1. 点击**"开始录制"**按钮
2. 浏览器会请求摄像头和麦克风权限 → **允许**
3. 左侧应该显示摄像头预览画面
4. 查看状态:
   - 显示 "● 录制中" (绿色)
   - 会话 ID 显示
   - 右侧开始显示 AI 分析文本

### 3. 验证数据流

**浏览器控制台** (F12 → Console):
```
Connecting to frames WebSocket: ws://localhost:3000/frames/{sessionId}
Frames WebSocket connected
Sent frame 1
Sent frame 2
...
Connecting to analysis WebSocket: ws://localhost:8080/ws/analysis/{sessionId}
Analysis WebSocket connected
Received token: 用户
Received token: 正在
...
```

**Signaling Service 日志**:
```
Frames WebSocket connected for session: {sessionId}
Received frame 1 for session {sessionId}
Forwarded frame 1 to Python for session {sessionId}
Connected to Python AI for session {sessionId}
```

**Python AI Service 日志**:
```
WebSocket connected for session: {sessionId}
Received frame 1 for session {sessionId}, size: 50000 bytes
Added frame 1 analysis to context for session {sessionId}
```

**Spring Boot 日志**:
```
WebSocket client connected for session {sessionId}, total clients: 1
Received analysis from Python AI: token_index=0, content=用户
Saved analysis record for session {sessionId}
Broadcasting token to 1 clients
```

### 4. 停止录制

1. 点击**"停止录制"**按钮
2. 摄像头预览停止
3. WebSocket 连接关闭
4. 可以点击**"历史记录"**查看保存的会话

## 常见问题排查

### 问题 1: 前端无法连接到 Signaling Service

**现象**: 控制台显示 `WebSocket connection failed`

**检查**:
```bash
# 确认 signaling-service 正在运行
curl http://localhost:3000/health

# 检查环境变量
cd ~/skiuo/frontend
cat .env.development
# 确保 VITE_SIGNALING_WS_URL=ws://localhost:3000
```

### 问题 2: AI 分析没有返回

**现象**: 右侧分析区域一直显示 "已接收 Token: 0"

**检查**:
```bash
# 1. Python AI Service 是否运行
curl http://localhost:8000/health

# 2. 检查 QWEN_API_KEY 是否设置
cd ~/skiuo/ai-service
python3 -c "from app.config import settings; print(settings.qwen_api_key)"

# 3. 查看 Python 日志是否有错误
# 应该看到 "Received frame X" 和分析输出

# 4. 检查 gRPC 连接
# Spring Boot 日志应该显示 "Received analysis from Python AI"
```

### 问题 3: AI 分析的是雪花屏/噪点

**现象**: AI 输出类似 "该屏幕显示的是随机彩色噪点"

**原因**: 这是旧方案的问题，Canvas 方案已解决

**验证**:
```bash
# 检查前端是否使用了 frame-capture.ts
cd ~/skiuo/frontend/src/pages
grep -n "FrameCaptureService" RecordingPage.tsx
# 应该看到: import FrameCaptureService from '../services/frame-capture';

# 检查 signaling-service 是否使用了 frame-handler.js
cd ~/skiuo/signaling-service/src
grep -n "FrameHandler" server.js
# 应该看到: const FrameHandler = require('./frame-handler');
```

### 问题 4: 数据库连接失败

**现象**: Spring Boot 启动报错 `Connection refused`

**解决**:
```bash
# 检查 PostgreSQL 是否运行
docker ps | grep postgres
# 或本地: pg_isready

# 检查数据库是否存在
psql -U postgres -c "\l" | grep streammind

# 创建数据库 (如果不存在)
psql -U postgres -c "CREATE DATABASE streammind;"
```

### 问题 5: 分析文本重复或不连贯

**现象**: AI 分析每帧都重复相同内容，或者没有连续性

**检查**:
```bash
# 1. 检查 Python AI 的 context_manager 是否正常工作
# 查看日志应该显示: "Added frame X analysis to context"

# 2. 检查 qwen_client.py 的 prompt
cd ~/skiuo/ai-service/app
grep -A 5 "ANALYSIS_PROMPT" qwen_client.py
# 应该看到: "只描述发生的变化和新的活动"

# 3. 检查 main.py 的上下文累积逻辑
grep -A 3 "add_to_context" main.py
# 应该看到: summary = f"[帧{frame_count}分析] {accumulated_response[:200]}..."
```

## 性能优化建议

### 调整帧率

如果网络或 AI 处理速度较慢，可以降低帧率:

```typescript
// frontend/src/pages/RecordingPage.tsx
frameCaptureService.current.startCapture(1); // 1 frame per second

// 改为 0.5fps (2秒一帧)
frameCaptureService.current.startCapture(0.5);
```

### 调整上下文历史长度

```python
# ai-service/app/context_manager.py
context_manager = ContextManager(max_history=10)

# 减少到 5 可以降低 token 使用
context_manager = ContextManager(max_history=5)
```

### 调整图片质量

```typescript
// frontend/src/services/frame-capture.ts
this.canvas.toBlob((blob) => {
  // ...
}, 'image/jpeg', 0.8); // 80% 质量

// 降低到 60% 可以减少传输数据量
}, 'image/jpeg', 0.6);
```

## 关键代码文件清单

| 服务 | 文件 | 作用 |
|------|------|------|
| Frontend | `src/services/frame-capture.ts` | Canvas 截图并发送 |
| Frontend | `src/services/websocket.ts` | 接收 AI 分析 token |
| Frontend | `src/pages/RecordingPage.tsx` | 录制页面主逻辑 |
| Signaling | `src/frame-handler.js` | 接收并转发帧到 Python |
| Signaling | `src/server.js` | WebSocket 路由 `/frames/{id}` |
| AI Service | `app/main.py` | WebSocket 端点 `/ws/analyze/{id}` |
| AI Service | `app/qwen_client.py` | 调用 Qwen API 分析 |
| AI Service | `app/context_manager.py` | 维护对话上下文 |
| AI Service | `app/grpc_client.py` | 发送 token 到 Spring Boot |
| Core Service | `websocket/AnalysisWebSocketHandler.java` | 广播 token 到前端 |
| Core Service | `grpc/AnalysisGrpcServiceImpl.java` | 接收 Python 的 gRPC 调用 |

## 环境变量速查

### Frontend (.env.development)
```
VITE_API_URL=http://localhost:8080
VITE_SIGNALING_WS_URL=ws://localhost:3000
VITE_ANALYSIS_WS_URL=ws://localhost:8080/ws/analysis
```

### Signaling Service (.env)
```
NODE_SERVICE_PORT=3000
SPRING_BOOT_API_URL=http://localhost:8080
PYTHON_AI_WS_URL=ws://localhost:8000
LOG_LEVEL=info
```

### AI Service (环境变量或 .env)
```
QWEN_API_KEY=sk-xxxxx
SPRING_BOOT_GRPC_HOST=localhost
SPRING_BOOT_GRPC_PORT=9090
SERVICE_PORT=8000
LOG_LEVEL=INFO
```

### Core Service (application.yml 或环境变量)
```
DATABASE_URL=jdbc:postgresql://localhost:5432/streammind
DATABASE_USERNAME=postgres
DATABASE_PASSWORD=your_password
GRPC_SERVER_PORT=9090
```

## 下一步

- [ ] 测试完整录制流程
- [ ] 验证 AI 分析连贯性
- [ ] 测试历史记录查看功能
- [ ] 性能压测 (长时间录制)
- [ ] 部署到生产环境 (见 DEPLOYMENT.md)

## 联系与反馈

如有问题，请检查:
1. 所有服务的日志输出
2. 浏览器控制台的错误信息
3. 网络请求 (F12 → Network)
4. 数据库连接状态
