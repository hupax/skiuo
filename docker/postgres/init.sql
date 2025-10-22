-- StreamMind Database Initialization Script
-- This script runs automatically when PostgreSQL container starts for the first time

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable pg_trgm for text search performance
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Sessions table
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL DEFAULT 'CREATED',
    -- Status values: CREATED, ACTIVE, STOPPED, COMPLETED, ERROR
    start_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP,
    duration_seconds INTEGER,
    title VARCHAR(255),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_status CHECK (status IN ('CREATED', 'ACTIVE', 'STOPPED', 'COMPLETED', 'ERROR'))
);

-- Analysis records table
CREATE TABLE IF NOT EXISTS analysis_records (
    id BIGSERIAL PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    token_index INTEGER NOT NULL,
    timestamp BIGINT NOT NULL,  -- Unix timestamp in milliseconds
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status);
CREATE INDEX IF NOT EXISTS idx_sessions_start_time ON sessions(start_time DESC);
CREATE INDEX IF NOT EXISTS idx_analysis_session_id ON analysis_records(session_id);
CREATE INDEX IF NOT EXISTS idx_analysis_timestamp ON analysis_records(timestamp);
CREATE INDEX IF NOT EXISTS idx_analysis_token_index ON analysis_records(session_id, token_index);

-- Function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers to auto-update updated_at
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_sessions_updated_at
    BEFORE UPDATE ON sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Insert default admin user (password: admin123, hashed with BCrypt)
-- Note: Change this password in production!
INSERT INTO users (username, email, password_hash)
VALUES (
    'admin',
    'admin@streammind.dev',
    '$2a$10$X5wFWq.9v4yXJ1zVQO2E2OYGqvqXYvJ5h1YqJZvJZ8qGqVqXYvJ5h'
)
ON CONFLICT (username) DO NOTHING;

-- Create a view for session summaries
CREATE OR REPLACE VIEW session_summaries AS
SELECT
    s.id,
    s.user_id,
    u.username,
    s.status,
    s.start_time,
    s.end_time,
    s.duration_seconds,
    s.title,
    COUNT(ar.id) AS total_tokens,
    MIN(ar.timestamp) AS first_analysis_time,
    MAX(ar.timestamp) AS last_analysis_time
FROM sessions s
LEFT JOIN users u ON s.user_id = u.id
LEFT JOIN analysis_records ar ON s.id = ar.session_id
GROUP BY s.id, s.user_id, u.username, s.status, s.start_time, s.end_time,
         s.duration_seconds, s.title;

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO streammind;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO streammind;
GRANT SELECT ON session_summaries TO streammind;

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'StreamMind database initialized successfully!';
END $$;
