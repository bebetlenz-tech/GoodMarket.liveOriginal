
-- ====================================
-- COMMUNITY STORIES TABLES
-- ====================================
-- Complete table structure for Community Stories module
-- Run this in your Supabase SQL Editor

-- ====================================
-- 1. COMMUNITY STORIES SUBMISSIONS TABLE
-- ====================================
CREATE TABLE IF NOT EXISTS community_stories_submissions (
    id SERIAL PRIMARY KEY,
    submission_id VARCHAR(100) UNIQUE NOT NULL,
    wallet_address VARCHAR(42) NOT NULL,
    tweet_url TEXT NOT NULL,
    storage_path TEXT, -- ImgBB URL for screenshots
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'approved_low', 'approved_high', 'rejected', 'approved'
    reward_amount DECIMAL(18,8) DEFAULT 0,
    transaction_hash VARCHAR(66),
    reviewed_at TIMESTAMP WITH TIME ZONE,
    reviewed_by VARCHAR(42),
    admin_comment TEXT,
    submitted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for community_stories_submissions
CREATE INDEX IF NOT EXISTS idx_cs_submissions_wallet ON community_stories_submissions(wallet_address);
CREATE INDEX IF NOT EXISTS idx_cs_submissions_status ON community_stories_submissions(status);
CREATE INDEX IF NOT EXISTS idx_cs_submissions_submission_id ON community_stories_submissions(submission_id);
CREATE INDEX IF NOT EXISTS idx_cs_submissions_submitted_at ON community_stories_submissions(submitted_at);
CREATE INDEX IF NOT EXISTS idx_cs_submissions_reviewed_at ON community_stories_submissions(reviewed_at);

-- Enable RLS
ALTER TABLE community_stories_submissions ENABLE ROW LEVEL SECURITY;

-- Create policy
CREATE POLICY "Allow all operations on community_stories_submissions" ON community_stories_submissions FOR ALL USING (true);

-- ====================================
-- 2. COMMUNITY STORIES COOLDOWNS TABLE
-- ====================================
CREATE TABLE IF NOT EXISTS community_stories_cooldowns (
    id SERIAL PRIMARY KEY,
    wallet_address VARCHAR(42) UNIQUE NOT NULL,
    last_reward_month VARCHAR(7), -- Format: 'YYYY-MM'
    last_reward_amount DECIMAL(18,8),
    last_reward_date TIMESTAMP WITH TIME ZONE,
    total_earned DECIMAL(18,8) DEFAULT 0,
    total_submissions INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for community_stories_cooldowns
CREATE INDEX IF NOT EXISTS idx_cs_cooldowns_wallet ON community_stories_cooldowns(wallet_address);
CREATE INDEX IF NOT EXISTS idx_cs_cooldowns_last_reward_month ON community_stories_cooldowns(last_reward_month);

-- Enable RLS
ALTER TABLE community_stories_cooldowns ENABLE ROW LEVEL SECURITY;

-- Create policy
CREATE POLICY "Allow all operations on community_stories_cooldowns" ON community_stories_cooldowns FOR ALL USING (true);

-- ====================================
-- 3. COMMUNITY STORIES ADMIN NOTIFICATIONS TABLE
-- ====================================
CREATE TABLE IF NOT EXISTS community_stories_admin_notifications (
    id SERIAL PRIMARY KEY,
    submission_id VARCHAR(100) NOT NULL,
    admin_wallet VARCHAR(42) NOT NULL,
    is_read BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    FOREIGN KEY (submission_id) REFERENCES community_stories_submissions(submission_id) ON DELETE CASCADE
);

-- Create indexes for community_stories_admin_notifications
CREATE INDEX IF NOT EXISTS idx_cs_notifications_submission ON community_stories_admin_notifications(submission_id);
CREATE INDEX IF NOT EXISTS idx_cs_notifications_admin ON community_stories_admin_notifications(admin_wallet);
CREATE INDEX IF NOT EXISTS idx_cs_notifications_is_read ON community_stories_admin_notifications(is_read);

-- Enable RLS
ALTER TABLE community_stories_admin_notifications ENABLE ROW LEVEL SECURITY;

-- Create policy
CREATE POLICY "Allow all operations on community_stories_admin_notifications" ON community_stories_admin_notifications FOR ALL USING (true);

-- ====================================
-- AUTO-UPDATE TRIGGERS
-- ====================================

-- Create function to auto-update updated_at timestamp (if not exists)
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for auto-updating updated_at
CREATE TRIGGER update_cs_submissions_updated_at 
    BEFORE UPDATE ON community_stories_submissions 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_cs_cooldowns_updated_at 
    BEFORE UPDATE ON community_stories_cooldowns 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_cs_notifications_updated_at 
    BEFORE UPDATE ON community_stories_admin_notifications 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- ====================================
-- COLUMN DESCRIPTIONS
-- ====================================

-- community_stories_submissions columns:
-- id: Auto-incrementing primary key
-- submission_id: Unique submission ID (format: CS{12-char-hex})
-- wallet_address: User's wallet address
-- tweet_url: Twitter/X post URL (or '#' for direct screenshot uploads)
-- storage_path: ImgBB URL for screenshot images
-- status: Submission status - 'pending', 'approved_low' (1000 G$), 'approved_high' (5000 G$), 'rejected', 'approved'
-- reward_amount: Amount of G$ rewarded (0 for pending/rejected)
-- transaction_hash: Celo blockchain transaction hash
-- reviewed_at: Timestamp when admin reviewed
-- reviewed_by: Admin wallet address who reviewed
-- admin_comment: Admin's comment/reason for rejection
-- submitted_at: Timestamp when user submitted
-- created_at: Record creation timestamp
-- updated_at: Record update timestamp

-- community_stories_cooldowns columns:
-- id: Auto-incrementing primary key
-- wallet_address: User's wallet address (unique)
-- last_reward_month: Last month user received reward (format: 'YYYY-MM')
-- last_reward_amount: Amount of last reward received
-- last_reward_date: Date of last reward
-- total_earned: Total G$ earned from Community Stories
-- total_submissions: Total number of approved submissions
-- created_at: Record creation timestamp
-- updated_at: Record update timestamp

-- community_stories_admin_notifications columns:
-- id: Auto-incrementing primary key
-- submission_id: Reference to submission
-- admin_wallet: Admin wallet address to notify
-- is_read: Whether admin has seen the notification
-- created_at: Notification creation timestamp
-- updated_at: Record update timestamp
