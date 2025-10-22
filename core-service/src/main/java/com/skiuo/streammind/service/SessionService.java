package com.skiuo.streammind.service;

import com.skiuo.streammind.model.Session;
import com.skiuo.streammind.model.Session.SessionStatus;
import com.skiuo.streammind.repository.SessionRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Duration;
import java.time.LocalDateTime;
import java.util.List;
import java.util.UUID;

@Service
@RequiredArgsConstructor
@Slf4j
public class SessionService {

    private final SessionRepository sessionRepository;

    @Transactional
    public Session createSession(UUID userId, String title, String description) {
        Session session = new Session();
        session.setUserId(userId);
        session.setStatus(SessionStatus.CREATED);
        session.setStartTime(LocalDateTime.now());
        session.setTitle(title);
        session.setDescription(description);

        Session saved = sessionRepository.save(session);
        log.info("Created session {} for user {}", saved.getId(), userId);
        return saved;
    }

    @Transactional
    public Session startSession(UUID sessionId) {
        Session session = sessionRepository.findById(sessionId)
            .orElseThrow(() -> new RuntimeException("Session not found: " + sessionId));

        if (session.getStatus() != SessionStatus.CREATED) {
            throw new RuntimeException("Session is not in CREATED status");
        }

        session.setStatus(SessionStatus.ACTIVE);
        session.setStartTime(LocalDateTime.now());

        Session saved = sessionRepository.save(session);
        log.info("Started session {}", sessionId);
        return saved;
    }

    @Transactional
    public Session stopSession(UUID sessionId) {
        Session session = sessionRepository.findById(sessionId)
            .orElseThrow(() -> new RuntimeException("Session not found: " + sessionId));

        if (session.getStatus() != SessionStatus.ACTIVE) {
            throw new RuntimeException("Session is not in ACTIVE status");
        }

        LocalDateTime endTime = LocalDateTime.now();
        session.setStatus(SessionStatus.STOPPED);
        session.setEndTime(endTime);

        // Calculate duration
        Duration duration = Duration.between(session.getStartTime(), endTime);
        session.setDurationSeconds((int) duration.getSeconds());

        Session saved = sessionRepository.save(session);
        log.info("Stopped session {}, duration: {} seconds", sessionId, saved.getDurationSeconds());
        return saved;
    }

    @Transactional
    public Session completeSession(UUID sessionId) {
        Session session = sessionRepository.findById(sessionId)
            .orElseThrow(() -> new RuntimeException("Session not found: " + sessionId));

        session.setStatus(SessionStatus.COMPLETED);

        if (session.getEndTime() == null) {
            session.setEndTime(LocalDateTime.now());
            Duration duration = Duration.between(session.getStartTime(), session.getEndTime());
            session.setDurationSeconds((int) duration.getSeconds());
        }

        Session saved = sessionRepository.save(session);
        log.info("Completed session {}", sessionId);
        return saved;
    }

    @Transactional(readOnly = true)
    public Session getSession(UUID sessionId) {
        return sessionRepository.findById(sessionId)
            .orElseThrow(() -> new RuntimeException("Session not found: " + sessionId));
    }

    @Transactional(readOnly = true)
    public List<Session> getUserSessions(UUID userId) {
        return sessionRepository.findByUserIdOrderByStartTimeDesc(userId);
    }

    @Transactional(readOnly = true)
    public Page<Session> getUserSessionsPaged(UUID userId, Pageable pageable) {
        return sessionRepository.findByUserId(userId, pageable);
    }

    @Transactional(readOnly = true)
    public boolean existsAndBelongsToUser(UUID sessionId, UUID userId) {
        return sessionRepository.findByIdAndUserId(sessionId, userId).isPresent();
    }
}
