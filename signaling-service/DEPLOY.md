# Node.js Signaling Service - 服务器部署指南

## 为什么需要部署到服务器？

`wrtc` (WebRTC for Node.js) 包在 **macOS ARM64 (Apple Silicon)** 上没有预编译的二进制文件，导致 `npm install` 失败。

该包在 **Linux x86_64/ARM64** 服务器上可以正常安装和运行。

---

## 部署方式 1：直接部署到 Linux 服务器

### 1. 上传代码到服务器

```bash
# 方式 1：使用 scp
scp -r signaling-service/ user@your-server:/path/to/streammind/

# 方式 2：使用 git
ssh user@your-server
cd /path/to/streammind/
git clone <repo-url>
cd signaling-service
```

### 2. 安装依赖

```bash
# 确保 Node.js 版本 >= 18
node --version

# 安装依赖
npm install
```

如果遇到编译错误，确保安装了必要的构建工具：

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y build-essential python3

# CentOS/RHEL
sudo yum groupinstall "Development Tools"
sudo yum install python3
```

### 3. 配置环境变量

创建 `.env` 文件：

```bash
cat > .env <<EOF
# Spring Boot Core Service URL（如果 Spring Boot 在本地，填写本地 IP）
SPRING_BOOT_API_URL=http://YOUR_LOCAL_IP:8080

# Python AI Service WebSocket URL（如果 Python 在本地，填写本地 IP）
PYTHON_AI_WS_URL=ws://YOUR_LOCAL_IP:8001

# Signaling Service Port
PORT=8002

# Log Level
LOG_LEVEL=info
EOF
```

**注意：** 如果 Spring Boot 和 Python 服务在本地电脑运行，需要：
- 确保服务器能访问你的本地 IP（在同一局域网，或使用 VPN/内网穿透）
- 将 `YOUR_LOCAL_IP` 替换为你的局域网 IP（如 `192.168.1.100`）

### 4. 启动服务

**方式 1：使用 PM2（推荐生产环境）**

```bash
# 安装 PM2
npm install -g pm2

# 启动服务
pm2 start src/server.js --name streammind-signaling

# 查看日志
pm2 logs streammind-signaling

# 查看状态
pm2 status

# 设置开机自启
pm2 startup
pm2 save
```

**方式 2：直接启动（开发/测试）**

```bash
npm start
```

**方式 3：后台运行（使用 nohup）**

```bash
nohup npm start > logs/signaling.log 2>&1 &
```

### 5. 验证服务

```bash
# 检查进程
ps aux | grep node

# 检查端口
netstat -tuln | grep 8002

# 查看日志
pm2 logs streammind-signaling
# 或
tail -f logs/signaling.log
```

---

## 部署方式 2：使用 Docker（推荐）

### 1. 在服务器上构建镜像

```bash
cd signaling-service
docker build -t streammind-signaling .
```

### 2. 运行容器

```bash
docker run -d \
  --name streammind-signaling \
  -p 8002:8002 \
  -e SPRING_BOOT_API_URL="http://YOUR_LOCAL_IP:8080" \
  -e PYTHON_AI_WS_URL="ws://YOUR_LOCAL_IP:8001" \
  -e LOG_LEVEL="info" \
  --restart unless-stopped \
  streammind-signaling
```

### 3. 查看日志

```bash
docker logs -f streammind-signaling
```

---

## 网络配置

### 1. 防火墙开放端口

```bash
# Ubuntu/Debian (ufw)
sudo ufw allow 8002/tcp

# CentOS/RHEL (firewalld)
sudo firewall-cmd --permanent --add-port=8002/tcp
sudo firewall-cmd --reload
```

### 2. 云服务器安全组

如果使用阿里云/腾讯云/AWS等，需要在控制台添加安全组规则：
- **协议**：TCP
- **端口**：8002
- **来源**：0.0.0.0/0（或限制为特定 IP）

### 3. 前端配置

修改前端 `.env.local` 文件，将 signaling URL 指向服务器：

```bash
VITE_SIGNALING_WS_URL=ws://your-server-ip:8002
```

---

## 性能优化

### 1. 使用 Nginx 反向代理（可选）

```nginx
# /etc/nginx/sites-available/streammind-signaling
upstream signaling {
    server 127.0.0.1:8002;
}

server {
    listen 80;
    server_name signaling.yourdomain.com;

    location / {
        proxy_pass http://signaling;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

启用配置：
```bash
sudo ln -s /etc/nginx/sites-available/streammind-signaling /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 2. 配置 HTTPS（推荐）

使用 Let's Encrypt 免费 SSL 证书：

```bash
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d signaling.yourdomain.com
```

修改前端配置：
```bash
VITE_SIGNALING_WS_URL=wss://signaling.yourdomain.com
```

---

## 监控和日志

### 1. PM2 监控

```bash
# 实时监控
pm2 monit

# 查看详细信息
pm2 describe streammind-signaling

# 重启服务
pm2 restart streammind-signaling

# 停止服务
pm2 stop streammind-signaling
```

### 2. 日志轮转

PM2 自带日志轮转：

```bash
pm2 install pm2-logrotate
pm2 set pm2-logrotate:max_size 10M
pm2 set pm2-logrotate:retain 7
```

---

## 故障排查

### 问题 1：npm install 失败

**症状：** `wrtc` 编译错误

**解决方案：**
```bash
# 安装构建工具
sudo apt-get install build-essential python3

# 清理缓存重试
rm -rf node_modules package-lock.json
npm cache clean --force
npm install
```

### 问题 2：服务无法连接到本地 Spring Boot/Python

**症状：** `ECONNREFUSED`

**检查清单：**
1. 本地 IP 是否正确（不要使用 `localhost` 或 `127.0.0.1`）
2. 本地防火墙是否开放端口
3. 服务器能否 ping 通本地 IP
4. 是否在同一局域网（或使用 VPN）

**获取本地 IP：**
```bash
# macOS
ipconfig getifaddr en0

# Linux
hostname -I | awk '{print $1}'
```

### 问题 3：WebSocket 连接失败

**检查：**
```bash
# 测试 WebSocket 连接
wscat -c ws://your-server-ip:8002/signaling/test-session-id
```

如果没有 wscat：
```bash
npm install -g wscat
```

---

## 更新部署

### PM2 方式

```bash
cd signaling-service
git pull  # 或重新上传代码
npm install  # 如果有新依赖
pm2 restart streammind-signaling
```

### Docker 方式

```bash
cd signaling-service
docker build -t streammind-signaling .
docker stop streammind-signaling
docker rm streammind-signaling
docker run -d --name streammind-signaling ... # 使用之前的启动参数
```

---

## 完整部署示例

假设服务器 IP：`123.45.67.89`，本地 IP：`192.168.1.100`

```bash
# 1. 服务器上部署 signaling-service
ssh user@123.45.67.89
cd /opt
git clone <repo-url> streammind
cd streammind/signaling-service

# 2. 安装依赖
npm install

# 3. 配置环境变量
cat > .env <<EOF
SPRING_BOOT_API_URL=http://192.168.1.100:8080
PYTHON_AI_WS_URL=ws://192.168.1.100:8001
PORT=8002
LOG_LEVEL=info
EOF

# 4. 启动服务
npm install -g pm2
pm2 start src/server.js --name streammind-signaling
pm2 save

# 5. 开放防火墙
sudo ufw allow 8002/tcp

# 6. 本地电脑修改 frontend/.env.local
# VITE_SIGNALING_WS_URL=ws://123.45.67.89:8002

# 7. 启动其他服务（在本地电脑）
cd core-service && mvn spring-boot:run  # 终端 1
cd ai-service && uvicorn app.main:app --reload --port 8001  # 终端 2
cd frontend && npm run dev  # 终端 3

# 8. 浏览器访问 http://localhost:5173 测试
```

---

## 总结

- ✅ **推荐方案**：Linux 服务器 + PM2
- ✅ **备选方案**：Docker 容器
- ⚠️ **注意事项**：确保网络连通性（防火墙、安全组、局域网/VPN）
- 📝 **配置要点**：正确填写本地 Spring Boot 和 Python 服务的 IP 地址
