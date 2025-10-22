package com.skiuo.streammind.dto;

import com.skiuo.streammind.model.Session;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;
import java.util.UUID;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class SessionResponse {
    private UUID id;
    private UUID userId;
    private String status;
    private LocalDateTime startTime;
    private LocalDateTime endTime;
    private Integer durationSeconds;
    private String title;
    private String description;
    private String signalingUrl;

    public static SessionResponse from(Session session) {
        SessionResponse response = new SessionResponse();
        response.setId(session.getId());
        response.setUserId(session.getUserId());
        response.setStatus(session.getStatus().name());
        response.setStartTime(session.getStartTime());
        response.setEndTime(session.getEndTime());
        response.setDurationSeconds(session.getDurationSeconds());
        response.setTitle(session.getTitle());
        response.setDescription(session.getDescription());
        return response;
    }
}
