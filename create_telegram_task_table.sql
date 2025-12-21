
-- ====================================
-- TELEGRAM TASK TABLE
-- ====================================
-- Complete table structure for Telegram Task module
-- Run this in your Supabase SQL Editor

-- Create telegram_task_log table for tracking Telegram task submissions
CREATE TABLE IF NOT EXISTS telegram_task_log (
    id SERIAL PRIMARY KEY,
    wallet_address VARCHAR(42) NOT NULL,
    telegram_url TEXT NOT NULL,
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
    UNIQUE(telegram_url)
);

-- Create indexes for telegram_task_log
CREATE INDEX IF NOT EXISTS idx_telegram_task_wallet ON telegram_task_log(wallet_address);
CREATE INDEX IF NOT EXISTS idx_telegram_task_status ON telegram_task_log(status);
CREATE INDEX IF NOT EXISTS idx_telegram_task_created ON telegram_task_log(created_at);
CREATE INDEX IF NOT EXISTS idx_telegram_task_url ON telegram_task_log(telegram_url);
CREATE INDEX IF NOT EXISTS idx_telegram_task_tx_hash ON telegram_task_log(transaction_hash);

-- Enable RLS for telegram_task_log
ALTER TABLE telegram_task_log ENABLE ROW LEVEL SECURITY;

-- Create policy for telegram_task_log
CREATE POLICY "Allow all operations on telegram_task_log" ON telegram_task_log FOR ALL USING (true);

-- Create function to auto-update updated_at timestamp (if not exists)
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger for auto-updating updated_at on telegram_task_log
CREATE TRIGGER update_telegram_task_log_updated_at 
    BEFORE UPDATE ON telegram_task_log 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- ====================================
-- COLUMN DESCRIPTIONS
-- ====================================
-- id: Auto-incrementing primary key
-- wallet_address: User's wallet address who submitted the task
-- telegram_url: URL of the Telegram post (must be unique)
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
