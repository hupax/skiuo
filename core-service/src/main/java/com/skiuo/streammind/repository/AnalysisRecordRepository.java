package com.skiuo.streammind.repository;

import com.skiuo.streammind.model.AnalysisRecord;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.UUID;

@Repository
public interface AnalysisRecordRepository extends JpaRepository<AnalysisRecord, Long> {

    List<AnalysisRecord> findBySessionIdOrderByTokenIndexAsc(UUID sessionId);

    Page<AnalysisRecord> findBySessionIdOrderByTokenIndexAsc(UUID sessionId, Pageable pageable);

    @Query("SELECT ar FROM AnalysisRecord ar WHERE ar.sessionId = :sessionId AND ar.tokenIndex >= :fromIndex ORDER BY ar.tokenIndex ASC")
    List<AnalysisRecord> findBySessionIdFromIndex(
        @Param("sessionId") UUID sessionId,
        @Param("fromIndex") int fromIndex
    );

    long countBySessionId(UUID sessionId);

    void deleteBySessionId(UUID sessionId);
}
