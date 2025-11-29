-- Initial database setup for PlexAddons
-- This runs automatically when the PostgreSQL container starts

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create index for audit log auto-purge (will be used by scheduled cleanup)
-- The actual tables are created by Alembic migrations
