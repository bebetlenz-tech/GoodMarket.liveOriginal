
-- Create reward_configuration table for managing social task rewards
CREATE TABLE IF NOT EXISTS reward_configuration (
    id SERIAL PRIMARY KEY,
    task_type VARCHAR(50) UNIQUE NOT NULL, -- 'telegram_task', 'twitter_task', 'facebook_task'
    reward_amount DECIMAL(18,8) NOT NULL DEFAULT 100.0,
    last_updated_by VARCHAR(42),
    last_updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index
CREATE INDEX IF NOT EXISTS idx_reward_config_task_type ON reward_configuration(task_type);

-- Enable RLS
ALTER TABLE reward_configuration ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow all operations on reward_configuration" ON reward_configuration FOR ALL USING (true);

-- Insert default values
INSERT INTO reward_configuration (task_type, reward_amount) VALUES
    ('telegram_task', 100.0),
    ('twitter_task', 100.0),
    ('facebook_task', 100.0)
ON CONFLICT (task_type) DO NOTHING;

-- Create trigger for auto-updating last_updated_at
CREATE TRIGGER update_reward_config_updated_at 
    BEFORE UPDATE ON reward_configuration 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();
