package com.skiuo.streammind.model;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.hibernate.annotations.CreationTimestamp;

import java.time.LocalDateTime;
import java.util.UUID;

@Entity
@Table(name = "analysis_records", indexes = {
    @Index(name = "idx_analysis_session_id", columnList = "session_id"),
    @Index(name = "idx_analysis_timestamp", columnList = "timestamp"),
    @Index(name = "idx_analysis_token_index", columnList = "session_id, token_index")
})
@Data
@NoArgsConstructor
@AllArgsConstructor
public class AnalysisRecord {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "session_id", nullable = false)
    private UUID sessionId;

    @Column(nullable = false, columnDefinition = "TEXT")
    private String content;

    @Column(name = "token_index", nullable = false)
    private Integer tokenIndex;

    @Column(nullable = false)
    private Long timestamp;  // Unix timestamp in milliseconds

    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;
}
