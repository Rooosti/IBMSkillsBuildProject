from __future__ import annotations

from sqlalchemy.orm import Session

from app.services.steam_tag_taxonomy_service import list_tags_by_category, resolve_terms_to_tags

STEAM_TAG_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "resolve_steam_tags",
            "description": (
                "Resolve plain-English user terms into canonical Steam tags from the offline taxonomy. "
                "Use this before filtering owned games by tags."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "terms": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "limit_per_term": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 50,
                    },
                },
                "required": ["terms"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_steam_tags_by_category",
            "description": "List canonical Steam tags from the offline taxonomy for a specific category.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {"type": "string"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 500},
                },
                "required": ["category"],
            },
        },
    },
]


def run_steam_tag_tool(db: Session, tool_name: str, arguments: dict) -> dict:
    if tool_name == "resolve_steam_tags":
        return resolve_terms_to_tags(
            db=db,
            terms=arguments.get("terms") or [],
            limit_per_term=int(arguments.get("limit_per_term", 20)),
        )

    if tool_name == "list_steam_tags_by_category":
        return list_tags_by_category(
            db=db,
            category=str(arguments["category"]),
            limit=int(arguments.get("limit", 500)),
        )

    raise RuntimeError(f"Unsupported Steam tag tool: {tool_name}")
