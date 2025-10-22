## 架构：Spring Boot + 多技术栈混合

```
                    ┌─────────────────────┐
                    │   Spring Boot       │
                    │   (业务中枢)          │
                    │  - 会话管理          │
                    │  - 任务调度          │
                    │  - API网关           │
                    │  - 数据持久化         │
                    └──────────┬──────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
   ┌────▼────┐          ┌────▼────┐           ┌────▼────┐
   │ Python  │          │  Node.js│           │  Go     │
   │ 视觉分析 │          │ WebRTC  │           │ 流处理   │
   │ 服务     │          │ 信令服务 │           │ 服务     │
   └─────────┘          └─────────┘           └─────────┘
```

---

## 具体技术栈分工

### 1. **Spring Boot（核心控制层）**

**职责**：

- ✅ 业务逻辑协调
- ✅ 会话生命周期管理
- ✅ REST API提供
- ✅ 数据库操作（PostgreSQL）
- ✅ 用户认证与授权
- ✅ 任务调度与队列管理
- ✅ WebSocket信令转发

**技术栈**：

- Spring Boot 3.x
- Spring WebFlux (响应式)
- Spring Data JPA
- Spring Security
- Redis (缓存/队列)
- RabbitMQ/Kafka (消息队列)

**核心代码结构**：

```java
@RestController
@RequestMapping("/api/sessions")
public class SessionController {
    
    @Autowired
    private SessionService sessionService;
    
    @Autowired
    private PythonAIClient pythonAIClient;
    
    @Autowired
    private NodeSignalingClient nodeClient;
    
    @PostMapping("/start")
    public ResponseEntity<SessionResponse> startSession(@RequestBody StartRequest req) {
        // 1. 创建会话
        Session session = sessionService.createSession(req);
        
        // 2. 通知Node.js准备WebRTC
        nodeClient.setupWebRTC(session.getId());
        
        // 3. 通知Python准备AI模型
        pythonAIClient.initializeModel(session.getId());
        
        return ResponseEntity.ok(new SessionResponse(session));
    }
}
```

---

### 2. **Python服务（AI视觉分析层）**

**职责**：

- ✅ AI模型推理（Qwen/Gemini）
- ✅ 视频帧分析
- ✅ 音频转文字
- ✅ 实时流式输出

**技术栈**：

```python
- FastAPI (高性能异步)
- Transformers (Hugging Face)
- vLLM (推理加速)
- OpenCV (图像处理)
- PyTorch
```

**服务实现**：

```python
# ai_service.py
from fastapi import FastAPI, WebSocket
from transformers import Qwen2_5_VLForConditionalGeneration
import asyncio

app = FastAPI()
model = Qwen2_5_VLForConditionalGeneration.from_pretrained("Qwen2.5-VL-7B")

@app.websocket("/ws/analyze/{session_id}")
async def analyze_stream(websocket: WebSocket, session_id: str):
    await websocket.accept()
    
    while True:
        # 接收来自Spring Boot的帧数据
        frame_data = await websocket.receive_bytes()
        
        # AI分析
        analysis = model.analyze(frame_data, stream=True)
        
        # 流式返回结果
        for token in analysis:
            await websocket.send_text(token)
            
            # 同时发送回Spring Boot记录
            await notify_spring_boot(session_id, token)
```

**与Spring Boot通信（gRPC）**：

```python
# grpc_client.py
import grpc
from generated import analysis_pb2, analysis_pb2_grpc

async def notify_spring_boot(session_id: str, analysis: str):
    channel = grpc.aio.insecure_channel('spring-boot-host:9090')
    stub = analysis_pb2_grpc.AnalysisServiceStub(channel)
    
    await stub.SaveAnalysis(analysis_pb2.AnalysisRequest(
        session_id=session_id,
        content=analysis,
        timestamp=int(time.time() * 1000)
    ))
```

---

### 3. **Node.js服务（WebRTC信令层）**

**职责**：

- ✅ WebRTC信令服务器
- ✅ 视频流接收与转发
- ✅ 实时通信（低延迟）

**技术栈**：

```javascript
- Express/Nest.js
- Socket.io / ws (WebSocket)
- mediasoup (WebRTC媒体服务器)
```

**服务实现**：

```javascript
// signaling_server.js
const express = require('express');
const { Server } = require('socket.io');
const axios = require('axios');

const app = express();
const io = new Server(app);

io.on('connection', (socket) => {
  let sessionId = null;
  
  socket.on('start-session', async (data) => {
    sessionId = data.sessionId;
    
    // 通知Spring Boot会话开始
    await axios.post('http://spring-boot:8080/internal/session/connected', {
      sessionId,
      socketId: socket.id
    });
  });
  
  socket.on('video-frame', async (frameData) => {
    // 转发帧到Python AI服务
    await forwardToPython(sessionId, frameData);
  });
});

async function forwardToPython(sessionId, frameData) {
  const ws = new WebSocket(`ws://python-ai:8000/ws/analyze/${sessionId}`);
  ws.send(frameData);
  
  ws.on('message', (analysis) => {
    // 收到AI分析，发回Spring Boot
    axios.post('http://spring-boot:8080/internal/analysis/save', {
      sessionId,
      analysis
    });
  });
}
```

---

### 4. **Go服务（高性能流处理层，可选）**

**职责**：

- ✅ 视频流编解码
- ✅ 高并发流转发
- ✅ 媒体格式转换

**技术栈**：

```go
- Gin/Echo
- Pion (Go WebRTC)
- FFmpeg binding
```

**服务实现**：

```go
// stream_processor.go
package main

import (
    "github.com/gin-gonic/gin"
    "github.com/pion/webrtc/v3"
)

func main() {
    r := gin.Default()
    
    r.POST("/process-stream", func(c *gin.Context) {
        sessionId := c.Param("sessionId")
        
        // 创建WebRTC连接
        peerConnection, _ := webrtc.NewPeerConnection(webrtc.Configuration{})
        
        peerConnection.OnTrack(func(track *webrtc.TrackRemote, receiver *webrtc.RTPReceiver) {
            // 处理视频轨道
            go processVideoTrack(sessionId, track)
        })
    })
    
    r.Run(":8082")
}

func processVideoTrack(sessionId string, track *webrtc.TrackRemote) {
    for {
        rtp, _ := track.ReadRTP()
        
        // 发送到Python分析
        sendToPythonService(sessionId, rtp.Payload)
    }
}
```

---

## 微服务间通信方式

### 通信协议选择

|场景|推荐协议|理由|
|---|---|---|
|**Spring Boot ↔ Python**|gRPC|高性能二进制，类型安全|
|**Spring Boot ↔ Node.js**|REST + WebSocket|简单灵活|
|**Node.js ↔ Python**|WebSocket|实时流式通信|
|**Go ↔ Python**|gRPC|高性能|
|**异步任务**|RabbitMQ/Kafka|解耦，可靠|

---

### 具体实现：gRPC通信

**1. 定义protobuf（共享协议）**

```protobuf
// analysis.proto
syntax = "proto3";

service AnalysisService {
  rpc SaveAnalysis(AnalysisRequest) returns (AnalysisResponse);
  rpc GetAnalysis(GetAnalysisRequest) returns (stream AnalysisChunk);
}

message AnalysisRequest {
  string session_id = 1;
  string content = 2;
  int64 timestamp = 3;
}

message AnalysisResponse {
  bool success = 1;
  string message = 2;
}
```

**2. Spring Boot gRPC服务端**

```java
// AnalysisGrpcService.java
@GrpcService
public class AnalysisGrpcService extends AnalysisServiceGrpc.AnalysisServiceImplBase {
    
    @Autowired
    private AnalysisRepository analysisRepository;
    
    @Override
    public void saveAnalysis(AnalysisRequest request, 
                            StreamObserver<AnalysisResponse> responseObserver) {
        
        // 保存到数据库
        Analysis analysis = new Analysis();
        analysis.setSessionId(request.getSessionId());
        analysis.setContent(request.getContent());
        analysis.setTimestamp(new Date(request.getTimestamp()));
        
        analysisRepository.save(analysis);
        
        // 响应
        AnalysisResponse response = AnalysisResponse.newBuilder()
            .setSuccess(true)
            .setMessage("Saved")
            .build();
        
        responseObserver.onNext(response);
        responseObserver.onCompleted();
    }
}
```

**3. Python gRPC客户端**

```python
# grpc_client.py
import grpc
from generated import analysis_pb2, analysis_pb2_grpc

class SpringBootClient:
    def __init__(self):
        self.channel = grpc.insecure_channel('spring-boot:9090')
        self.stub = analysis_pb2_grpc.AnalysisServiceStub(self.channel)
    
    async def save_analysis(self, session_id: str, content: str):
        request = analysis_pb2.AnalysisRequest(
            session_id=session_id,
            content=content,
            timestamp=int(time.time() * 1000)
        )
        
        response = await self.stub.SaveAnalysis(request)
        return response.success
```

---

## 完整数据流

```
1. 用户请求
   iPhone → Spring Boot REST API (/api/sessions/start)
        ↓
   Spring Boot创建Session，返回sessionId

2. 建立WebRTC连接
   iPhone → Node.js信令服务器 (WebSocket)
        ↓
   Node.js通知Spring Boot连接建立 (REST)

3. 视频流处理
   iPhone WebRTC流 → Node.js
        ↓
   提取帧 → Python AI服务 (WebSocket)
        ↓
   AI分析结果 → Spring Boot (gRPC)
        ↓
   Spring Boot保存到PostgreSQL

4. 实时推送
   Spring Boot → WebSocket → 前端显示

5. 查询历史
   前端 → Spring Boot REST API → PostgreSQL → 返回记录
```

---

## Docker Compose编排

```yaml
version: '3.8'

services:
  # Spring Boot核心服务
  spring-boot:
    build: ./spring-boot-app
    ports:
      - "8080:8080"
      - "9090:9090"  # gRPC端口
    environment:
      - SPRING_PROFILES_ACTIVE=prod
      - POSTGRES_HOST=postgres
      - REDIS_HOST=redis
    depends_on:
      - postgres
      - redis
    networks:
      - app-network

  # Python AI服务
  python-ai:
    build: ./python-ai-service
    ports:
      - "8000:8000"
    environment:
      - MODEL_PATH=/models/qwen2.5-vl-7b
      - SPRING_BOOT_HOST=spring-boot
      - SPRING_BOOT_GRPC_PORT=9090
    volumes:
      - ./models:/models
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    networks:
      - app-network

  # Node.js信令服务
  node-signaling:
    build: ./node-signaling-server
    ports:
      - "3000:3000"
    environment:
      - SPRING_BOOT_URL=http://spring-boot:8080
      - PYTHON_AI_URL=ws://python-ai:8000
    networks:
      - app-network

  # Go流处理服务（可选）
  go-stream:
    build: ./go-stream-processor
    ports:
      - "8082:8082"
    environment:
      - PYTHON_AI_URL=python-ai:8000
    networks:
      - app-network

  # PostgreSQL数据库
  postgres:
    image: postgres:15
    ports:
      - "5432:5432"
    environment:
      - POSTGRES_DB=recording_db
      - POSTGRES_USER=admin
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres-data:/var/lib/postgresql/data
    networks:
      - app-network

  # Redis缓存
  redis:
    image: redis:7
    ports:
      - "6379:6379"
    networks:
      - app-network

  # RabbitMQ消息队列
  rabbitmq:
    image: rabbitmq:3-management
    ports:
      - "5672:5672"
      - "15672:15672"
    networks:
      - app-network

volumes:
  postgres-data:

networks:
  app-network:
    driver: bridge
```

---

## 项目目录结构

```
project-root/
├── spring-boot-app/              # Spring Boot核心
│   ├── src/main/java/
│   │   ├── controller/
│   │   ├── service/
│   │   ├── repository/
│   │   ├── grpc/                 # gRPC服务
│   │   └── client/               # 调用其他服务的客户端
│   ├── src/main/proto/           # protobuf定义
│   └── pom.xml
│
├── python-ai-service/            # Python AI服务
│   ├── app/
│   │   ├── main.py
│   │   ├── ai_model.py
│   │   └── grpc_client.py
│   ├── requirements.txt
│   └── Dockerfile
│
├── node-signaling-server/        # Node.js信令
│   ├── src/
│   │   ├── index.js
│   │   ├── signaling.js
│   │   └── websocket.js
│   ├── package.json
│   └── Dockerfile
│
├── go-stream-processor/          # Go流处理（可选）
│   ├── main.go
│   ├── stream.go
│   └── Dockerfile
│
├── proto/                        # 共享protobuf
│   └── analysis.proto
│
├── docker-compose.yml
└── README.md
```

