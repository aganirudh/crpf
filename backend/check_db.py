
import os
import sys

# Add the crpf directory to sys.path
sys.path.append(os.path.abspath("backend"))

from sqlalchemy import select, text
from pramaan.db.session import engine, session_scope
from pramaan.db.models import Officer, Bidder

try:
    with session_scope() as db:
        # Check columns of officer table
        result = db.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'officer'"))
        columns = [row[0] for row in result]
        print(f"Officer columns: {columns}")
        
        # Check if any officers exist
        officers = db.execute(select(Officer)).scalars().all()
        print(f"Number of officers: {len(officers)}")
        for o in officers:
            print(f"  - {o.name} ({o.external_id})")
            
        # Check columns of bidder table
        result = db.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'bidder'"))
        columns = [row[0] for row in result]
        print(f"Bidder columns: {columns}")
except Exception as e:
    print(f"Error: {e}")
