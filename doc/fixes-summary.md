# StreamMind 修复总结

> 日期：2025-10-24
> 会话：完整系统检查和修复

---

## 🔧 修复的核心问题

### 问题 1: Qwen API 返回 "Invalid video file"

**错误信息**:
```
[ERROR] Qwen API: <400> InternalError.Algo.InvalidParameter: Invalid video file.
```

**根本原因**: API 调用格式错误

#### ❌ 错误的代码
```python
# ai-service/app/qwen_client.py (旧版本)
message_content = [
    {"video": video_url},  # 格式不对！
    {"text": prompt}
]
```

#### ✅ 修复后的代码
```python
# ai-service/app/qwen_client.py (最终正确版本)
message_content = [
    {
        "video": video_url  # 不需要 type 字段，直接用 video 作为 key
    },
    {
        "text": prompt
    }
]
```

**参考文档**: https://help.aliyun.com/zh/model-studio/vision

---

### 问题 2: 停止录制后剩余任务分析结果丢失

**症状**: 点击"停止录制"后，队列中未处理的视频不再显示分析结果

**根本原因**: WebSocket 连接过早关闭

#### ❌ 错误逻辑
```typescript
// frontend/src/pages/RecordingPage.tsx (旧版本)
stopRecording() {
  videoRecorderService.stopRecording();
  wsClient.close();  // ❌ 立即关闭，分析结果无法接收
  await sessionAPI.stop(sessionId);
}
```

#### ✅ 修复后的逻辑
```typescript
// frontend/src/pages/RecordingPage.tsx (新版本)
stopRecording() {
  videoRecorderService.stopRecording();
  await sessionAPI.stop(sessionId);

  // 延迟 60 秒关闭 WebSocket，让剩余任务完成
  setTimeout(() => {
    wsClient.close();
  }, 60000);
}
```

---

### 问题 3: ai-service 无法读取 .env 配置

**症状**: Minio 配置未加载，上传失败

**根本原因**:
1. `.env` 文件路径配置错误：`"..env"` → `"../.env"`
2. Pydantic 默认拒绝额外字段

#### ✅ 修复
```python
# ai-service/app/config.py
class Settings(BaseSettings):
    # ... 配置项 ...

    class Config:
        env_file = "../.env"  # 修复路径
        env_file_encoding = 'utf-8'
        extra = 'ignore'  # 忽略其他服务的环境变量
        protected_namespaces = ('settings_',)
```

```python
# ai-service/app/main.py (顶部添加)
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)
```

---

## 📝 其他改进

### 1. 视频格式优化

将 FFmpeg 输出从 WebM 改为 MP4（Qwen API 推荐格式）

```python
# ai-service/app/video_processor.py
# 旧: window_000_0_15.webm
# 新: window_000_0_15.mp4

cmd = [
    'ffmpeg',
    '-i', video_path,
    '-ss', str(start_time),
    '-t', str(duration),
    '-c:v', 'libx264',      # H.264 编码
    '-preset', 'fast',
    '-crf', '23',
    '-an',                  # 跳过音频
    '-movflags', '+faststart',
    '-y',
    output_path
]
```

**注意**: 重新编码比 `-c copy` 慢，但确保视频格式正确。

---

### 2. 错误处理增强

#### 空结果检测
```python
# ai-service/app/main.py
if accumulated_response.strip():
    logger.info(f"Window {window.window_index + 1} analyzed")
else:
    logger.warning(f"Window {window.window_index + 1} returned empty response")
    await grpc_client.save_analysis(
        session_id=session_id,
        content="[警告] 此窗口分析未返回内容\n",
        ...
    )
```

#### API 错误检测
```python
# ai-service/app/qwen_client.py
if "code" in data and data["code"] != "Success":
    error_msg = data.get("message", "Unknown error")
    logger.error(f"Qwen API error: {error_msg}")
    yield f"[ERROR] Qwen API: {error_msg}"
    break
```

---

### 3. 日志增强

添加了更详细的日志输出：

```python
logger.info(f"Sent window marker for window {window.window_index + 1}")
logger.info(f"Window {window.window_index + 1} analyzed: {len(accumulated_response)} chars, {token_count} tokens")
logger.info(f"Window uploaded: {video_url}")
```

---

### 4. Minio 配置补全

在 `.env` 和 `docker-compose.yml` 中添加了 Minio 配置：

```bash
# .env
MINIO_ENDPOINT=https://minio-api.supanx.net
MINIO_BUCKET=test
MINIO_ACCESS_KEY=admin
MINIO_SECRET_KEY=supanX&11
MINIO_PUBLIC_URL=https://minio-api.supanx.net/test/
```

```yaml
# docker-compose.yml
environment:
  MINIO_ENDPOINT: ${MINIO_ENDPOINT}
  MINIO_BUCKET: ${MINIO_BUCKET}
  MINIO_ACCESS_KEY: ${MINIO_ACCESS_KEY}
  MINIO_SECRET_KEY: ${MINIO_SECRET_KEY}
  MINIO_PUBLIC_URL: ${MINIO_PUBLIC_URL}
```

---

## ⚠️ 仍未修复的问题

### 原始视频文件未删除

**位置**: `/tmp/videos/{sessionId}/*.webm`

**问题**: Python 分析完成后，Spring Boot 保存的原始视频片段不会被删除

**建议方案**:
```python
# ai-service/app/main.py:349 后添加
try:
    if Path(video_path).exists():
        Path(video_path).unlink()
        logger.info(f"Deleted original video: {video_path}")
except Exception as e:
    logger.warning(f"Failed to delete original video: {e}")
```

**影响**: 磁盘空间持续增长

---

## 📊 修改文件清单

| 文件 | 修改内容 |
|------|---------|
| `ai-service/app/qwen_client.py` | ✅ 修复 API 调用格式 |
| `ai-service/app/config.py` | ✅ 修复 .env 路径，添加 extra='ignore' |
| `ai-service/app/main.py` | ✅ 显式加载 .env，增强错误处理和日志 |
| `ai-service/app/video_processor.py` | ✅ 改为 MP4 格式，使用 H.264 编码 |
| `ai-service/app/minio_client.py` | ✅ 自动检测 Content-Type |
| `frontend/src/pages/RecordingPage.tsx` | ✅ 延迟关闭 WebSocket |
| `.env` | ✅ 添加 Minio 配置 |
| `docker-compose.yml` | ✅ 传递 Minio 环境变量 |

---

## 🧪 测试步骤

### 1. 重启服务

```bash
# Docker 模式
docker-compose restart ai-service core-service

# 本地开发模式
cd ai-service
source .venv/bin/activate
python3.12 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. 测试录制

1. 打开 http://localhost:5173
2. 登录（如果 token 过期，先 `localStorage.clear()` 然后重新登录）
3. 点击"开始录制"
4. 录制 30 秒左右
5. 点击"停止录制"
6. 观察分析结果是否正常显示

### 3. 检查日志

```bash
# Python AI 日志
docker logs -f streammind-ai | grep -E "Window|analyzed|Minio|Qwen API"

# Spring Boot 日志
docker logs -f streammind-core | grep -E "session|video|Worker"
```

### 4. 预期结果

✅ 每个窗口应该显示完整的分析结果
✅ 不应再出现 "Invalid video file" 错误
✅ 停止录制后仍能接收剩余任务的分析结果

---

## 📚 新增文档

1. **`doc/video-lifecycle.md`** - 视频生命周期完整文档
2. **`frontend/debug-auth.html`** - 认证诊断工具
3. **`doc/fixes-summary.md`** - 本文档

---

## 🎯 下次优化建议

1. **实现原始视频清理** - 避免磁盘空间耗尽
2. **添加重试机制** - Qwen API 调用失败时自动重试
3. **优化 FFmpeg 参数** - 根据实际需求调整编码质量和速度
4. **添加进度指示** - 显示当前正在处理第几个窗口
5. **实现会话历史查看** - 用户可以查看之前的录制分析结果

---

**修复完成时间**: 2025-10-24
**修复者**: Claude Code
