from sqlalchemy import select
from app.db.session import SessionLocal
from app.models.steam_tag import SteamTag

def inspect():
    with SessionLocal() as db:
        rows = db.execute(select(SteamTag).limit(10)).scalars().all()
        for row in rows:
            print(f"{row.canonical_name}: ID={row.steam_tag_id}, Cat={row.category}")

if __name__ == "__main__":
    inspect()
