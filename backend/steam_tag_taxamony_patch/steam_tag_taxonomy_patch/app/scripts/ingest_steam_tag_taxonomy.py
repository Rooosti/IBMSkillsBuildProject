from __future__ import annotations

from app.db.session import SessionLocal
from app.services.steam_tag_taxonomy_service import (
    fetch_steam_tags_doc_html,
    parse_taxonomy_from_html,
    upsert_taxonomy,
)


def main() -> None:
    html = fetch_steam_tags_doc_html()
    taxonomy_rows = parse_taxonomy_from_html(html)

    with SessionLocal() as db:
        result = upsert_taxonomy(db, taxonomy_rows)

    print(result)


if __name__ == "__main__":
    main()
