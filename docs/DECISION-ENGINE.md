# Decision engine (bot-server)

**Требования к game backend (job, API, env):** [GAME-BACKEND-REQUIREMENTS.md](./GAME-BACKEND-REQUIREMENTS.md)

## Modules

| Module | Role |
|--------|------|
| `hand_evaluator` + `pokerkit_adapter` | Made-hand strength (PokerKit 0.7.3) |
| `preflop_charts` | NLH chart lookup (open, IP/OOP defend, BB vs steal, 3-bet) |
| `omaha_preflop_charts` | PLO 4–7: 2-card combo hits vs chart ranges |
| `action_history` | Villain line from `previousActions` |
| `range_estimator` | Villain range string for MC equity |
| `equity_calculator` | `calculate_equities` (PokerKit) |
| `preflop_decision` / `postflop_decision` | Action selection |

## Env

```env
BOT_EQUITY_ENABLED=true
BOT_EQUITY_SAMPLE_COUNT=300
BOT_USE_ACTION_HISTORY=true
```

## Backend: `previousActions`

Send street actions so bot can tighten villain range:

```json
"previousActions": [
  {"playerId": "villain-1", "action": "RAISE", "amount": 60},
  {"playerId": "villain-1", "action": "BET", "amount": 90}
]
```

## Chart data

- `app/decision/data/nlh_preflop_charts.json`
- `app/decision/data/omaha_preflop_charts.json`

Edit range strings (PokerKit `parse_range` syntax).
