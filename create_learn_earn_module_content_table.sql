
-- ====================================
-- LEARN & EARN MODULE CONTENT TABLE
-- ====================================

-- Create learn_earn_module_links table for storing module content
CREATE TABLE IF NOT EXISTS learn_earn_module_links (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    url TEXT, -- Optional, for reference only
    description TEXT,
    content TEXT, -- Actual module content (HTML/text)
    reading_time_minutes INTEGER DEFAULT 5, -- Required reading time
    display_order INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_module_links_active ON learn_earn_module_links(is_active, display_order);
CREATE INDEX IF NOT EXISTS idx_module_links_title ON learn_earn_module_links(title);
CREATE INDEX IF NOT EXISTS idx_module_links_display_order ON learn_earn_module_links(display_order);

-- Enable RLS
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

-- Create trigger for auto-updating updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_module_links_updated_at 
    BEFORE UPDATE ON learn_earn_module_links 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Insert sample module content (optional - you can remove this if you want to add manually)
INSERT INTO learn_earn_module_links (title, description, content, reading_time_minutes, display_order, is_active)
VALUES 
(
    'Understanding GoodDollar',
    'Learn about GoodDollar and Universal Basic Income',
    '<h2>What is GoodDollar?</h2>
    <p>GoodDollar (G$) is a cryptocurrency designed to provide universal basic income to everyone.</p>
    <h3>Key Features</h3>
    <ul>
        <li>Daily UBI claims available at goodwallet.xyz</li>
        <li>Built on Celo blockchain for low transaction fees</li>
        <li>Community-driven governance</li>
        <li>Accessible to everyone worldwide</li>
    </ul>',
    5,
    1,
    true
),
(
    'Government and Governance',
    'How GoodDollar is governed by the community',
    '<h2>Understanding Good Governance in GoodDollar</h2>
    <p>Good governance is essential for the success and sustainability of the GoodDollar ecosystem.</p>
    <h3>What is Governance?</h3>
    <p>Governance refers to the decision-making processes that determine how the GoodDollar protocol evolves.</p>
    <ul>
        <li>Protocol parameters (like UBI distribution amounts)</li>
        <li>New features and upgrades</li>
        <li>Resource allocation</li>
        <li>Partnership decisions</li>
    </ul>',
    5,
    2,
    true
)
ON CONFLICT DO NOTHING;
