package com.skiuo.streammind.controller;

import com.skiuo.streammind.dto.SessionRequest;
import com.skiuo.streammind.dto.SessionResponse;
import com.skiuo.streammind.model.Session;
import com.skiuo.streammind.service.SessionService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.UUID;
import java.util.stream.Collectors;

@RestController
@RequestMapping("/api/sessions")
@RequiredArgsConstructor
@Slf4j
public class SessionController {

    private final SessionService sessionService;

    @PostMapping("/start")
    public ResponseEntity<SessionResponse> startSession(
            @AuthenticationPrincipal UUID userId,
            @RequestBody SessionRequest request) {

        log.info("Starting session for user {}", userId);

        // Create session
        Session session = sessionService.createSession(
            userId,
            request.getTitle(),
            request.getDescription()
        );

        // Immediately activate it
        session = sessionService.startSession(session.getId());

        SessionResponse response = SessionResponse.from(session);
        response.setSignalingUrl("ws://localhost:3000/signaling/" + session.getId());

        return ResponseEntity.ok(response);
    }

    @PostMapping("/{id}/stop")
    public ResponseEntity<SessionResponse> stopSession(
            @AuthenticationPrincipal UUID userId,
            @PathVariable UUID id) {

        log.info("Stopping session {} for user {}", id, userId);

        // Verify session belongs to user
        if (!sessionService.existsAndBelongsToUser(id, userId)) {
            return ResponseEntity.notFound().build();
        }

        Session session = sessionService.stopSession(id);
        return ResponseEntity.ok(SessionResponse.from(session));
    }

    @GetMapping("/{id}")
    public ResponseEntity<SessionResponse> getSession(
            @AuthenticationPrincipal UUID userId,
            @PathVariable UUID id) {

        if (!sessionService.existsAndBelongsToUser(id, userId)) {
            return ResponseEntity.notFound().build();
        }

        Session session = sessionService.getSession(id);
        return ResponseEntity.ok(SessionResponse.from(session));
    }

    @GetMapping
    public ResponseEntity<List<SessionResponse>> getUserSessions(@AuthenticationPrincipal UUID userId) {
        List<Session> sessions = sessionService.getUserSessions(userId);
        List<SessionResponse> responses = sessions.stream()
            .map(SessionResponse::from)
            .collect(Collectors.toList());

        return ResponseEntity.ok(responses);
    }

    @GetMapping("/{id}/status")
    public ResponseEntity<SessionResponse> getSessionStatus(
            @AuthenticationPrincipal UUID userId,
            @PathVariable UUID id) {

        if (!sessionService.existsAndBelongsToUser(id, userId)) {
            return ResponseEntity.notFound().build();
        }

        Session session = sessionService.getSession(id);
        return ResponseEntity.ok(SessionResponse.from(session));
    }
}
