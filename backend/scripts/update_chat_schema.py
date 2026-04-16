import sys
import os
from sqlalchemy import text

# Add the parent directory to sys.path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import engine

def update_schema():
    print("Connecting to database to update chat_messages schema...")
    with engine.begin() as conn:
        try:
            # Check if column exists first to be safe
            check_column = conn.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name='chat_messages' AND column_name='metadata_json'"
            )).fetchone()
            
            if not check_column:
                print("Adding metadata_json column to chat_messages...")
                conn.execute(text("ALTER TABLE chat_messages ADD COLUMN metadata_json JSONB"))
                print("Successfully added metadata_json column.")
            else:
                print("Column metadata_json already exists.")
                
        except Exception as e:
            print(f"Error updating schema: {e}")
            sys.exit(1)

if __name__ == "__main__":
    update_schema()
