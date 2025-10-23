package com.skiuo.streammind.worker;

import com.skiuo.streammind.service.TaskQueueService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.context.event.EventListener;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Mono;

import jakarta.annotation.PreDestroy;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;

/**
 * 视频处理 Worker
 * 从任务队列取出任务，调用 Python AI 服务进行分析
 */
@Component
@RequiredArgsConstructor
@Slf4j
public class VideoProcessingWorker {

    private final TaskQueueService taskQueueService;

    @Value("${app.python-ai.url:http://localhost:8000}")
    private String pythonAiUrl;

    @Value("${app.worker.thread-count:2}")
    private int workerThreadCount;

    private ExecutorService executorService;
    private volatile boolean running = true;

    /**
     * 应用启动后启动 Worker 线程池
     */
    @EventListener(ApplicationReadyEvent.class)
    public void startWorkers() {
        log.info("Starting {} video processing workers", workerThreadCount);

        executorService = Executors.newFixedThreadPool(workerThreadCount);

        for (int i = 0; i < workerThreadCount; i++) {
            final int workerId = i + 1;
            executorService.submit(() -> workerLoop(workerId));
        }

        log.info("Video processing workers started successfully");
    }

    /**
     * Worker 循环：持续从队列取任务并处理
     */
    private void workerLoop(int workerId) {
        log.info("Worker #{} started", workerId);

        while (running) {
            try {
                // 从队列取任务（阻塞）
                TaskQueueService.VideoAnalysisTask task = taskQueueService.dequeueTask();

                log.info("Worker #{} picked up task for session {}", workerId, task.getSessionId());

                taskQueueService.incrementActiveWorkers();

                try {
                    // 调用 Python AI 服务分析视频
                    processVideoTask(workerId, task);
                } catch (Exception e) {
                    log.error("Worker #{} failed to process task for session {}",
                            workerId, task.getSessionId(), e);
                } finally {
                    taskQueueService.decrementActiveWorkers();
                }

            } catch (InterruptedException e) {
                log.info("Worker #{} interrupted", workerId);
                Thread.currentThread().interrupt();
                break;
            } catch (Exception e) {
                log.error("Worker #{} encountered unexpected error", workerId, e);
            }
        }

        log.info("Worker #{} stopped", workerId);
    }

    /**
     * 处理视频分析任务
     * 调用 Python AI 服务的 /analyze-video 端点
     */
    private void processVideoTask(int workerId, TaskQueueService.VideoAnalysisTask task) {
        log.info("Worker #{} processing video: {}", workerId, task.getVideoPath());

        WebClient client = WebClient.builder()
                .baseUrl(pythonAiUrl)
                .build();

        // 构建请求体
        Map<String, String> requestBody = new HashMap<>();
        requestBody.put("session_id", task.getSessionId().toString());
        requestBody.put("video_path", task.getVideoPath());

        try {
            // 调用 Python AI 服务（同步等待完成）
            String response = client.post()
                    .uri("/analyze-video")
                    .contentType(MediaType.APPLICATION_JSON)
                    .bodyValue(requestBody)
                    .retrieve()
                    .bodyToMono(String.class)
                    .timeout(java.time.Duration.ofMinutes(10))  // 10 分钟超时
                    .onErrorResume(e -> {
                        log.error("Worker #{} failed to call Python AI for session {}",
                                workerId, task.getSessionId(), e);
                        return Mono.just("{\"error\":\"" + e.getMessage() + "\"}");
                    })
                    .block();  // 阻塞等待完成

            log.info("Worker #{} completed task for session {}, response: {}",
                    workerId, task.getSessionId(), response);

        } catch (Exception e) {
            log.error("Worker #{} error processing video for session {}",
                    workerId, task.getSessionId(), e);
        }
    }

    /**
     * 应用关闭时停止 Worker
     */
    @PreDestroy
    public void stopWorkers() {
        log.info("Stopping video processing workers...");
        running = false;

        if (executorService != null) {
            executorService.shutdown();
            try {
                if (!executorService.awaitTermination(30, TimeUnit.SECONDS)) {
                    log.warn("Workers did not terminate gracefully, forcing shutdown");
                    executorService.shutdownNow();
                }
            } catch (InterruptedException e) {
                log.error("Error while stopping workers", e);
                executorService.shutdownNow();
                Thread.currentThread().interrupt();
            }
        }

        log.info("Video processing workers stopped");
    }
}
