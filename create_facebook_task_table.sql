
-- ====================================
-- FACEBOOK TASK TABLE
-- ====================================

-- Create facebook_task_log table for tracking Facebook task submissions
CREATE TABLE IF NOT EXISTS facebook_task_log (
    id SERIAL PRIMARY KEY,
    wallet_address VARCHAR(42) NOT NULL,
    facebook_url TEXT NOT NULL,
    reward_amount DECIMAL(18,8) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'completed', 'rejected', 'failed'
    transaction_hash VARCHAR(66),
    approved_by VARCHAR(42),
    approved_at TIMESTAMP WITH TIME ZONE,
    rejected_by VARCHAR(42),
    rejected_at TIMESTAMP WITH TIME ZONE,
    rejection_reason TEXT,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for facebook_task_log
CREATE INDEX IF NOT EXISTS idx_facebook_task_log_wallet ON facebook_task_log(wallet_address);
CREATE INDEX IF NOT EXISTS idx_facebook_task_log_status ON facebook_task_log(status);
CREATE INDEX IF NOT EXISTS idx_facebook_task_log_created_at ON facebook_task_log(created_at);
CREATE INDEX IF NOT EXISTS idx_facebook_task_log_facebook_url ON facebook_task_log(facebook_url);

-- Enable RLS for facebook_task_log
ALTER TABLE facebook_task_log ENABLE ROW LEVEL SECURITY;

-- Create policy for facebook_task_log (allow all operations)
CREATE POLICY "Allow all operations on facebook_task_log" ON facebook_task_log FOR ALL USING (true);

-- Create trigger for auto-updating updated_at on facebook_task_log
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_facebook_task_log_updated_at 
    BEFORE UPDATE ON facebook_task_log 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();
