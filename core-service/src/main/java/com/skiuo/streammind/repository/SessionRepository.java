package com.skiuo.streammind.repository;

import com.skiuo.streammind.model.Session;
import com.skiuo.streammind.model.Session.SessionStatus;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Repository
public interface SessionRepository extends JpaRepository<Session, UUID> {

    List<Session> findByUserIdOrderByStartTimeDesc(UUID userId);

    Page<Session> findByUserId(UUID userId, Pageable pageable);

    Optional<Session> findByIdAndUserId(UUID id, UUID userId);

    List<Session> findByStatus(SessionStatus status);

    long countByUserId(UUID userId);
}
