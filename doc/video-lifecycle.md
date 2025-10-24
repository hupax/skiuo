# StreamMind 视频生命周期与删除逻辑文档

> 最后更新：2025-10-24

本文档详细说明 StreamMind 项目中视频文件从录制到删除的完整生命周期。

---

## 📊 概览：视频文件的生命周期

```
用户点击"开始录制"
    ↓
前端录制 30s 视频片段 (WebM)
    ↓
上传到 Spring Boot
    ↓
保存到 /tmp/videos/{sessionId}/video_{timestamp}.webm  [原始片段]
    ↓
加入任务队列
    ↓
Worker 线程取出任务
    ↓
调用 Python AI 服务分析
    ↓
Python: FFmpeg 切片为滑动窗口 → ./temp_windows/{sessionId}/window_*.webm  [窗口文件]
    ↓
Python: 上传窗口到 Minio → https://minio-api.supanx.net/test/videos/{uuid}_{filename}  [临时URL]
    ↓
Python: Qwen-VL 分析 (使用 Minio URL)
    ↓
分析完成后清理:
    ├─ 删除 Minio 上的窗口文件  ✅
    ├─ 删除本地窗口文件  ✅
    └─ 原始片段文件 /tmp/videos/{sessionId}/*  ⚠️ 当前未删除！
```

---

## 🔄 完整流程详解

### 1️⃣ 前端：点击"开始录制"

**文件**: `frontend/src/pages/RecordingPage.tsx:32-90`

#### 步骤流程

```typescript
startRecording() {
  // 1. 创建会话
  const session = await sessionAPI.start('录制会话', 'AI视频分析');
  // → POST /api/sessions/start
  // → 返回 { id, userId, status: 'ACTIVE', startTime, ... }

  // 2. 获取摄像头权限
  const stream = await navigator.mediaDevices.getUserMedia({
    video: { width: 1280, height: 720, frameRate: 30 },
    audio: false
  });

  // 3. 初始化录制服务
  videoRecorderService = new VideoRecorderService();
  await videoRecorderService.initialize(stream, {
    sessionId: session.id,
    segmentDuration: 30000,  // 30 秒一个片段
    onUploadSuccess: (res) => setUploadedSegments(prev => prev + 1)
  });

  videoRecorderService.startRecording();
  // → 启动 MediaRecorder，每 30 秒自动停止并上传

  // 4. 连接 WebSocket 接收分析结果
  wsClient.connect(session.id, (token) => {
    setTokens(prev => [...prev, token]);
  });
}
```

---

### 2️⃣ 前端：视频片段录制与上传

**文件**: `frontend/src/services/video-recorder.ts`

#### 录制逻辑

```typescript
class VideoRecorderService {
  private startSegment() {
    // 1. 创建 MediaRecorder (WebM 格式, VP8 编码)
    this.mediaRecorder = new MediaRecorder(this.mediaStream, {
      mimeType: 'video/webm;codecs=vp8,opus',
      videoBitsPerSecond: 2500000  // 2.5 Mbps
    });

    // 2. 收集数据
    this.mediaRecorder.ondataavailable = (event) => {
      this.recordedChunks.push(event.data);
    };

    // 3. 片段完成时处理
    this.mediaRecorder.onstop = () => {
      this.handleSegmentComplete();
    };

    this.mediaRecorder.start();

    // 4. 设置 30 秒定时器
    setTimeout(() => this.stopSegment(), 30000);
  }

  private async handleSegmentComplete() {
    const blob = new Blob(this.recordedChunks, { type: 'video/webm' });

    // 上传到服务器
    await this.uploadSegment(blob, segmentIndex);

    // 如果还在录制，继续下一个片段
    if (this.isRecording) {
      this.segmentIndex++;
      this.startSegment();  // 递归录制下一个片段
    }
  }

  private async uploadSegment(blob: Blob, index: number) {
    const formData = new FormData();
    formData.append('video', blob, `segment_${index}.webm`);

    // POST /api/videos/{sessionId}/upload
    await api.post(`/api/videos/${sessionId}/upload`, formData);
  }
}
```

**关键点**：
- ✅ 每 30 秒自动录制一个片段
- ✅ 片段录制完成后**立即上传**
- ✅ 上传成功后继续录制下一个片段（循环）
- ✅ 停止录制时会完成当前片段的上传

---

### 3️⃣ Spring Boot：接收视频并入队

**文件**: `core-service/src/main/java/.../controller/VideoUploadController.java:46-114`

#### 处理流程

```java
@PostMapping("/{sessionId}/upload")
public ResponseEntity uploadVideo(UUID userId, UUID sessionId, MultipartFile videoFile) {
    // 1. 验证会话
    if (!sessionService.existsAndBelongsToUser(sessionId, userId)) {
        return ResponseEntity.notFound().build();
    }

    // 2. 创建会话专用目录
    Path sessionDir = Paths.get("/tmp/videos", sessionId.toString());
    Files.createDirectories(sessionDir);

    // 3. 保存视频文件（带时间戳避免冲突）
    String filename = String.format("video_%d.webm", System.currentTimeMillis());
    Path filePath = sessionDir.resolve(filename);
    Files.copy(videoFile.getInputStream(), filePath, REPLACE_EXISTING);

    // 示例路径：/tmp/videos/abc-123-def/video_1729758000000.webm

    // 4. 创建任务并加入队列
    taskQueueService.enqueueVideoAnalysisTask(sessionId, filePath.toString());

    return ResponseEntity.ok(/* 成功响应 */);
}
```

**文件存储位置**：
- **目录**: `/tmp/videos/{sessionId}/`
- **命名**: `video_{timestamp}.webm`
- **示例**: `/tmp/videos/abc-123-def/video_1729758123456.webm`

**任务队列**：
- 使用 `LinkedBlockingQueue<VideoAnalysisTask>`
- 多个片段会按顺序排队
- 2个 Worker 线程并发处理（可配置）

---

### 4️⃣ Spring Boot Worker：处理任务队列

**文件**: `core-service/src/main/java/.../worker/VideoProcessingWorker.java:61-134`

#### Worker 循环

```java
private void workerLoop(int workerId) {
    while (running) {
        // 1. 从队列取任务（阻塞）
        VideoAnalysisTask task = taskQueueService.dequeueTask();

        // 2. 调用 Python AI 服务
        processVideoTask(workerId, task);
    }
}

private void processVideoTask(int workerId, VideoAnalysisTask task) {
    WebClient client = WebClient.builder()
        .baseUrl("http://ai-service:8000")
        .build();

    // 构建请求
    Map<String, String> body = Map.of(
        "session_id", task.getSessionId().toString(),
        "video_path", task.getVideoPath()  // /tmp/videos/{sessionId}/video_*.webm
    );

    // POST /analyze-video (阻塞等待完成，最多 10 分钟)
    String response = client.post()
        .uri("/analyze-video")
        .bodyValue(body)
        .retrieve()
        .bodyToMono(String.class)
        .timeout(Duration.ofMinutes(10))
        .block();
}
```

**关键点**：
- ✅ Worker 会阻塞等待 Python 分析完成（最多10分钟）
- ✅ 2个 Worker 可以并发处理 2 个视频片段
- ⚠️ **分析完成后不删除原始视频文件** `/tmp/videos/{sessionId}/*`

---

### 5️⃣ Python AI：视频分析与文件管理

**文件**: `ai-service/app/main.py:195-349`

#### 完整分析流程

```python
@app.post("/analyze-video")
async def analyze_video(request: VideoAnalysisRequest):
    session_id = request.session_id
    video_path = request.video_path
    # 示例：/tmp/videos/abc-123/video_1729758123456.webm

    # ========================================
    # 步骤 1: FFmpeg 切片为滑动窗口
    # ========================================
    windows = video_processor.slice_video_with_sliding_window(
        video_path,
        session_id
    )
    # 生成文件示例：
    # ./temp_windows/abc-123/window_000_0_15.webm  (0-15秒)
    # ./temp_windows/abc-123/window_001_10_25.webm (10-25秒)
    # ./temp_windows/abc-123/window_002_20_30.webm (20-30秒)

    # ========================================
    # 步骤 2: 逐个窗口分析
    # ========================================
    uploaded_urls = []  # 记录 Minio URL 用于清理

    for window in windows:
        # 2.1 发送窗口标记到前端
        marker = f"\n\n📹 [分析窗口 {window.window_index + 1}/{len(windows)}]\n"
        await grpc_client.save_analysis(session_id, marker, token_index)

        # 2.2 上传窗口到 Minio
        video_url = minio_client.upload_video(window.file_path)
        uploaded_urls.append(video_url)
        # 示例 URL: https://minio-api.supanx.net/test/videos/a1b2c3d4_window_000_0_15.webm

        # 2.3 Qwen-VL 分析（使用 Minio URL）
        async for token in qwen_client.analyze_video_streaming(
            video_path=video_url,  # 传递 Minio URL
            start_time=window.start_time,
            end_time=window.end_time,
            context=context,
            previous_summary=previous_summary
        ):
            # 2.4 流式发送 token 到 Spring Boot → WebSocket → 前端
            await grpc_client.save_analysis(session_id, token, token_index)
            token_index += 1

    # ========================================
    # 步骤 3: 清理 Minio 临时文件
    # ========================================
    logger.info(f"Cleaning up {len(uploaded_urls)} files from Minio...")
    for url in uploaded_urls:
        minio_client.delete_video(url)
    # ✅ 删除：https://minio-api.supanx.net/test/videos/*.webm

    # ========================================
    # 步骤 4: 清理本地窗口文件
    # ========================================
    video_processor.cleanup_windows(session_id)
    # ✅ 删除：./temp_windows/{sessionId}/ 整个目录

    return VideoAnalysisResponse(
        session_id=session_id,
        total_windows=len(windows),
        status="completed"
    )
```

---

## 🗑️ 文件删除逻辑详解

### ✅ 已实现的删除

#### 1. Minio 临时文件（已删除）

**位置**: `ai-service/app/main.py:336-342`

```python
# 分析完成后立即删除
for url in uploaded_urls:
    try:
        minio_client.delete_video(url)
        # 删除：https://minio-api.supanx.net/test/videos/{uuid}_{filename}
    except Exception as e:
        logger.warning(f"Failed to delete Minio file {url}: {e}")
```

**删除时机**: 所有窗口分析完成后
**删除内容**: 上传到 Minio 的所有窗口视频文件
**状态**: ✅ 正常工作

---

#### 2. 本地窗口文件（已删除）

**位置**: `ai-service/app/main.py:344-348`

```python
try:
    video_processor.cleanup_windows(session_id)
    # 删除目录：./temp_windows/{sessionId}/
except Exception as e:
    logger.warning(f"Failed to cleanup local windows: {e}")
```

**实现代码**: `ai-service/app/video_processor.py:203-217`

```python
def cleanup_windows(self, session_id: str):
    session_dir = self.output_dir / session_id
    # ./temp_windows/{sessionId}/

    if session_dir.exists():
        import shutil
        shutil.rmtree(session_dir)  # 递归删除整个目录
        logger.info(f"Cleaned up windows for session: {session_id}")
```

**删除时机**: 所有窗口分析完成后
**删除内容**: `./temp_windows/{sessionId}/` 整个目录及所有窗口文件
**状态**: ✅ 正常工作

---

### ⚠️ 未实现的删除（问题）

#### 3. Spring Boot 原始视频片段（未删除）

**存储位置**: `/tmp/videos/{sessionId}/video_*.webm`

**当前状态**: ⚠️ **分析完成后不会删除！**

**影响**：
- 每次录制会积累大量视频文件
- 占用服务器磁盘空间
- 需要手动清理或定期清理脚本

**文件示例**：
```
/tmp/videos/abc-123-def/
  ├── video_1729758000000.webm  (30s 视频片段 #1)
  ├── video_1729758030000.webm  (30s 视频片段 #2)
  ├── video_1729758060000.webm  (30s 视频片段 #3)
  └── ...
```

**建议修复方案**：

**方案 1**: Python 分析完成后通知 Spring Boot 删除原始文件

```python
# ai-service/app/main.py:349 后添加
try:
    # 通知 Spring Boot 删除原始视频
    response = httpx.post(
        f"{spring_boot_url}/api/videos/{session_id}/cleanup",
        json={"video_path": video_path}
    )
except Exception as e:
    logger.warning(f"Failed to cleanup original video: {e}")
```

**方案 2**: Python 分析完成后直接删除（需要挂载共享目录）

```python
# ai-service/app/main.py:349 后添加
try:
    if Path(video_path).exists():
        Path(video_path).unlink()
        logger.info(f"Deleted original video: {video_path}")
except Exception as e:
    logger.warning(f"Failed to delete original video: {e}")
```

**方案 3**: 会话结束时批量清理

```java
// SessionService.java:stopSession() 中添加
public Session stopSession(UUID sessionId) {
    // ... existing code ...

    // 清理视频文件
    cleanupSessionVideos(sessionId);

    return saved;
}

private void cleanupSessionVideos(UUID sessionId) {
    Path sessionDir = Paths.get(videoStorageDir, sessionId.toString());
    try {
        Files.walk(sessionDir)
            .sorted(Comparator.reverseOrder())
            .forEach(path -> {
                try { Files.delete(path); }
                catch (IOException e) { /* log */ }
            });
    } catch (IOException e) {
        log.error("Failed to cleanup videos for session {}", sessionId, e);
    }
}
```

---

## 🔍 当前问题分析

### 问题 1: 原始视频文件未删除

**症状**: `/tmp/videos/` 目录持续增长
**原因**: 没有清理逻辑
**优先级**: 🔴 高（影响磁盘空间）

---

### 问题 2: 停止录制后剩余任务可能丢失分析结果

**症状**: 点击"停止录制"后，队列中的视频不再显示分析结果
**原因**: WebSocket 提前关闭（已在本次修复）
**状态**: ✅ 已修复（延迟 60 秒关闭 WebSocket）

---

### 问题 3: 窗口 2/3 分析结果为空

**症状**: 部分窗口返回空白
**可能原因**:
1. Qwen API 对视频内容返回空结果
2. API 调用失败但未正确捕获错误
3. 视频窗口内容重复导致 AI 认为无新内容

**状态**: ✅ 已增强错误检测和日志

---

## 📝 文件清理时序图

```
时间线 →

[前端录制 30s]
    ↓
[上传片段] → /tmp/videos/{sessionId}/video_1.webm  📁 保存
    ↓
[入队列]
    ↓
[Worker 取任务]
    ↓
[Python 接收] → video_path = /tmp/videos/{sessionId}/video_1.webm
    ↓
[FFmpeg 切片] → ./temp_windows/{sessionId}/window_*.webm  📁 创建
    ↓
[上传 Minio] → https://minio-api.supanx.net/test/videos/xxx.webm  ☁️ 上传
    ↓
[Qwen 分析] (使用 Minio URL)
    ↓
[分析完成]
    ├─ 删除 Minio 文件  ☁️ ✅ 删除
    ├─ 删除本地窗口    📁 ✅ 删除 ./temp_windows/{sessionId}/
    └─ 原始片段？      📁 ❌ 未删除 /tmp/videos/{sessionId}/video_1.webm

[下一个片段上传...] 循环
```

---

## 🎯 建议的改进优先级

### P0 - 紧急

1. **实现原始视频文件清理**
   - 避免磁盘空间耗尽
   - 推荐使用"方案 2"（Python 直接删除）

### P1 - 重要

2. **添加磁盘空间监控**
   - 定期检查 `/tmp/videos` 大小
   - 超过阈值时发出警告

3. **添加定时清理任务**
   - 每天清理超过 24 小时的视频文件
   - 作为兜底方案

### P2 - 优化

4. **实现视频文件归档**
   - 用户可选择保留原始视频
   - 存储到用户专属目录或对象存储

---

## 📊 存储空间估算

**假设**：
- 视频码率：2.5 Mbps
- 片段时长：30 秒
- 录制时长：1 小时

**计算**：
```
单个片段大小 = 2.5 Mbps × 30s ÷ 8 = 9.375 MB ≈ 10 MB
1小时录制 = 120 个片段 × 10 MB = 1.2 GB

如果 100 个用户各录制 1 小时：
未清理前：1.2 GB × 100 = 120 GB ⚠️
```

**结论**: 必须实现原始视频清理！

---

## 🔗 相关文件索引

| 功能 | 文件路径 |
|------|---------|
| 前端录制 | `frontend/src/services/video-recorder.ts` |
| 视频上传 | `core-service/.../controller/VideoUploadController.java` |
| 任务队列 | `core-service/.../service/TaskQueueService.java` |
| Worker 处理 | `core-service/.../worker/VideoProcessingWorker.java` |
| AI 分析 | `ai-service/app/main.py` |
| 视频切片 | `ai-service/app/video_processor.py` |
| Minio 客户端 | `ai-service/app/minio_client.py` |

---

**文档版本**: v1.0
**作者**: Claude Code
**日期**: 2025-10-24
