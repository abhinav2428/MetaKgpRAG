"""
setup_db.py
-----------
One-time script to create the graphmind PostgreSQL user and database,
then auto-create all SQLAlchemy tables.

Usage:
    python setup_db.py --pg-password YOUR_POSTGRES_SUPERUSER_PASSWORD

Or set the PGPASSWORD environment variable first.
"""

import subprocess
import sys
import argparse
import os

PSQL = r"C:\Program Files\PostgreSQL\18\bin\psql.exe"

SQL_COMMANDS = [
    "CREATE USER graphmind WITH PASSWORD 'graphmind';",
    "CREATE DATABASE graphmind OWNER graphmind;",
    "GRANT ALL PRIVILEGES ON DATABASE graphmind TO graphmind;",
]


def run_psql(password: str, sql: str):
    env = os.environ.copy()
    env["PGPASSWORD"] = password
    result = subprocess.run(
        [PSQL, "-U", "postgres", "-c", sql],
        env=env,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 and "already exists" not in result.stderr:
        print(f"  [WARN] {result.stderr.strip()}")
    else:
        print(f"  [OK] {sql[:60]}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pg-password", default=os.getenv("PGPASSWORD", ""),
                        help="PostgreSQL superuser (postgres) password")
    args = parser.parse_args()

    if not args.pg_password:
        args.pg_password = input("Enter your PostgreSQL superuser password: ")

    print("\n[1/2] Creating database and user...")
    for sql in SQL_COMMANDS:
        run_psql(args.pg_password, sql)

    print("\n[2/2] Creating application tables...")
    # Import here so the DB URL is already configured
    from backend.database import engine, Base
    import backend.models  # noqa: F401 – registers all models
    Base.metadata.create_all(bind=engine)
    print("  [OK] All tables created.")
    print("\n✅ Setup complete! Start the server with:")
    print("   uvicorn backend.main:app --reload --port 8000\n")


if __name__ == "__main__":
    main()
