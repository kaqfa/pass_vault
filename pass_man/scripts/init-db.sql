-- Database initialization script for Pass-Man development environment
--
-- This script sets up the initial database configuration for development.
-- It creates necessary extensions and performs initial setup.
--
-- Related Documentation:
-- - SRS.md: Section 7 Database Schema
-- - ARCHITECTURE.md: Database Design

-- Create UUID extension for UUID support
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create database if it doesn't exist (handled by POSTGRES_DB env var)
-- The database 'passmandb' is created automatically by the postgres image

-- Set timezone
SET timezone = 'UTC';

-- Create initial database settings
ALTER DATABASE passmandb SET timezone TO 'UTC';

-- Log the initialization
DO $$
BEGIN
    RAISE NOTICE 'Pass-Man database initialized successfully';
    RAISE NOTICE 'Database: passmandb';
    RAISE NOTICE 'Timezone: UTC';
    RAISE NOTICE 'UUID extension: enabled';
END $$;