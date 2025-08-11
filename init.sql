CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE podcasts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    url TEXT UNIQUE NOT NULL,
    title TEXT,
    audio_filename TEXT,
    status TEXT NOT NULL DEFAULT 'queued',
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration INTEGER,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0
);

CREATE INDEX idx_podcasts_url ON podcasts(url);
CREATE INDEX idx_podcasts_status ON podcasts(status);  
CREATE INDEX idx_podcasts_created_at ON podcasts(created_at DESC);