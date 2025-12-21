
-- ====================================
-- ANALYTICS TABLES
-- ====================================
-- Complete table structure for Analytics module
-- Run this in your Supabase SQL Editor

-- ====================================
-- 1. USER DATA TABLE
-- ====================================
CREATE TABLE IF NOT EXISTS user_data (
    id SERIAL PRIMARY KEY,
    wallet_address VARCHAR(42) UNIQUE NOT NULL,
    first_login TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    total_logins INTEGER DEFAULT 1,
    total_sessions INTEGER DEFAULT 0,
    ubi_verified BOOLEAN DEFAULT FALSE,
    verification_timestamp TIMESTAMP WITH TIME ZONE,
    total_page_views INTEGER DEFAULT 0,
    user_agent TEXT,
    ip_address INET,
    username VARCHAR(50) UNIQUE,
    username_set_at TIMESTAMP WITH TIME ZONE,
    username_edited BOOLEAN DEFAULT FALSE,
    username_last_edited TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for user_data
CREATE INDEX IF NOT EXISTS idx_user_data_wallet ON user_data(wallet_address);
CREATE INDEX IF NOT EXISTS idx_user_data_verified ON user_data(ubi_verified);

-- Enable RLS
ALTER TABLE user_data ENABLE ROW LEVEL SECURITY;

-- Create policy
CREATE POLICY "Allow all operations on user_data" ON user_data FOR ALL USING (true);

-- Create trigger for auto-updating updated_at
CREATE TRIGGER update_user_data_updated_at 
    BEFORE UPDATE ON user_data 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- ====================================
-- 2. USER SESSIONS TABLE
-- ====================================
CREATE TABLE IF NOT EXISTS user_sessions (
    id SERIAL PRIMARY KEY,
    wallet_address VARCHAR(42) NOT NULL,
    activity_type VARCHAR(50) NOT NULL, -- 'login', 'logout', 'page_view', 'verification_attempt', 'ubi_activity'
    session_id VARCHAR(100),
    page VARCHAR(100),
    success BOOLEAN,
    details JSONB,
    ip_address INET,
    user_agent TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Foreign key reference
    CONSTRAINT fk_user_sessions_wallet 
        FOREIGN KEY (wallet_address) 
        REFERENCES user_data(wallet_address) 
        ON DELETE CASCADE
);

-- Create indexes for user_sessions
CREATE INDEX IF NOT EXISTS idx_user_sessions_wallet ON user_sessions(wallet_address);
CREATE INDEX IF NOT EXISTS idx_user_sessions_activity ON user_sessions(activity_type);
CREATE INDEX IF NOT EXISTS idx_user_sessions_timestamp ON user_sessions(timestamp);
CREATE INDEX IF NOT EXISTS idx_user_sessions_session_id ON user_sessions(session_id);

-- Enable RLS
ALTER TABLE user_sessions ENABLE ROW LEVEL SECURITY;

-- Create policy
CREATE POLICY "Allow all operations on user_sessions" ON user_sessions FOR ALL USING (true);

-- ====================================
-- 3. ADMIN ACTIONS LOG TABLE
-- ====================================
CREATE TABLE IF NOT EXISTS admin_actions_log (
    id SERIAL PRIMARY KEY,
    admin_wallet VARCHAR(42) NOT NULL,
    action_type VARCHAR(100) NOT NULL,
    action_details JSONB DEFAULT '{}',
    target_wallet VARCHAR(42),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for admin_actions_log
CREATE INDEX IF NOT EXISTS idx_admin_actions_log_admin_wallet ON admin_actions_log(admin_wallet);
CREATE INDEX IF NOT EXISTS idx_admin_actions_log_action_type ON admin_actions_log(action_type);
CREATE INDEX IF NOT EXISTS idx_admin_actions_log_target_wallet ON admin_actions_log(target_wallet);
CREATE INDEX IF NOT EXISTS idx_admin_actions_log_created_at ON admin_actions_log(created_at);

-- Enable RLS
ALTER TABLE admin_actions_log ENABLE ROW LEVEL SECURITY;

-- Create policy
CREATE POLICY "Allow all operations on admin_actions_log" ON admin_actions_log FOR ALL USING (true);

-- Create trigger for auto-updating updated_at
CREATE TRIGGER update_admin_actions_log_updated_at 
    BEFORE UPDATE ON admin_actions_log 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- ====================================
-- COLUMN DESCRIPTIONS
-- ====================================

-- user_data columns:
-- id: Auto-incrementing primary key
-- wallet_address: User's wallet address (unique)
-- first_login: Timestamp of first login
-- last_login: Timestamp of last login
-- total_logins: Total number of logins
-- total_sessions: Total number of sessions
-- ubi_verified: Whether user is UBI verified
-- verification_timestamp: Timestamp of verification
-- total_page_views: Total page views
-- user_agent: Browser user agent
-- ip_address: User's IP address
-- username: User's chosen username (unique)
-- username_set_at: When username was first set
-- username_edited: Whether username has been edited
-- username_last_edited: Last time username was edited
-- created_at: Record creation timestamp
-- updated_at: Record update timestamp

-- user_sessions columns:
-- id: Auto-incrementing primary key
-- wallet_address: User's wallet address
-- activity_type: Type of activity ('login', 'logout', 'page_view', etc.)
-- session_id: Session identifier
-- page: Page visited
-- success: Whether activity was successful
-- details: Additional details (JSON)
-- ip_address: User's IP address
-- user_agent: Browser user agent
-- timestamp: Activity timestamp
-- created_at: Record creation timestamp

-- admin_actions_log columns:
-- id: Auto-incrementing primary key
-- admin_wallet: Admin's wallet address
-- action_type: Type of admin action
-- action_details: Action details (JSON)
-- target_wallet: Target user's wallet address
-- created_at: Action timestamp
-- updated_at: Record update timestamp
