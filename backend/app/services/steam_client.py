from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

import httpx


class SteamApiError(RuntimeError):
    pass


@dataclass(slots=True)
class SteamStoreAppRecord:
    appid: int
    name: str | None
    last_modified: int | None
    price_change_number: int | None


class SteamClient:
    def __init__(
        self,
        api_key: str,
        *,
        timeout: float = 30.0,
        partner_base_url: str = "https://partner.steam-api.com",
        public_api_base_url: str = "https://api.steampowered.com",
        store_base_url: str = "https://store.steampowered.com",
    ) -> None:
        self.api_key = api_key
        self.partner_base_url = partner_base_url.rstrip("/")
        self.public_api_base_url = public_api_base_url.rstrip("/")
        self.store_base_url = store_base_url.rstrip("/")
        self.http = httpx.Client(timeout=timeout)

    def close(self) -> None:
        self.http.close()

    def _get_json(self, url: str, *, params: dict[str, Any]) -> dict[str, Any]:
        response = self.http.get(url, params=params)
        response.raise_for_status()
        try:
            return response.json()
        except ValueError as exc:
            raise SteamApiError(f"Steam returned non-JSON for {url}") from exc

    def iter_store_app_list(
        self,
        *,
        if_modified_since: int | None = None,
        have_description_language: str | None = None,
        include_games: bool = True,
        include_dlc: bool = False,
        include_software: bool = False,
        include_videos: bool = False,
        include_hardware: bool = False,
        max_results: int = 50_000,
    ) -> Iterable[SteamStoreAppRecord]:
        last_appid = 0

        while True:
            params = {
                "key": self.api_key,
                "max_results": max_results,
                "last_appid": last_appid,
                "include_games": str(include_games).lower(),
                "include_dlc": str(include_dlc).lower(),
                "include_software": str(include_software).lower(),
                "include_videos": str(include_videos).lower(),
                "include_hardware": str(include_hardware).lower(),
            }
            if if_modified_since is not None:
                params["if_modified_since"] = if_modified_since
            if have_description_language:
                params["have_description_language"] = have_description_language

            payload = self._get_json(
                f"{self.partner_base_url}/IStoreService/GetAppList/v1/",
                params=params,
            )

            response = payload.get("response", {})
            apps = response.get("apps", [])
            if not apps:
                break

            for item in apps:
                appid = int(item["appid"])
                yield SteamStoreAppRecord(
                    appid=appid,
                    name=item.get("name"),
                    last_modified=item.get("last_modified"),
                    price_change_number=item.get("price_change_number"),
                )
                last_appid = appid

            if not response.get("have_more_results"):
                break

    def get_app_details(
        self,
        app_ids: list[int],
        *,
        language: str = "english",
        country: str = "US",
        filters: str | None = None,
    ) -> dict[int, dict[str, Any]]:
        if not app_ids:
            return {}

        params: dict[str, Any] = {
            "appids": ",".join(str(app_id) for app_id in app_ids),
            "l": language,
            "cc": country,
        }
        if filters:
            params["filters"] = filters

        payload = self._get_json(
            f"{self.store_base_url}/api/appdetails",
            params=params,
        )

        normalized: dict[int, dict[str, Any]] = {}
        for raw_appid, wrapper in payload.items():
            try:
                appid = int(raw_appid)
            except (TypeError, ValueError):
                continue
            if not wrapper.get("success"):
                continue
            data = wrapper.get("data") or {}
            normalized[appid] = data
        return normalized

    def get_owned_games(
        self,
        *,
        steam_id: str,
        include_appinfo: bool = True,
        include_played_free_games: bool = True,
        appids_filter: list[int] | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "key": self.api_key,
            "steamid": steam_id,
            "include_appinfo": str(include_appinfo).lower(),
            "include_played_free_games": str(include_played_free_games).lower(),
        }
        if appids_filter:
            params["appids_filter"] = ",".join(str(app_id) for app_id in appids_filter)

        payload = self._get_json(
            f"{self.partner_base_url}/IPlayerService/GetOwnedGames/v1/",
            params=params,
        )
        return payload.get("response", {}).get("games", [])

    def get_recently_played_games(self, *, steam_id: str, count: int = 20) -> list[dict[str, Any]]:
        payload = self._get_json(
            f"{self.partner_base_url}/IPlayerService/GetRecentlyPlayedGames/v1/",
            params={
                "key": self.api_key,
                "steamid": steam_id,
                "count": count,
            },
        )
        return payload.get("response", {}).get("games", [])
