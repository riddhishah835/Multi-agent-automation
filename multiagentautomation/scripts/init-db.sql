-- Initialize PostgreSQL database for Agentic OS

-- Create tables for checkpoints
CREATE TABLE IF NOT EXISTS checkpoints (
    id SERIAL PRIMARY KEY,
    run_id VARCHAR(255) NOT NULL,
    node_id VARCHAR(255),
    status VARCHAR(50),
    checkpoint_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(run_id, node_id)
);

-- Create table for traces
CREATE TABLE IF NOT EXISTS traces (
    id SERIAL PRIMARY KEY,
    run_id VARCHAR(255) NOT NULL,
    tenant_id VARCHAR(255) NOT NULL,
    event_type VARCHAR(100),
    trace_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (run_id) REFERENCES checkpoints(run_id)
);

-- Create indexes for fast queries
CREATE INDEX idx_checkpoints_run_id ON checkpoints(run_id);
CREATE INDEX idx_checkpoints_status ON checkpoints(status);
CREATE INDEX idx_traces_run_id ON traces(run_id);
CREATE INDEX idx_traces_tenant_id ON traces(tenant_id);
CREATE INDEX idx_traces_event_type ON traces(event_type);