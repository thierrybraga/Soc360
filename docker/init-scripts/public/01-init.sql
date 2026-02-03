-- Open-Monitor v3.0 - Public Database Initialization
-- CVEs, NVD Data, Vulnerabilities

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For text search

-- Set timezone
SET timezone = 'UTC';

-- Performance tuning for large dataset operations
SET work_mem = '128MB';
SET maintenance_work_mem = '512MB';
SET effective_cache_size = '1GB';

-- Tune for bulk inserts
SET synchronous_commit = 'off';  -- Faster writes, acceptable for CVE data

-- Grant permissions
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO openmonitor;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO openmonitor;

-- Create GIN index function for JSONB columns (called after table creation)
-- This will be created by SQLAlchemy, but kept here for reference
/*
CREATE INDEX IF NOT EXISTS idx_vulnerabilities_vendors_gin 
    ON vulnerabilities USING GIN (vendors jsonb_path_ops);
    
CREATE INDEX IF NOT EXISTS idx_vulnerabilities_products_gin 
    ON vulnerabilities USING GIN (products jsonb_path_ops);
*/

-- Log initialization
DO $$
BEGIN
    RAISE NOTICE 'Public database initialized at %', NOW();
    RAISE NOTICE 'Ready for NVD data synchronization';
END $$;
