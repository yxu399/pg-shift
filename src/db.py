import os
import psycopg2
from psycopg2.extras import RealDictCursor
import time

# A arbitrary constant integer for the Postgres Advisory Lock
ADVISORY_LOCK_ID = 4294967295 

class Database:
    def __init__(self, db_url):
        self.db_url = db_url
        self.conn = None

    def connect(self):
        """Establishes connection to the database."""
        if self.conn is None or self.conn.closed:
            try:
                self.conn = psycopg2.connect(self.db_url, cursor_factory=RealDictCursor)
                # Ensure we start in a known state
                self.conn.autocommit = False 
            except psycopg2.Error as e:
                raise Exception(f"Failed to connect to DB: {e}")

    def close(self):
        if self.conn and not self.conn.closed:
            self.conn.close()

    def acquire_lock(self):
        """Acquires a global exclusive lock for migrations with a timeout."""
        self.connect()
        with self.conn.cursor() as cur:
            # Prevent infinite hangs: Set a local statement timeout (e.g., 10 seconds for the lock)
            # Note: This timeout applies to the 'acquiring' step, not the migration duration.
            cur.execute("SET lock_timeout = '10s'")
            try:
                cur.execute("SELECT pg_advisory_lock(%s)", (ADVISORY_LOCK_ID,))
            except psycopg2.errors.LockNotAvailable:
                raise Exception("Could not acquire migration lock. Is another migration running?")

    def release_lock(self):
        """Releases the global exclusive lock."""
        if self.conn and not self.conn.closed:
            with self.conn.cursor() as cur:
                cur.execute("SELECT pg_advisory_unlock(%s)", (ADVISORY_LOCK_ID,))

    def get_conn(self):
        self.connect()
        return self.conn