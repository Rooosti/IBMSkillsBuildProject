from sqlalchemy import create_engine

from app.core.config import settings
from app.db.base import Base
from app.models.steam_tag import SteamTag, SteamTagAlias, SteamQueryTagMap


def main() -> None:
    engine = create_engine(settings.database_url)

    Base.metadata.create_all(
        bind=engine,
        tables=[
            SteamTag.__table__,
            SteamTagAlias.__table__,
            SteamQueryTagMap.__table__,
        ],
        checkfirst=True,
    )

    print("Created steam tag tables if missing.")


if __name__ == "__main__":
    main()
