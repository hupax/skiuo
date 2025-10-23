package com.skiuo.streammind.controller;

import com.skiuo.streammind.service.SessionService;
import com.skiuo.streammind.service.TaskQueueService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardCopyOption;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

/**
 * 视频上传控制器（新方案）
 * 接收前端录制的视频片段，保存到临时目录，并加入处理队列
 */
@RestController
@RequestMapping("/api/videos")
@RequiredArgsConstructor
@Slf4j
public class VideoUploadController {

    private final SessionService sessionService;
    private final TaskQueueService taskQueueService;

    @Value("${app.video.storage-dir:/tmp/videos}")
    private String videoStorageDir;

    /**
     * 上传视频片段
     *
     * @param userId 用户 ID
     * @param sessionId 会话 ID
     * @param videoFile 视频文件
     * @return 上传响应
     */
    @PostMapping("/{sessionId}/upload")
    public ResponseEntity<Map<String, Object>> uploadVideo(
            @AuthenticationPrincipal UUID userId,
            @PathVariable UUID sessionId,
            @RequestParam("video") MultipartFile videoFile) {

        log.info("Received video upload for session {}, size: {} bytes",
                sessionId, videoFile.getSize());

        // 验证会话是否存在且属于当前用户
        if (!sessionService.existsAndBelongsToUser(sessionId, userId)) {
            log.warn("Session {} not found or doesn't belong to user {}", sessionId, userId);
            return ResponseEntity.notFound().build();
        }

        // 验证文件不为空
        if (videoFile.isEmpty()) {
            log.warn("Uploaded video file is empty for session {}", sessionId);
            Map<String, Object> errorResponse = new HashMap<>();
            errorResponse.put("error", "Video file is empty");
            return ResponseEntity.badRequest().body(errorResponse);
        }

        try {
            // 创建会话专用目录
            Path sessionDir = Paths.get(videoStorageDir, sessionId.toString());
            Files.createDirectories(sessionDir);

            // 生成文件名（带时间戳避免冲突）
            String originalFilename = videoFile.getOriginalFilename();
            String extension = originalFilename != null && originalFilename.contains(".")
                ? originalFilename.substring(originalFilename.lastIndexOf("."))
                : ".webm";

            long timestamp = System.currentTimeMillis();
            String filename = String.format("video_%d%s", timestamp, extension);
            Path filePath = sessionDir.resolve(filename);

            // 保存文件
            Files.copy(videoFile.getInputStream(), filePath, StandardCopyOption.REPLACE_EXISTING);
            log.info("Saved video to: {}", filePath);

            // 创建分析任务并加入队列
            String absolutePath = filePath.toAbsolutePath().toString();
            taskQueueService.enqueueVideoAnalysisTask(sessionId, absolutePath);
            log.info("Enqueued video analysis task for session {}", sessionId);

            // 返回成功响应
            Map<String, Object> response = new HashMap<>();
            response.put("status", "received");
            response.put("sessionId", sessionId.toString());
            response.put("filename", filename);
            response.put("size", videoFile.getSize());
            response.put("message", "Video received and queued for analysis");

            return ResponseEntity.ok(response);

        } catch (IOException e) {
            log.error("Failed to save video for session {}", sessionId, e);
            Map<String, Object> errorResponse = new HashMap<>();
            errorResponse.put("error", "Failed to save video: " + e.getMessage());
            return ResponseEntity.internalServerError().body(errorResponse);
        } catch (Exception e) {
            log.error("Unexpected error processing video upload for session {}", sessionId, e);
            Map<String, Object> errorResponse = new HashMap<>();
            errorResponse.put("error", "Internal server error: " + e.getMessage());
            return ResponseEntity.internalServerError().body(errorResponse);
        }
    }

    /**
     * 获取队列状态（可选，用于调试）
     */
    @GetMapping("/queue/status")
    public ResponseEntity<Map<String, Object>> getQueueStatus() {
        Map<String, Object> status = new HashMap<>();
        status.put("queueSize", taskQueueService.getQueueSize());
        status.put("activeWorkers", taskQueueService.getActiveWorkerCount());
        return ResponseEntity.ok(status);
    }
}
