from sqlalchemy.orm import Session

from app.services.steam_store_search import search_steam_store, vector_search_games
from app.services.recommendation_service import rank_games
from app.services.chat_tools import (
    get_library_import_status,
    get_user_context,
    get_recently_played_games,
    get_game_metadata,
    get_reference_game_features,
    search_owned_games,
    list_owned_games,
)

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_library_import_status",
            "description": (
                "Gets the status of the user's Steam library import, including total game count, "
                "total playtime, and top 5 most played games."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_owned_games",
        "description": (
            "Lists games owned by the authenticated user from the SQL database. "
            "Use this when the user asks what games they own or wants their library listed."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "minimum": 1, "maximum": 100},
                "offset": {"type": "integer", "minimum": 0},
            },
            "required": [],
        },
    },
    },
    {
        "type": "function",
        "function": {
            "name": "get_user_context",
            "description": (
                "Gets the authenticated user's recommendation context including library summary, "
                "recently played games, preferences, and device profile."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_recently_played_games",
            "description": "Gets recently played games for the authenticated user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "minimum": 1, "maximum": 20}
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_game_metadata",
            "description": (
                "Gets structured metadata for a Steam game including description, genres, tags, "
                "categories, controller support, multiplayer flags, Steam Deck status, and requirements."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "steam_app_id": {"type": "integer"}
                },
                "required": ["steam_app_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_reference_game_features",
            "description": (
                "Gets the feature profile for a reference game the user mentioned, identified by steam_app_id."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "steam_app_id": {"type": "integer"}
                },
                "required": ["steam_app_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_owned_games",
            "description": "Search the user's owned Steam library.",
            "parameters": {
                "type": "object",
                "properties": {
                    "genres": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Actual game genres like Action, RPG, Strategy, Adventure, Simulation."
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Mood/theme/style tags like Horror, Cozy, Relaxing, Survival Horror, Atmospheric, Cute."
                    },
                    "coop_only": {"type": "boolean"},
                    "controller_required": {"type": "boolean"},
                    "steam_deck_only": {"type": "boolean"},
                    "max_minutes_played": {"type": "integer"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 12},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_steam_store",
            "description": (
                "Searches the live Steam store for NEW games. "
                "Use this when the user wants games they do not already own, or when library search found no matches. "
                "Put the user's natural-language request in query_text. "
                "Use preferred_tags for moods, themes, vibes, subgenres, and Steam tags like Horror, Cozy, Relaxing, Atmospheric, Survival Horror, Psychological Horror, Cute, Wholesome, Sandbox. "
                "Use genres only for broad game genres like Action, RPG, Strategy, Adventure, Simulation, Casual, Racing, Sports."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query_text": {
                        "type": "string",
                        "description": (
                            "The user's natural-language request, such as "
                            "'cozy relaxing games', 'survival horror under $20', or 'story-rich sci-fi RPGs'."
                        ),
                    },
                    "preferred_tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Optional Steam-style tags, themes, moods, or subgenres. "
                            "Examples: Horror, Survival Horror, Psychological Horror, Cozy, Relaxing, Atmospheric, Cute, Wholesome, Open World, Base Building."
                        ),
                    },
                    "genres": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Optional broad genres only. "
                            "Examples: Action, RPG, Strategy, Adventure, Simulation, Casual, Indie."
                        ),
                    },
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 12,
                        "description": "Maximum number of results to return.",
                    },
                },
                "required": ["query_text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "semantic_search_store",
            "description": (
                "Performs a SEMANTIC (conceptual) search for games in our local catalog. "
                "Use this for complex, descriptive, or 'fuzzy' queries like 'games about depression', "
                "'something like hollow knight', or 'atmospheric games with deep lore'. "
                "This searches the database concept-to-concept rather than by literal tags."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query_text": {
                        "type": "string",
                        "description": "The descriptive or conceptual query."
                    },
                    "limit": {"type": "integer", "minimum": 1, "maximum": 20},
                },
                "required": ["query_text"],
            },
        },
    },
]


import json

def _clean_args(args: dict) -> dict:
    """
    Some models (like Granite) occasionally wrap JSON types in strings 
    (e.g., "true" instead of true). This helper tries to normalize them.
    """
    cleaned = {}
    for k, v in args.items():
        if isinstance(v, str):
            v_lower = v.lower().strip()
            if v_lower == "true":
                cleaned[k] = True
            elif v_lower == "false":
                cleaned[k] = False
            elif v_lower == "null" or v_lower == "none":
                cleaned[k] = None
            elif v.startswith("[") and v.endswith("]"):
                try:
                    cleaned[k] = json.loads(v.replace("'", '"'))
                except:
                    cleaned[k] = v
            else:
                cleaned[k] = v
        else:
            cleaned[k] = v
    return cleaned

async def run_tool(db: Session, steam_id: str, tool_name: str, arguments: dict) -> dict:
    arguments = _clean_args(arguments)
    
    if tool_name == "get_library_import_status":
        return get_library_import_status(db, steam_id)
    if tool_name == "list_owned_games":
        return list_owned_games(
            db=db,
            steam_id=steam_id,
            limit=int(arguments.get("limit", 50)),
            offset=int(arguments.get("offset", 0)),
        )

    if tool_name == "search_steam_store":
        return search_steam_store(
            query_text=str(arguments.get("query_text", "")),
            preferred_tags=arguments.get("preferred_tags"),
            genres=arguments.get("genres"),
            limit=int(arguments.get("limit", 12)),
        )

    if tool_name == "semantic_search_store":
        return await vector_search_games(
            query_text=str(arguments.get("query_text", "")),
            limit=int(arguments.get("limit", 12)),
        )

    if tool_name == "get_user_context":
        return await get_user_context(db, steam_id)

    if tool_name == "get_recently_played_games":
        limit = int(arguments.get("limit", 5))
        return get_recently_played_games(db, steam_id, limit=limit)

    if tool_name == "get_game_metadata":
        steam_app_id = int(arguments["steam_app_id"])
        return get_game_metadata(db, steam_app_id)

    if tool_name == "get_reference_game_features":
        steam_app_id = int(arguments["steam_app_id"])
        return get_reference_game_features(db, steam_app_id)

    if tool_name == "search_owned_games":
        return search_owned_games(
            db=db,
            steam_id=steam_id,
            genres=arguments.get("genres"),
            tags=arguments.get("tags"),
            coop_only=arguments.get("coop_only"),
            controller_required=arguments.get("controller_required"),
            steam_deck_only=arguments.get("steam_deck_only"),
            max_minutes_played=arguments.get("max_minutes_played"),
            limit=int(arguments.get("limit", 10)),
        )

    if tool_name == "rank_recommendations":
        return {
            "ranked_results": rank_games(
                db=db,
                steam_id=steam_id,
                candidates=arguments.get("candidates", []),
                context_tags=arguments.get("context_tags"),
            )
        }

    raise RuntimeError(f"Unsupported tool: {tool_name}")
