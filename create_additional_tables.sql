
-- ====================================
-- ADDITIONAL MISSING TABLES
-- ====================================
-- Complete table structure for missing modules
-- Run this in your Supabase SQL Editor

-- ====================================
-- 1. RELOADLY ORDERS TABLE (Mobile Top-Up)
-- ====================================
CREATE TABLE IF NOT EXISTS reloadly_orders (
    id SERIAL PRIMARY KEY,
    order_id VARCHAR(50) UNIQUE NOT NULL,
    wallet_address VARCHAR(42) NOT NULL,
    phone_number VARCHAR(20) NOT NULL,
    operator_id INTEGER NOT NULL,
    product_id VARCHAR(100),
    local_amount DECIMAL(10,2) NOT NULL,
    local_currency VARCHAR(10) NOT NULL,
    g_dollar_amount DECIMAL(18,8) NOT NULL,
    amount DECIMAL(18,8), -- backward compatibility
    status VARCHAR(50) DEFAULT 'pending_payment',
    merchant_address VARCHAR(42),
    payment_timeout TIMESTAMP WITH TIME ZONE,
    transaction_hash VARCHAR(66),
    reloadly_transaction_id VARCHAR(100),
    payment_confirmed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for reloadly_orders
CREATE INDEX IF NOT EXISTS idx_reloadly_orders_wallet ON reloadly_orders(wallet_address);
CREATE INDEX IF NOT EXISTS idx_reloadly_orders_order_id ON reloadly_orders(order_id);
CREATE INDEX IF NOT EXISTS idx_reloadly_orders_status ON reloadly_orders(status);
CREATE INDEX IF NOT EXISTS idx_reloadly_orders_created_at ON reloadly_orders(created_at);

-- Enable RLS
ALTER TABLE reloadly_orders ENABLE ROW LEVEL SECURITY;

-- Create policy
CREATE POLICY "Allow all operations on reloadly_orders" ON reloadly_orders FOR ALL USING (true);

-- Create trigger
CREATE TRIGGER update_reloadly_orders_updated_at 
    BEFORE UPDATE ON reloadly_orders 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- ====================================
-- 2. COMMUNITY SCREENSHOTS TABLE
-- ====================================
CREATE TABLE IF NOT EXISTS community_screenshots (
    id SERIAL PRIMARY KEY,
    screenshot_url TEXT NOT NULL,
    wallet_address VARCHAR(42) DEFAULT 'admin_requirement',
    title VARCHAR(200),
    image_type VARCHAR(50) DEFAULT 'requirement', -- 'requirement', 'user_submission'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_community_screenshots_image_type ON community_screenshots(image_type);
CREATE INDEX IF NOT EXISTS idx_community_screenshots_wallet ON community_screenshots(wallet_address);
CREATE INDEX IF NOT EXISTS idx_community_screenshots_created_at ON community_screenshots(created_at);

-- Enable RLS
ALTER TABLE community_screenshots ENABLE ROW LEVEL SECURITY;

-- Create policy
CREATE POLICY "Allow all operations on community_screenshots" ON community_screenshots FOR ALL USING (true);

-- ====================================
-- 3. ADMIN BROADCAST MESSAGES TABLE
-- ====================================
CREATE TABLE IF NOT EXISTS admin_broadcast_messages (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    sender_wallet VARCHAR(42) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_admin_broadcast_messages_active ON admin_broadcast_messages(is_active);
CREATE INDEX IF NOT EXISTS idx_admin_broadcast_messages_created_at ON admin_broadcast_messages(created_at);
CREATE INDEX IF NOT EXISTS idx_admin_broadcast_messages_sender ON admin_broadcast_messages(sender_wallet);

-- Enable RLS
ALTER TABLE admin_broadcast_messages ENABLE ROW LEVEL SECURITY;

-- Create policy
CREATE POLICY "Allow all operations on admin_broadcast_messages" ON admin_broadcast_messages FOR ALL USING (true);

-- Create trigger
CREATE TRIGGER update_admin_broadcast_messages_updated_at 
    BEFORE UPDATE ON admin_broadcast_messages 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- ====================================
-- 4. FORUM IMAGES TABLE
-- ====================================
CREATE TABLE IF NOT EXISTS forum_images (
    id SERIAL PRIMARY KEY,
    post_id INTEGER NOT NULL,
    image_url TEXT NOT NULL,
    uploaded_by VARCHAR(42) NOT NULL,
    upload_source VARCHAR(50) DEFAULT 'url', -- 'imgbb', 'url', 'other'
    image_size_bytes INTEGER,
    image_width INTEGER,
    image_height INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_forum_images_post_id ON forum_images(post_id);
CREATE INDEX IF NOT EXISTS idx_forum_images_uploaded_by ON forum_images(uploaded_by);
CREATE INDEX IF NOT EXISTS idx_forum_images_created_at ON forum_images(created_at);

-- Enable RLS
ALTER TABLE forum_images ENABLE ROW LEVEL SECURITY;

-- Create policy
CREATE POLICY "Allow all operations on forum_images" ON forum_images FOR ALL USING (true);

-- ====================================
-- 5. TASK COMPLETION SYSTEM TABLES
-- ====================================

-- Task completion log table
CREATE TABLE IF NOT EXISTS task_completion_log (
    id SERIAL PRIMARY KEY,
    transaction_hash VARCHAR(66) NOT NULL,
    wallet_address VARCHAR(42) NOT NULL,
    task_id VARCHAR(50) NOT NULL,
    task_type VARCHAR(50) NOT NULL,
    reward_amount DECIMAL(18,8) NOT NULL,
    status VARCHAR(20) DEFAULT 'completed',
    verification_method VARCHAR(50),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- User task progress table
CREATE TABLE IF NOT EXISTS user_task_progress (
    id SERIAL PRIMARY KEY,
    wallet_address VARCHAR(42) NOT NULL,
    task_id VARCHAR(50) NOT NULL,
    progress JSONB DEFAULT '{}',
    completed_at TIMESTAMP WITH TIME ZONE,
    last_attempt TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    streak_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(wallet_address, task_id)
);

-- Create indexes for task completion system
CREATE INDEX IF NOT EXISTS idx_task_completion_log_wallet ON task_completion_log(wallet_address);
CREATE INDEX IF NOT EXISTS idx_task_completion_log_task_id ON task_completion_log(task_id);
CREATE INDEX IF NOT EXISTS idx_task_completion_log_timestamp ON task_completion_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_user_task_progress_wallet ON user_task_progress(wallet_address);
CREATE INDEX IF NOT EXISTS idx_user_task_progress_task_id ON user_task_progress(task_id);

-- Enable RLS
ALTER TABLE task_completion_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_task_progress ENABLE ROW LEVEL SECURITY;

-- Create policies
CREATE POLICY "Allow all operations on task_completion_log" ON task_completion_log FOR ALL USING (true);
CREATE POLICY "Allow all operations on user_task_progress" ON user_task_progress FOR ALL USING (true);
