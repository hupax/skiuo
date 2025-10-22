package com.skiuo.streammind.controller;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

/**
 * Internal API endpoints for service-to-service communication
 * These endpoints are called by Node.js signaling service
 */
@Slf4j
@RestController
@RequestMapping("/internal")
@RequiredArgsConstructor
public class InternalController {

    /**
     * Notification endpoint when session connects
     * Called by Node.js signaling service
     */
    @PostMapping("/session/connected")
    public ResponseEntity<Void> sessionConnected(@RequestBody Map<String, Object> payload) {
        String sessionId = (String) payload.get("sessionId");
        Long timestamp = ((Number) payload.get("timestamp")).longValue();

        log.info("Session connected: {} at {}", sessionId, timestamp);

        // TODO: Update session status in database if needed

        return ResponseEntity.ok().build();
    }

    /**
     * Notification endpoint when session disconnects
     * Called by Node.js signaling service
     */
    @PostMapping("/session/disconnected")
    public ResponseEntity<Void> sessionDisconnected(@RequestBody Map<String, Object> payload) {
        String sessionId = (String) payload.get("sessionId");
        Long timestamp = ((Number) payload.get("timestamp")).longValue();

        log.info("Session disconnected: {} at {}", sessionId, timestamp);

        // TODO: Update session status or cleanup if needed

        return ResponseEntity.ok().build();
    }

    /**
     * Health check endpoint for internal services
     */
    @GetMapping("/health")
    public ResponseEntity<Map<String, String>> health() {
        return ResponseEntity.ok(Map.of("status", "UP"));
    }
}
