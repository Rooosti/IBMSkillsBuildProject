from app.db.session import SessionLocal
from app.services.steam_store_search import search_steam_store

def test():
    res = search_steam_store("chill cozy games under $5")
    import json
    print(json.dumps(res, indent=2))

if __name__ == "__main__":
    test()
