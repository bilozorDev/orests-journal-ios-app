-- Enable pgvector extension for semantic search
CREATE EXTENSION IF NOT EXISTS vector
WITH SCHEMA extensions;

-- Add embedding columns to pet_health_categories
ALTER TABLE pet_health_categories
ADD COLUMN embedding vector(384);

-- Add embedding columns to pet_health_events
ALTER TABLE pet_health_events
ADD COLUMN embedding vector(384);

-- Create HNSW index on pet_health_categories embeddings
-- Using inner product (IP) for normalized embeddings from gte-small model
CREATE INDEX idx_pet_health_categories_embedding
ON pet_health_categories
USING hnsw (embedding vector_ip_ops);

-- Create HNSW index on pet_health_events embeddings
CREATE INDEX idx_pet_health_events_embedding
ON pet_health_events
USING hnsw (embedding vector_ip_ops);
