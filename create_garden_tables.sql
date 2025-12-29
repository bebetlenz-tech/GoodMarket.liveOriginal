-- Garden Tables for G$ Garden Minigame

-- Garden plots table
CREATE TABLE IF NOT EXISTS garden_plots (
    id SERIAL PRIMARY KEY,
    wallet_address VARCHAR(42) NOT NULL,
    plot_id INTEGER NOT NULL,
    crop_type VARCHAR(50),
    planted_at TIMESTAMP WITH TIME ZONE,
    growth_percent DECIMAL(5,2) DEFAULT 0,
    status VARCHAR(20) DEFAULT 'empty',
    watered BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(wallet_address, plot_id)
);

-- Garden harvests table
CREATE TABLE IF NOT EXISTS garden_harvests (
    id SERIAL PRIMARY KEY,
    wallet_address VARCHAR(42) NOT NULL,
    harvest_date DATE NOT NULL,
    harvests_today INTEGER DEFAULT 0,
    total_earned DECIMAL(18,8) DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(wallet_address, harvest_date)
);

-- Garden AI helpers table
CREATE TABLE IF NOT EXISTS garden_ai_helpers (
    id SERIAL PRIMARY KEY,
    wallet_address VARCHAR(42) NOT NULL,
    helper_type VARCHAR(50) NOT NULL,
    hired_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    active BOOLEAN DEFAULT TRUE,
    UNIQUE(wallet_address, helper_type)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_garden_plots_wallet ON garden_plots(wallet_address);
CREATE INDEX IF NOT EXISTS idx_garden_harvests_wallet ON garden_harvests(wallet_address);
CREATE INDEX IF NOT EXISTS idx_garden_ai_helpers_wallet ON garden_ai_helpers(wallet_address);

-- Enable RLS
ALTER TABLE garden_plots ENABLE ROW LEVEL SECURITY;
ALTER TABLE garden_harvests ENABLE ROW LEVEL SECURITY;
ALTER TABLE garden_ai_helpers ENABLE ROW LEVEL SECURITY;

-- Create policies
CREATE POLICY "Allow all operations on garden_plots" ON garden_plots FOR ALL USING (true);
CREATE POLICY "Allow all operations on garden_harvests" ON garden_harvests FOR ALL USING (true);
CREATE POLICY "Allow all operations on garden_ai_helpers" ON garden_ai_helpers FOR ALL USING (true);

