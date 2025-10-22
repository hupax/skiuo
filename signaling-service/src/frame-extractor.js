const sharp = require('sharp');
const logger = require('./logger');

/**
 * Frame Extractor
 *
 * 从 WebRTC video track 中提取视频帧
 * 注意：这是一个简化的实现，实际生产环境中需要使用 ffmpeg 或 canvas
 */
class FrameExtractor {
  constructor(videoTrack, sessionId, onFrameCallback) {
    this.videoTrack = videoTrack;
    this.sessionId = sessionId;
    this.onFrameCallback = onFrameCallback;
    this.intervalId = null;
    this.isRunning = false;
  }

  start() {
    if (this.isRunning) {
      logger.warn(`Frame extractor already running for session ${this.sessionId}`);
      return;
    }

    this.isRunning = true;
    logger.info(`Starting frame extraction for session ${this.sessionId}`);

    // 每秒提取一帧（实际实现需要从 MediaStreamTrack 中获取视频帧）
    this.intervalId = setInterval(() => {
      this.extractFrame();
    }, 1000);
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

    logger.info(`Stopped frame extraction for session ${this.sessionId}`);
  }

  /**
   * 提取视频帧（当前是 mock 实现）
   *
   * 真实实现需要：
   * 1. 使用 node-canvas 从 MediaStreamTrack 渲染帧
   * 2. 或者使用 ffmpeg 从 RTP 流中解码帧
   * 3. 或者使用 mediasoup 等媒体服务器
   */
  async extractFrame() {
    try {
      // TODO: 实际实现需要从 videoTrack 中获取真实的视频帧
      // 当前返回一个 mock 的 base64 图片
      const mockFrame = await this.generateMockFrame();

      if (this.onFrameCallback) {
        this.onFrameCallback(mockFrame);
      }
    } catch (error) {
      logger.error(`Error extracting frame for session ${this.sessionId}:`, error);
    }
  }

  /**
   * 生成 mock 帧（用于测试）
   * 实际生产环境中需要替换为真实的帧提取逻辑
   */
  async generateMockFrame() {
    // 创建一个简单的彩色图片作为 mock
    const width = 640;
    const height = 480;
    const channels = 3;

    // 生成随机颜色的图片
    const buffer = Buffer.alloc(width * height * channels);
    for (let i = 0; i < buffer.length; i += channels) {
      buffer[i] = Math.floor(Math.random() * 256);     // R
      buffer[i + 1] = Math.floor(Math.random() * 256); // G
      buffer[i + 2] = Math.floor(Math.random() * 256); // B
    }

    // 使用 sharp 转换为 JPEG 并编码为 base64
    const jpegBuffer = await sharp(buffer, {
      raw: {
        width,
        height,
        channels
      }
    })
      .jpeg({ quality: 80 })
      .toBuffer();

    return jpegBuffer.toString('base64');
  }
}

module.exports = FrameExtractor;
