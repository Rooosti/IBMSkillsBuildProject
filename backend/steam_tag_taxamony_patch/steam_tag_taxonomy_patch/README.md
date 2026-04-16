# Steam tag taxonomy patch

This patch adds an offline Steam tag taxonomy database that your LLM can use for tag resolution and query expansion.

It is based on the official Steamworks Steam Tags documentation categories and weighting guidance.

Included files:
- `app/models/steam_tag.py`
- `app/services/steam_tag_taxonomy_service.py`
- `app/services/steam_tag_tools.py`
- `app/scripts/ingest_steam_tag_taxonomy.py`
- `app/scripts/seed_steam_query_tag_map.py`
- `app/data/steam_query_tag_map_seed.json`

## What this gives you

- A local `steam_tags` taxonomy table sourced from the official Steamworks tags doc.
- Alias resolution so the LLM can ask for `shooter`, `cozy`, `soulslike`, `farm sim`, and similar user language.
- A seeded `steam_query_tag_map` table for query expansion.
- LLM-facing helper tools:
  - `resolve_steam_tags`
  - `list_steam_tags_by_category`

## Install dependencies

If you do not already have them:

```bash
pip install requests beautifulsoup4
```

## Apply models / migration

Create a migration for these new tables:
- `steam_tags`
- `steam_tag_aliases`
- `steam_query_tag_map`

If your project uses a different `Base` import path, update the import in `app/models/steam_tag.py`.

## Seed flow

1. Ingest the official taxonomy from Steamworks docs:

```bash
python -m app.scripts.ingest_steam_tag_taxonomy
```

2. Seed the curated query map:

```bash
python -m app.scripts.seed_steam_query_tag_map
```

## Integrating with your LLM flow

Add the functions from `app/services/steam_tag_tools.py` into your tool registry.

Recommended pattern:
- When the user says something like `shooter`, `cozy`, `soulslike`, or `farm sim`, first call `resolve_steam_tags`.
- Then call your owned-game search using the canonical resolved tag names.

## Important design rule

Do not make the LLM choose numeric tag IDs directly.
Have the LLM choose plain-English tag concepts, then let your backend resolve those into canonical tags and optional IDs.

## Example

User says:
- `What shooter games do I own?`

LLM flow:
1. `resolve_steam_tags(["shooter"])`
2. backend returns canonical tags like `Shooter`, `FPS`, `Third-Person Shooter`, `Top-Down Shooter`
3. call your owned-game search with `tags=[...]`

## Notes

- The Steamworks doc is HTML, not a formal API. The ingestion script is resilient, but you should treat it as a versioned snapshot process.
- The query map seed includes more terms than the official table headings alone. During seeding, any canonical tag that does not exist in the ingested taxonomy is skipped safely.
