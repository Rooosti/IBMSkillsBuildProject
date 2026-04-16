# Steam-First Personal Game Recommender MVP

## One-line summary
A Steam-first personal game recommender that uses a user's owned library, declared hardware profile, and game metadata to answer natural-language game requests with deterministic compatibility checks plus semantic retrieval.

## Problem statement
Fragmented and disjointed platforms for game acquisition and usage create a confusing, hard-to-navigate environment. Decision fatigue, platform coordination, hardware constraints, and varying user knowledge about specific games make choosing what to play or buy unnecessarily difficult.

## MVP scope
This MVP intentionally narrows scope to **Steam-first discovery and recommendation**.

It does **not** attempt to fully integrate PlayStation or Xbox libraries because those ecosystems are much more closed and do not provide the same practical public access patterns for library and metadata ingestion.

### Goals
- Let a user sign in with Steam
- Read the user's owned games, when available via Steam privacy settings / API access
- Collect a lightweight hardware profile and preference profile
- Accept natural-language requests such as:
  - "Something like Baldur's Gate 3 but shorter and less complex"
  - "Good co-op game for two people on Steam Deck"
  - "What should I install tonight from my library?"
- Filter candidates using hard constraints
- Retrieve semantically similar games using embeddings
- Rank results using only the user's own data and game metadata
- Generate a short explanation for why each recommendation fits

### Non-goals
- Cross-platform account linking beyond Steam in the MVP
- Collaborative filtering across many users
- Cross-user behavior modeling like "people like you also played"
- Full automation of hardware detection via Steam
- Perfect recommendations; this is a fragile MVP focused on usefulness and correctness

## Product positioning
This is **not** a universal game platform aggregator in v1.

This is a **Steam-first AI assistant for personalized game discovery and play decisions**.

## Core product principles
1. **Deterministic facts beat model guesses**
   - Hardware fit, platform support, controller support, co-op flags, price, and ownership should be resolved by structured data and rules.
2. **Semantic search handles fuzzy language**
   - Vague requests like "BG3 but less intense" should go through embeddings and LLM query understanding.
3. **No cross-user recommendation dependency**
   - Personalization should come from the user's own library, profile, and request history.
4. **Explanations matter**
   - The LLM should explain why a game matches the user's request, hardware, and ownership state.

## Why Steam-first
### Steam can help with
- User sign-in via Steam/OpenID or Steam-native auth flows
- Owned library lookup for users who allow the relevant visibility/access
- Game metadata and store-level enrichment
- Game-level compatibility signals such as Steam Deck status

### Steam does not reliably provide
- Per-user hardware profile like CPU/GPU/RAM in a directly usable public API form

Therefore, the MVP should treat:
- **ownership** as Steam-derived when possible
- **hardware profile** as app-owned user data

## High-level architecture
The system should be split into two separate flows.

### 1. Offline ingestion / indexing
Purpose: build and refresh the game knowledge base.

Steps:
1. Fetch Steam catalog/store metadata
2. Normalize metadata into a canonical game schema
3. Store structured facts in a relational database
4. Build embeddings for descriptive text, tags, and summaries
5. Store vectors in a vector database

### 2. Online query / recommendation flow
Purpose: answer a user's request in real time.

Steps:
1. User signs in and/or provides a prompt
2. System loads user profile, hardware profile, and owned library
3. LLM parses the request into a strict JSON schema
4. Hard-filter engine queries the relational DB
5. Semantic retrieval queries the vector DB
6. Ranker merges and scores candidates
7. Optional Steam enrichment fills in final details
8. LLM generates explanations for the final recommendations

## Recommended architecture components

### Frontend
- Web app or lightweight desktop/web hybrid
- User sign-in with Steam
- Onboarding form for hardware and play preferences
- Search/chat style interface for natural-language requests

### Backend API
Responsible for:
- user auth session handling
- profile storage
- library sync
- query orchestration
- retrieval and ranking
- LLM prompt assembly
- response formatting

### Relational database
Use SQLite for a fragile MVP, or Postgres if you want safer scaling.

Store:
- canonical game records
- hard metadata / filterable attributes
- user profiles
- user-owned games
- recommendation logs

### Vector database
Use ChromaDB for the MVP.

Store embeddings for:
- game descriptions
- tags and normalized tag summaries
- curated "why play this" blurbs
- optional synthetic summaries generated from metadata

### LLM
Use an LLM for:
- natural-language query parsing into strict JSON
- explanation generation for final results
- optional clarification questions when the request is underspecified

Do **not** use the LLM as the source of truth for compatibility, ownership, or hard filters.

## Architecture diagram logic (cleaned up)
The original diagram is directionally correct, but the online and offline flows should be separated.

### Offline
Steam / catalog source -> metadata normalizer -> relational DB
Steam / catalog source -> text preparation -> embedding job -> vector DB

### Online
User query -> LLM query parser -> structured JSON
Structured JSON -> hard filter engine -> relational DB candidate set
Structured JSON -> query embedding -> vector DB semantic set
Candidate sets -> ranking / merge layer -> final top N
Final top N + user context -> LLM explanation -> response

## Why remove LangGraph for MVP
A graph orchestration framework is probably unnecessary at this stage.

A normal backend service with explicit pipeline steps is simpler, easier to debug, and more fragile-MVP friendly.

Use a workflow/orchestration library later only if you truly need:
- branching multi-step tool use
- retries and recovery logic
- complex clarification loops
- multi-agent behavior

## Query understanding design
The LLM should output strict structured JSON, not prose.

Example:

```json
{
  "intent": "find_game",
  "reference_games": ["Baldur's Gate 3"],
  "constraints": {
    "coop": true,
    "shorter_than_reference": true,
    "less_complex_than_reference": true,
    "controller_required": false,
    "owned_only": false,
    "steam_deck_compatible": null,
    "max_price": null
  },
  "ranking_preferences": {
    "novelty": 0.4,
    "familiarity": 0.6
  },
  "clarification_needed": false
}
```

## Retrieval and recommendation strategy
### Rule 1: hard filters first
Use structured SQL filters for facts such as:
- owned vs not owned
- platform/store availability
- controller support
- Steam Deck compatibility
- multiplayer/co-op flags
- party size
- price cap
- performance tier
- genre exclusions

### Rule 2: semantic retrieval second
Use embeddings for fuzzy intent such as:
- "like Hades but more relaxed"
- "couch co-op but beginner friendly"
- "story-heavy but not too long"

### Rule 3: rank with single-user personalization
Rank candidates using only:
- current request fit
- compatibility fit
- owned library similarity
- user preferences
- recency of user interest
- novelty vs familiarity balance

### Rule 4: LLM explains, not decides core facts
The LLM should explain why a result fits, but it should not invent unsupported compatibility claims.

## Personalization without cross-user data
This MVP should use **content-based recommendation**, not collaborative filtering.

### Inputs for personalization
- user's owned games
- optionally user's recently played games
- explicit likes/dislikes
- preferred genres/tags
- preferred session length
- preferred complexity
- solo vs co-op tendency
- controller preference
- device/hardware profile

### Example taste-profile features
- normalized tag frequencies from owned/liked games
- embedding centroid of the user's liked games
- platform and controller preference flags
- complexity preference score
- session-length preference score

### Ranking concept
Overall candidate score can be a weighted combination of:
- hard compatibility pass/fail
- semantic similarity to current request
- similarity to user's taste profile
- ownership state match
- freshness / novelty bonus
- repetition penalty

## User hardware strategy
Do not depend on Steam to provide user hardware.

Instead, store a lightweight app-owned profile.

### MVP hardware/profile questions
- device type: desktop, laptop, Steam Deck, handheld PC
- performance tier: low, mid, high
- controller required: yes/no
- storage sensitivity: yes/no
- online multiplayer okay: yes/no
- preferred session length: short, medium, long

### Optional future hardware detection
If you later build a native helper app, you can detect local machine specs with user consent and convert them into a normalized performance tier.

## Data model
Below is a suggested relational schema for the MVP.

### `games`
Canonical game records.

Fields:
- id
- steam_app_id
- title
- short_description
- release_date
- developer
- publisher
- price_current
- price_currency
- header_image_url
- store_url
- is_active

### `game_features`
Structured metadata for filtering.

Fields:
- game_id
- genres_json
- tags_json
- categories_json
- has_singleplayer
- has_multiplayer
- has_online_coop
- has_local_coop
- has_pvp
- controller_support
- steam_deck_status
- supported_languages_json

### `game_requirements`
Normalized requirements and fit signals.

Fields:
- game_id
- min_os
- min_cpu_text
- min_gpu_text
- min_ram_gb
- min_storage_gb
- recommended_os
- recommended_cpu_text
- recommended_gpu_text
- recommended_ram_gb
- recommended_storage_gb
- performance_tier_estimate

### `game_semantic_docs`
Prepared text used to embed the game.

Fields:
- game_id
- semantic_text
- version
- updated_at

### `users`
App users.

Fields:
- id
- steam_id
- created_at
- updated_at

### `user_device_profiles`
App-owned hardware and play constraints.

Fields:
- user_id
- device_type
- performance_tier
- controller_required
- storage_sensitive
- bandwidth_sensitive
- preferred_session_length
- accessibility_notes
- updated_at

### `user_preferences`
Explicit long-lived user preferences.

Fields:
- user_id
- favorite_genres_json
- favorite_tags_json
- disliked_tags_json
- complexity_preference
- novelty_preference
- solo_vs_coop_preference
- budget_preference
- updated_at

### `user_owned_games`
User ownership snapshot from Steam.

Fields:
- user_id
- game_id
- steam_app_id
- owned
- playtime_minutes
- last_synced_at

### `recommendation_events`
Logs for debugging and future tuning.

Fields:
- id
- user_id
- query_text
- parsed_query_json
- candidate_ids_json
- returned_ids_json
- timestamp

## Vector DB design
One vector per game is enough for MVP.

### Recommended embedded text recipe
Construct a semantic text field from:
- title
- short description
- normalized genres
- normalized tags
- play-style summary
- complexity summary
- pacing/session summary
- co-op summary
- controller summary
- Steam Deck summary

Example semantic text:

```text
Hades. Action roguelike with fast combat, strong build variety, and short session loops. Great for solo play. Controller-friendly. Medium complexity. Repeated runs with story progression. Good fit for players who like tight combat and replayability.
```

## End-to-end online request flow
### Example request
"I want something like Baldur's Gate 3 but shorter, less complex, and good on Steam Deck. Prefer co-op if possible."

### Pipeline
1. Load user profile and owned library
2. Parse request into structured JSON
3. Extract reference game features for BG3
4. Hard filter for:
   - Steam Deck compatible
   - co-op if available or preferred
   - exclude unsupported games
5. Semantic search for:
   - "BG3-like"
   - shorter
   - less complex
6. Merge filtered candidates with semantic candidates
7. Rank using:
   - request fit
   - similarity to reference game
   - user taste profile
   - owned vs not owned mode
8. Send top candidates to LLM for explanation
9. Return top 3 to 5 recommendations

## Recommendation modes
Support explicit modes because they change filtering behavior.

### 1. Discovery mode
"What should I buy/play next?"
- allow unowned games
- optionally exclude already owned games

### 2. Library mode
"What should I install tonight from my library?"
- owned_only = true
- prioritize unplayed or lightly played games

### 3. Party mode
"What can two of us play together on the couch?"
- require local co-op or shared-compatible multiplayer
- require controller support if relevant

## API sketch
### `POST /auth/steam/callback`
Creates or updates a user session after Steam sign-in.

### `POST /users/{id}/sync-library`
Fetches and normalizes owned Steam games for the user.

### `PUT /users/{id}/device-profile`
Stores or updates the user's hardware and play constraints.

### `PUT /users/{id}/preferences`
Stores or updates user preferences.

### `POST /recommendations/query`
Request body:

```json
{
  "user_id": "123",
  "query": "something like Baldur's Gate 3 but shorter and less complex",
  "mode": "discovery"
}
```

Response body:

```json
{
  "parsed_query": {
    "intent": "find_game"
  },
  "results": [
    {
      "game_id": "g1",
      "title": "Divinity: Original Sin 2",
      "score": 0.82,
      "reasons": [
        "shares party-based RPG DNA",
        "fits your co-op preference",
        "playable on your target device tier"
      ]
    }
  ]
}
```

## Ranking pseudocode
```python
score = 0
score += request_semantic_similarity * 0.35
score += user_taste_similarity * 0.20
score += reference_game_similarity * 0.20
score += ownership_mode_match * 0.10
score += compatibility_confidence * 0.15

if fails_hard_constraint:
    score = 0
```

Treat weights as tunable constants, not product truths.

## Prompting guidance for coding bots / LLMs
When generating code, follow these rules:

1. Separate offline ingestion from online serving.
2. Use SQL for hard constraints and filtering.
3. Use the vector DB only for semantic retrieval, not hard facts.
4. Keep the LLM output schema strict and machine-parseable.
5. Store user hardware/profile in app-owned tables, not in the vector DB.
6. Design for Steam-first ownership sync.
7. Prefer explicit deterministic ranking features over hidden model decisions.
8. Build for easy debugging: log parsed queries, filter reasons, candidate scores, and final explanations.

## Engineering priorities
### Phase 1
- Steam sign-in
- user profile onboarding
- owned library sync
- relational schema
- game metadata ingestion
- semantic text generation and embedding
- basic recommendation endpoint

### Phase 2
- ranking improvements
- richer explanations
- clarification questions
- better session-length and complexity modeling
- install/owned/unplayed recommendation modes

### Phase 3
- richer device detection
- external catalog expansion beyond Steam
- feedback loop for likes/dislikes
- re-ranking experiments

## Risks and limitations
- Steam library visibility may limit ownership sync for some users
- Requirement text from game stores may be noisy and inconsistently formatted
- Steam Deck and controller metadata may not fully capture real-world play experience
- Semantic similarity can overfit on broad genre language without strong ranking controls
- A content-based system may be less serendipitous than collaborative filtering, but it is more privacy-preserving and easier to justify in an MVP

## Recommended stack
### Minimal stack
- Frontend: Next.js or simple React app
- Backend: FastAPI or Express
- Relational DB: SQLite for MVP
- Vector DB: ChromaDB
- Embeddings: any reliable embedding model available in your stack
- LLM: Qwen or equivalent instruction model for parsing + explanation

### Suggested service boundaries
- `ingestion_service`
- `recommendation_service`
- `llm_service` or shared module
- `steam_integration_service`

## Final product definition
Build a **Steam-first personal game recommender** that:
- knows what the user owns
- knows what hardware/profile constraints the user has declared
- understands natural-language requests
- filters by hard compatibility facts
- retrieves semantically relevant games
- ranks results using only the user's own data and content metadata
- explains recommendations clearly and honestly

## Build checklist
- [ ] Steam auth flow
- [ ] owned-games sync
- [ ] game metadata ingestion
- [ ] canonical SQL schema
- [ ] semantic text construction
- [ ] vector indexing
- [ ] LLM query parser with strict JSON output
- [ ] hard-filter engine
- [ ] ranking layer
- [ ] explanation generator
- [ ] recommendation endpoint
- [ ] query/recommendation logging

## Instructions to future coding agents
Implement the system as a **Steam-first, content-based, retrieval-plus-ranking recommender**.

Do not implement collaborative filtering. Do not assume access to console ecosystem APIs. Do not store hard compatibility facts only in embeddings. Do not let the LLM be the source of truth for ownership or hardware fit.

Prefer simple, debuggable components over agentic orchestration frameworks in v1.
