-- Initialize database with pgvector extension
-- This script runs automatically when the postgres container starts

-- Enable pgvector extension for vector similarity search
CREATE EXTENSION IF NOT EXISTS vector;

-- Create initial schemas (these will be properly created via migrations)
-- This is just for Docker initialization

-- Log initialization
DO $$
BEGIN
    RAISE NOTICE 'Database initialized with pgvector extension';
END $$;
