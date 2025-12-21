
-- ====================================
-- MINIGAMES TABLES
-- ====================================
-- Complete table structure for Minigames module
-- Run this in your Supabase SQL Editor

-- ====================================
-- 1. MINIGAME_BALANCES TABLE
-- ====================================
-- Stores user's deposit balance and withdrawal totals
CREATE TABLE IF NOT EXISTS minigame_balances (
    id SERIAL PRIMARY KEY,
    wallet_address VARCHAR(42) NOT NULL UNIQUE,
    available_balance DECIMAL(18,8) DEFAULT 0,
    total_withdrawn DECIMAL(18,8) DEFAULT 0,
    last_deposit_date DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for minigame_balances
CREATE INDEX IF NOT EXISTS idx_minigame_balances_wallet ON minigame_balances(wallet_address);
CREATE INDEX IF NOT EXISTS idx_minigame_balances_updated ON minigame_balances(updated_at);

-- Enable RLS for minigame_balances
ALTER TABLE minigame_balances ENABLE ROW LEVEL SECURITY;

-- Create policy for minigame_balances
CREATE POLICY "Allow all operations on minigame_balances" ON minigame_balances FOR ALL USING (true);

-- ====================================
-- 2. MINIGAME_DEPOSITS_LOG TABLE
-- ====================================
-- Logs all deposits made to MERCHANT_ADDRESS
CREATE TABLE IF NOT EXISTS minigame_deposits_log (
    id SERIAL PRIMARY KEY,
    wallet_address VARCHAR(42) NOT NULL,
    amount DECIMAL(18,8) NOT NULL,
    tx_hash VARCHAR(66) NOT NULL UNIQUE,
    deposit_date DATE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for minigame_deposits_log
CREATE INDEX IF NOT EXISTS idx_minigame_deposits_wallet ON minigame_deposits_log(wallet_address);
CREATE INDEX IF NOT EXISTS idx_minigame_deposits_date ON minigame_deposits_log(deposit_date);
CREATE INDEX IF NOT EXISTS idx_minigame_deposits_tx_hash ON minigame_deposits_log(tx_hash);

-- Enable RLS for minigame_deposits_log
ALTER TABLE minigame_deposits_log ENABLE ROW LEVEL SECURITY;

-- Create policy for minigame_deposits_log
CREATE POLICY "Allow all operations on minigame_deposits_log" ON minigame_deposits_log FOR ALL USING (true);

-- ====================================
-- 3. MINIGAME_WITHDRAWALS_LOG TABLE
-- ====================================
-- Logs all withdrawals sent from GAMES_KEY
CREATE TABLE IF NOT EXISTS minigame_withdrawals_log (
    id SERIAL PRIMARY KEY,
    wallet_address VARCHAR(42) NOT NULL,
    amount DECIMAL(18,8) NOT NULL,
    tx_hash VARCHAR(66) NOT NULL,
    session_id VARCHAR(100),
    withdrawal_date DATE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for minigame_withdrawals_log
CREATE INDEX IF NOT EXISTS idx_minigame_withdrawals_wallet ON minigame_withdrawals_log(wallet_address);
CREATE INDEX IF NOT EXISTS idx_minigame_withdrawals_date ON minigame_withdrawals_log(withdrawal_date);
CREATE INDEX IF NOT EXISTS idx_minigame_withdrawals_tx_hash ON minigame_withdrawals_log(tx_hash);

-- Enable RLS for minigame_withdrawals_log
ALTER TABLE minigame_withdrawals_log ENABLE ROW LEVEL SECURITY;

-- Create policy for minigame_withdrawals_log
CREATE POLICY "Allow all operations on minigame_withdrawals_log" ON minigame_withdrawals_log FOR ALL USING (true);

-- ====================================
-- 4. MINIGAME_SESSIONS TABLE
-- ====================================
-- Tracks individual game sessions
CREATE TABLE IF NOT EXISTS minigame_sessions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL UNIQUE,
    wallet_address VARCHAR(42) NOT NULL,
    game_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'in_progress',
    bet_amount DECIMAL(18,8) DEFAULT 0,
    score INTEGER DEFAULT 0,
    g_dollar_earned DECIMAL(18,8) DEFAULT 0,
    game_data JSONB,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Create indexes for minigame_sessions
CREATE INDEX IF NOT EXISTS idx_minigame_sessions_wallet ON minigame_sessions(wallet_address);
CREATE INDEX IF NOT EXISTS idx_minigame_sessions_game_type ON minigame_sessions(game_type);
CREATE INDEX IF NOT EXISTS idx_minigame_sessions_status ON minigame_sessions(status);
CREATE INDEX IF NOT EXISTS idx_minigame_sessions_started ON minigame_sessions(started_at);

-- Enable RLS for minigame_sessions
ALTER TABLE minigame_sessions ENABLE ROW LEVEL SECURITY;

-- Create policy for minigame_sessions
CREATE POLICY "Allow all operations on minigame_sessions" ON minigame_sessions FOR ALL USING (true);

-- ====================================
-- 5. DAILY_GAME_LIMITS TABLE
-- ====================================
-- Tracks daily play limits for each game type
CREATE TABLE IF NOT EXISTS daily_game_limits (
    id SERIAL PRIMARY KEY,
    wallet_address VARCHAR(42) NOT NULL,
    game_date DATE NOT NULL,
    game_type VARCHAR(50) NOT NULL,
    plays_today INTEGER DEFAULT 0,
    earned_today DECIMAL(18,8) DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(wallet_address, game_type, game_date)
);

-- Create indexes for daily_game_limits
CREATE INDEX IF NOT EXISTS idx_daily_game_limits_wallet ON daily_game_limits(wallet_address);
CREATE INDEX IF NOT EXISTS idx_daily_game_limits_date ON daily_game_limits(game_date);
CREATE INDEX IF NOT EXISTS idx_daily_game_limits_game_type ON daily_game_limits(game_type);

-- Enable RLS for daily_game_limits
ALTER TABLE daily_game_limits ENABLE ROW LEVEL SECURITY;

-- Create policy for daily_game_limits
CREATE POLICY "Allow all operations on daily_game_limits" ON daily_game_limits FOR ALL USING (true);

-- ====================================
-- 6. USER_GAME_STATS TABLE
-- ====================================
-- Stores cumulative game statistics per user per game type
CREATE TABLE IF NOT EXISTS user_game_stats (
    id SERIAL PRIMARY KEY,
    wallet_address VARCHAR(42) NOT NULL,
    game_type VARCHAR(50) NOT NULL,
    total_plays INTEGER DEFAULT 0,
    total_score INTEGER DEFAULT 0,
    highest_score INTEGER DEFAULT 0,
    total_earned DECIMAL(18,8) DEFAULT 0,
    virtual_tokens INTEGER DEFAULT 0,
    last_played TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(wallet_address, game_type)
);

-- Create indexes for user_game_stats
CREATE INDEX IF NOT EXISTS idx_user_game_stats_wallet ON user_game_stats(wallet_address);
CREATE INDEX IF NOT EXISTS idx_user_game_stats_game_type ON user_game_stats(game_type);
CREATE INDEX IF NOT EXISTS idx_user_game_stats_last_played ON user_game_stats(last_played);

-- Enable RLS for user_game_stats
ALTER TABLE user_game_stats ENABLE ROW LEVEL SECURITY;

-- Create policy for user_game_stats
CREATE POLICY "Allow all operations on user_game_stats" ON user_game_stats FOR ALL USING (true);

-- ====================================
-- 7. MINIGAME_REWARDS_LOG TABLE
-- ====================================
-- Logs reward disbursements (for non-crash games if needed)
CREATE TABLE IF NOT EXISTS minigame_rewards_log (
    id SERIAL PRIMARY KEY,
    transaction_hash VARCHAR(66) NOT NULL,
    wallet_address VARCHAR(42) NOT NULL,
    game_type VARCHAR(50) NOT NULL,
    session_id VARCHAR(100),
    reward_amount DECIMAL(18,8) NOT NULL,
    score INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for minigame_rewards_log
CREATE INDEX IF NOT EXISTS idx_minigame_rewards_wallet ON minigame_rewards_log(wallet_address);
CREATE INDEX IF NOT EXISTS idx_minigame_rewards_game_type ON minigame_rewards_log(game_type);
CREATE INDEX IF NOT EXISTS idx_minigame_rewards_tx_hash ON minigame_rewards_log(transaction_hash);
CREATE INDEX IF NOT EXISTS idx_minigame_rewards_created ON minigame_rewards_log(created_at);

-- Enable RLS for minigame_rewards_log
ALTER TABLE minigame_rewards_log ENABLE ROW LEVEL SECURITY;

-- Create policy for minigame_rewards_log
CREATE POLICY "Allow all operations on minigame_rewards_log" ON minigame_rewards_log FOR ALL USING (true);

-- ====================================
-- TRIGGERS
-- ====================================
-- Create function to auto-update updated_at timestamp (if not exists)
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger for auto-updating updated_at on minigame_balances
CREATE TRIGGER update_minigame_balances_updated_at 
    BEFORE UPDATE ON minigame_balances 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- ====================================
-- COLUMN DESCRIPTIONS
-- ====================================

-- MINIGAME_BALANCES:
-- id: Auto-incrementing primary key
-- wallet_address: User's wallet address (unique)
-- available_balance: Current balance available for playing/withdrawal (deposits + winnings - bets - withdrawals)
-- total_withdrawn: Cumulative amount withdrawn
-- last_deposit_date: Date of last deposit
-- created_at: Timestamp when record was created
-- updated_at: Timestamp when record was last updated

-- MINIGAME_DEPOSITS_LOG:
-- id: Auto-incrementing primary key
-- wallet_address: User's wallet address who made the deposit
-- amount: Amount deposited in G$
-- tx_hash: Blockchain transaction hash (unique)
-- deposit_date: Date of deposit
-- created_at: Timestamp when record was created

-- MINIGAME_WITHDRAWALS_LOG:
-- id: Auto-incrementing primary key
-- wallet_address: User's wallet address who withdrew
-- amount: Amount withdrawn in G$
-- tx_hash: Blockchain transaction hash
-- session_id: Associated withdrawal session ID
-- withdrawal_date: Date of withdrawal
-- created_at: Timestamp when record was created

-- MINIGAME_SESSIONS:
-- id: Auto-incrementing primary key
-- session_id: Unique session identifier
-- wallet_address: User's wallet address
-- game_type: Type of game (crash_game, etc.)
-- status: Session status - 'in_progress', 'completed'
-- bet_amount: Amount bet in G$
-- score: Game score (for crash_game, multiplier * 100)
-- g_dollar_earned: Amount earned from this session
-- game_data: JSON data with game details (multiplier, cashed_out, crashed, etc.)
-- started_at: Timestamp when session started
-- completed_at: Timestamp when session completed

-- DAILY_GAME_LIMITS:
-- id: Auto-incrementing primary key
-- wallet_address: User's wallet address
-- game_date: Date for this limit tracking
-- game_type: Type of game
-- plays_today: Number of plays today
-- earned_today: Amount earned today
-- created_at: Timestamp when record was created

-- USER_GAME_STATS:
-- id: Auto-incrementing primary key
-- wallet_address: User's wallet address
-- game_type: Type of game
-- total_plays: Total number of plays
-- total_score: Cumulative score
-- highest_score: Highest score achieved
-- total_earned: Total amount earned
-- virtual_tokens: Virtual tokens earned (if applicable)
-- last_played: Timestamp of last play
-- created_at: Timestamp when record was created

-- MINIGAME_REWARDS_LOG:
-- id: Auto-incrementing primary key
-- transaction_hash: Blockchain transaction hash
-- wallet_address: User's wallet address who received reward
-- game_type: Type of game
-- session_id: Associated game session ID
-- reward_amount: Amount of reward in G$
-- score: Game score
-- created_at: Timestamp when reward was disbursed

-- ====================================
-- NOTES
-- ====================================
-- 1. All tables use RLS (Row Level Security) with permissive policies
-- 2. Indexes are created for commonly queried columns
-- 3. Timestamps use TIMESTAMP WITH TIME ZONE for proper timezone handling
-- 4. DECIMAL(18,8) is used for G$ amounts to match blockchain precision
-- 5. Auto-update trigger is set on minigame_balances.updated_at
