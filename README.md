# StreamMind

AI-powered real-time activity recording system with video analysis using Qwen-VL-Max.

## Architecture

```
Browser (React + WebRTC)
    ↓ WebSocket/REST
Node.js Signaling ←→ Python AI (Qwen-VL) ←gRPC→ Spring Boot Core
    ↓ WebSocket           ↓ HTTP               ↓ JDBC/Redis
                                            PostgreSQL + Redis
```

### Services

- **core-service**: Spring Boot 3.5 + Java 17 (REST API, gRPC Server, WebSocket, JWT Auth)
- **ai-service**: Python 3.12 + FastAPI (Qwen-VL-Max Integration, Streaming Analysis)
- **signaling-service**: Node.js 20 (WebRTC Signaling, Frame Extraction) - *Deployed separately*
- **frontend**: React 19 + TypeScript + Vite

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Qwen API Key from [DashScope](https://dashscope.console.aliyun.com/)

### Deploy

```bash
# 1. Clone and configure
git clone <repo-url>
cd skiuo
cp .env.example .env
nano .env  # Set QWEN_API_KEY, JWT_SECRET, POSTGRES_PASSWORD

# 2. Start services
docker-compose up -d

# 3. Check logs
docker-compose logs -f

# 4. Verify
curl http://localhost:8080/actuator/health
curl http://localhost:8000/health
```

## Environment Variables

Minimal required configuration in `.env`:

```bash
# Required
QWEN_API_KEY=sk-your-api-key-here
JWT_SECRET=$(openssl rand -base64 32)
POSTGRES_PASSWORD=$(openssl rand -base64 16)

# Optional (defaults provided)
LOG_LEVEL=INFO
SPRING_PROFILES_ACTIVE=prod
```

## API Endpoints

### Authentication
```bash
# Register
POST /api/auth/register
{"username": "user", "email": "user@example.com", "password": "password123"}

# Login
POST /api/auth/login
{"username": "user", "password": "password123"}
```

### Sessions
```bash
# Start recording
POST /api/sessions/start
Authorization: Bearer <token>
{"title": "Session", "description": "Description"}

# Stop recording
POST /api/sessions/{id}/stop

# Get sessions
GET /api/sessions

# Get analysis
GET /api/sessions/{id}/analysis
```

### WebSocket
```
ws://localhost:8080/ws/analysis/{sessionId}
```

## Docker Services

| Service | Container | Ports | Purpose |
|---------|-----------|-------|---------|
| PostgreSQL | streammind-postgres | 5432 | Database |
| Redis | streammind-redis | 6379 | Cache |
| Spring Boot | streammind-core | 8080, 9090 | API + gRPC |
| Python AI | streammind-ai | 8000 | AI Analysis |

### Service Communication

- **Python → Spring Boot**: gRPC (`core-service:9090`)
- **Spring Boot → PostgreSQL**: JDBC (`postgres:5432`)
- **Spring Boot → Redis**: Redis Protocol (`redis:6379`)
- **External → Services**: Via Caddy proxy

### Logs

All services configured with JSON logging and automatic rotation:

```bash
# View logs
docker-compose logs -f core-service
docker-compose logs -f ai-service

# Tail last 100 lines
docker-compose logs --tail=100 core-service
```

**Log Rotation:**
- PostgreSQL/Redis: 10MB × 3 files
- Spring Boot/Python: 50MB × 5 files

## Caddy Configuration

Example `Caddyfile`:

```caddy
api.yourdomain.com {
    handle /api/* {
        reverse_proxy localhost:8080
    }

    handle /ws/* {
        reverse_proxy localhost:8080
    }

    handle /health {
        reverse_proxy localhost:8080
    }
}
```

## Management

```bash
# View status
docker-compose ps

# View resource usage
docker stats streammind-core streammind-ai

# Update deployment
git pull
docker-compose up -d --build

# Backup database
docker exec streammind-postgres pg_dump -U streammind streammind > backup.sql

# Clean up
docker-compose down
docker-compose down -v  # ⚠️  Deletes data
```

## Troubleshooting

**Services won't start:**
```bash
docker-compose logs <service-name>
docker-compose build --no-cache <service-name>
```

**Service communication fails:**
```bash
docker exec streammind-ai ping core-service
docker exec streammind-core ping postgres
```

**Database connection error:**
```bash
docker-compose logs postgres
docker exec streammind-postgres pg_isready -U streammind
```

**Python gRPC connection error:**
```bash
docker exec streammind-core netstat -tuln | grep 9090
docker exec streammind-ai ls -la /app/app/generated/
```

## Development

All code is containerized. For local development:

```bash
# Rebuild after code changes
docker-compose up -d --build core-service
docker-compose up -d --build ai-service

# Enter container
docker exec -it streammind-core sh
docker exec -it streammind-ai bash
```

## Documentation

- **DEPLOY.md**: Complete deployment guide with Caddy config, backup, monitoring
- **CLAUDE.md**: AI assistant instructions for code maintenance
- **doc/**: Architecture design documents

## Tech Stack

- Spring Boot 3.5 + Java 17
- Python 3.12 + FastAPI
- PostgreSQL 15 + Redis 7
- Docker + Docker Compose
- Qwen-VL-Max API
- gRPC + WebSocket + REST

## License

MIT
