# StreamMind 本地开发环境启动指南

## 🔧 发现的问题和修复

### 1. Spring Boot JWT 问题

**问题**: JJWT 0.12.x API 变化，`parserBuilder()` 已过时

**修复**: 更新 `core-service/src/main/java/com/skiuo/streammind/security/JwtUtil.java`

需要将 `Jwts.parserBuilder()` 改为 `Jwts.parser()`

### 2. gRPC 生成的类缺失

**问题**: `AnalysisServiceGrpc` 等类未生成

**修复**: 需要先编译 protobuf

---

## 🚀 本地启动步骤（不用 docker-compose）

### 前置准备

1. **安装依赖**:
   - Java 17
   - Node.js 20+
   - Python 3.11+
   - Maven
   - Docker (仅用于 PostgreSQL 和 Redis)

2. **获取 Qwen API Key**:
   - 访问 https://dashscope.console.aliyun.com/
   - 创建 API Key

---

### Step 1: 启动基础设施 (PostgreSQL + Redis)

```bash
# 启动 PostgreSQL
docker run -d \
  --name streammind-postgres \
  -e POSTGRES_DB=streammind \
  -e POSTGRES_USER=streammind \
  -e POSTGRES_PASSWORD=streammind_dev_password \
  -p 5432:5432 \
  -v $(pwd)/docker/postgres/init.sql:/docker-entrypoint-initdb.d/init.sql \
  postgres:15-alpine

# 启动 Redis
docker run -d \
  --name streammind-redis \
  -p 6379:6379 \
  redis:7-alpine

# 验证启动
docker ps | grep streammind
```

---

### Step 2: 修复 JWT 代码

编辑 `core-service/src/main/java/com/skiuo/streammind/security/JwtUtil.java`:

```java
// 替换所有 parserBuilder() 为 parser()
// 并修改链式调用

public UUID getUserIdFromToken(String token) {
    Claims claims = Jwts.parser()  // 改这里
        .verifyWith(getSigningKey())  // 改这里
        .build()
        .parseSignedClaims(token)  // 改这里
        .getPayload();

    return UUID.fromString(claims.getSubject());
}

public String getUsernameFromToken(String token) {
    Claims claims = Jwts.parser()
        .verifyWith(getSigningKey())
        .build()
        .parseSignedClaims(token)
        .getPayload();

    return claims.get("username", String.class);
}

public boolean validateToken(String token) {
    try {
        Jwts.parser()
            .verifyWith(getSigningKey())
            .build()
            .parseSignedClaims(token);
        return true;
    } catch (Exception e) {
        return false;
    }
}
```

---

### Step 3: 生成 Protobuf 代码

```bash
# Java (Spring Boot)
cd core-service
mvn protobuf:compile protobuf:compile-custom
cd ..

# 验证生成
ls -l core-service/target/generated-sources/protobuf/

# Python (AI Service)
pip install grpcio-tools  # 如果未安装
mkdir -p ai-service/app/generated
python3 -m grpc_tools.protoc \
    -I./proto \
    --python_out=./ai-service/app/generated \
    --grpc_python_out=./ai-service/app/generated \
    ./proto/analysis.proto

touch ai-service/app/generated/__init__.py

# 验证生成
ls -l ai-service/app/generated/
```

---

### Step 4: 配置环境变量

```bash
# 创建配置文件
cat > core-service/src/main/resources/application-local.yml << 'EOF'
spring:
  application:
    name: core-service

  datasource:
    url: jdbc:postgresql://localhost:5432/streammind
    username: streammind
    password: streammind_dev_password
    driver-class-name: org.postgresql.Driver

  jpa:
    hibernate:
      ddl-auto: validate
    show-sql: true

  data:
    redis:
      host: localhost
      port: 6379

  security:
    jwt:
      secret: dev-secret-key-change-in-production
      expiration: 86400000

server:
  port: 8080

grpc:
  server:
    port: 9090

logging:
  level:
    com.skiuo.streammind: DEBUG
EOF

# Python AI Service 配置
cat > ai-service/.env << 'EOF'
QWEN_API_KEY=你的实际API_KEY
QWEN_API_URL=https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation
SPRING_BOOT_GRPC_HOST=localhost
SPRING_BOOT_GRPC_PORT=9090
PYTHON_SERVICE_PORT=8000
LOG_LEVEL=DEBUG
EOF

# Node.js Signaling Service 配置
cat > signaling-service/.env << 'EOF'
SPRING_BOOT_API_URL=http://localhost:8080
PYTHON_AI_WS_URL=ws://localhost:8000
NODE_SERVICE_PORT=3000
LOG_LEVEL=debug
EOF

# Frontend 配置
cat > frontend/.env.local << 'EOF'
VITE_API_URL=http://localhost:8080
VITE_SIGNALING_WS_URL=ws://localhost:3000
VITE_ANALYSIS_WS_URL=ws://localhost:8080/ws/analysis
EOF
```

---

### Step 5: 启动后端服务

**Terminal 1 - Spring Boot Core Service**:
```bash
cd core-service

# 先编译
mvn clean compile

# 如果有错误，再次生成 protobuf
mvn protobuf:compile protobuf:compile-custom

# 启动
mvn spring-boot:run -Dspring-boot.run.profiles=local
```

**Terminal 2 - Python AI Service**:
```bash
cd ai-service

# 安装依赖
pip install -r requirements.txt

# 启动
uvicorn app.main:app --reload --port 8000
```

**Terminal 3 - Node.js Signaling Service**:
```bash
cd signaling-service

# 安装依赖
npm install

# 启动
npm run dev
```

---

### Step 6: 启动前端

**Terminal 4 - Frontend**:
```bash
cd frontend

# 安装依赖
npm install

# 启动
npm run dev
```

---

## ✅ 验证服务启动

```bash
# 检查 PostgreSQL
docker exec -it streammind-postgres psql -U streammind -d streammind -c "\dt"

# 检查各服务
curl http://localhost:8080/actuator/health  # Spring Boot
curl http://localhost:8000/health           # Python AI
curl http://localhost:3000/health           # Node.js Signaling
curl http://localhost:5173                  # Frontend (浏览器)
```

---

## 🐛 常见问题排查

### 1. Spring Boot 无法启动

**错误**: `找不到符号 AnalysisServiceGrpc`

**解决**:
```bash
cd core-service
mvn protobuf:compile protobuf:compile-custom
mvn clean compile
```

### 2. Python gRPC 导入错误

**错误**: `ModuleNotFoundError: No module named 'generated'`

**解决**:
```bash
cd ai-service
mkdir -p app/generated
python3 -m grpc_tools.protoc -I../proto \
    --python_out=./app/generated \
    --grpc_python_out=./app/generated \
    ../proto/analysis.proto
touch app/generated/__init__.py
```

### 3. JWT 编译错误

**错误**: `找不到符号 parserBuilder()`

**解决**: 按照上面 Step 2 修复 JwtUtil.java

### 4. 数据库连接失败

**检查**:
```bash
docker logs streammind-postgres
docker exec -it streammind-postgres psql -U streammind -d streammind
```

### 5. WebRTC 连接失败

**原因**: 浏览器需要 HTTPS 或 localhost 才能访问摄像头

**解决**: 确保访问 http://localhost:5173

### 6. Qwen API 调用失败

**检查**:
- API Key 是否正确
- 账户余额是否充足
- API 调用配额

---

## 📝 测试流程

1. **访问前端**: http://localhost:5173
2. **注册账号**: 用户名 `test`, 密码 `test123`, 邮箱 `test@test.com`
3. **登录**
4. **点击"开始录制"**
5. **允许摄像头和麦克风权限**
6. **观察**:
   - 左侧视频预览是否正常
   - 右侧 AI 分析是否有 token 流式输出
   - Console 查看 WebSocket 和 WebRTC 连接状态
7. **点击"停止录制"**
8. **查看历史记录**

---

## 🔍 日志查看

```bash
# Spring Boot 日志
cd core-service && mvn spring-boot:run | tee logs/spring-boot.log

# Python 日志
cd ai-service && uvicorn app.main:app --reload 2>&1 | tee logs/python.log

# Node.js 日志
cd signaling-service && npm run dev 2>&1 | tee logs/nodejs.log

# 浏览器 Console
F12 -> Console (查看前端日志和错误)
```

---

## 🎯 下一步

1. ✅ 修复 JWT 代码
2. ✅ 生成 protobuf 代码
3. ✅ 启动所有服务
4. ✅ 测试完整流程
5. 🔧 如有错误，查看日志并修复
