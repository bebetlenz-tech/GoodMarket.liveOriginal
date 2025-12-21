
-- ====================================
-- NEWS FEED TABLES
-- ====================================
-- Complete table structure for News Feed module
-- Run this in your Supabase SQL Editor

-- ====================================
-- 1. NEWS ARTICLES TABLE
-- ====================================
CREATE TABLE IF NOT EXISTS news_articles (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    category VARCHAR(50) DEFAULT 'announcement',
    priority VARCHAR(20) DEFAULT 'medium', -- 'low', 'medium', 'high'
    author VARCHAR(100) DEFAULT 'Admin',
    published BOOLEAN DEFAULT TRUE,
    featured BOOLEAN DEFAULT FALSE,
    image_url TEXT,
    url TEXT, -- External link URL (optional)
    view_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for news_articles table
CREATE INDEX IF NOT EXISTS idx_news_articles_published ON news_articles(published);
CREATE INDEX IF NOT EXISTS idx_news_articles_featured ON news_articles(featured);
CREATE INDEX IF NOT EXISTS idx_news_articles_category ON news_articles(category);
CREATE INDEX IF NOT EXISTS idx_news_articles_created_at ON news_articles(created_at);
CREATE INDEX IF NOT EXISTS idx_news_articles_priority ON news_articles(priority);

-- Enable RLS
ALTER TABLE news_articles ENABLE ROW LEVEL SECURITY;

-- Create policy
CREATE POLICY "Allow all operations on news_articles" ON news_articles FOR ALL USING (true);

-- Create trigger for auto-updating updated_at
CREATE TRIGGER update_news_articles_updated_at 
    BEFORE UPDATE ON news_articles 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- ====================================
-- COLUMN DESCRIPTIONS
-- ====================================

-- news_articles columns:
-- id: Auto-incrementing primary key
-- title: Article title (max 200 characters)
-- content: Full article content (text)
-- category: Article category - 'announcement', 'update', 'community', 'blockchain', 'reward', 'feature', 'maintenance', 'partnership'
-- priority: Display priority - 'low', 'medium', 'high'
-- author: Article author name
-- published: Whether article is published (true/false)
-- featured: Whether article is featured on homepage (true/false)
-- image_url: URL to article image (optional)
-- url: External link URL (optional)
-- view_count: Number of times article has been viewed
-- created_at: Article creation timestamp
-- updated_at: Article update timestamp
