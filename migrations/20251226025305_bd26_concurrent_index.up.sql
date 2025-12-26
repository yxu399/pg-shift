-- SQL for 'up' migration
-- Created: 20251226025305
-- migration: no-transaction

CREATE INDEX CONCURRENTLY idx_test_tx_id ON test_tx(id);