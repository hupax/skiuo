const { spawn } = require('child_process');
const logger = require('./logger');
const fs = require('fs');
const path = require('path');

/**
 * Frame Extractor using FFmpeg
 *
 * 从 WebRTC MediaStreamTrack 使用 ffmpeg 提取视频帧
 *
 * 工作原理：
 * 1. 监听 MediaStreamTrack 的 RTP 包
 * 2. 将 RTP 数据通过管道传给 ffmpeg
 * 3. ffmpeg 解码并输出 JPEG 帧
 */
class FrameExtractor {
  constructor(videoTrack, sessionId, onFrameCallback) {
    this.videoTrack = videoTrack;
    this.sessionId = sessionId;
    this.onFrameCallback = onFrameCallback;
    this.isRunning = false;
    this.frameCount = 0;
    this.ffmpegProcess = null;
    this.receiver = null;
    this.rtpPackets = [];
    this.intervalId = null;
  }

  start() {
    if (this.isRunning) {
      logger.warn(`Frame extractor already running for session ${this.sessionId}`);
      return;
    }

    this.isRunning = true;
    logger.info(`Starting frame extraction for session ${this.sessionId}`);

    // 由于 wrtc 的限制，我们使用定时器方式生成测试帧
    // 真实实现需要捕获 RTP 包并喂给 ffmpeg
    this.startFrameCapture();
  }

  stop() {
    if (!this.isRunning) {
      return;
    }

    this.isRunning = false;

    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }

    if (this.ffmpegProcess) {
      this.ffmpegProcess.kill('SIGTERM');
      this.ffmpegProcess = null;
    }

    logger.info(`Stopped frame extraction for session ${this.sessionId}. Total frames: ${this.frameCount}`);
  }

  /**
   * 启动帧捕获
   *
   * 注意：wrtc 在 Node.js 中不提供直接的视频帧访问
   * 这里使用 ffmpeg 生成测试图像作为占位符
   */
  startFrameCapture() {
    // 每秒生成一帧测试图像
    this.intervalId = setInterval(() => {
      this.captureFrame();
    }, 1000);
  }

  /**
   * 捕获一帧
   */
  async captureFrame() {
    try {
      const base64Frame = await this.generateFrameWithFFmpeg();

      this.frameCount++;

      if (this.onFrameCallback) {
        this.onFrameCallback(base64Frame);
      }

      logger.debug(`Captured frame ${this.frameCount} for session ${this.sessionId}`);
    } catch (error) {
      logger.error(`Error capturing frame for session ${this.sessionId}:`, error);
    }
  }

  /**
   * 使用 ffmpeg 生成测试帧
   *
   * 生成一个包含文字的测试图像
   * 真实场景需要从 RTP 流解码
   */
  async generateFrameWithFFmpeg() {
    return new Promise((resolve, reject) => {
      const timestamp = new Date().toLocaleTimeString();

      // 使用 ffmpeg 生成一个带文字的测试图像
      // -f lavfi: 使用 lavfi (Libavfilter) 输入
      // color=c=0x1a1a2e: 深色背景
      // drawtext: 绘制文字
      const ffmpeg = spawn('ffmpeg', [
        '-f', 'lavfi',
        '-i', `color=c=0x1a1a2e:s=1280x720:d=0.1`,
        '-vf', [
          `drawtext=fontfile=/System/Library/Fonts/Supplemental/Arial.ttf:text='StreamMind Frame ${this.frameCount}':fontcolor=white:fontsize=48:x=(w-text_w)/2:y=(h-text_h)/2-100`,
          `drawtext=fontfile=/System/Library/Fonts/Supplemental/Arial.ttf:text='Session\\: ${this.sessionId.substring(0, 8)}':fontcolor=white:fontsize=32:x=(w-text_w)/2:y=(h-text_h)/2`,
          `drawtext=fontfile=/System/Library/Fonts/Supplemental/Arial.ttf:text='Time\\: ${timestamp}':fontcolor=white:fontsize=32:x=(w-text_w)/2:y=(h-text_h)/2+60`
        ].join(','),
        '-frames:v', '1',
        '-f', 'image2',
        '-c:v', 'mjpeg',
        '-q:v', '2',
        'pipe:1'
      ]);

      const chunks = [];

      ffmpeg.stdout.on('data', (chunk) => {
        chunks.push(chunk);
      });

      ffmpeg.stderr.on('data', (data) => {
        // ffmpeg 输出到 stderr，这是正常的
        logger.debug(`FFmpeg stderr: ${data.toString().substring(0, 100)}`);
      });

      ffmpeg.on('close', (code) => {
        if (code === 0 && chunks.length > 0) {
          const buffer = Buffer.concat(chunks);
          const base64 = buffer.toString('base64');
          resolve(base64);
        } else {
          reject(new Error(`FFmpeg exited with code ${code}`));
        }
      });

      ffmpeg.on('error', (error) => {
        reject(error);
      });

      // 超时保护
      setTimeout(() => {
        if (ffmpeg.exitCode === null) {
          ffmpeg.kill('SIGTERM');
          reject(new Error('FFmpeg timeout'));
        }
      }, 5000);
    });
  }
}

module.exports = FrameExtractor;
