# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**StreamMind** is an AI-powered activity recording system that captures video through a web browser, performs AI analysis using sliding window technique, and generates coherent text descriptions of user activities. Suitable for coding sessions, crafting, cooking tutorials, and any process that needs documentation.

**Current Status**: Implemented - Core services are functional. See `/doc/dev3.md` for current architecture.

## Project Evolution

The project evolved through multiple design iterations:
- `/doc/prompt.md` - Navigation guide between design versions
- `/doc/dev1.md` - Initial multi-language architecture design (Spring Boot + Python + Node.js + Go)
- `/doc/dev2.md` - WebRTC-based design (实时截图方案，已废弃)
- `/doc/dev3.md` - **Current architecture** (视频上传 + 滑动窗口分析方案)

## Architecture (Current Implementation - dev3.md)

### Multi-Service Architecture

```
Web Frontend (React + MediaRecorder)
    ↓ 30秒视频片段上传
Spring Boot Core (业务中枢)
    ↓ 任务队列调度
Python AI Service (视频分析)
    ↓ 滑动窗口切片 → Minio → Qwen-VL
    ↓ 流式返回结果
Spring Boot → WebSocket → Frontend
```

### Service Responsibilities

1. **Frontend** (`frontend/`): React app with MediaRecorder API, records 30-second video chunks, uploads to Spring Boot
2. **Spring Boot Core** (`core-service/`): REST API, session management, task queue, gRPC server, WebSocket broadcasting, PostgreSQL persistence
3. **Python AI** (`ai-service/`): FastAPI service, video sliding window processing, Qwen-VL API integration, streaming analysis, Minio storage

### Technology Stack

- **Frontend**: React 19, MediaRecorder API, WebSocket, Axios
- **Spring Boot**: Java 17, Spring Boot 3.5, PostgreSQL 15, Redis, WebSocket, gRPC, WebFlux
- **Python**: FastAPI, Qwen-VL-Max API, FFmpeg, boto3 (Minio/S3), grpcio

### Communication Protocols

- Frontend → Spring Boot: HTTP POST (video upload) + REST API (session management)
- Spring Boot ↔ Python: gRPC (bidirectional streaming)
- Python → Minio: S3-compatible API (temporary video storage)
- Python → Qwen API: HTTP streaming (AI analysis)
- Spring Boot → Frontend: WebSocket (streaming tokens)

## Directory Structure

```
streammind/
├── frontend/              # React frontend (MediaRecorder video capture)
├── ai-service/           # Python AI analysis service (FastAPI + Qwen + FFmpeg)
├── core-service/         # Spring Boot core service (gRPC + REST + WebSocket)
├── proto/                # Shared protobuf definitions (gRPC interfaces)
├── doc/                  # Design documents (dev3.md is current)
├── docker/               # Docker configs (PostgreSQL init scripts)
├── docker-compose.yml    # Production deployment
└── .env.example          # Environment variable template
```

## Database Schema

### PostgreSQL Tables

- **users**: id, username, email, password_hash, created_at, updated_at
- **sessions**: id, user_id, status, start_time, end_time, duration_seconds, title, description
- **analysis_records**: id, session_id, content, token_index, timestamp, created_at

## Core Workflows (Implemented)

### Start Recording Flow
1. User clicks "Start Recording" in frontend
2. Frontend → Spring Boot: `POST /api/sessions/start`
3. Spring Boot creates session, returns session_id
4. Frontend starts MediaRecorder, records 30-second chunks

### Video Upload & Analysis Flow
1. Frontend uploads 30-second video → Spring Boot: `POST /api/videos/{sessionId}/upload`
2. Spring Boot saves video temporarily, creates task in queue
3. Worker thread calls Python AI: `POST /analyze-video` with video path
4. Python AI:
   - Slices video with sliding window (15s window, 10s step)
   - Uploads each window to Minio
   - Sends video URL to Qwen-VL API for analysis
   - Streams tokens back via gRPC
   - Deletes Minio files after analysis
5. Spring Boot receives tokens via gRPC, saves to database, broadcasts to frontend
6. Frontend displays tokens in real-time via WebSocket

### Stop Recording Flow
1. User clicks "Stop Recording"
2. Frontend → Spring Boot: `POST /api/sessions/{id}/stop`
3. Spring Boot updates session status, waits for pending tasks
4. Frontend can view full analysis history

## Key Implementation Details

### Video Processing (Python AI Service)

- **Sliding Window**: 15-second windows with 10-second step (5-second overlap)
- **FFmpeg**: Extracts video windows without re-encoding
- **Minio Storage**: Temporary upload to get public URLs for Qwen API
- **Context Management**: Maintains conversation history for coherent analysis

### AI Analysis (Qwen-VL Integration)

- **Model**: qwen-vl-max (Alibaba Cloud DashScope API)
- **Streaming**: Uses SSE (Server-Sent Events) with `incremental_output: true`
- **Input**: Accepts both HTTP URLs (from Minio) and local file:// paths
- **Prompt**: Custom prompts for maintaining context across windows

### gRPC Communication

- **Service**: AnalysisService with SaveAnalysis and GetAnalysis RPCs
- **Bidirectional Streaming**: Python → Spring Boot for real-time token delivery
- **Proto Definition**: `/proto/analysis.proto`

### Storage

- **PostgreSQL**: Session metadata and analysis records
- **Minio**: Temporary video window storage (S3-compatible)
- **File System**: Local temp_windows for video processing

## Common Commands

```bash
# Start all services with Docker Compose
docker-compose up

# Run Python AI service (development)
cd ai-service
python3.12 -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run Spring Boot service (development)
cd core-service
export QWEN_API_KEY=your-key
mvn spring-boot:run

# Run Frontend (development)
cd frontend
npm install
npm run dev

# Build core-service
cd core-service
mvn clean package
```

## Environment Variables

Required environment variables (see `.env.example`):

```bash
# Qwen API
QWEN_API_KEY=sk-your-api-key

# Minio (S3-compatible storage)
MINIO_ENDPOINT=https://minio-api.supanx.net
MINIO_BUCKET=test
MINIO_ACCESS_KEY=your-access-key
MINIO_SECRET_KEY=your-secret-key
MINIO_PUBLIC_URL=https://minio-api.supanx.net/test/

# Security
JWT_SECRET=your-jwt-secret
POSTGRES_PASSWORD=your-postgres-password

# Database
POSTGRES_DB=streammind
POSTGRES_USER=streammind

# Ports (optional)
CORE_SERVICE_PORT=8080
GRPC_PORT=9090
AI_SERVICE_PORT=8000
```

## Important Notes

- Project follows **dev3.md architecture** (video upload + sliding window analysis)
- **Not real-time**: Accepts 30s-2min delay for quality analysis
- **No video storage**: Videos are deleted after analysis (MVP)
- **Minio required**: For temporary video storage accessible by Qwen API
- **Python 3.12**: Required for AI service
- **FFmpeg**: Must be installed on system for video processing
