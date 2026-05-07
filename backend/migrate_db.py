
import os
import sys

# Add the crpf directory to sys.path
sys.path.append(os.path.abspath("backend"))

from sqlalchemy import text
from pramaan.db.session import engine, session_scope

def migrate():
    with session_scope() as db:
        print("Migrating database...")
        # Add email and hashed_password to officer
        try:
            db.execute(text("ALTER TABLE officer ADD COLUMN IF NOT EXISTS email VARCHAR(255) UNIQUE"))
            db.execute(text("ALTER TABLE officer ADD COLUMN IF NOT EXISTS hashed_password VARCHAR(255)"))
            print("Updated officer table.")
        except Exception as e:
            print(f"Error updating officer table: {e}")

        # Add email and hashed_password to bidder
        try:
            db.execute(text("ALTER TABLE bidder ADD COLUMN IF NOT EXISTS email VARCHAR(255)"))
            db.execute(text("ALTER TABLE bidder ADD COLUMN IF NOT EXISTS hashed_password VARCHAR(255)"))
            print("Updated bidder table.")
        except Exception as e:
            print(f"Error updating bidder table: {e}")
        
        db.commit()
    print("Migration complete.")

if __name__ == "__main__":
    migrate()
