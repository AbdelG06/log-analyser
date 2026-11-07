CREATE TABLE IF NOT EXISTS auth_events (
    id BIGSERIAL PRIMARY KEY,
    event_time TIMESTAMP NULL,
    host TEXT NOT NULL,
    service TEXT NOT NULL,
    pid INTEGER NULL,
    event_type TEXT NOT NULL,
    username TEXT NULL,
    source_ip INET NULL,
    country TEXT NULL,
    message TEXT NOT NULL,
    source_file TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS module_errors (
    id BIGSERIAL PRIMARY KEY,
    module_name TEXT NOT NULL,
    error_type TEXT NOT NULL,
    error_message TEXT NOT NULL,
    source_file TEXT NULL,
    line_number INTEGER NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ip_country (
    source_ip INET PRIMARY KEY,
    country TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS auth_events_type_idx ON auth_events (event_type);
CREATE INDEX IF NOT EXISTS auth_events_user_idx ON auth_events (username);
CREATE INDEX IF NOT EXISTS auth_events_country_idx ON auth_events (country);

CREATE OR REPLACE VIEW failed_attempts_by_country AS
SELECT COALESCE(country, 'UNKNOWN') AS country, COUNT(*) AS failed_attempts
FROM auth_events
WHERE event_type IN ('failed_password', 'invalid_user')
GROUP BY COALESCE(country, 'UNKNOWN')
ORDER BY failed_attempts DESC;

CREATE OR REPLACE VIEW successful_attempts_by_user AS
SELECT username, COUNT(*) AS successful_attempts
FROM auth_events
WHERE event_type = 'successful_login'
GROUP BY username
ORDER BY successful_attempts DESC;

CREATE OR REPLACE VIEW failed_invalid_users AS
SELECT event_time, username, source_ip, country, message, source_file
FROM auth_events
WHERE event_type = 'invalid_user'
ORDER BY event_time;

CREATE OR REPLACE VIEW failed_invalid_users_by_user AS
SELECT COALESCE(username, 'UNKNOWN') AS username, COUNT(*) AS failed_attempts
FROM auth_events
WHERE event_type = 'invalid_user'
GROUP BY COALESCE(username, 'UNKNOWN')
ORDER BY failed_attempts DESC;
