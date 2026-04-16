from sqlalchemy import text
from app.db.session import engine

def fix_schema():
    with engine.connect() as conn:
        print("Enabling pgvector extension...")
        try:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
            print("Successfully enabled pgvector.")
        except Exception as e:
            print(f"Error enabling pgvector: {e}")

        print("Adding embedding column to game_semantic_docs...")
        try:
            # We use 384 dimensions to match granite-embedding-30m-english
            conn.execute(text("ALTER TABLE game_semantic_docs ADD COLUMN IF NOT EXISTS embedding vector(384)"))
            conn.commit()
            print("Successfully added embedding column.")
        except Exception as e:
            print(f"Error adding embedding column: {e}")

        # Also ensure steam_tag_id exists as per previous version of this script
        print("Ensuring steam_tag_id exists on steam_tags...")
        try:
            conn.execute(text("ALTER TABLE steam_tags ADD COLUMN IF NOT EXISTS steam_tag_id INTEGER"))
            conn.commit()
        except Exception as e:
            print(f"Error with steam_tag_id: {e}")

if __name__ == "__main__":
    fix_schema()
