import pytest
import os
import psycopg2
from click.testing import CliRunner
from unittest.mock import patch  # <--- Added this import

# Configuration for the TEST database
TEST_DB_URL = "postgres://admin:secret@localhost:5432/test_pgmigrate"

@pytest.fixture(scope="function")
def clean_db():
    """
    Wipes the 'public' schema of the test database before every test.
    This ensures no state leaks between tests.
    """
    try:
        conn = psycopg2.connect(TEST_DB_URL)
        conn.autocommit = True
        with conn.cursor() as cur:
            # Drop everything and recreate the schema
            cur.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
        conn.close()
    except Exception as e:
        pytest.fail(f"Could not connect to test database: {e}")

@pytest.fixture
def runner(clean_db):
    """
    Returns a Click Runner that is isolated from your real file system
    and points to the test database.
    """
    runner = CliRunner()
    
    # CORRECTED: Use patch.dict to safely mock os.environ
    with patch.dict(os.environ, {"DATABASE_URL": TEST_DB_URL}):
        yield runner