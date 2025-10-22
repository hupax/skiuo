package com.skiuo.streammind.websocket;

import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;
import org.springframework.web.socket.CloseStatus;
import org.springframework.web.socket.TextMessage;
import org.springframework.web.socket.WebSocketSession;
import org.springframework.web.socket.handler.TextWebSocketHandler;

import java.io.IOException;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CopyOnWriteArraySet;

@Component
@Slf4j
public class AnalysisWebSocketHandler extends TextWebSocketHandler {

    // Map<sessionId, Set<WebSocketSession>>
    private final Map<String, CopyOnWriteArraySet<WebSocketSession>> sessionClients = new ConcurrentHashMap<>();

    @Override
    public void afterConnectionEstablished(WebSocketSession session) throws Exception {
        String sessionId = getSessionIdFromPath(session);
        if (sessionId != null) {
            sessionClients.computeIfAbsent(sessionId, k -> new CopyOnWriteArraySet<>()).add(session);
            log.info("WebSocket client connected for session {}, total clients: {}",
                sessionId, sessionClients.get(sessionId).size());
        } else {
            log.warn("WebSocket connection without session ID");
            session.close(CloseStatus.BAD_DATA);
        }
    }

    @Override
    public void afterConnectionClosed(WebSocketSession session, CloseStatus status) throws Exception {
        String sessionId = getSessionIdFromPath(session);
        if (sessionId != null) {
            CopyOnWriteArraySet<WebSocketSession> clients = sessionClients.get(sessionId);
            if (clients != null) {
                clients.remove(session);
                log.info("WebSocket client disconnected for session {}, remaining clients: {}",
                    sessionId, clients.size());

                if (clients.isEmpty()) {
                    sessionClients.remove(sessionId);
                }
            }
        }
    }

    @Override
    protected void handleTextMessage(WebSocketSession session, TextMessage message) throws Exception {
        // Client messages not expected in this implementation
        // This is a one-way broadcast from server to client
        log.debug("Received message from client: {}", message.getPayload());
    }

    /**
     * Broadcast analysis token to all clients connected to a specific session
     */
    public void broadcastAnalysisToken(String sessionId, String token) {
        CopyOnWriteArraySet<WebSocketSession> clients = sessionClients.get(sessionId);
        if (clients != null && !clients.isEmpty()) {
            TextMessage message = new TextMessage(token);

            clients.forEach(client -> {
                if (client.isOpen()) {
                    try {
                        synchronized (client) {
                            client.sendMessage(message);
                        }
                        log.debug("Sent token to client for session {}", sessionId);
                    } catch (IOException e) {
                        log.error("Error sending message to WebSocket client", e);
                    }
                }
            });
        } else {
            log.debug("No clients connected for session {}", sessionId);
        }
    }

    /**
     * Extract sessionId from WebSocket path
     * Expected path: /ws/analysis/{sessionId}
     */
    private String getSessionIdFromPath(WebSocketSession session) {
        String path = session.getUri().getPath();
        String[] parts = path.split("/");
        if (parts.length >= 4 && "analysis".equals(parts[2])) {
            return parts[3];
        }
        return null;
    }

    @Override
    public void handleTransportError(WebSocketSession session, Throwable exception) throws Exception {
        log.error("WebSocket transport error", exception);
        if (session.isOpen()) {
            session.close(CloseStatus.SERVER_ERROR);
        }
    }
}
