# StreamMind

AI-powered real-time activity recording system with video analysis using Qwen-VL-Max.

## Architecture

```
Browser (React + WebRTC)
    ↓ WebSocket/REST
Node.js Signaling ←→ Python AI (Qwen-VL) ←→ Spring Boot Core
    ↓ WebSocket           ↓ gRPC              ↓ PostgreSQL + Redis
```

## Server Deployment

### 1. Prerequisites

```bash
# On Ubuntu/Debian server
sudo apt update
sudo apt install -y docker docker-compose git openjdk-17-jdk python3 python3-pip nodejs npm

# Verify installations
docker --version
java -version
python3 --version
node --version
```

### 2. Deploy

```bash
# Clone repository
git clone <repo-url>
cd skiuo

# Configure environment
cp .env.example .env
nano .env  # Add your QWEN_API_KEY

# Start infrastructure
docker-compose up -d postgres redis

# Generate protobuf (first time only)
cd core-service && mvn protobuf:compile protobuf:compile-custom && cd ..
mkdir -p ai-service/app/generated/proto
python3 -m grpc_tools.protoc -I./proto \
  --python_out=./ai-service/app/generated \
  --grpc_python_out=./ai-service/app/generated \
  ./proto/analysis.proto
touch ai-service/app/generated/__init__.py
touch ai-service/app/generated/proto/__init__.py

# Install Python dependencies
cd ai-service && pip3 install -r requirements.txt && cd ..

# Install Node.js dependencies
cd signaling-service && npm install && cd ..

# Install frontend dependencies
cd frontend && npm install && npm run build && cd ..
```

### 3. Start Services (using PM2)

```bash
# Install PM2
npm install -g pm2

# Start Spring Boot
cd core-service
pm2 start "mvn spring-boot:run" --name streammind-core

# Start Python AI
cd ../ai-service
pm2 start "uvicorn app.main:app --host 0.0.0.0 --port 8000" --name streammind-ai

# Start Node.js Signaling
cd ../signaling-service
pm2 start src/server.js --name streammind-signaling

# Save PM2 configuration
pm2 save
pm2 startup
```

### 4. Configure Nginx (Optional)

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # Frontend
    location / {
        root /path/to/skiuo/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # Spring Boot API
    location /api {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # WebSocket
    location /ws {
        proxy_pass http://localhost:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Signaling
    location /signaling {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### 5. Access

- Frontend: http://your-server-ip (or http://your-domain.com)
- Spring Boot API: http://your-server-ip:8080
- Python AI Docs: http://your-server-ip:8000/docs

## Environment Variables

Key variables in `.env`:

```bash
# Required - Get from https://dashscope.console.aliyun.com/
QWEN_API_KEY=sk-your-api-key-here

# Database
POSTGRES_PASSWORD=your-secure-password
DATABASE_URL=jdbc:postgresql://localhost:5432/streammind

# JWT Secret (change in production!)
JWT_SECRET=your-secret-key-at-least-32-characters-long

# Service URLs (adjust for your setup)
SPRING_BOOT_GRPC_HOST=localhost
SPRING_BOOT_GRPC_PORT=9090
PYTHON_SERVICE_PORT=8000
```

## API Endpoints

### Authentication
```bash
# Register
POST /api/auth/register
{"username": "user", "email": "user@example.com", "password": "password123"}

# Login (returns JWT)
POST /api/auth/login
{"username": "user", "password": "password123"}
```

### Sessions
```bash
# Start recording
POST /api/sessions/start
Authorization: Bearer <token>
{"title": "Coding Session", "description": "Algorithm practice"}

# Stop recording
POST /api/sessions/{id}/stop
Authorization: Bearer <token>

# List sessions
GET /api/sessions
Authorization: Bearer <token>

# Get analysis
GET /api/sessions/{id}/analysis
Authorization: Bearer <token>
```

### WebSocket
```
ws://your-server/ws/analysis/{sessionId}
```

## Tech Stack

- **Backend**: Spring Boot 3.5 + Java 17
- **AI Service**: FastAPI + Python 3.12 + Qwen-VL-Max
- **Signaling**: Node.js 20 + Express + WebRTC
- **Frontend**: React 19 + TypeScript + Vite
- **Database**: PostgreSQL 15 + Redis 7
- **Communication**: REST + WebSocket + gRPC

## Management Commands

```bash
# Check service status
pm2 status

# View logs
pm2 logs streammind-core
pm2 logs streammind-ai
pm2 logs streammind-signaling

# Restart services
pm2 restart all

# Stop services
pm2 stop all

# Delete services
pm2 delete all
```

## Troubleshooting

**Q: Qwen API errors?**
```bash
# Check API key
echo $QWEN_API_KEY

# View Python logs
pm2 logs streammind-ai
```

**Q: Database connection errors?**
```bash
# Check PostgreSQL
docker logs streammind-postgres
docker exec -it streammind-postgres psql -U streammind -d streammind -c '\dt'
```

**Q: Port already in use?**
```bash
# Find process using port
lsof -i :8080
lsof -i :8000
lsof -i :3000

# Kill process
kill -9 <PID>
```

**Q: Frontend build fails?**
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
npm run build
```

## Project Structure

```
skiuo/
├── core-service/         # Spring Boot backend
├── ai-service/          # Python AI service
├── signaling-service/   # Node.js WebRTC signaling
├── frontend/            # React frontend
├── proto/              # Protobuf definitions
├── docker/             # Database init scripts
├── doc/                # Design documents
├── docker-compose.yml  # Infrastructure
└── .env               # Configuration
```

## License

MIT
