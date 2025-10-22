require('dotenv').config();

module.exports = {
  // Service ports
  port: process.env.NODE_SERVICE_PORT || 3000,

  // Spring Boot API
  springBootApiUrl: process.env.SPRING_BOOT_API_URL || 'http://localhost:8080',

  // Python AI WebSocket
  pythonAiWsUrl: process.env.PYTHON_AI_WS_URL || 'ws://localhost:8000',

  // WebRTC configuration
  webrtc: {
    iceServers: [
      { urls: 'stun:stun.l.google.com:19302' },
      { urls: 'stun:stun1.l.google.com:19302' }
    ]
  },

  // Frame extraction
  frameInterval: 1000, // Extract 1 frame per second
  jpegQuality: 80,

  // Logging
  logLevel: process.env.LOG_LEVEL || 'info'
};
