const express = require('express');
const http = require('http');
const WebSocket = require('ws');
const config = require('./config');
const logger = require('./logger');
const FrameHandler = require('./frame-handler');

const app = express();
const server = http.createServer(app);
const wss = new WebSocket.Server({ server });

// Middleware
app.use(express.json());

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({ status: 'healthy', service: 'signaling-service' });
});

// WebSocket connection handler
wss.on('connection', (ws, req) => {
  const url = new URL(req.url, `ws://${req.headers.host}`);
  const pathParts = url.pathname.split('/');

  // Handle different WebSocket paths
  if (pathParts.length >= 3) {
    const sessionId = pathParts[2];

    // Path: /frames/{sessionId} - For video frame transmission
    if (pathParts[1] === 'frames') {
      logger.info(`Frames WebSocket connected for session: ${sessionId}`);

      const handler = new FrameHandler(ws, sessionId);
      handler.start();

      ws.on('close', () => {
        logger.info(`Frames WebSocket closed for session: ${sessionId}`);
        handler.stop();
      });

      ws.on('error', (error) => {
        logger.error(`Frames WebSocket error for session ${sessionId}:`, error);
        handler.stop();
      });
    } else {
      logger.warn('WebSocket connection with invalid path:', url.pathname);
      ws.close(1008, 'Invalid path');
    }
  } else {
    logger.warn('WebSocket connection with invalid path:', url.pathname);
    ws.close(1008, 'Invalid path');
  }
});

// Start server
server.listen(config.port, () => {
  logger.info(`Signaling service listening on port ${config.port}`);
  logger.info(`Spring Boot API: ${config.springBootApiUrl}`);
  logger.info(`Python AI WebSocket: ${config.pythonAiWsUrl}`);
});

// Graceful shutdown
process.on('SIGTERM', () => {
  logger.info('SIGTERM signal received: closing HTTP server');
  server.close(() => {
    logger.info('HTTP server closed');
    process.exit(0);
  });
});

process.on('SIGINT', () => {
  logger.info('SIGINT signal received: closing HTTP server');
  server.close(() => {
    logger.info('HTTP server closed');
    process.exit(0);
  });
});
