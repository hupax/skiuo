const { RTCPeerConnection } = require('wrtc');
const WebSocket = require('ws');
const axios = require('axios');
const config = require('./config');
const logger = require('./logger');
const FrameExtractor = require('./frame-extractor');

class SignalingHandler {
  constructor(clientWs, sessionId) {
    this.clientWs = clientWs;
    this.sessionId = sessionId;
    this.peerConnection = null;
    this.pythonWs = null;
    this.frameExtractor = null;
    this.isActive = false;
  }

  start() {
    this.isActive = true;
    this.setupWebSocketHandlers();
    this.connectToPythonAI();
    this.notifySpringBoot('connected');
  }

  stop() {
    this.isActive = false;

    if (this.frameExtractor) {
      this.frameExtractor.stop();
      this.frameExtractor = null;
    }

    if (this.peerConnection) {
      this.peerConnection.close();
      this.peerConnection = null;
    }

    if (this.pythonWs) {
      this.pythonWs.close();
      this.pythonWs = null;
    }

    this.notifySpringBoot('disconnected');
  }

  setupWebSocketHandlers() {
    this.clientWs.on('message', async (message) => {
      try {
        const data = JSON.parse(message);
        await this.handleSignalingMessage(data);
      } catch (error) {
        logger.error(`Error handling message for session ${this.sessionId}:`, error);
        this.sendToClient({ type: 'error', message: error.message });
      }
    });
  }

  async handleSignalingMessage(data) {
    const { type } = data;

    switch (type) {
      case 'offer':
        await this.handleOffer(data.sdp);
        break;

      case 'ice-candidate':
        await this.handleIceCandidate(data.candidate);
        break;

      default:
        logger.warn(`Unknown message type: ${type}`);
    }
  }

  async handleOffer(sdp) {
    logger.info(`Received offer for session ${this.sessionId}`);

    // Create peer connection
    this.peerConnection = new RTCPeerConnection({
      iceServers: config.webrtc.iceServers
    });

    // Handle ICE candidates
    this.peerConnection.onicecandidate = (event) => {
      if (event.candidate) {
        this.sendToClient({
          type: 'ice-candidate',
          candidate: event.candidate
        });
      }
    };

    // Handle tracks (video/audio)
    this.peerConnection.ontrack = (event) => {
      logger.info(`Received track: ${event.track.kind} for session ${this.sessionId}`);

      if (event.track.kind === 'video') {
        // Start frame extraction
        this.frameExtractor = new FrameExtractor(
          event.track,
          this.sessionId,
          (base64Frame) => this.forwardFrameToPython(base64Frame)
        );
        this.frameExtractor.start();
      }
    };

    // Set remote description (offer)
    await this.peerConnection.setRemoteDescription({ type: 'offer', sdp });

    // Create answer
    const answer = await this.peerConnection.createAnswer();
    await this.peerConnection.setLocalDescription(answer);

    // Send answer back to client
    this.sendToClient({
      type: 'answer',
      sdp: answer.sdp
    });

    logger.info(`Sent answer for session ${this.sessionId}`);
  }

  async handleIceCandidate(candidate) {
    if (this.peerConnection) {
      await this.peerConnection.addIceCandidate(candidate);
      logger.debug(`Added ICE candidate for session ${this.sessionId}`);
    }
  }

  connectToPythonAI() {
    const wsUrl = `${config.pythonAiWsUrl}/ws/analyze/${this.sessionId}`;
    logger.info(`Connecting to Python AI: ${wsUrl}`);

    this.pythonWs = new WebSocket(wsUrl);

    this.pythonWs.on('open', () => {
      logger.info(`Connected to Python AI for session ${this.sessionId}`);
    });

    this.pythonWs.on('message', (data) => {
      // Python AI sends back analysis tokens (optional)
      logger.debug(`Received analysis from Python: ${data}`);
    });

    this.pythonWs.on('error', (error) => {
      logger.error(`Python WebSocket error for session ${this.sessionId}:`, error);
    });

    this.pythonWs.on('close', () => {
      logger.warn(`Python WebSocket closed for session ${this.sessionId}`);
      // Attempt reconnect?
    });
  }

  forwardFrameToPython(base64Frame) {
    if (this.pythonWs && this.pythonWs.readyState === WebSocket.OPEN) {
      this.pythonWs.send(base64Frame);
      logger.debug(`Forwarded frame to Python for session ${this.sessionId}`);
    } else {
      logger.warn(`Python WebSocket not ready for session ${this.sessionId}`);
    }
  }

  sendToClient(message) {
    if (this.clientWs.readyState === WebSocket.OPEN) {
      this.clientWs.send(JSON.stringify(message));
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

module.exports = SignalingHandler;
