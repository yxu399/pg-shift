-- SQL for 'up' migration
-- Created: 20251226030859

BEGIN;

CREATE INDEX CONCURRENTLY idx_big_data_email ON big_data_table(user_email);

COMMIT;