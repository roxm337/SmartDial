SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS agents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    script TEXT NOT NULL,
    retell_agent_id TEXT NOT NULL UNIQUE,
    retell_llm_id TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS campaigns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (agent_id) REFERENCES agents (id)
);

CREATE TABLE IF NOT EXISTS calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id INTEGER NOT NULL,
    retell_call_id TEXT UNIQUE,
    phone TEXT NOT NULL,
    name TEXT,
    status TEXT NOT NULL DEFAULT 'queued',
    transcript TEXT,
    duration INTEGER,
    recording_url TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (campaign_id) REFERENCES campaigns (id)
);

CREATE INDEX IF NOT EXISTS idx_campaigns_agent_id ON campaigns (agent_id);
CREATE INDEX IF NOT EXISTS idx_calls_campaign_id ON calls (campaign_id);
CREATE INDEX IF NOT EXISTS idx_calls_retell_call_id ON calls (retell_call_id);
"""

