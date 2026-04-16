import os
import requests
from bs4 import BeautifulSoup
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.user import User
from app.models.user_owned_game import UserOwnedGame
from app.services.steam_client import SteamClient
from app.services.steam_ingestion_service import upsert_game_from_store_data


def fetch_real_tags(app_id: int) -> list[str]:
    """
    The Steam store page itself contains the most reliable tags.
    """
    url = f"https://store.steampowered.com/app/{app_id}/"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        tag_elements = soup.select(".app_tag")
        tags = [
            tag.get_text().strip()
            for tag in tag_elements
            if tag.get_text().strip() and tag.get_text().strip() != "+"
        ]
        return tags
    except Exception as e:
        print(f"  Error scraping tags for {app_id}: {e}")
        return []


def _ingest_app_ids(app_ids: list[int]) -> None:
    api_key = os.environ.get("STEAM_WEB_API_KEY")
    if not api_key:
        print("Error: STEAM_WEB_API_KEY not found")
        return

    client = SteamClient(api_key=api_key)

    try:
        with SessionLocal() as db:
            print(f"Ingesting metadata and real tags for {len(app_ids)} owned games.")

            count = 0
            for app_id in app_ids:
                count += 1
                print(f"[{count}/{len(app_ids)}] Processing {app_id}...")

                try:
                    details_by_app_id = client.get_app_details([app_id])
                    details = details_by_app_id.get(app_id)

                    if not details:
                        print(f"  Skipping {app_id}: No details found")
                        continue

                    real_tags = fetch_real_tags(app_id)
                    if real_tags:
                        details["tags"] = {tag: 1 for tag in real_tags}

                    upsert_game_from_store_data(
                        db=db,
                        app_id=app_id,
                        source_record=None,
                        details=details,
                        semantic_doc_version="v1",
                    )

                    print(f"  Ingested {app_id}: {details.get('name')}")
                    db.commit()

                except Exception as e:
                    db.rollback()
                    print(f"  Error processing {app_id}: {e}")

    finally:
        client.close()

    print("Ingestion complete.")


def ingest_owned_metadata() -> None:
    """
    Original behavior: ingest metadata for all owned games in the database.
    """
    with SessionLocal() as db:
        app_ids = db.scalars(select(UserOwnedGame.steam_app_id)).all()

    app_ids = sorted({int(app_id) for app_id in app_ids if app_id is not None})
    _ingest_app_ids(app_ids)


def ingest_owned_metadata_for_user(steam_id: str) -> None:
    """
    Ingest metadata only for the connected user's owned games.
    """
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.steam_id == steam_id))

        if not user:
            print(f"No user found for steam_id={steam_id}")
            return

        app_ids = db.scalars(
            select(UserOwnedGame.steam_app_id).where(UserOwnedGame.user_id == user.id)
        ).all()

    app_ids = sorted({int(app_id) for app_id in app_ids if app_id is not None})

    if not app_ids:
        print(f"No owned games found for steam_id={steam_id}")
        return

    print(f"Starting owned metadata ingest for steam_id={steam_id}")
    _ingest_app_ids(app_ids)


if __name__ == "__main__":
    ingest_owned_metadata()
