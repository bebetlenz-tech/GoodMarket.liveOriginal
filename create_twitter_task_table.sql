
-- ====================================
-- TWITTER TASK TABLE
-- ====================================
-- Complete table structure for Twitter Task module
-- Run this in your Supabase SQL Editor

-- Create twitter_task_log table for tracking Twitter task submissions
CREATE TABLE IF NOT EXISTS twitter_task_log (
    id SERIAL PRIMARY KEY,
    wallet_address VARCHAR(42) NOT NULL,
    twitter_url TEXT NOT NULL,
    reward_amount DECIMAL(18,8) NOT NULL,
    transaction_hash VARCHAR(66),
    status VARCHAR(20) DEFAULT 'pending',
    approved_by VARCHAR(42),
    approved_at TIMESTAMP WITH TIME ZONE,
    rejected_by VARCHAR(42),
    rejected_at TIMESTAMP WITH TIME ZONE,
    rejection_reason TEXT,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(twitter_url)
);

-- Create indexes for twitter_task_log
CREATE INDEX IF NOT EXISTS idx_twitter_task_wallet ON twitter_task_log(wallet_address);
CREATE INDEX IF NOT EXISTS idx_twitter_task_status ON twitter_task_log(status);
CREATE INDEX IF NOT EXISTS idx_twitter_task_created ON twitter_task_log(created_at);
CREATE INDEX IF NOT EXISTS idx_twitter_task_url ON twitter_task_log(twitter_url);
CREATE INDEX IF NOT EXISTS idx_twitter_task_tx_hash ON twitter_task_log(transaction_hash);

-- Enable RLS for twitter_task_log
ALTER TABLE twitter_task_log ENABLE ROW LEVEL SECURITY;

-- Create policy for twitter_task_log
CREATE POLICY "Allow all operations on twitter_task_log" ON twitter_task_log FOR ALL USING (true);

-- Create function to auto-update updated_at timestamp (if not exists)
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger for auto-updating updated_at on twitter_task_log
CREATE TRIGGER update_twitter_task_log_updated_at 
    BEFORE UPDATE ON twitter_task_log 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- ====================================
-- COLUMN DESCRIPTIONS
-- ====================================
-- id: Auto-incrementing primary key
-- wallet_address: User's wallet address who submitted the task
-- twitter_url: URL of the Twitter/X post (must be unique)
-- reward_amount: Amount of G$ to be rewarded (usually 100.0)
-- transaction_hash: Blockchain transaction hash after reward disbursement
-- status: Current status - 'pending', 'completed', 'rejected', 'failed'
-- approved_by: Admin wallet address who approved the submission
-- approved_at: Timestamp when approved
-- rejected_by: Admin wallet address who rejected the submission
-- rejected_at: Timestamp when rejected
-- rejection_reason: Reason for rejection (if rejected)
-- error_message: Error message if disbursement failed
-- created_at: Timestamp when record was created
-- updated_at: Timestamp when record was last updated
