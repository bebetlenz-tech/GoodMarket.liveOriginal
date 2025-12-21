
-- ====================================
-- UBI VERIFICATION TABLE
-- ====================================
-- Complete table structure for UBI Verification tracking
-- Run this in your Supabase SQL Editor

-- Create ubi_verification_log table for tracking UBI verification attempts and results
CREATE TABLE IF NOT EXISTS ubi_verification_log (
    id SERIAL PRIMARY KEY,
    wallet_address VARCHAR(42) NOT NULL,
    verification_status VARCHAR(20) NOT NULL, -- 'success', 'failed', 'expired'
    verification_method VARCHAR(50) DEFAULT 'blockchain_check',
    ubi_claim_found BOOLEAN DEFAULT false,
    latest_claim_block INTEGER,
    latest_claim_timestamp TIMESTAMP WITH TIME ZONE,
    latest_claim_amount DECIMAL(18,8),
    total_activities_found INTEGER DEFAULT 0,
    activities_breakdown JSONB, -- JSON object with claims, events, etc.
    error_message TEXT,
    ip_address VARCHAR(45),
    user_agent TEXT,
    session_id VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for ubi_verification_log
CREATE INDEX IF NOT EXISTS idx_ubi_verification_wallet ON ubi_verification_log(wallet_address);
CREATE INDEX IF NOT EXISTS idx_ubi_verification_status ON ubi_verification_log(verification_status);
CREATE INDEX IF NOT EXISTS idx_ubi_verification_created ON ubi_verification_log(created_at);
CREATE INDEX IF NOT EXISTS idx_ubi_verification_session ON ubi_verification_log(session_id);
CREATE INDEX IF NOT EXISTS idx_ubi_verification_claim_timestamp ON ubi_verification_log(latest_claim_timestamp);

-- Enable RLS for ubi_verification_log
ALTER TABLE ubi_verification_log ENABLE ROW LEVEL SECURITY;

-- Create policy for ubi_verification_log
CREATE POLICY "Allow all operations on ubi_verification_log" ON ubi_verification_log FOR ALL USING (true);

-- Create function to auto-update updated_at timestamp (if not exists)
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger for auto-updating updated_at on ubi_verification_log
CREATE TRIGGER update_ubi_verification_log_updated_at 
    BEFORE UPDATE ON ubi_verification_log 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- ====================================
-- COLUMN DESCRIPTIONS
-- ====================================
-- id: Auto-incrementing primary key
-- wallet_address: User's wallet address being verified
-- verification_status: Result of verification - 'success', 'failed', 'expired'
-- verification_method: Method used - 'blockchain_check', 'cached', etc.
-- ubi_claim_found: Whether UBI claim activity was found
-- latest_claim_block: Block number of latest UBI claim
-- latest_claim_timestamp: Timestamp of latest UBI claim
-- latest_claim_amount: Amount of G$ claimed
-- total_activities_found: Total number of UBI activities found (claims + events)
-- activities_breakdown: JSON object with detailed breakdown of activities
-- error_message: Error message if verification failed
-- ip_address: IP address of verification request
-- user_agent: Browser user agent
-- session_id: Session ID for tracking
-- created_at: Timestamp when verification was performed
-- updated_at: Timestamp when record was last updated
