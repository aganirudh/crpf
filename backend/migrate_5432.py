
import os
import sys

# Add the crpf directory to sys.path
sys.path.append(os.path.abspath("backend"))

from sqlalchemy import create_engine, text

db_url = "postgresql+psycopg://pramaan:pramaan@localhost:5432/pramaan"
print(f"Connecting to {db_url}...")

try:
    engine = create_engine(db_url)
    with engine.connect() as conn:
        print("Connected! Running migration...")
        conn.execute(text("ALTER TABLE officer ADD COLUMN IF NOT EXISTS email VARCHAR(255) UNIQUE"))
        conn.execute(text("ALTER TABLE officer ADD COLUMN IF NOT EXISTS hashed_password VARCHAR(255)"))
        conn.execute(text("ALTER TABLE bidder ADD COLUMN IF NOT EXISTS email VARCHAR(255)"))
        conn.execute(text("ALTER TABLE bidder ADD COLUMN IF NOT EXISTS hashed_password VARCHAR(255)"))
        conn.commit()
        print("Migration complete on 5432.")
except Exception as e:
    print(f"Failed on 5432: {e}")
