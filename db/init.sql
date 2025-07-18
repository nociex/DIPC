-- Database initialization script for DIPC
-- This script sets up the basic database structure

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create enum types
CREATE TYPE task_status_enum AS ENUM (
    'pending',
    'processing', 
    'completed',
    'failed',
    'cancelled'
);

CREATE TYPE storage_policy_enum AS ENUM (
    'permanent',
    'temporary'
);

-- Create tasks table
CREATE TABLE IF NOT EXISTS tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(255) NOT NULL,
    parent_task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
    status task_status_enum NOT NULL DEFAULT 'pending',
    task_type VARCHAR(50) NOT NULL,
    file_url TEXT,
    original_filename VARCHAR(255),
    options JSONB DEFAULT '{}',
    estimated_cost DECIMAL(10,4),
    actual_cost DECIMAL(10,4),
    results JSONB,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Create file_metadata table
CREATE TABLE IF NOT EXISTS file_metadata (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
    original_filename VARCHAR(255) NOT NULL,
    file_type VARCHAR(50) NOT NULL,
    file_size BIGINT NOT NULL,
    storage_path TEXT NOT NULL,
    storage_policy storage_policy_enum NOT NULL DEFAULT 'temporary',
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_tasks_user_id ON tasks(user_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks(created_at);
CREATE INDEX IF NOT EXISTS idx_tasks_parent_task_id ON tasks(parent_task_id);
CREATE INDEX IF NOT EXISTS idx_file_metadata_task_id ON file_metadata(task_id);
CREATE INDEX IF NOT EXISTS idx_file_metadata_expires_at ON file_metadata(expires_at);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger to automatically update updated_at
CREATE TRIGGER update_tasks_updated_at 
    BEFORE UPDATE ON tasks 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Insert sample data for development (optional)
-- This will only run if the environment is development
DO $$
BEGIN
    IF current_setting('server_version_num')::int >= 140000 THEN
        -- PostgreSQL 14+ syntax
        IF EXISTS (SELECT 1 FROM pg_settings WHERE name = 'shared_preload_libraries') THEN
            -- Development seed data can be added here
            NULL;
        END IF;
    END IF;
END $$;