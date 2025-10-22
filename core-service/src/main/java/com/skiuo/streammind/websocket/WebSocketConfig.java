package com.skiuo.streammind.websocket;

import lombok.RequiredArgsConstructor;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.socket.config.annotation.EnableWebSocket;
import org.springframework.web.socket.config.annotation.WebSocketConfigurer;
import org.springframework.web.socket.config.annotation.WebSocketHandlerRegistry;

@Configuration
@EnableWebSocket
@RequiredArgsConstructor
public class WebSocketConfig implements WebSocketConfigurer {

    private final AnalysisWebSocketHandler analysisWebSocketHandler;

    @Override
    public void registerWebSocketHandlers(WebSocketHandlerRegistry registry) {
        registry.addHandler(analysisWebSocketHandler, "/ws/analysis/{sessionId}")
            .setAllowedOrigins(
                "https://skiuo.supanx.net",
                "https://api.supanx.net",
                "http://localhost:5173",
                "http://localhost:3000"
            );
    }
}
