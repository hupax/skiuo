# Multi-stage build for Spring Boot
FROM maven:3.9-eclipse-temurin-17 AS build

WORKDIR /build

# Copy proto files first (for protobuf generation)
COPY proto /proto

# Copy pom.xml and download dependencies (better layer caching)
COPY core-service/pom.xml .
RUN mvn dependency:go-offline -B

# Copy source code
COPY core-service/src ./src

# Build application and generate protobuf
RUN mvn clean package -DskipTests

# Runtime stage
FROM eclipse-temurin:17-jre

WORKDIR /app

# Install curl for healthcheck
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Create non-root user (use existing group 1000 if exists)
RUN groupadd -r -g 1001 spring 2>/dev/null || true && \
    useradd -r -u 1001 -g 1001 spring

# Copy JAR from build stage
COPY --from=build /build/target/*.jar app.jar

# Change ownership
RUN chown spring:spring app.jar

# Switch to non-root user
USER spring:spring

# Expose ports
# 8080: REST API + WebSocket
# 9090: gRPC
EXPOSE 8080 9090

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8080/actuator/health || exit 1

# JVM options for container
ENV JAVA_OPTS="-Xms512m -Xmx1024m -XX:+UseContainerSupport -XX:MaxRAMPercentage=75.0"

# Run application
ENTRYPOINT ["sh", "-c", "java $JAVA_OPTS -jar app.jar"]
