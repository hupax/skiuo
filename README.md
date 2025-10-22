# StreamMind

**AI-powered real-time activity recording system** that captures video and audio through a web browser, performs real-time AI analysis, and generates coherent text descriptions.

## 🎯 Overview

StreamMind uses a microservices architecture to:
- Capture video/audio via WebRTC from browser
- Extract frames and forward to AI analysis
- Generate streaming text descriptions using Qwen Vision AI
- Save and broadcast analysis results in real-time

## 🏗️ Architecture

```
React Frontend (WebRTC)
    ↓ WebSocket + WebRTC
Node.js Signaling (Frame extraction)
    ↓ WebSocket              ↓ REST
Python AI Service ←───→ Spring Boot Core
    (Qwen API)         (gRPC)   (Database + WebSocket)
```

### Services

1. **core-service** (Spring Boot 3.5.6, Java 17)
   - REST API for session management
   - gRPC server for receiving AI analysis
   - WebSocket broadcasting to frontend
   - PostgreSQL persistence
   - JWT authentication

2. **ai-service** (Python 3.11, FastAPI)
   - Qwen-VL-Max API integration
   - Streaming token generation
   - gRPC client to Spring Boot
   - Session context management

3. **signaling-service** (Node.js 20)
   - WebRTC signaling server
   - Video frame extraction (1fps)
   - Forward frames to Python AI
   - Notify Spring Boot of events

4. **frontend** (React 18, Vite) - *To be implemented*
   - WebRTC client
   - Real-time video preview
   - Streaming text display
   - Session management UI

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Java 17 (for local dev)
- Node.js 20+ (for local dev)
- Python 3.11+ (for local dev)
- Qwen API Key from [DashScope](https://dashscope.console.aliyun.com/)

### Setup

1. **Clone and configure**:
   ```bash
   cd skiuo
   cp .env.example .env
   # Edit .env and add your QWEN_API_KEY
   ```

2. **Generate protobuf code**:

   **For Java (core-service)**:
   ```bash
   cd core-service
   mvn protobuf:compile protobuf:compile-custom
   cd ..
   ```

   **For Python (ai-service)**:
   ```bash
   mkdir -p ai-service/app/generated
   python3 -m grpc_tools.protoc \
       -I./proto \
       --python_out=./ai-service/app/generated \
       --grpc_python_out=./ai-service/app/generated \
       ./proto/analysis.proto
   touch ai-service/app/generated/__init__.py
   ```

3. **Start with Docker Compose**:
   ```bash
   docker-compose up
   ```

4. **Access the application**:
   - Spring Boot API: http://localhost:8080
   - Python AI Service: http://localhost:8000
   - Node.js Signaling: http://localhost:3000
   - PostgreSQL: localhost:5432
   - Redis: localhost:6379

### Development Mode

For development with hot-reload:

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

Includes:
- pgAdmin: http://localhost:5050 (admin@streammind.dev / admin)
- Redis Commander: http://localhost:8081
- Hot-reload for all services

## 📋 API Endpoints

### Authentication

```bash
# Register
POST /api/auth/register
Content-Type: application/json

{
  "username": "user",
  "email": "user@example.com",
  "password": "password123"
}

# Login
POST /api/auth/login
Content-Type: application/json

{
  "username": "user",
  "password": "password123"
}
```

### Sessions

```bash
# Start recording
POST /api/sessions/start
Authorization: Bearer <token>
Content-Type: application/json

{
  "title": "Coding Session",
  "description": "Algorithm practice"
}

# Stop recording
POST /api/sessions/{id}/stop
Authorization: Bearer <token>

# Get session details
GET /api/sessions/{id}
Authorization: Bearer <token>

# List user sessions
GET /api/sessions
Authorization: Bearer <token>
```

## 🔧 Development

### Run Services Locally

**Infrastructure (PostgreSQL + Redis)**:
```bash
docker-compose -f docker-compose.dev.yml up
```

**Core Service (Spring Boot)**:
```bash
cd core-service
mvn spring-boot:run
```

**AI Service (Python)**:
```bash
cd ai-service
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**Signaling Service (Node.js)**:
```bash
cd signaling-service
npm install
npm run dev
```

## 📊 Database Schema

- **users**: User accounts with BCrypt hashed passwords
- **sessions**: Recording sessions (CREATED → ACTIVE → STOPPED → COMPLETED)
- **analysis_records**: AI-generated tokens with timestamps and indices

Default admin user:
- Username: `admin`
- Password: `admin123` (change this!)

## 🔐 Environment Variables

See `.env.example` for all configuration options.

Critical variables:
- `QWEN_API_KEY`: **Required** for AI analysis
- `JWT_SECRET`: Change in production!
- `POSTGRES_PASSWORD`: Change in production!

## 🐛 Troubleshooting

**Protobuf compilation errors**:
```bash
# Install required tools
mvn --version  # Ensure Maven is installed
pip install grpcio-tools  # For Python
```

**Docker build fails**:
```bash
# Clean and rebuild
docker-compose down -v
docker-compose build --no-cache
docker-compose up
```

**Database connection errors**:
```bash
# Check if PostgreSQL is ready
docker-compose logs postgres
# Ensure core-service waits for postgres health check
```

**Qwen API errors**:
- Verify API key in `.env`
- Check API quota at DashScope console
- Review logs: `docker-compose logs ai-service`

**WebSocket connection issues**:
- Check CORS settings in SecurityConfig.java
- Verify WebSocket path: `/ws/analysis/{sessionId}`
- Check browser console for errors

## 📝 Project Structure

```
skiuo/
├── doc/                      # Design documents
│   ├── dev1.md              # Initial architecture
│   ├── dev2.md              # Final architecture
│   └── prompt.md            # Design notes
├── proto/                    # Shared protobuf definitions
│   └── analysis.proto
├── docker/                   # Docker initialization
│   └── postgres/init.sql
├── core-service/            # Spring Boot backend
│   ├── src/main/java/com/skiuo/streammind/
│   │   ├── controller/
│   │   ├── service/
│   │   ├── repository/
│   │   ├── model/
│   │   ├── dto/
│   │   ├── grpc/
│   │   ├── websocket/
│   │   └── security/
│   ├── pom.xml
│   └── Dockerfile
├── ai-service/              # Python AI service
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── qwen_client.py
│   │   ├── grpc_client.py
│   │   └── context_manager.py
│   ├── requirements.txt
│   └── Dockerfile
├── signaling-service/       # Node.js WebRTC
│   ├── src/
│   │   ├── server.js
│   │   ├── signaling.js
│   │   ├── frame-extractor.js
│   │   ├── config.js
│   │   └── logger.js
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
├── docker-compose.dev.yml
├── .env.example
├── CLAUDE.md                # AI assistant instructions
└── README.md
```

## 🎓 Technical Stack

| Component | Technology |
|-----------|-----------|
| Backend API | Spring Boot 3.5.6, Java 17 |
| AI Service | Python 3.11, FastAPI |
| Signaling | Node.js 20, Express, WebSocket |
| Frontend | React 18, Vite (TODO) |
| Database | PostgreSQL 15 |
| Cache | Redis 7 |
| AI Model | Alibaba Qwen-VL-Max API |
| Communication | REST, WebSocket, gRPC, WebRTC |
| Container | Docker, Docker Compose |

## 📈 Current Status

✅ **Completed**:
- Spring Boot REST API with JWT authentication
- PostgreSQL schema and JPA entities
- gRPC server for receiving AI analysis
- WebSocket broadcasting for real-time tokens
- Python FastAPI service with Qwen API integration
- Node.js WebRTC signaling server
- Docker Compose orchestration
- Development environment setup

⏳ **In Progress / TODO**:
- React frontend implementation
- Actual WebRTC frame extraction (currently mock)
- Frontend WebSocket client
- End-to-end testing
- Production deployment configuration

## 🚧 Known Limitations

1. **Frame Extraction**: The Node.js service has a mock frame extractor. Real implementation requires:
   - Proper RTP packet handling
   - Video decoding (ffmpeg integration)
   - Or using a media server like Mediasoup

2. **Frontend**: React frontend is not yet implemented

3. **Authentication**: Currently basic JWT. Consider adding:
   - Refresh tokens
   - OAuth2 support
   - Rate limiting

## 📄 License

MIT

## 🙏 Acknowledgments

- Design based on requirements in `doc/dev2.md`
- AI model powered by Alibaba Cloud DashScope Qwen-VL-Max
- Evolved from original `coding-recorder` project

---

For detailed architecture and design decisions, see:
- `/doc/dev1.md` - Initial multi-language design
- `/doc/dev2.md` - Final simplified architecture
- `/doc/prompt.md` - Design evolution notes
