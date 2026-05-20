# Money Poker Bot Server Specification

## Purpose

The bot-server is a separate Python service for a money poker platform. It receives bot turn jobs from the main Game Engine, calculates a realistic bot action using only visible game information, waits a human-like delay, and sends the proposed action back to the Game Engine for validation.

Bots must always be clearly marked as `BOT`. Hidden bots pretending to be humans are prohibited.

## Authority Boundaries

The main Backend / Game Engine is the only authority for:

- poker rules
- action validation
- table state
- hand state
- pot logic
- cards and deck
- showdown
- payouts

The Python bot-server may only:

- receive bot turn jobs
- load bot profiles
- read visible game state supplied in the job
- calculate a proposed action
- send that proposed action to the Game Engine
- cache bot state and log actions

The bot-server must never:

- know opponent hidden cards
- generate cards
- decide winners
- directly modify pot, stacks, cards, winners, table state, or hand state
- access private user data
- change wallets

## Stack

- Python
- FastAPI
- Celery
- Redis
- PostgreSQL
- SQLAlchemy
- Pydantic
- Docker

## Bot Job Input

```json
{
  "botId": "bot-1",
  "tableId": "table-1",
  "handId": "hand-1",
  "turnId": "turn-1",
  "street": "PREFLOP",
  "gameType": "NLH",
  "botHoleCards": ["As", "Kd"],
  "boardCards": [],
  "potSize": 150,
  "currentBet": 50,
  "botStack": 1000,
  "botCurrentBet": 0,
  "position": "BTN",
  "activePlayersCount": 6,
  "legalActions": ["FOLD", "CALL", "RAISE"],
  "minRaise": 100,
  "maxRaise": 1000
}
```

## Allowed Bot Output

```json
{
  "action": "FOLD",
  "amount": null,
  "reason": "Weak hand facing a bet"
}
```

Allowed actions are `FOLD`, `CHECK`, `CALL`, `BET`, `RAISE`, and `ALL_IN`.

## Human-Like Delay

- Simple decision: 800-1500 ms
- Normal decision: 2000-4000 ms
- Hard decision: 5000-8000 ms

## Duplicate Action Protection

Before sending a bot action, the worker creates a Redis lock:

```text
lock:bot:{botId}:hand:{handId}:turn:{turnId}
```

If the lock already exists, the worker stops and does not send a duplicate action.

## API

- `GET /health`
- `POST /bots/action`
- `GET /bots/{botId}/state`
- `POST /bots/{botId}/enable`
- `POST /bots/{botId}/disable`

## Game Engine Integration

The bot-server sends proposed actions to:

```text
POST {MAIN_BACKEND_URL}/internal/bot-action
```

Payload:

```json
{
  "botId": "bot-1",
  "tableId": "table-1",
  "handId": "hand-1",
  "action": "CALL",
  "amount": 50
}
```

The request uses an internal service token. The Game Engine must validate bot actions exactly like human actions.

## Acceptance Criteria

1. Bot-server runs as a separate Docker service.
2. Bot actions are processed asynchronously.
3. Redis queue works.
4. Bot has realistic delay.
5. Bot cannot act twice in one turn.
6. Bot only sends proposed action.
7. Game Engine validates every bot action.
8. Bot does not know hidden cards.
9. Bot profiles produce different behavior.
10. Bot is clearly marked as `BOT`.
