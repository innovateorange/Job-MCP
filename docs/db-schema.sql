-- Supabase table schemas
CREATE TABLE users (
  id UUID PRIMARY KEY,
  email TEXT NOT NULL
);

CREATE TABLE profiles (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  skills JSONB,
  experience JSONB
);

CREATE TABLE applications (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  job_url TEXT,
  status TEXT,
  applied_at TIMESTAMP
);

CREATE TABLE preferences (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  job_types TEXT[]
);

-- Enable pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- Add RLS
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
-- TODO: Add RLS policies
