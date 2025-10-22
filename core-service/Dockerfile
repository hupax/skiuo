# Multi-stage build for Spring Boot
FROM maven:3.9-eclipse-temurin-17-alpine AS build

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
FROM eclipse-temurin:17-jre-alpine

WORKDIR /app

# Install curl for healthcheck
RUN apk add --no-cache curl

# Create non-root user
RUN addgroup -g 1000 spring && \
    adduser -u 1000 -G spring -s /bin/sh -D spring

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
