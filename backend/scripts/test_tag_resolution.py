from app.db.session import SessionLocal
from app.services.steam_tag_taxonomy_service import resolve_terms_to_tags

def test():
    with SessionLocal() as db:
        res = resolve_terms_to_tags(db, ["cozy", "chill"])
        import json
        print(json.dumps(res, indent=2))

if __name__ == "__main__":
    test()
