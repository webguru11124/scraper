-- init_db.sql
CREATE TABLE IF NOT EXISTS scraped_data (
    id SERIAL PRIMARY KEY,
    registrant VARCHAR(255),
    status VARCHAR(255),
    class VARCHAR(255),
    location VARCHAR(255),
    details_link TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
