# StreamMind - Server Deployment Guide

## Quick Deploy Script

复制以下内容到服务器并执行：

```bash
#!/bin/bash
set -e

echo "=== StreamMind Server Deployment ==="
echo ""

# 1. Install dependencies
echo "[1/6] Installing system dependencies..."
sudo apt update
sudo apt install -y docker.io docker-compose git openjdk-17-jdk python3 python3-pip nodejs npm maven
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER

# 2. Clone repository
echo "[2/6] Cloning repository..."
cd ~
git clone <your-repo-url> skiuo
cd skiuo

# 3. Configure environment
echo "[3/6] Configuring environment..."
cp .env.example .env
echo "⚠️  Please edit .env and add your QWEN_API_KEY"
echo "   nano .env"
read -p "Press Enter after editing .env..."

# 4. Start infrastructure
echo "[4/6] Starting PostgreSQL and Redis..."
docker-compose up -d postgres redis
sleep 10

# 5. Generate protobuf
echo "[5/6] Generating protobuf code..."
cd core-service
mvn protobuf:compile protobuf:compile-custom
cd ..

mkdir -p ai-service/app/generated/proto
python3 -m grpc_tools.protoc \
    -I./proto \
    --python_out=./ai-service/app/generated \
    --grpc_python_out=./ai-service/app/generated \
    ./proto/analysis.proto
touch ai-service/app/generated/__init__.py
touch ai-service/app/generated/proto/__init__.py

# 6. Install dependencies
echo "[6/6] Installing service dependencies..."
cd ai-service && pip3 install -r requirements.txt && cd ..
cd signaling-service && npm install && cd ..
cd frontend && npm install && npm run build && cd ..

# 7. Install and configure PM2
echo "Installing PM2..."
sudo npm install -g pm2

# 8. Start services
echo "Starting services with PM2..."
cd ~/skiuo/core-service
pm2 start "mvn spring-boot:run" --name streammind-core --log ~/logs/core.log

cd ~/skiuo/ai-service
pm2 start "uvicorn app.main:app --host 0.0.0.0 --port 8000" --name streammind-ai --log ~/logs/ai.log

cd ~/skiuo/signaling-service
pm2 start src/server.js --name streammind-signaling --log ~/logs/signaling.log

pm2 save
pm2 startup

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📊 Check service status:"
echo "   pm2 status"
echo ""
echo "📝 View logs:"
echo "   pm2 logs streammind-core"
echo "   pm2 logs streammind-ai"
echo "   pm2 logs streammind-signaling"
echo ""
echo "🌐 Access:"
echo "   Spring Boot API: http://$(curl -s ifconfig.me):8080"
echo "   Python AI Docs:  http://$(curl -s ifconfig.me):8000/docs"
echo "   Frontend:        http://$(curl -s ifconfig.me):5173"
echo ""
```

## Manual Deployment Steps

如果自动脚本失败，可以手动执行：

### 1. 安装依赖

```bash
sudo apt update
sudo apt install -y docker.io docker-compose git \
    openjdk-17-jdk python3 python3-pip nodejs npm maven

# 启动 Docker
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER
newgrp docker
```

### 2. 克隆代码

```bash
cd ~
git clone <your-repo-url> skiuo
cd skiuo
```

### 3. 配置环境变量

```bash
cp .env.example .env
nano .env
```

**必须配置的变量：**
```bash
QWEN_API_KEY=sk-your-api-key-here
POSTGRES_PASSWORD=your-secure-password
JWT_SECRET=your-jwt-secret-at-least-32-chars
```

### 4. 启动基础设施

```bash
docker-compose up -d postgres redis
docker ps  # 验证容器运行
```

### 5. 生成 Protobuf 代码

```bash
# Java
cd core-service
mvn protobuf:compile protobuf:compile-custom
cd ..

# Python
mkdir -p ai-service/app/generated/proto
python3 -m grpc_tools.protoc \
    -I./proto \
    --python_out=./ai-service/app/generated \
    --grpc_python_out=./ai-service/app/generated \
    ./proto/analysis.proto
touch ai-service/app/generated/__init__.py
touch ai-service/app/generated/proto/__init__.py
```

### 6. 安装依赖

```bash
# Python
cd ai-service
pip3 install -r requirements.txt
cd ..

# Node.js
cd signaling-service
npm install
cd ..

# Frontend
cd frontend
npm install
npm run build
cd ..
```

### 7. 使用 PM2 启动服务

```bash
# 安装 PM2
sudo npm install -g pm2

# 创建日志目录
mkdir -p ~/logs

# 启动 Spring Boot
cd ~/skiuo/core-service
pm2 start "mvn spring-boot:run" --name streammind-core

# 启动 Python AI
cd ~/skiuo/ai-service
pm2 start "uvicorn app.main:app --host 0.0.0.0 --port 8000" --name streammind-ai

# 启动 Node.js Signaling
cd ~/skiuo/signaling-service
pm2 start src/server.js --name streammind-signaling

# 保存 PM2 配置
pm2 save
pm2 startup  # 按提示执行命令以设置开机启动
```

### 8. 配置 Nginx（可选但推荐）

```bash
sudo apt install -y nginx

sudo nano /etc/nginx/sites-available/streammind
```

**Nginx 配置：**
```nginx
server {
    listen 80;
    server_name your-domain.com;

    # Frontend
    location / {
        root /home/username/skiuo/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # Spring Boot API
    location /api {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # WebSocket
    location /ws {
        proxy_pass http://localhost:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }

    # Signaling
    location /signaling {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Python AI Docs
    location /ai-docs {
        proxy_pass http://localhost:8000/docs;
    }
}
```

**启用配置：**
```bash
sudo ln -s /etc/nginx/sites-available/streammind /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 9. 配置防火墙

```bash
# 允许 HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# 如果不使用 Nginx，允许服务端口
sudo ufw allow 8080/tcp  # Spring Boot
sudo ufw allow 8000/tcp  # Python AI
sudo ufw allow 3000/tcp  # Node.js Signaling
sudo ufw allow 5173/tcp  # Frontend dev

sudo ufw enable
sudo ufw status
```

## 验证部署

```bash
# 检查服务状态
pm2 status

# 查看日志
pm2 logs

# 测试 API
curl http://localhost:8080/actuator/health
curl http://localhost:8000/health

# 检查数据库
docker exec -it streammind-postgres psql -U streammind -d streammind -c '\dt'
```

## 更新部署

```bash
cd ~/skiuo
git pull

# 重启服务
pm2 restart all

# 如果有代码更改，可能需要
cd frontend && npm run build && cd ..
pm2 restart streammind-core
```

## 监控和维护

```bash
# 实时监控
pm2 monit

# 查看详细信息
pm2 describe streammind-core

# 查看日志（实时）
pm2 logs --lines 100

# 清理日志
pm2 flush

# 重启特定服务
pm2 restart streammind-ai
```

## 故障排查

### 服务无法启动

```bash
# 检查端口占用
lsof -i :8080
lsof -i :8000
lsof -i :3000

# 检查日志
pm2 logs streammind-core --lines 50
```

### 数据库连接失败

```bash
# 检查容器
docker ps
docker logs streammind-postgres

# 测试连接
docker exec -it streammind-postgres psql -U streammind -d streammind
```

### Protobuf 错误

```bash
# 重新生成
cd core-service && mvn clean && mvn protobuf:compile protobuf:compile-custom
cd ../ai-service && rm -rf app/generated && cd ..
# 重新运行 protoc 命令
```

## 生产环境优化

### 1. 使用生产配置

编辑 `core-service/src/main/resources/application.yml`：
```yaml
spring:
  profiles:
    active: prod
  jpa:
    show-sql: false
logging:
  level:
    root: WARN
    com.skiuo: INFO
```

### 2. 配置 HTTPS (Let's Encrypt)

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

### 3. 配置日志轮转

```bash
pm2 install pm2-logrotate
pm2 set pm2-logrotate:max_size 10M
pm2 set pm2-logrotate:retain 7
```

### 4. 数据库备份

```bash
# 创建备份脚本
cat > ~/backup-db.sh <<'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
docker exec streammind-postgres pg_dump -U streammind streammind > ~/backups/streammind_$DATE.sql
find ~/backups -name "streammind_*.sql" -mtime +7 -delete
EOF

chmod +x ~/backup-db.sh

# 添加到 crontab (每天凌晨2点备份)
(crontab -l 2>/dev/null; echo "0 2 * * * ~/backup-db.sh") | crontab -
```

## 安全建议

1. **更改默认密码**: 修改 `.env` 中的 `POSTGRES_PASSWORD` 和 `JWT_SECRET`
2. **限制端口访问**: 使用 Nginx 作为反向代理，不直接暴露服务端口
3. **配置 HTTPS**: 使用 Let's Encrypt 免费证书
4. **定期更新**: `sudo apt update && sudo apt upgrade`
5. **配置防火墙**: 只开放必要的端口 (80, 443)
6. **监控日志**: 定期检查 `pm2 logs` 查找异常

## 回滚

```bash
cd ~/skiuo
git log --oneline  # 查看提交历史
git checkout <commit-hash>  # 回滚到特定版本
pm2 restart all
```
