# 项目名称

## 🎯 **StreamMind**
## 📋 产品需求（Product Requirements）

### 核心需求

**一句话描述**：

>
通过摄像头和麦克风实时记录用户活动，AI自动生成连贯的文字记录，适用于编程学习、手工制作、烹饪教学等任何需要过程记录的场景。

### 功能需求

#### 1. **实时录制**

- 用户通过浏览器访问，无需安装App
- 点击"开始录制"，申请摄像头和麦克风权限
- 实时显示画面预览
- 支持暂停/继续/停止

#### 2. **AI实时分析**

- 实时理解视频和音频内容
- 生成连贯的文字描述（不是碎片化的）
- 流式输出（逐字显示，像ChatGPT打字效果）
- 保持上下文记忆（前后关联）

#### 3. **记录管理**

- 自动保存所有分析记录
- 按时间轴展示
- 支持查看历史记录
- 导出为Markdown格式

#### 4. **用户界面**

- 简洁的Web界面
- 实时画面显示
- 实时文字显示（流式更新）
- 历史记录查询

### 非功能需求

#### 1. **性能要求**

- 视频延迟 < 200ms
- AI分析延迟 < 2秒
- 流式输出延迟 < 100ms
- 支持1080p@30fps

#### 2. **可靠性**

- 断线重连
- 数据持久化
- 错误恢复

#### 3. **扩展性**

- 支持多用户同时使用
- AI服务可水平扩展
- 存储可扩展

---

## 🏗️ 架构设计（Architecture Design）

### 整体架构

```
┌─────────────────────────────────────────┐
│           Web Frontend                  │
│     (React)         │
│  - 摄像头/麦克风采集                     │
│  - 实时画面显示                          │
│  - WebRTC客户端                         │
│  - 实时文字显示                          │
└──────────────┬──────────────────────────┘
               │
               │ WebRTC + WebSocket
               │
┌──────────────▼──────────────────────────┐
│      Node.js Signaling Service          │
│         (实时通信层)                     │
│  - WebRTC信令服务器                      │
│  - 视频流接收                            │
│  - 帧提取与转发                          │
└──────────────┬──────────────────────────┘
               │
         ┌─────┴─────┐
         │           │
         ↓           ↓
┌────────────┐  ┌──────────────────────┐
│Spring Boot │  │  Python AI Service   │
│  (业务中枢) │  │    (AI分析层)         │
│            │  │                      │
│- REST API  │  │- 视频分析            │
│- 会话管理  │  │- 音频分析            │
│- 用户管理  │  │- 流式生成            │
│- 数据持久化│  │- 上下文管理          │
│- WebSocket │  │- 模型推理            │
│  广播      │  │                      │
└─────┬──────┘  └──────────┬───────────┘
      │                    │
      │ gRPC              │
      └────────┬───────────┘
               │
         ┌─────┴─────┐
         ↓           ↓
    ┌────────┐  ┌────────┐
    │PostreSQL│  │ Redis  │
    │        │  │(可选)   │
    └────────┘  └────────┘
```

---

## 📦 服务职责分工（Service Responsibilities）

### 1️⃣ **Frontend Service（前端服务）**

**名称**: `streammind-frontend`

**职责**：

- ✅ 提供Web用户界面
- ✅ 申请摄像头和麦克风权限
- ✅ 实时显示视频画面
- ✅ 建立WebRTC连接
- ✅ 接收并显示AI分析结果（流式）
- ✅ 提供历史记录查询界面

**要做的事**：

```
1. 页面渲染
   - 登录/注册页面
   - 录制主界面
   - 历史记录页面

2. 媒体采集
   - 调用 navigator.mediaDevices.getUserMedia()
   - 获取 MediaStream
   - 显示到 <video> 元素

3. WebRTC通信
   - 创建 RTCPeerConnection
   - 与Node.js进行SDP协商
   - 发送音视频流

4. 实时显示
   - WebSocket连接到Spring Boot
   - 接收流式token
   - 逐字显示分析结果

5. 用户交互
   - 开始/停止录制
   - 查询历史记录
   - 导出记录
```

**不做的事**：

- ❌ 不处理视频编解码
- ❌ 不保存数据
- ❌ 不做AI分析

---

### 2️⃣ **Node.js Signaling Service（实时通信服务）**

**名称**: `streammind-signaling`

**职责**：

- ✅ WebRTC信令协调
- ✅ 接收实时视频流
- ✅ 提取关键帧
- ✅ 转发帧到AI服务

**要做的事**：

```
1. WebRTC信令
   - WebSocket服务器
   - 处理Offer/Answer/ICE Candidate
   - 管理RTCPeerConnection

2. 视频流处理
   - 接收WebRTC音视频轨道
   - 每秒采样1-2帧（降低AI负载）
   - 转换成JPEG格式

3. 数据转发
   - WebSocket连接到Python AI
   - 发送帧数据 + sessionId
   - 接收AI分析结果

4. 通知Spring Boot
   - 连接建立/断开事件
   - 流状态更新
```

**不做的事**：

- ❌ 不做AI分析
- ❌ 不存储数据
- ❌ 不做业务逻辑

---

### 3️⃣ **Python AI Service（AI分析服务）**

**名称**: `streammind-ai`

**职责**：

- ✅ AI视频分析
- ✅ AI音频分析
- ✅ 流式生成文字
- ✅ 上下文管理

**要做的事**：

```
1. 接收数据
   - WebSocket服务器
   - 接收JPEG帧 + sessionId
   - 接收音频片段

2. AI推理
   - 加载Qwen2.5-VL模型（或调用Gemini API）
   - 视频帧 → 分析
   - 音频 → 转文字
   - 保持对话上下文

3. 流式生成
   - 逐token生成
   - 每个token立即输出
   - yield/generator模式

4. 结果发送
   - gRPC调用Spring Boot
   - 每个token实时发送
   - 携带sessionId和timestamp

5. 上下文管理
   - 维护每个session的对话历史
   - 定期裁剪（防止过长）
   - 生成连贯的分析
```

**不做的事**：

- ❌ 不处理视频流（只处理单帧）
- ❌ 不存储数据（交给Spring Boot）
- ❌ 不做用户管理

---

### 4️⃣ **Spring Boot Core Service（核心业务服务）**

**名称**: `streammind-core`

**职责**：

- ✅ 业务逻辑协调
- ✅ 数据持久化
- ✅ 用户管理
- ✅ API网关
- ✅ 实时消息广播

**要做的事**：

```
1. REST API
   - POST /api/sessions/start（开始录制）
   - POST /api/sessions/stop（停止录制）
   - GET /api/sessions/{id}（查询会话）
   - GET /api/sessions/{id}/analysis（获取分析记录）
   - GET /api/sessions（列表）
   - POST /api/auth/login（登录）
   - POST /api/auth/register（注册）

2. 会话管理
   - 创建session记录
   - 更新session状态
   - 记录开始/结束时间
   - 管理会话生命周期

3. gRPC服务端
   - 接收Python发来的analysis token
   - 立即保存到数据库
   - 写入Redis（可选，用于实时查询）

4. WebSocket广播
   - 维护WebSocket连接
   - 收到token后立即广播到前端
   - 按sessionId分组广播

5. 数据持久化
   - Session表（会话信息）
   - AnalysisRecord表（分析记录）
   - User表（用户信息）

6. 报告生成
   - 汇总分析记录
   - 生成Markdown报告
   - 提供下载

7. 协调其他服务
   - 通知Node.js准备WebRTC
   - 通知Python初始化模型
   - 处理服务健康检查
```

**不做的事**：

- ❌ 不处理视频流
- ❌ 不做AI推理
- ❌ 不做WebRTC信令

---

## 🛠️ 技术栈（Technology Stack）

### Frontend（前端）

```javascript
技术栈：
- 框架: React 18
- WebRTC: 原生 RTCPeerConnection API
- WebSocket: 原生 WebSocket API
- UI库: Tailwind CSS
- 构建: Vite

关键库：
- react
- axios (HTTP请求)
- 无需额外WebRTC库（浏览器原生）

开发环境：
- Node.js 18+
- npm/yarn/pnpm
```

---

### Node.js Signaling Service

```javascript
技术栈：
- 运行时: Node.js 20 LTS
- 框架: Express 4.x
- WebSocket: ws / socket.io
- WebRTC: wrtc / node-webrtc
- 图像处理: sharp (JPEG转换)

依赖：
{
  "express": "^4.18.0",
  "ws": "^8.14.0",
  "wrtc": "^0.4.7",
  "sharp": "^0.32.0",
  "axios": "^1.5.0"
}

开发环境：
- Node.js 20+
- npm
- Docker (用于wrtc的依赖)
```

---

### Python AI Service

```python
技术栈：
- 语言: Python 3.10+
- 框架: FastAPI
- AI模型: Qwen2.5-VL / Gemini API
- WebSocket: websockets / FastAPI WebSocket
- gRPC: grpcio
- 图像处理: Pillow
- 深度学习: PyTorch

依赖：
requirements.txt:
fastapi==0.104.0
uvicorn[standard]==0.24.0
websockets==12.0
grpcio==1.59.0
grpcio-tools==1.59.0
torch==2.1.0
transformers==4.35.0
Pillow==10.1.0
opencv-python==4.8.0

可选（本地推理）：
vllm==0.2.0
accelerate==0.24.0

可选（云端API）：
google-generativeai==0.3.0

硬件要求（本地推理）：
- NVIDIA GPU (16GB+ VRAM)
- CUDA 11.8+
- 32GB+ RAM

硬件要求（云端API）：
- 2C4G即可
```

---

### Spring Boot Core Service

```xml
技术栈：
- 语言: Java 17
- 框架: Spring Boot 3.2
- 数据库: PostgreSQL 15
- 缓存: Redis 7 (可选)
- gRPC: grpc-spring-boot-starter
- WebSocket: Spring WebSocket

依赖：
<dependencies>
    <!-- Spring Boot基础 -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-web</artifactId>
    </dependency>
    
    <!-- WebFlux响应式 -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-webflux</artifactId>
    </dependency>
    
    <!-- WebSocket -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-websocket</artifactId>
    </dependency>
    
    <!-- 数据库 -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-data-jpa</artifactId>
    </dependency>
    <dependency>
        <groupId>org.postgresql</groupId>
        <artifactId>postgresql</artifactId>
    </dependency>
    
    <!-- Redis -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-data-redis</artifactId>
    </dependency>
    
    <!-- gRPC -->
    <dependency>
        <groupId>net.devh</groupId>
        <artifactId>grpc-spring-boot-starter</artifactId>
        <version>2.15.0.RELEASE</version>
    </dependency>
    
    <!-- 安全 -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-security</artifactId>
    </dependency>
    
    <!-- JWT -->
    <dependency>
        <groupId>io.jsonwebtoken</groupId>
        <artifactId>jjwt-api</artifactId>
        <version>0.12.0</version>
    </dependency>
</dependencies>

JDK版本：
- Java 17
```

---

### Infrastructure（基础设施）

```yaml
容器化：
- Docker 24+
- Docker Compose 2.x

数据库：
- PostgreSQL 15
  - Extensions: uuid-ossp, pg_trgm

缓存（可选）：
- Redis 7

消息队列（可选，后期扩展）：
- RabbitMQ 3.12 / Kafka 3.5

监控（可选）：
- Prometheus + Grafana
- Jaeger (分布式追踪)

部署：
- 开发环境: docker-compose
- 生产环境: Docker / Kubernetes (后期)
```

---

## 📊 数据模型（Data Models）

### PostgreSQL表结构

```sql
-- 用户表
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 会话表
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    status VARCHAR(20) NOT NULL, -- CREATED, ACTIVE, STOPPED, COMPLETED
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    duration_seconds INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 分析记录表
CREATE TABLE analysis_records (
    id BIGSERIAL PRIMARY KEY,
    session_id UUID REFERENCES sessions(id),
    content TEXT NOT NULL,
    token_index INTEGER, -- 第几个token
    timestamp BIGINT NOT NULL, -- Unix timestamp (ms)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_status ON sessions(status);
CREATE INDEX idx_analysis_session_id ON analysis_records(session_id);
CREATE INDEX idx_analysis_timestamp ON analysis_records(timestamp);
```

---

## 🔄 核心流程（Core Flows）

### 1. 开始录制流程

```
用户 → Frontend: 点击"开始录制"
Frontend → Spring Boot: POST /api/sessions/start
Spring Boot → DB: 创建session记录
Spring Boot → Node.js: 通知准备WebRTC
Spring Boot → Python: 通知初始化模型
Spring Boot → Frontend: 返回sessionId + signalingUrl
Frontend → Node.js: WebSocket建立WebRTC信令
Frontend ↔ Node.js: SDP协商
Frontend ═══ Node.js: WebRTC连接建立
Frontend ═══→ Node.js: 开始传输音视频流
```

### 2. 实时分析流程

```
Node.js: 接收视频流（30fps）
Node.js: 每秒采样1帧
Node.js → Python: WebSocket发送帧(JPEG)
Python: AI模型推理
Python: 流式生成token
Python → Spring Boot: gRPC发送每个token
Spring Boot → DB: 保存token
Spring Boot → Frontend: WebSocket广播token
Frontend: 显示token
(循环进行)
```

### 3. 停止录制流程

```
用户 → Frontend: 点击"停止录制"
Frontend → Spring Boot: POST /api/sessions/{id}/stop
Spring Boot → DB: 更新session状态
Spring Boot → Node.js: 断开连接
Spring Boot → Python: 清理上下文
Spring Boot → DB: 生成报告
Spring Boot → Frontend: 返回完成状态
```

---

## 📁 项目目录结构

```
streammind/
├── frontend/                        # 前端
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   └── utils/
│   ├── package.json
│   └── Dockerfile
│
├── signaling-service/              # Node.js信令服务
│   ├── src/
│   │   ├── server.js
│   │   ├── signaling.js
│   │   ├── webrtc.js
│   │   └── config.js
│   ├── package.json
│   └── Dockerfile
│
├── ai-service/                     # Python AI服务
│   ├── app/
│   │   ├── main.py
│   │   ├── model.py
│   │   ├── websocket_handler.py
│   │   ├── grpc_client.py
│   │   └── context_manager.py
│   ├── proto/
│   │   └── analysis.proto
│   ├── requirements.txt
│   └── Dockerfile
│
├── core-service/                   # Spring Boot核心服务
│   ├── src/main/java/com/streammind/
│   │   ├── StreamMindApplication.java
│   │   ├── controller/
│   │   │   ├── SessionController.java
│   │   │   └── AuthController.java
│   │   ├── service/
│   │   │   ├── SessionService.java
│   │   │   ├── AnalysisService.java
│   │   │   └── UserService.java
│   │   ├── repository/
│   │   ├── grpc/
│   │   │   └── AnalysisGrpcService.java
│   │   ├── websocket/
│   │   │   └── AnalysisWebSocketHandler.java
│   │   └── model/
│   ├── src/main/proto/
│   │   └── analysis.proto
│   ├── pom.xml
│   └── Dockerfile
│
├── proto/                          # 共享的protobuf定义
│   └── analysis.proto
│
├── docker-compose.yml
├── docker-compose.dev.yml
├── .env.example
└── README.md
```
