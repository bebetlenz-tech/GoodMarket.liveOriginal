
-- ====================================
-- DEVELOPER PROFILE TABLE
-- ====================================
-- This table stores information about developers/moderators to display on the homepage

CREATE TABLE IF NOT EXISTS developer_profile (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    position TEXT NOT NULL,
    image_url TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index for better query performance
CREATE INDEX IF NOT EXISTS idx_developer_profile_active ON developer_profile(is_active);

-- Enable Row Level Security
ALTER TABLE developer_profile ENABLE ROW LEVEL SECURITY;

-- Create policy to allow all operations
CREATE POLICY "Allow all operations on developer_profile" ON developer_profile FOR ALL USING (true);

-- Create function to auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_developer_profile_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger for auto-updating updated_at
CREATE TRIGGER update_developer_profile_timestamp 
    BEFORE UPDATE ON developer_profile 
    FOR EACH ROW 
    EXECUTE FUNCTION update_developer_profile_updated_at();

-- ====================================
-- SAMPLE DATA (OPTIONAL - UNCOMMENT TO USE)
-- ====================================
-- Insert a sample developer profile
-- Uncomment the lines below to add your profile:

-- INSERT INTO developer_profile (name, position, image_url, is_active) 
-- VALUES (
--     'Your Name',
--     'Community Moderator of GoodDollar & Developer of GoodMarket',
--     'https://your-image-url.com/photo.jpg',
--     true
-- );

-- ====================================
-- USEFUL QUERIES
-- ====================================

-- View all active developer profiles:
-- SELECT * FROM developer_profile WHERE is_active = true ORDER BY created_at DESC;

-- Update a developer profile:
-- UPDATE developer_profile SET name = 'New Name', position = 'New Position' WHERE id = 1;

-- Deactivate a profile (soft delete):
-- UPDATE developer_profile SET is_active = false WHERE id = 1;

-- Delete a profile permanently:
-- DELETE FROM developer_profile WHERE id = 1;
