import subprocess
import os
import click
import datetime
import secrets
import psycopg2
from .db import Database
from .utils import get_migrations

# Helper to get DB URL from env
def get_db_url():
    url = os.getenv("DATABASE_URL")
    if not url:
        raise click.UsageError("DATABASE_URL environment variable is missing.")
    return url

@click.group()
def cli():
    """PostgreSQL Migration Tool"""
    pass

@cli.command()
def init():
    """Initializes the migration table and directory."""
    if not os.path.exists("migrations"):
        os.makedirs("migrations")
        click.echo("✅ Created 'migrations/' directory.")
    else:
        click.echo("ℹ️  'migrations/' directory already exists.")

    db = Database(get_db_url())
    try:
        db.connect()
        conn = db.get_conn()
        with conn:
            with conn.cursor() as cur:
                click.echo("Checking database connection...")
                cur.execute("SELECT to_regclass('public.schema_migrations');")
                if cur.fetchone()['to_regclass']:
                    click.echo("ℹ️  Table 'schema_migrations' already exists.")
                else:
                    cur.execute("""
                        CREATE TABLE schema_migrations (
                            version VARCHAR(255) PRIMARY KEY,
                            name VARCHAR(255) NOT NULL,
                            checksum VARCHAR(64) NOT NULL,
                            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            batch INTEGER NOT NULL DEFAULT 1
                        );
                    """)
                    click.echo("✅ Created table 'schema_migrations'.")
    except Exception as e:
        click.secho(f"❌ Error: {e}", fg="red")
    finally:
        db.close()

@cli.command()
@click.argument('name')
def make(name):
    """Generates a new migration file pair."""
    timestamp = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")
    suffix = secrets.token_hex(2)
    safe_name = "".join(c if c.isalnum() else "_" for c in name).strip("_")
    base_filename = f"{timestamp}_{suffix}_{safe_name}"
    
    up_file = os.path.join("migrations", f"{base_filename}.up.sql")
    down_file = os.path.join("migrations", f"{base_filename}.down.sql")
    
    with open(up_file, 'w') as f:
        f.write("-- SQL for 'up' migration\n")
        f.write(f"-- Created: {timestamp}\n\n")
        f.write("BEGIN;\n\n-- Write your migration here\n\nCOMMIT;")

    with open(down_file, 'w') as f:
        f.write("-- SQL for 'down' migration\n\n")
        f.write("BEGIN;\n\n-- Write your rollback here\n\nCOMMIT;")

    click.echo(f"✅ Created migration pair:")
    click.echo(f"   trigger -> {up_file}")
    click.echo(f"   trigger -> {down_file}")

@cli.command()
def list_files():
    """(Dev Helper) Lists discovered migration files and their checksums."""
    migrations = get_migrations()
    if not migrations:
        click.echo("No migrations found.")
        return

    sorted_keys = sorted(migrations.keys())
    print(f"{'VERSION':<25} | {'STATUS':<10} | {'CHECKSUM (UP)':<15}")
    print("-" * 65)
    for version in sorted_keys:
        m = migrations[version]
        status = "OK"
        if not m.up_path: status = "NO UP"
        elif not m.down_path: status = "NO DOWN"
        short_hash = m.up_checksum[:8] if m.up_checksum else "------"
        print(f"{version:<25} | {status:<10} | {short_hash}")

@cli.command()
@click.option('--dry-run', is_flag=True, help="Simulate without running SQL.")
def up(dry_run):
    """Applies all pending migrations."""
    db = Database(get_db_url())
    try:
        if not dry_run:
            db.acquire_lock()
        conn = db.get_conn()
        local_migrations = get_migrations()
        
        applied_migrations = {}
        max_applied_batch = 0
        
        with conn.cursor() as cur:
            cur.execute("SELECT version, checksum, batch FROM schema_migrations ORDER BY version ASC")
            for row in cur.fetchall():
                applied_migrations[row['version']] = row
                if row['batch'] > max_applied_batch:
                    max_applied_batch = row['batch']

        # Validation
        for version, row in applied_migrations.items():
            if version not in local_migrations:
                raise click.ClickException(f"❌ Missing file for applied migration: {version}")
            if local_migrations[version].up_checksum != row['checksum']:
                click.echo(f"❌ FATAL: Checksum mismatch for {version}")
                raise click.ClickException("Migration history has been altered. Aborting.")

        # Planning
        pending = []
        all_local_versions = sorted(local_migrations.keys())
        last_applied_version = list(applied_migrations.keys())[-1] if applied_migrations else ""
        
        for version in all_local_versions:
            if version not in applied_migrations:
                if version < last_applied_version:
                    click.secho(f"⚠️  Warning: Detected out-of-order migration: {version}", fg="yellow")
                pending.append(local_migrations[version])

        if not pending:
            click.echo("✅ Database is up to date.")
            return

        next_batch = max_applied_batch + 1
        click.echo(f"🚀 Found {len(pending)} pending migrations. Batch ID: {next_batch}")

        for migration in pending:
            if not migration.up_path:
                 raise click.ClickException(f"Missing .up.sql for {migration.version}")

            with open(migration.up_path, 'r') as f:
                sql_content = f.read()

            no_transaction_mode = "-- migration: no-transaction" in sql_content.lower()

            if dry_run:
                click.secho(f"[Dry Run] Would apply: {migration.version} ({'No-Tx' if no_transaction_mode else 'Tx'})", fg="cyan")
                continue

            print(f"Applying {migration.version}...", end=" ", flush=True)
            if no_transaction_mode:
                apply_no_transaction(conn, migration, sql_content, next_batch)
            else:
                apply_standard(conn, migration, sql_content, next_batch)
            print("Done.")

    except Exception as e:
        click.secho(f"\n❌ Error: {e}", fg="red")
    finally:
        if not dry_run:
            try: db.release_lock()
            except: pass
        db.close()

@cli.command()
@click.option('--dry-run', is_flag=True, help="Simulate without running SQL.")
def down(dry_run):
    """Reverts the last batch of migrations."""
    db = Database(get_db_url())
    try:
        if not dry_run:
            db.acquire_lock()
        conn = db.get_conn()
        local_migrations = get_migrations()
        
        # 1. Identify what to revert (Last Batch)
        to_revert = []
        current_batch = 0
        
        with conn.cursor() as cur:
            cur.execute("SELECT MAX(batch) FROM schema_migrations")
            res = cur.fetchone()
            current_batch = res['max'] if res and res['max'] else 0
            
            if current_batch == 0:
                click.echo("Nothing to revert (database is empty).")
                return

            cur.execute("""
                SELECT version, name, checksum 
                FROM schema_migrations 
                WHERE batch = %s 
                ORDER BY version DESC
            """, (current_batch,))
            to_revert = cur.fetchall()

        click.echo(f"📉 Reverting Batch {current_batch} ({len(to_revert)} migrations)")

        # 2. Revert Loop
        for row in to_revert:
            version = row['version']
            if version not in local_migrations:
                click.secho(f"❌ Error: Cannot revert {version}. File not found locally.", fg="red")
                raise click.Abort()
                
            migration = local_migrations[version]
            if not migration.down_path:
                click.secho(f"❌ Error: Migration {version} has no .down.sql file.", fg="red")
                raise click.Abort()

            with open(migration.down_path, 'r') as f:
                sql_content = f.read()
                
            no_transaction_mode = "-- migration: no-transaction" in sql_content.lower()
            
            if dry_run:
                click.secho(f"[Dry Run] Would revert: {version} ({'No-Tx' if no_transaction_mode else 'Tx'})", fg="cyan")
                continue

            print(f"Reverting {version}...", end=" ", flush=True)
            if no_transaction_mode:
                revert_no_transaction(conn, version, sql_content)
            else:
                revert_standard(conn, version, sql_content)
            print("Done.")

    except Exception as e:
        click.secho(f"\n❌ Error: {e}", fg="red")
    finally:
        if not dry_run:
            try: db.release_lock()
            except: pass
        db.close()

# --- Helpers ---

def apply_standard(conn, migration, sql_content, batch_id):
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(sql_content)
                cur.execute("""
                    INSERT INTO schema_migrations (version, name, checksum, applied_at, batch)
                    VALUES (%s, %s, %s, NOW(), %s)
                """, (migration.version, migration.name, migration.up_checksum, batch_id))
    except psycopg2.Error as e:
        raise Exception(f"Migration failed in transaction: {e.pgerror}")

def apply_no_transaction(conn, migration, sql_content, batch_id):
    old_isolation = conn.isolation_level
    conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
    try:
        with conn.cursor() as cur:
            cur.execute(sql_content)
    except psycopg2.Error as e:
        conn.set_isolation_level(old_isolation)
        raise Exception(f"FATAL: No-Transaction migration failed. Error: {e.pgerror}")

    conn.set_isolation_level(old_isolation)
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO schema_migrations (version, name, checksum, applied_at, batch)
                    VALUES (%s, %s, %s, NOW(), %s)
                """, (migration.version, migration.name, migration.up_checksum, batch_id))
    except Exception as e:
         raise Exception(f"Migration succeeded, but saving metadata failed! Error: {e}")

def revert_standard(conn, version, sql_content):
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(sql_content)
                cur.execute("DELETE FROM schema_migrations WHERE version = %s", (version,))
    except psycopg2.Error as e:
        raise Exception(f"Revert failed in transaction: {e.pgerror}")

def revert_no_transaction(conn, version, sql_content):
    old_isolation = conn.isolation_level
    conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
    try:
        with conn.cursor() as cur:
            cur.execute(sql_content)
    except psycopg2.Error as e:
        conn.set_isolation_level(old_isolation)
        raise Exception(f"FATAL: No-Transaction revert failed. Error: {e.pgerror}")

    conn.set_isolation_level(old_isolation)
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM schema_migrations WHERE version = %s", (version,))
    except Exception as e:
         raise Exception(f"Revert succeeded, but cleaning metadata failed! Error: {e}")

@cli.command()
def status():
    """Shows the status of all migrations (Applied vs Pending)."""
    db = Database(get_db_url())
    
    try:
        # 1. Get Local State
        local_migrations = get_migrations()
        all_versions = set(local_migrations.keys())
        
        # 2. Get DB State
        db_state = {}
        try:
            db.connect()
            conn = db.get_conn()
            with conn.cursor() as cur:
                cur.execute("SELECT version, applied_at, batch FROM schema_migrations")
                for row in cur.fetchall():
                    db_state[row['version']] = row
                    all_versions.add(row['version'])
        except Exception:
            # If table doesn't exist yet, just show local files
            pass
        finally:
            db.close()

        # 3. Build the Dashboard
        sorted_versions = sorted(list(all_versions))
        
        print(f"{'VERSION':<20} | {'STATUS':<10} | {'BATCH':<5} | {'NAME'}")
        print("-" * 65)

        for v in sorted_versions:
            local = local_migrations.get(v)
            remote = db_state.get(v)
            
            # Determine Status
            status_str = "???"
            batch_str = "-"
            name = local.name if local else "(File Missing!)"
            color = None
            
            if remote and local:
                status_str = "Applied"
                batch_str = str(remote['batch'])
                color = "green"
            elif local and not remote:
                status_str = "Pending"
                color = "yellow"
            elif remote and not local:
                status_str = "**MISSING**"
                batch_str = str(remote['batch'])
                color = "red"
                
            # Print with color
            row = f"{v:<20} | {status_str:<10} | {batch_str:<5} | {name}"
            click.secho(row, fg=color)

    except Exception as e:
        click.secho(f"Error checking status: {e}", fg="red")

@cli.command()
@click.option('--output', default='schema.sql', help='Output file path (default: schema.sql).')
def dump(output):
    """Dumps the current database schema (structure only) to a SQL file."""
    url = get_db_url()
    
    # Check if pg_dump is installed
    try:
        subprocess.run(['pg_dump', '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        click.secho("❌ Error: 'pg_dump' executable not found.", fg="red")
        click.echo("   You must have the PostgreSQL client tools installed on this machine.")
        click.echo("   (e.g., 'brew install libpq' on Mac or 'apt-get install postgresql-client' on Linux)")
        return

    click.echo(f"📸 Snapshotting database schema to '{output}'...")

    try:
        # Construct the pg_dump command
        # -s: Schema only (no data)
        # --no-owner: Skip 'ALTER TABLE ... OWNER TO' (makes it portable)
        # --no-privileges: Skip GRANT/REVOKE (cleaner)
        # -f: Output file
        cmd = ['pg_dump', url, '-f', output, '-s', '--no-owner', '--no-privileges']
        
        # Execute
        subprocess.run(cmd, check=True)
        
        # Check if file was actually created and has content
        if os.path.exists(output) and os.path.getsize(output) > 0:
            click.echo(f"✅ Schema dumped successfully.")
        else:
            click.secho("⚠️  Warning: Output file is empty.", fg="yellow")
            
    except subprocess.CalledProcessError as e:
        click.secho(f"❌ Error during pg_dump: {e}", fg="red")