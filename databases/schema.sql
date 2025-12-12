-- Role table
CREATE TABLE IF NOT EXISTS roles (
    role_id SERIAL PRIMARY KEY,
    role_name VARCHAR(100) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Users table
CREATE TABLE IF NOT EXISTS users (
    user_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    discord_id BIGINT NOT NULL UNIQUE,
    department VARCHAR(100),
    position VARCHAR(100),
    trackabi_id VARCHAR(100),
    desklog_id VARCHAR(100),
    role_id INTEGER REFERENCES roles(role_id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Screen Share Sessions table
CREATE TABLE IF NOT EXISTS screen_share_sessions (
    session_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE,
    screen_share_on_time TIMESTAMP NOT NULL,
    screen_share_on_reason TEXT,
    screen_share_off_time TIMESTAMP,
    screen_share_off_reason TEXT,
    duration_minutes INTEGER,
    is_screen_shared BOOLEAN DEFAULT FALSE,
    is_screen_frozen BOOLEAN DEFAULT FALSE,
    not_shared_duration_minutes INTEGER DEFAULT 0,
    screen_frozen_duration_minutes INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_users_discord_id ON users(discord_id);
CREATE INDEX IF NOT EXISTS idx_screen_share_user_id ON screen_share_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_screen_share_on_time ON screen_share_sessions(screen_share_on_time);