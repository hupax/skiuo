package com.skiuo.streammind.service;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.UUID;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * 任务队列服务
 * 管理视频分析任务的队列和调度
 */
@Service
@RequiredArgsConstructor
@Slf4j
public class TaskQueueService {

    // 任务队列（阻塞队列，线程安全）
    private final BlockingQueue<VideoAnalysisTask> taskQueue = new LinkedBlockingQueue<>();

    // 活跃 Worker 计数器
    private final AtomicInteger activeWorkerCount = new AtomicInteger(0);

    /**
     * 视频分析任务
     */
    @Data
    @AllArgsConstructor
    public static class VideoAnalysisTask {
        private UUID sessionId;
        private String videoPath;
        private Instant createdAt;
    }

    /**
     * 将视频分析任务加入队列
     *
     * @param sessionId 会话 ID
     * @param videoPath 视频文件路径
     */
    public void enqueueVideoAnalysisTask(UUID sessionId, String videoPath) {
        VideoAnalysisTask task = new VideoAnalysisTask(
                sessionId,
                videoPath,
                Instant.now()
        );

        try {
            taskQueue.put(task);  // 阻塞添加（队列满时等待）
            log.info("Enqueued task for session {}, queue size: {}", sessionId, taskQueue.size());
        } catch (InterruptedException e) {
            log.error("Failed to enqueue task for session {}", sessionId, e);
            Thread.currentThread().interrupt();
        }
    }

    /**
     * 从队列中取出任务（阻塞操作）
     * 供 Worker 线程调用
     *
     * @return 视频分析任务
     * @throws InterruptedException 中断异常
     */
    public VideoAnalysisTask dequeueTask() throws InterruptedException {
        VideoAnalysisTask task = taskQueue.take();  // 阻塞取出（队列空时等待）
        log.info("Dequeued task for session {}, remaining queue size: {}",
                task.getSessionId(), taskQueue.size());
        return task;
    }

    /**
     * 获取当前队列大小
     *
     * @return 队列中的任务数
     */
    public int getQueueSize() {
        return taskQueue.size();
    }

    /**
     * 增加活跃 Worker 计数
     */
    public void incrementActiveWorkers() {
        int count = activeWorkerCount.incrementAndGet();
        log.debug("Active workers: {}", count);
    }

    /**
     * 减少活跃 Worker 计数
     */
    public void decrementActiveWorkers() {
        int count = activeWorkerCount.decrementAndGet();
        log.debug("Active workers: {}", count);
    }

    /**
     * 获取活跃 Worker 数量
     *
     * @return 活跃 Worker 数
     */
    public int getActiveWorkerCount() {
        return activeWorkerCount.get();
    }

    /**
     * 清空队列（谨慎使用，仅用于测试或紧急情况）
     */
    public void clearQueue() {
        int size = taskQueue.size();
        taskQueue.clear();
        log.warn("Cleared task queue, removed {} tasks", size);
    }
}
