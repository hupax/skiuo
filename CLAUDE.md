# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**StreamMind** is an AI-powered real-time activity recording system that captures video and audio through a web browser, performs real-time AI analysis, and generates coherent text descriptions of user activities. Suitable for coding sessions, crafting, cooking tutorials, and any process that needs documentation.

**Current Status**: Design/Planning Phase - Core architecture documents exist in `/doc`, but implementation has not yet begun.

## Project Evolution

The project evolved from an initial RTMP-based design (`coding-recorder`) to a more sophisticated WebRTC-based architecture (`StreamMind`). Key design documents:
- `/doc/prompt.md` - Navigation guide between design versions
- `/doc/dev1.md` - Initial multi-language architecture design (Spring Boot + Python + Node.js + Go)
- `/doc/dev2.md` - Final simplified architecture design

## Architecture (Final Design - dev2.md)

### Multi-Service Architecture

```
Web Frontend (React + WebRTC)
    ↓
Node.js Signaling Service (WebRTC signaling + frame extraction)
    ↓
    ├─→ Spring Boot Core (Business logic + API + Data persistence)
    └─→ Python AI Service (Vision/Audio analysis + Streaming output)
```

### Service Responsibilities

1. **Frontend** (`streammind-frontend`): React app with WebRTC client, real-time video preview, streaming text display
2. **Node.js Signaling** (`signaling-service`): WebRTC signaling server, receives video streams, extracts frames, forwards to AI
3. **Python AI** (`ai-service`): FastAPI service with Qwen2.5-VL or Gemini API, generates streaming analysis, maintains context
4. **Spring Boot Core** (`core-service`): REST API, session management, gRPC server, WebSocket broadcasting, PostgreSQL persistence

### Technology Stack

- **Frontend**: React 18, native WebRTC API, Tailwind CSS, Vite
- **Node.js**: Express 4.x, ws/socket.io, wrtc, sharp
- **Python**: FastAPI, Qwen2.5-VL/Gemini, PyTorch, grpcio, websockets
- **Spring Boot**: Java 17, Spring Boot 3.2, PostgreSQL 15, Redis (optional), WebSocket, gRPC

### Communication Protocols

- Frontend ↔ Node.js: WebRTC + WebSocket (signaling)
- Node.js ↔ Python: WebSocket (frame data)
- Python → Spring Boot: gRPC (analysis results)
- Spring Boot → Frontend: WebSocket (streaming tokens)
- Frontend → Spring Boot: REST API (session management)

## Planned Directory Structure

```
streammind/
├── frontend/              # React frontend
├── signaling-service/     # Node.js WebRTC signaling
├── ai-service/           # Python AI analysis service
├── core-service/         # Spring Boot core service
├── proto/                # Shared protobuf definitions
├── doc/                  # Design documents
├── docker-compose.yml
└── docker-compose.dev.yml
```

## Database Schema (Planned)

### PostgreSQL Tables

- **users**: id, username, email, password_hash, created_at, updated_at
- **sessions**: id, user_id, status, start_time, end_time, duration_seconds
- **analysis_records**: id, session_id, content, token_index, timestamp

## Core Workflows (Planned)

### Start Recording Flow
1. User clicks "Start Recording" in frontend
2. Frontend → Spring Boot: `POST /api/sessions/start`
3. Spring Boot creates session, notifies Node.js and Python services
4. Frontend establishes WebRTC connection via Node.js signaling
5. Video/audio streaming begins

### Real-time Analysis Flow
1. Node.js receives video stream (30fps), samples 1 frame/second
2. Node.js → Python: Sends JPEG frame via WebSocket
3. Python AI performs inference, generates streaming tokens
4. Python → Spring Boot: Sends each token via gRPC
5. Spring Boot saves token to database + broadcasts to frontend via WebSocket
6. Frontend displays token in real-time

### Stop Recording Flow
1. User clicks "Stop Recording"
2. Frontend → Spring Boot: `POST /api/sessions/{id}/stop`
3. Spring Boot updates session status, notifies services
4. Report generation and cleanup

## Development Guidelines

### When Starting Implementation

1. **Infrastructure First**: Set up Docker Compose with PostgreSQL and Redis
2. **Service Order**: Implement in this order:
   - Spring Boot Core (database models, basic REST API)
   - Python AI Service (model loading, basic inference)
   - Node.js Signaling (WebRTC setup)
   - Frontend (UI + WebRTC client)
3. **Inter-service Communication**: Define protobuf schema first, generate code for all services
4. **Testing Strategy**: Test each service independently before integration

### Key Implementation Points

- **Async Processing**: All video/AI processing must be non-blocking
- **Context Management**: Python service maintains per-session conversation history
- **Resource Cleanup**: Ensure proper WebRTC connection and model resource cleanup
- **Error Handling**: Implement reconnection logic for WebSocket/WebRTC failures
- **Streaming**: Use generator/yield patterns for AI token streaming

## Commands (Planned)

Once implementation begins, common commands will be:

```bash
# Start all services
docker-compose up

# Development mode
docker-compose -f docker-compose.dev.yml up

# Run specific service
cd core-service && mvn spring-boot:run
cd ai-service && uvicorn app.main:app --reload
cd signaling-service && npm run dev
cd frontend && npm run dev
```

## Environment Variables (Planned)

Required environment variables for each service documented in `.env.example`:
- `QWEN_API_KEY` or `GEMINI_API_KEY` (for AI service)
- `DATABASE_URL` (PostgreSQL connection)
- `REDIS_URL` (optional, for caching)
- `JWT_SECRET` (for authentication)

## Important Notes

- This is a **design-phase project** - no code has been implemented yet
- The `/doc` directory contains the complete architecture and requirements
- Original RTMP-based design was superseded by WebRTC architecture
- Focus is on **real-time streaming** and **contextual AI analysis**
- Target use cases: coding documentation, tutorial recording, process documentation
