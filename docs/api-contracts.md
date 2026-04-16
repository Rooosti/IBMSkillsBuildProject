# API Contracts

## Recommendation query

### Request
`POST /recommendations/query`

```json
{
  "userId": "123",
  "query": "something like Hades but more relaxed",
  "mode": "discovery"
}
```

### Response

```json
{
  "parsed_query": {
    "intent": "find_game"
  },
  "results": [
    {
      "game_id": "g1",
      "title": "Game Title",
      "score": 0.82,
      "reasons": [
        "matches your request",
        "fits your hardware",
        "aligns with your preferences"
      ]
    }
  ]
}
```

## Steam auth

### Planned routes
- `GET /auth/steam`
- `GET /auth/steam/callback`

## User profile

### Planned routes
- `PUT /users/{id}/device-profile`
- `PUT /users/{id}/preferences`

## Library sync

### Planned route
- `POST /users/{id}/sync-library`
