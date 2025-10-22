package com.skiuo.streammind.service;

import com.skiuo.streammind.dto.AuthRequest;
import com.skiuo.streammind.dto.AuthResponse;
import com.skiuo.streammind.model.User;
import com.skiuo.streammind.repository.UserRepository;
import com.skiuo.streammind.security.JwtUtil;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.UUID;

@Service
@RequiredArgsConstructor
@Slf4j
public class UserService {

    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;
    private final JwtUtil jwtUtil;

    @Transactional
    public AuthResponse register(AuthRequest request) {
        // Check if username exists
        if (userRepository.existsByUsername(request.getUsername())) {
            throw new RuntimeException("Username already exists");
        }

        // Check if email exists
        if (userRepository.existsByEmail(request.getEmail())) {
            throw new RuntimeException("Email already exists");
        }

        // Create new user
        User user = new User();
        user.setUsername(request.getUsername());
        user.setEmail(request.getEmail());
        user.setPasswordHash(passwordEncoder.encode(request.getPassword()));

        User saved = userRepository.save(user);
        log.info("Registered new user: {}", saved.getUsername());

        // Generate token
        String token = jwtUtil.generateToken(saved.getId(), saved.getUsername());

        return new AuthResponse(
            saved.getId(),
            saved.getUsername(),
            saved.getEmail(),
            token
        );
    }

    @Transactional(readOnly = true)
    public AuthResponse login(AuthRequest request) {
        User user = userRepository.findByUsername(request.getUsername())
            .orElseThrow(() -> new RuntimeException("Invalid username or password"));

        if (!passwordEncoder.matches(request.getPassword(), user.getPasswordHash())) {
            throw new RuntimeException("Invalid username or password");
        }

        log.info("User logged in: {}", user.getUsername());

        // Generate token
        String token = jwtUtil.generateToken(user.getId(), user.getUsername());

        return new AuthResponse(
            user.getId(),
            user.getUsername(),
            user.getEmail(),
            token
        );
    }

    @Transactional(readOnly = true)
    public User getUserById(UUID userId) {
        return userRepository.findById(userId)
            .orElseThrow(() -> new RuntimeException("User not found"));
    }

    @Transactional(readOnly = true)
    public User getUserByUsername(String username) {
        return userRepository.findByUsername(username)
            .orElseThrow(() -> new RuntimeException("User not found"));
    }
}
