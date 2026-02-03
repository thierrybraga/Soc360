-- Open-Monitor v3.0 - Core Database Initialization
-- Users, Assets, Rules, Reports, Sessions

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create schema (optional, using public by default)
-- CREATE SCHEMA IF NOT EXISTS openmonitor;

-- Set timezone
SET timezone = 'UTC';

-- Performance tuning for this session
SET work_mem = '64MB';
SET maintenance_work_mem = '256MB';

-- Grant permissions (for application user if different from owner)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO openmonitor;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO openmonitor;

-- Create index on common text search patterns
-- (Actual table creation is handled by SQLAlchemy)

-- Log initialization
DO $$
BEGIN
    RAISE NOTICE 'Core database initialized at %', NOW();
END $$;
