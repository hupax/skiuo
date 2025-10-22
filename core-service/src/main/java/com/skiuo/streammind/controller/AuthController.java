package com.skiuo.streammind.controller;

import com.skiuo.streammind.dto.AuthRequest;
import com.skiuo.streammind.dto.AuthResponse;
import com.skiuo.streammind.service.UserService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/auth")
@RequiredArgsConstructor
@Slf4j
public class AuthController {

    private final UserService userService;

    @PostMapping("/register")
    public ResponseEntity<AuthResponse> register(@Valid @RequestBody AuthRequest request) {
        log.info("Registration attempt for username: {}", request.getUsername());
        AuthResponse response = userService.register(request);
        return ResponseEntity.ok(response);
    }

    @PostMapping("/login")
    public ResponseEntity<AuthResponse> login(@Valid @RequestBody AuthRequest request) {
        log.info("Login attempt for username: {}", request.getUsername());
        AuthResponse response = userService.login(request);
        return ResponseEntity.ok(response);
    }
}
