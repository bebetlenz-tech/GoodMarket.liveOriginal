
-- Garden Balance Table for G$ Garden Minigame
-- This table tracks each user's accumulated garden earnings and withdrawal history

CREATE TABLE IF NOT EXISTS garden_balance (
    id SERIAL PRIMARY KEY,
    wallet_address VARCHAR(42) NOT NULL UNIQUE,
    total_earned DECIMAL(18,8) DEFAULT 0,
    total_withdrawn DECIMAL(18,8) DEFAULT 0,
    available_balance DECIMAL(18,8) DEFAULT 0,
    last_harvest_at TIMESTAMP WITH TIME ZONE,
    last_withdrawal_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Garden Withdrawal Log Table
CREATE TABLE IF NOT EXISTS garden_withdrawals (
    id SERIAL PRIMARY KEY,
    wallet_address VARCHAR(42) NOT NULL,
    amount DECIMAL(18,8) NOT NULL,
    transaction_hash VARCHAR(66),
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'completed', 'failed'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_garden_balance_wallet ON garden_balance(wallet_address);
CREATE INDEX IF NOT EXISTS idx_garden_withdrawals_wallet ON garden_withdrawals(wallet_address);
CREATE INDEX IF NOT EXISTS idx_garden_withdrawals_status ON garden_withdrawals(status);

-- Enable RLS
ALTER TABLE garden_balance ENABLE ROW LEVEL SECURITY;
ALTER TABLE garden_withdrawals ENABLE ROW LEVEL SECURITY;

-- Create policies
CREATE POLICY "Allow all operations on garden_balance" ON garden_balance FOR ALL USING (true);
CREATE POLICY "Allow all operations on garden_withdrawals" ON garden_withdrawals FOR ALL USING (true);

-- Create trigger for auto-updating updated_at
CREATE TRIGGER update_garden_balance_updated_at 
    BEFORE UPDATE ON garden_balance 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();
