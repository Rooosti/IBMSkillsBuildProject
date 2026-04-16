from sqlalchemy import select
from app.db.session import SessionLocal
from app.models.game_catalog import Game, GameFeature

def inspect_tags():
    with SessionLocal() as db:
        rows = db.execute(
            select(Game.title, GameFeature.tags_json)
            .join(GameFeature, Game.id == GameFeature.game_id)
        ).all()
        
        for title, tags in rows:
            print(f"{title}: {tags}")

if __name__ == "__main__":
    inspect_tags()
