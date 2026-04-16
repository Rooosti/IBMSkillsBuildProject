from __future__ import annotations

import argparse
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.services.steam_client import SteamClient
from app.services.steam_ingestion_service import IngestionConfig, ingest_catalog


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest Steam store catalog metadata into the local database.")
    parser.add_argument("--database-url", default=os.environ.get("DATABASE_URL", "sqlite:///./app.db"))
    parser.add_argument("--language", default=os.environ.get("STEAM_STORE_LANGUAGE", "english"))
    parser.add_argument("--country", default=os.environ.get("STEAM_STORE_COUNTRY", "US"))
    parser.add_argument("--if-modified-since", type=int, default=None)
    parser.add_argument("--max-apps", type=int, default=None)
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--commit-every", type=int, default=100)
    args = parser.parse_args()

    api_key = os.environ["STEAM_WEB_API_KEY"]
    engine = create_engine(args.database_url)
    client = SteamClient(api_key=api_key)

    with Session(engine) as db:
        result = ingest_catalog(
            db,
            client,
            IngestionConfig(
                language=args.language,
                country=args.country,
                appdetails_batch_size=args.batch_size,
                commit_every=args.commit_every,
                if_modified_since=args.if_modified_since,
                max_apps=args.max_apps,
            ),
        )

    client.close()
    print(
        {
            "scanned": result.scanned,
            "detailed": result.detailed,
            "inserted_or_updated": result.inserted_or_updated,
            "skipped_non_games": result.skipped_non_games,
            "skipped_missing_details": result.skipped_missing_details,
        }
    )


if __name__ == "__main__":
    main()
