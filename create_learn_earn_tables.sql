
-- ====================================
-- LEARN & EARN COMPLETE TABLE SETUP
-- ====================================
-- This file contains all tables needed for the Learn & Earn module
-- Run this in your Supabase SQL Editor to create all tables at once

-- First, create the update_updated_at_column() function if it doesn't exist
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ====================================
-- 1. QUIZ QUESTIONS TABLE
-- ====================================
CREATE TABLE IF NOT EXISTS quiz_questions (
    quiz_id SERIAL PRIMARY KEY,
    question_id VARCHAR(50) UNIQUE NOT NULL,
    question TEXT NOT NULL,
    answer_a TEXT NOT NULL,
    answer_b TEXT NOT NULL,
    answer_c TEXT NOT NULL,
    answer_d TEXT NOT NULL,
    correct VARCHAR(1) NOT NULL CHECK (correct IN ('A', 'B', 'C', 'D')),
    difficulty VARCHAR(20) DEFAULT 'medium',
    category VARCHAR(50) DEFAULT 'general',
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for quiz_questions
CREATE INDEX IF NOT EXISTS idx_quiz_questions_active ON quiz_questions(active);
CREATE INDEX IF NOT EXISTS idx_quiz_questions_difficulty ON quiz_questions(difficulty);
CREATE INDEX IF NOT EXISTS idx_quiz_questions_category ON quiz_questions(category);

-- Enable RLS for quiz_questions
ALTER TABLE quiz_questions ENABLE ROW LEVEL SECURITY;

-- Create policy for quiz_questions
CREATE POLICY "Allow all operations on quiz_questions" ON quiz_questions FOR ALL USING (true);

-- Create trigger for auto-updating updated_at
CREATE TRIGGER update_quiz_questions_updated_at 
    BEFORE UPDATE ON quiz_questions 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- ====================================
-- 2. QUIZ SETTINGS TABLE
-- ====================================
CREATE TABLE IF NOT EXISTS quiz_settings (
    id SERIAL PRIMARY KEY,
    questions_per_quiz INTEGER DEFAULT 5,
    time_limit_seconds INTEGER DEFAULT 300,
    reward_per_correct DECIMAL(10, 2) DEFAULT 200.00,
    cooldown_hours INTEGER DEFAULT 24,
    max_attempts_per_day INTEGER DEFAULT 1,
    min_correct_for_reward INTEGER DEFAULT 3,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Insert default settings if table is empty
INSERT INTO quiz_settings (
    questions_per_quiz, 
    time_limit_seconds, 
    reward_per_correct, 
    cooldown_hours, 
    max_attempts_per_day,
    min_correct_for_reward
)
SELECT 5, 300, 200.00, 24, 1, 3
WHERE NOT EXISTS (SELECT 1 FROM quiz_settings LIMIT 1);

-- Enable RLS for quiz_settings
ALTER TABLE quiz_settings ENABLE ROW LEVEL SECURITY;

-- Create policy for quiz_settings
CREATE POLICY "Allow all operations on quiz_settings" ON quiz_settings FOR ALL USING (true);

-- Create trigger for auto-updating updated_at
CREATE TRIGGER update_quiz_settings_updated_at 
    BEFORE UPDATE ON quiz_settings 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- ====================================
-- 3. LEARNEARN_LOG TABLE
-- ====================================
CREATE TABLE IF NOT EXISTS learnearn_log (
    id SERIAL PRIMARY KEY,
    wallet_address VARCHAR(42) NOT NULL,
    quiz_id VARCHAR(255) NOT NULL,
    amount_g$ DECIMAL(10, 2) NOT NULL,
    correct_answers INTEGER DEFAULT 0,
    total_questions INTEGER DEFAULT 0,
    answers JSONB DEFAULT '[]',
    status BOOLEAN DEFAULT false,
    transaction_hash VARCHAR(66),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for learnearn_log
CREATE INDEX IF NOT EXISTS idx_learnearn_log_wallet ON learnearn_log(wallet_address);
CREATE INDEX IF NOT EXISTS idx_learnearn_log_quiz_id ON learnearn_log(quiz_id);
CREATE INDEX IF NOT EXISTS idx_learnearn_log_timestamp ON learnearn_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_learnearn_log_status ON learnearn_log(status);

-- Enable RLS for learnearn_log
ALTER TABLE learnearn_log ENABLE ROW LEVEL SECURITY;

-- Create policy for learnearn_log
CREATE POLICY "Allow all operations on learnearn_log" ON learnearn_log FOR ALL USING (true);

-- Create trigger for auto-updating updated_at
CREATE TRIGGER update_learnearn_log_updated_at 
    BEFORE UPDATE ON learnearn_log 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- ====================================
-- 4. ACHIEVEMENT_CARD_SALES TABLE
-- ====================================
CREATE TABLE IF NOT EXISTS achievement_card_sales (
    id SERIAL PRIMARY KEY,
    wallet_address VARCHAR(42) NOT NULL,
    card_type VARCHAR(50) NOT NULL,
    price_g$ DECIMAL(10, 2) NOT NULL,
    transaction_hash VARCHAR(66),
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for achievement_card_sales
CREATE INDEX IF NOT EXISTS idx_achievement_card_sales_wallet ON achievement_card_sales(wallet_address);
CREATE INDEX IF NOT EXISTS idx_achievement_card_sales_status ON achievement_card_sales(status);
CREATE INDEX IF NOT EXISTS idx_achievement_card_sales_created_at ON achievement_card_sales(created_at);

-- Enable RLS for achievement_card_sales
ALTER TABLE achievement_card_sales ENABLE ROW LEVEL SECURITY;

-- Create policy for achievement_card_sales
CREATE POLICY "Allow all operations on achievement_card_sales" ON achievement_card_sales FOR ALL USING (true);

-- Create trigger for auto-updating updated_at
CREATE TRIGGER update_achievement_card_sales_updated_at 
    BEFORE UPDATE ON achievement_card_sales 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- ====================================
-- 5. LEARN_EARN_MODULE_LINKS TABLE
-- ====================================
CREATE TABLE IF NOT EXISTS learn_earn_module_links (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    description TEXT,
    display_order INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_module_links_active ON learn_earn_module_links(is_active, display_order);

-- Enable RLS for learn_earn_module_links
ALTER TABLE learn_earn_module_links ENABLE ROW LEVEL SECURITY;

-- Create policies for learn_earn_module_links
CREATE POLICY "Allow read access to active module links" ON learn_earn_module_links
    FOR SELECT
    USING (is_active = true);

CREATE POLICY "Allow service role to manage module links" ON learn_earn_module_links
    FOR ALL
    USING (auth.role() = 'service_role');

-- Create trigger for auto-updating updated_at
CREATE TRIGGER update_module_links_updated_at 
    BEFORE UPDATE ON learn_earn_module_links 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- ====================================
-- 6. ADMIN_ACTIONS_LOG TABLE
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

-- Enable RLS for admin_actions_log
ALTER TABLE admin_actions_log ENABLE ROW LEVEL SECURITY;

-- Create policy for admin_actions_log
CREATE POLICY "Allow all operations on admin_actions_log" ON admin_actions_log FOR ALL USING (true);

-- Create trigger for auto-updating updated_at on admin_actions_log
CREATE TRIGGER update_admin_actions_log_updated_at 
    BEFORE UPDATE ON admin_actions_log 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- ====================================
-- VERIFICATION
-- ====================================
-- Run this to verify all tables were created successfully:
-- SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name IN (
--     'quiz_questions', 
--     'quiz_settings', 
--     'learnearn_log', 
--     'achievement_card_sales', 
--     'learn_earn_module_links',
--     'admin_actions_log'
-- );
