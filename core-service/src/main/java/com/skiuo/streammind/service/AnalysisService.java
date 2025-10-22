package com.skiuo.streammind.service;

import com.skiuo.streammind.model.AnalysisRecord;
import com.skiuo.streammind.repository.AnalysisRecordRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.UUID;

@Service
@RequiredArgsConstructor
@Slf4j
public class AnalysisService {

    private final AnalysisRecordRepository analysisRecordRepository;

    @Transactional
    public AnalysisRecord saveAnalysis(UUID sessionId, String content, int tokenIndex, long timestamp) {
        AnalysisRecord record = new AnalysisRecord();
        record.setSessionId(sessionId);
        record.setContent(content);
        record.setTokenIndex(tokenIndex);
        record.setTimestamp(timestamp);

        AnalysisRecord saved = analysisRecordRepository.save(record);
        log.debug("Saved analysis token {} for session {}", tokenIndex, sessionId);
        return saved;
    }

    @Transactional(readOnly = true)
    public List<AnalysisRecord> getSessionAnalysis(UUID sessionId) {
        return analysisRecordRepository.findBySessionIdOrderByTokenIndexAsc(sessionId);
    }

    @Transactional(readOnly = true)
    public Page<AnalysisRecord> getSessionAnalysisPaged(UUID sessionId, Pageable pageable) {
        return analysisRecordRepository.findBySessionIdOrderByTokenIndexAsc(sessionId, pageable);
    }

    @Transactional(readOnly = true)
    public List<AnalysisRecord> getSessionAnalysisFromIndex(UUID sessionId, int fromIndex) {
        return analysisRecordRepository.findBySessionIdFromIndex(sessionId, fromIndex);
    }

    @Transactional(readOnly = true)
    public long getAnalysisCount(UUID sessionId) {
        return analysisRecordRepository.countBySessionId(sessionId);
    }

    @Transactional
    public void deleteSessionAnalysis(UUID sessionId) {
        analysisRecordRepository.deleteBySessionId(sessionId);
        log.info("Deleted all analysis records for session {}", sessionId);
    }

    /**
     * Generate markdown report from analysis records
     */
    @Transactional(readOnly = true)
    public String generateMarkdownReport(UUID sessionId) {
        List<AnalysisRecord> records = getSessionAnalysis(sessionId);

        StringBuilder markdown = new StringBuilder();
        markdown.append("# StreamMind Session Analysis Report\n\n");
        markdown.append("**Session ID:** ").append(sessionId).append("\n\n");
        markdown.append("**Total Tokens:** ").append(records.size()).append("\n\n");
        markdown.append("---\n\n");

        for (AnalysisRecord record : records) {
            markdown.append("## Token #").append(record.getTokenIndex()).append("\n\n");
            markdown.append("**Timestamp:** ").append(record.getTimestamp()).append("\n\n");
            markdown.append(record.getContent()).append("\n\n");
            markdown.append("---\n\n");
        }

        return markdown.toString();
    }
}
