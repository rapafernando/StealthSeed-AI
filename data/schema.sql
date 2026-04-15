CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS personas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    prompt_instructions TEXT,
    minimum_organic_posts INTEGER DEFAULT 3
);

CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    password TEXT,
    platform TEXT NOT NULL,
    persona_id INTEGER,
    status TEXT DEFAULT 'active',
    last_posted_at DATETIME,
    FOREIGN KEY(persona_id) REFERENCES personas(id)
);

CREATE TABLE IF NOT EXISTS threads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform TEXT NOT NULL,
    thread_url TEXT NOT NULL UNIQUE,
    niche TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS engagements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id INTEGER,
    account_id INTEGER,
    phase TEXT NOT NULL, -- 'Rapport' or 'Seed'
    message_content TEXT,
    utm_link_dropped TEXT,
    clicks INTEGER DEFAULT 0,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(thread_id) REFERENCES threads(id),
    FOREIGN KEY(account_id) REFERENCES accounts(id)
);

CREATE VIEW IF NOT EXISTS seeding_efficiency AS
SELECT 
    e.account_id,
    a.username,
    a.platform,
    SUM(CASE WHEN e.phase = 'Rapport' THEN 1 ELSE 0 END) AS rapport_posts,
    SUM(CASE WHEN e.phase = 'Seed' THEN 1 ELSE 0 END) AS seeds_dropped,
    SUM(e.clicks) as total_link_clicks,
    CASE 
        WHEN SUM(CASE WHEN e.phase = 'Rapport' THEN 1 ELSE 0 END) > 0 
        THEN CAST(SUM(e.clicks) AS FLOAT) / SUM(CASE WHEN e.phase = 'Rapport' THEN 1 ELSE 0 END)
        ELSE 0 
    END AS click_per_rapport_ratio
FROM engagements e
JOIN accounts a ON e.account_id = a.id
GROUP BY e.account_id;

CREATE TABLE IF NOT EXISTS system_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    target_niche TEXT,
    product_link TEXT,
    gemini_api_key TEXT,
    cooldown_minutes INTEGER DEFAULT 90,
    agent_status TEXT DEFAULT 'stopped'
);

CREATE TABLE IF NOT EXISTS search_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tag TEXT NOT NULL UNIQUE,
    platform TEXT,
    status TEXT DEFAULT 'active'
);
