import os
from src.main import cli
from src.db import Database

# Helper to check DB state
def table_exists(db_url, table_name):
    db = Database(db_url)
    db.connect()
    conn = db.get_conn()
    with conn.cursor() as cur:
        cur.execute("SELECT to_regclass(%s)", (table_name,))
        res = cur.fetchone()
    db.close()
    return res['to_regclass'] is not None

def test_init_command(runner):
    """Test that init creates the folder and the metadata table."""
    # We use isolated_filesystem so we don't clutter your real project
    with runner.isolated_filesystem():
        result = runner.invoke(cli, ['init'])
        
        assert result.exit_code == 0
        assert "Created 'migrations/' directory" in result.output
        assert os.path.exists("migrations")
        
        # Verify DB table was created
        assert table_exists(os.environ["DATABASE_URL"], "public.schema_migrations")

def test_migration_lifecycle(runner):
    """Test the full flow: Make -> Up -> Down."""
    with runner.isolated_filesystem():
        # 1. SETUP
        runner.invoke(cli, ['init'])
        
        # 2. MAKE: Generate a migration
        result = runner.invoke(cli, ['make', 'create_test_table'])
        assert result.exit_code == 0
        
        # Find the generated file paths
        files = os.listdir("migrations")
        up_file = next(f for f in files if f.endswith(".up.sql"))
        
        # Write valid SQL into the generated file
        with open(os.path.join("migrations", up_file), "w") as f:
            f.write("CREATE TABLE pytest_table (id serial primary key);")

        # 3. UP: Apply the migration
        result = runner.invoke(cli, ['up'])
        assert result.exit_code == 0
        assert "Applying" in result.output
        
        # Verify table exists in DB
        assert table_exists(os.environ["DATABASE_URL"], "public.pytest_table")

        # 4. DOWN: Revert the migration
        # First, we need to populate the down file!
        down_file = next(f for f in files if f.endswith(".down.sql"))
        with open(os.path.join("migrations", down_file), "w") as f:
            f.write("DROP TABLE pytest_table;")
            
        result = runner.invoke(cli, ['down'])
        assert result.exit_code == 0
        assert "Reverting" in result.output
        
        # Verify table is GONE
        assert not table_exists(os.environ["DATABASE_URL"], "public.pytest_table")

def test_transaction_safety(runner):
    """Test that a syntax error rolls back the entire transaction."""
    with runner.isolated_filesystem():
        runner.invoke(cli, ['init'])
        runner.invoke(cli, ['make', 'broken_migration'])
        
        files = os.listdir("migrations")
        up_file = next(f for f in files if f.endswith(".up.sql"))
        
        # Write BROKEN SQL (Valid first, invalid second)
        with open(os.path.join("migrations", up_file), "w") as f:
            f.write("CREATE TABLE should_not_exist (id int);")
            f.write("\nTHIS_IS_INVALID_SQL;") # <--- Syntax Error
            
        # Run UP
        result = runner.invoke(cli, ['up'])
        
        # Should fail
        assert result.exit_code != 0
        assert "syntax error" in result.output.lower()
        
        # Verify Rollback: The table 'should_not_exist' must NOT exist
        assert not table_exists(os.environ["DATABASE_URL"], "public.should_not_exist")