from __future__ import annotations

from app.db.session import SessionLocal
from app.services.steam_tag_taxonomy_service import load_query_map_seed, seed_query_tag_map


def main() -> None:
    mappings = load_query_map_seed()

    with SessionLocal() as db:
        result = seed_query_tag_map(db, mappings)

    print(result)


if __name__ == "__main__":
    main()
