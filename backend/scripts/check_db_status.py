from sqlalchemy import text
from app.db.session import engine

def check_db():
    tables = [
        'games',
        'game_features',
        'user_owned_games',
        'steam_tags',
        'steam_tag_aliases',
        'steam_query_tag_map'
    ]
    with engine.connect() as conn:
        for table in tables:
            try:
                result = conn.execute(text(f"SELECT count(*) FROM {table}"))
                count = result.scalar()
                print(f"{table}: {count}")
            except Exception as e:
                print(f"{table}: Table not found or error: {e}")

if __name__ == "__main__":
    check_db()
