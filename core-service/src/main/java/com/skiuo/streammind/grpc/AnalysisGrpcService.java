package com.skiuo.streammind.grpc;

import com.skiuo.streammind.model.AnalysisRecord;
import com.skiuo.streammind.service.AnalysisService;
import com.skiuo.streammind.websocket.AnalysisWebSocketHandler;
import io.grpc.stub.StreamObserver;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import net.devh.boot.grpc.server.service.GrpcService;

import java.util.List;
import java.util.UUID;

@GrpcService
@RequiredArgsConstructor
@Slf4j
public class AnalysisGrpcService extends AnalysisServiceGrpc.AnalysisServiceImplBase {

    private final AnalysisService analysisService;
    private final AnalysisWebSocketHandler webSocketHandler;

    @Override
    public void saveAnalysis(AnalysisRequest request, StreamObserver<AnalysisResponse> responseObserver) {
        try {
            log.debug("Received analysis token {} for session {}",
                request.getTokenIndex(), request.getSessionId());

            UUID sessionId = UUID.fromString(request.getSessionId());

            // Save to database
            AnalysisRecord record = analysisService.saveAnalysis(
                sessionId,
                request.getContent(),
                request.getTokenIndex(),
                request.getTimestamp()
            );

            // Broadcast to WebSocket clients
            webSocketHandler.broadcastAnalysisToken(sessionId.toString(), request.getContent());

            // Send response
            AnalysisResponse response = AnalysisResponse.newBuilder()
                .setSuccess(true)
                .setMessage("Saved")
                .setSavedId(record.getId())
                .build();

            responseObserver.onNext(response);
            responseObserver.onCompleted();

        } catch (Exception e) {
            log.error("Error saving analysis", e);
            AnalysisResponse response = AnalysisResponse.newBuilder()
                .setSuccess(false)
                .setMessage("Error: " + e.getMessage())
                .build();

            responseObserver.onNext(response);
            responseObserver.onCompleted();
        }
    }

    @Override
    public void getAnalysis(GetAnalysisRequest request, StreamObserver<AnalysisChunk> responseObserver) {
        try {
            UUID sessionId = UUID.fromString(request.getSessionId());
            int fromIndex = request.getFromTokenIndex();

            List<AnalysisRecord> records;
            if (fromIndex > 0) {
                records = analysisService.getSessionAnalysisFromIndex(sessionId, fromIndex);
            } else {
                records = analysisService.getSessionAnalysis(sessionId);
            }

            // Stream results back
            for (AnalysisRecord record : records) {
                AnalysisChunk chunk = AnalysisChunk.newBuilder()
                    .setId(record.getId())
                    .setSessionId(record.getSessionId().toString())
                    .setContent(record.getContent())
                    .setTokenIndex(record.getTokenIndex())
                    .setTimestamp(record.getTimestamp())
                    .build();

                responseObserver.onNext(chunk);
            }

            responseObserver.onCompleted();

        } catch (Exception e) {
            log.error("Error getting analysis", e);
            responseObserver.onError(e);
        }
    }
}
