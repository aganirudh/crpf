import os
import sys
import logging
import uuid

# Ensure backend directory is in path
sys.path.insert(0, os.path.abspath('.'))

from pramaan.db.session import SessionLocal
from pramaan.db.models import Tender
from pramaan.agents.cartographer import Cartographer

logging.basicConfig(level=logging.INFO)

def main():
    db = SessionLocal()
    tender_id = "a2eecd0d-82f7-4e68-821e-554b5eab3678"
    tender = db.get(Tender, uuid.UUID(tender_id))
    
    if not tender:
        print(f"No tender found in DB with ID: {tender_id}")
        return
        
    print(f"Testing cartographer on Tender: {tender.id} ({tender.filename})")
    
    cart = Cartographer(db)
    try:
        cart.run(tender, actor="test_script")
        print("Cartographer ran successfully!")
    except Exception as e:
        import traceback
        print("ERROR IN CARTOGRAPHER:")
        traceback.print_exc()

if __name__ == "__main__":
    main()
