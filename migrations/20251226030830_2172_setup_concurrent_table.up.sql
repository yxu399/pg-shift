-- SQL for 'up' migration
-- Created: 20251226030830

BEGIN;

CREATE TABLE big_data_table (
    id SERIAL PRIMARY KEY,
    user_email TEXT NOT NULL
);

COMMIT;