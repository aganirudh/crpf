
import os
import sys

# Add the crpf directory to sys.path
sys.path.append(os.path.abspath("backend"))

from sqlalchemy import create_engine, text

# Try 5432
db_url = "postgresql+psycopg://pramaan:pramaan@localhost:5432/pramaan"
print(f"Connecting to {db_url}...")

try:
    engine = create_engine(db_url)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        print(f"Success! {result.scalar()}")
except Exception as e:
    print(f"Failed on 5432: {e}")

# Try 5433
db_url = "postgresql+psycopg://pramaan:pramaan@localhost:5433/pramaan"
print(f"Connecting to {db_url}...")
try:
    engine = create_engine(db_url)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        print(f"Success! {result.scalar()}")
except Exception as e:
    print(f"Failed on 5433: {e}")
