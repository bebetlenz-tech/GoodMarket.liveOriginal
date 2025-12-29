
-- Create learn_earn_module_links table
CREATE TABLE IF NOT EXISTS learn_earn_module_links (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    url TEXT, -- Now optional, for reference only
    description TEXT,
    content TEXT, -- New field: Actual module content (HTML/text)
    reading_time_minutes INTEGER DEFAULT 5, -- Required reading time
    display_order INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_module_links_active ON learn_earn_module_links(is_active, display_order);

-- Add RLS policies
ALTER TABLE learn_earn_module_links ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist
DROP POLICY IF EXISTS "Allow read access to active module links" ON learn_earn_module_links;
DROP POLICY IF EXISTS "Allow service role to manage module links" ON learn_earn_module_links;

-- Allow all authenticated users to read active module links
CREATE POLICY "Allow read access to active module links" ON learn_earn_module_links
    FOR SELECT
    USING (is_active = true);

-- Only allow service role to modify
CREATE POLICY "Allow service role to manage module links" ON learn_earn_module_links
    FOR ALL
    USING (auth.role() = 'service_role');
