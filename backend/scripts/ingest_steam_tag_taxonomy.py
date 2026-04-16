import json
from pathlib import Path

from app.db.session import SessionLocal
from app.services.steam_tag_taxonomy_service import upsert_taxonomy

DATA_PATH = Path(__file__).resolve().parents[1] / "app" / "data" / "steam_tags_taxonomy.json"


def main() -> None:
    with DATA_PATH.open("r", encoding="utf-8") as f:
        taxonomy_rows = json.load(f)

    with SessionLocal() as db:
        result = upsert_taxonomy(db, taxonomy_rows)

    print(result)


if __name__ == "__main__":
    main()
