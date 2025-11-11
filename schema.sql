-- Database schema for Telegram Video Bot
-- Creates tables for users, videos, ads, messages, user states, and admin sessions

-- Users table
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    username VARCHAR(255),
    first_name VARCHAR(255),
    first_interaction TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_interaction TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    interaction_count INTEGER DEFAULT 0
);

-- Videos table
CREATE TABLE IF NOT EXISTS videos (
    id VARCHAR(255) PRIMARY KEY,
    file_id VARCHAR(255) NOT NULL,
    file_unique_id VARCHAR(255),
    duration INTEGER,
    width INTEGER,
    height INTEGER,
    file_size BIGINT,
    thumbnail_file_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    message_id BIGINT,
    channel_id BIGINT,
    caption TEXT,
    caption_entities JSONB,
    mime_type VARCHAR(100),
    file_name VARCHAR(500)
);

-- Ads table
CREATE TABLE IF NOT EXISTS ads (
    id VARCHAR(255) PRIMARY KEY,
    type VARCHAR(50) DEFAULT 'text',
    content TEXT NOT NULL,
    url TEXT,
    duration INTEGER DEFAULT 60,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    views INTEGER DEFAULT 0,
    last_shown TIMESTAMP
);

-- Messages table (for tracking message deletion)
CREATE TABLE IF NOT EXISTS messages (
    message_key VARCHAR(255) PRIMARY KEY,
    user_id BIGINT NOT NULL,
    chat_id BIGINT NOT NULL,
    message_id BIGINT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    delete_at TIMESTAMP NOT NULL,
    is_video BOOLEAN DEFAULT FALSE
);

-- User states table (for tracking ad sessions and user interactions)
CREATE TABLE IF NOT EXISTS user_states (
    user_id BIGINT PRIMARY KEY,
    ad_session_token VARCHAR(255),
    ad_session_start TIMESTAMP,
    ad_id VARCHAR(255),
    video_id VARCHAR(255),
    ad_completed BOOLEAN DEFAULT FALSE,
    ad_completed_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Admin sessions table (for admin authentication)
CREATE TABLE IF NOT EXISTS admin_sessions (
    token VARCHAR(255) PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_users_last_interaction ON users(last_interaction DESC);
CREATE INDEX IF NOT EXISTS idx_videos_created_at ON videos(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ads_active ON ads(active) WHERE active = TRUE;
CREATE INDEX IF NOT EXISTS idx_messages_delete_at ON messages(delete_at);
CREATE INDEX IF NOT EXISTS idx_admin_sessions_last_activity ON admin_sessions(last_activity DESC);
