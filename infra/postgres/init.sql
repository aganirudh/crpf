-- PRAMAAN Postgres init: extensions and append-only ledger setup
-- Runs once on a fresh volume.

CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- pgvector for embedding columns on evidence_node (W3+).
-- This is best-effort: if the image doesn't ship it, the migration will skip it.
DO $$
BEGIN
  CREATE EXTENSION IF NOT EXISTS "vector";
EXCEPTION WHEN OTHERS THEN
  RAISE NOTICE 'pgvector not available — embedding columns will fall back to bytea';
END $$;
