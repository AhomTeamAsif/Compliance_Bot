-- Role table
CREATE TABLE IF NOT EXISTS roles (
    role_id SERIAL PRIMARY KEY,
    role_name VARCHAR(100) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT TIMEZONE('utc', CURRENT_TIMESTAMP)
);

--insert roles
INSERT INTO roles (role_name) 
VALUES 
    ('SUPER'), 
    ('ADMIN'), 
    ('NORMAL')
ON CONFLICT (role_name) DO NOTHING;

-- Users table

CREATE TABLE IF NOT EXISTS users (
    user_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    department VARCHAR(100),
    position VARCHAR(100),
    discord_id BIGINT,
    trackabi_id VARCHAR(100),
    desklog_id VARCHAR(100),
    role_id INTEGER REFERENCES roles(role_id) ON DELETE SET NULL DEFAULT 3,
    pending_leaves INTEGER DEFAULT 10,
    is_deleted BOOLEAN DEFAULT FALSE,
    contract_started_at TIMESTAMP DEFAULT TIMEZONE('utc', CURRENT_TIMESTAMP),
    created_at TIMESTAMP DEFAULT TIMEZONE('utc', CURRENT_TIMESTAMP),
    updated_at TIMESTAMP DEFAULT TIMEZONE('utc', CURRENT_TIMESTAMP)
);

-- User delete log table
CREATE TABLE IF NOT EXISTS user_delete_logs (
    id SERIAL PRIMARY KEY,
    deleted_user_id INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
    deleted_by_user_id INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
    reason TEXT,
    seniors_informed BOOLEAN,
    admins_informed BOOLEAN,
    is_with_us BOOLEAN,
    deleted_at TIMESTAMP DEFAULT TIMEZONE('utc', CURRENT_TIMESTAMP)
);

-- Permissions table
CREATE TABLE IF NOT EXISTS permissions (
    permission_id SERIAL PRIMARY KEY,
    permission_name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP DEFAULT TIMEZONE('utc', CURRENT_TIMESTAMP)
);

-- Insert predefined permissions
INSERT INTO permissions (permission_name, description) 
VALUES
    ('administer', 'Administrative privilages'),
    ('user_register', 'Register new users'),
    ('user_update', 'Update user information'),
    ('user_delete', 'Delete users'),
    ('discipline_compliance', 'Manage discipline and compliance'),
    ('view_reports', 'View system reports'),
    ('manage_permissions', 'Manage user permissions')
ON CONFLICT (permission_name) DO NOTHING;

-- User-permissions junction table (individual user permissions)
CREATE TABLE IF NOT EXISTS user_permissions (
    user_permission_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE,
    permission_id INTEGER REFERENCES permissions(permission_id) ON DELETE CASCADE,
    granted_at TIMESTAMP DEFAULT TIMEZONE('utc', CURRENT_TIMESTAMP),
    granted_by INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
    UNIQUE(user_id, permission_id)
);

-- Time tracking tables
CREATE TABLE IF NOT EXISTS time_tracking (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    starting_time TIMESTAMP NOT NULL,
    end_of_the_day TIMESTAMP,
    present_date DATE NOT NULL,
    clock_in TIMESTAMP[],
    clock_out TIMESTAMP[],
    clockin_reason TEXT[],
    clockout_reason TEXT[],
    time_logged_in INTEGER DEFAULT 0,
    break_duration INTEGER DEFAULT 0,
    break_counter INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT TIMEZONE('utc', CURRENT_TIMESTAMP),

    CONSTRAINT fk_user_time_tracking FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- Late arrival tracking
CREATE TABLE IF NOT EXISTS late_reasons (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    time_tracking_id INTEGER NOT NULL REFERENCES time_tracking(id) ON DELETE CASCADE,
    late_mins INTEGER NOT NULL,
    reason TEXT NOT NULL,
    is_admin_informed BOOLEAN DEFAULT FALSE,
    morning_meeting_attended BOOLEAN DEFAULT FALSE,
    recorded_at TIMESTAMP DEFAULT TIMEZONE('utc', CURRENT_TIMESTAMP),
    admin_approval BOOLEAN DEFAULT FALSE,
    
    CONSTRAINT fk_user_late FOREIGN KEY (user_id) REFERENCES users(user_id),
    CONSTRAINT fk_time_tracking_late FOREIGN KEY (time_tracking_id) REFERENCES time_tracking(id)
);

-- Daily work plan tracking
CREATE TABLE IF NOT EXISTS work_updates (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    time_tracking_id INTEGER NOT NULL REFERENCES time_tracking(id) ON DELETE CASCADE,
    start_of_the_day_plan TEXT[],
    desklog_on BOOLEAN DEFAULT FALSE,
    trackabi_on BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT TIMEZONE('utc', CURRENT_TIMESTAMP),
    admin_approval BOOLEAN DEFAULT FALSE,
    
    CONSTRAINT fk_user_work_update FOREIGN KEY (user_id) REFERENCES users(user_id),
    CONSTRAINT fk_time_tracking_work FOREIGN KEY (time_tracking_id) REFERENCES time_tracking(id)
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
    created_at TIMESTAMP DEFAULT TIMEZONE('utc', CURRENT_TIMESTAMP)
);

-- Daily compliance tracking table
CREATE TABLE IF NOT EXISTS daily_compliance (
    compliance_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    
    -- Desklog compliance
    desklog_usage BOOLEAN,
    desklog_reason TEXT,
    
    -- Trackabi compliance
    trackabi_usage BOOLEAN,
    trackabi_reason TEXT,
    
    -- Discord compliance
    discord_usage BOOLEAN,
    discord_reason TEXT,
    
    -- Break rules compliance
    break_usage BOOLEAN,
    break_reason TEXT,
    
    -- Google Drive backup compliance
    google_drive_usage BOOLEAN,
    google_drive_reason TEXT,
    
    -- Metadata
    recorded_by_discord_id BIGINT NOT NULL,
    recorded_at TIMESTAMP DEFAULT TIMEZONE('utc', CURRENT_TIMESTAMP),
    
    CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES users(user_id)
);



-- Indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_users_discord_id ON users(discord_id);
CREATE INDEX IF NOT EXISTS idx_screen_share_user_id ON screen_share_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_screen_share_on_time ON screen_share_sessions(screen_share_on_time);
CREATE INDEX IF NOT EXISTS idx_daily_compliance_user ON daily_compliance(user_id);
CREATE INDEX IF NOT EXISTS idx_daily_compliance_date ON daily_compliance(recorded_at);
CREATE INDEX IF NOT EXISTS idx_time_tracking_user_date ON time_tracking(user_id, present_date);
CREATE INDEX IF NOT EXISTS idx_time_tracking_date ON time_tracking(present_date);
CREATE INDEX IF NOT EXISTS idx_late_reasons_user ON late_reasons(user_id);
CREATE INDEX IF NOT EXISTS idx_work_updates_user ON work_updates(user_id);