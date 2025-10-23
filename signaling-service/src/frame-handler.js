const WebSocket = require('ws');
const axios = require('axios');
const config = require('./config');
const logger = require('./logger');

/**
 * Frame Handler
 * 接收前端发来的视频帧并转发给 Python AI
 */
class FrameHandler {
  constructor(clientWs, sessionId) {
    this.clientWs = clientWs;
    this.sessionId = sessionId;
    this.pythonWs = null;
    this.isActive = false;
    this.frameCount = 0;
  }

  start() {
    this.isActive = true;
    this.setupWebSocketHandlers();
    this.connectToPythonAI();
    this.notifySpringBoot('connected');
  }

  stop() {
    this.isActive = false;

    if (this.pythonWs) {
      this.pythonWs.close();
      this.pythonWs = null;
    }

    this.notifySpringBoot('disconnected');
  }

  setupWebSocketHandlers() {
    this.clientWs.on('message', async (message) => {
      try {
        // 前端发来的是 base64 编码的 JPEG 图片
        const base64Frame = message.toString();

        this.frameCount++;
        logger.debug(`Received frame ${this.frameCount} for session ${this.sessionId}`);

        // 转发给 Python AI
        this.forwardFrameToPython(base64Frame);

      } catch (error) {
        logger.error(`Error handling frame for session ${this.sessionId}:`, error);
      }
    });
  }

  connectToPythonAI() {
    const wsUrl = `${config.pythonAiWsUrl}/ws/analyze/${this.sessionId}`;
    logger.info(`Connecting to Python AI: ${wsUrl}`);

    this.pythonWs = new WebSocket(wsUrl);

    this.pythonWs.on('open', () => {
      logger.info(`Connected to Python AI for session ${this.sessionId}`);
    });

    this.pythonWs.on('message', (data) => {
      // Python AI sends back analysis tokens (optional, mainly uses gRPC)
      logger.debug(`Received analysis from Python: ${data.toString().substring(0, 50)}`);
    });

    this.pythonWs.on('error', (error) => {
      logger.error(`Python WebSocket error for session ${this.sessionId}:`, error);
    });

    this.pythonWs.on('close', () => {
      logger.warn(`Python WebSocket closed for session ${this.sessionId}`);
    });
  }

  forwardFrameToPython(base64Frame) {
    if (this.pythonWs && this.pythonWs.readyState === WebSocket.OPEN) {
      this.pythonWs.send(base64Frame);
      logger.debug(`Forwarded frame ${this.frameCount} to Python for session ${this.sessionId}`);
    } else {
      logger.warn(`Python WebSocket not ready for session ${this.sessionId}, state: ${this.pythonWs?.readyState}`);
    }
  }

  async notifySpringBoot(event) {
    try {
      await axios.post(`${config.springBootApiUrl}/internal/session/${event}`, {
        sessionId: this.sessionId,
        timestamp: Date.now()
      });
      logger.info(`Notified Spring Boot: ${event} for session ${this.sessionId}`);
    } catch (error) {
      logger.error(`Failed to notify Spring Boot (${event}):`, error.message);
    }
  }
}

module.exports = FrameHandler;
