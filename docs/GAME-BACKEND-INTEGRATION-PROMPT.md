# Промпт для Game Backend: интеграция с Bot Server

Скопируй этот документ целиком в задачу / Cursor / чат для репозитория **game backend** (`/opt/poker`, NestJS).

---

## Роль и границы

Ты дорабатываешь **Game Backend (Game Engine)** для интеграции с отдельным сервисом **poker-bot-server** (`https://bot.playesop.net`).

**Game Backend — единственный источник истины:**
- правила покера, колода, банк, стеки, валидация ходов, showdown, выплаты;
- рассылка состояния стола клиентам (WebSocket/REST).

**Bot-server только:**
- получает job с **видимым** состоянием для бота;
- считает предложенное действие (Hold'em + Omaha 4/5/6/7);
- отправляет его обратно на internal API;
- **не** меняет стол напрямую и **не** видит карты оппонентов.

**Браузер никогда не вызывает bot-server** в money-игре. Только backend → bot-server.

---

## Архитектура

```text
Browser  ←── WebSocket/REST ──→  Game Backend  ←── HTTP internal ──→  Bot Server
                                      │
                                      └── POST https://bot.playesop.net/bots/action
                                      └── POST …/internal/bot-action  ← ответ бота
```

**Dashboard** (опционально): админ открывает `https://bot.playesop.net/dashboard` → bot-server вызывает `POST /internal/bot-join` на game backend. Игроки в браузере этого не видят.

---

## 1. Переменные окружения (обязательно в процессе API)

Добавь в `docker-compose` сервиса **backend** (не только в `.env` на диске):

```env
INTERNAL_BOT_SERVICE_ENABLED=true
INTERNAL_BOT_SERVICE_TOKEN=<длинный-секрет-совпадает-с-bot-server>
INTERNAL_BOT_SERVICE_TOKEN_EXPIRES_AT=2030-01-01T00:00:00.000Z
BOT_SERVER_URL=https://bot.playesop.net
BOT_SERVER_SERVICE_TOKEN=<тот же секрет, что SERVICE_TOKEN на bot-server>
```

**Критично:** после `docker compose up` команда  
`docker compose exec backend printenv | grep INTERNAL_BOT`  
должна показывать `ENABLED=true` и `TOKEN=…`.  
Если пусто — Nest не видит env → ошибка `Internal bot service token is disabled`.

На bot-server (отдельный сервер):

```env
MAIN_BACKEND_URL=https://playesop.net/api
SERVICE_TOKEN=<тот же INTERNAL_BOT_SERVICE_TOKEN>
```

---

## 2. Internal API (реализовать / проверить)

Все эндпоинты под префиксом `{API}/internal/…`, защита:

```http
Authorization: Bearer <INTERNAL_BOT_SERVICE_TOKEN>
Content-Type: application/json
```

### 2.1 `POST /internal/bot-join`

**Вызывает:** bot-server (по запросу с dashboard), не браузер.

**Request:**

```json
{
  "botId": "cmojrjsch3o4oczpopsmbco3g",
  "tableId": "cmp6vzbxq0001hgegs3ohkze3",
  "isBot": true,
  "preferredSeat": 3
}
```

`preferredSeat` — опционально.

**Response (успех):**

```json
{
  "ok": true,
  "botId": "…",
  "tableId": "…",
  "seatIndex": 3
}
```

**Response (ошибка):**

```json
{
  "ok": false,
  "errorCode": "INVALID_BOT_SERVICE_TOKEN",
  "message": "…"
}
```

HTTP status может быть 4xx, но тело должно содержать `ok: false` (bot-server это парсит).

---

### 2.2 `POST /internal/bot-leave`

**Request:**

```json
{
  "botId": "…",
  "tableId": "…",
  "isBot": true
}
```

**Response:** `{ "ok": true }` или `{ "ok": false, "errorCode": "…", "message": "…" }`.

---

### 2.3 `POST /internal/bot-action`

**Вызывает:** bot-server после расчёта хода.

**Request:**

```json
{
  "botId": "…",
  "tableId": "…",
  "handId": "…",
  "turnId": "…",
  "action": "CALL",
  "amount": 50
}
```

`amount` — обязателен для `CALL`, `BET`, `RAISE`, `ALL_IN`; для `FOLD` / `CHECK` — `null` или omit.

Допустимые `action`: `FOLD`, `CHECK`, `CALL`, `BET`, `RAISE`, `ALL_IN`.

**Поведение:**
- валидировать ход **так же**, как ход человека;
- при успехе обновить стол и разослать snapshot всем клиентам;
- при ошибке: `{ "ok": false, "errorCode": "…", "message": "…" }`.

**Response (успех):**

```json
{
  "ok": true
}
```

---

### 2.4 `POST /internal/bot-action/validate-turn` (опционально)

**Request:**

```json
{
  "botId": "…",
  "tableId": "…",
  "handId": "…",
  "turnId": "…",
  "legalActions": ["FOLD", "CALL", "RAISE"]
}
```

**Response:**

```json
{
  "valid": true
}
```

Если эндпоинта нет (404) — bot-server всё равно отправит финальный ход на `/internal/bot-action`.

---

## 3. Вызов bot-server на каждом ходе бота (главное)

Когда `currentActor` — игрок с `isBot === true`, **сервер game backend** (не фронтенд) должен:

```http
POST https://bot.playesop.net/bots/action
Authorization: Bearer <BOT_SERVER_SERVICE_TOKEN>
Content-Type: application/json
```

Ожидаемый ответ: **HTTP 202**

```json
{
  "queued": true,
  "jobId": "uuid",
  "botId": "…",
  "tableId": "…",
  "handId": "…",
  "turnId": "…",
  "isBot": true
}
```

Через 2–12 секунд bot-server вызовет `POST /internal/bot-action` с решением.

**Не дублируй** один и тот же `turnId` десятками запросов без нужды — bot-server защищается lock'ом, но лишние job = задержки.

**Таймаут:** вызывай bot-server асинхронно (очередь / fire-and-forget), не блокируй игровой поток надолго.

---

## 4. Формат job для `POST /bots/action`

Поддерживаются **два** формата.

### Формат A — плоский (предпочтительный)

Все поля в корне JSON → напрямую `BotTurnJob`:

```json
{
  "botId": "bot-user-id",
  "tableId": "table-id",
  "handId": "hand-id",
  "turnId": "unique-turn-id",
  "street": "FLOP",
  "gameType": "OMAHA_5",
  "botHoleCards": ["As", "Kd", "Qh", "Jc", "Ts"],
  "boardCards": ["2d", "3c", "4h"],
  "potSize": 500,
  "currentBet": 50,
  "botStack": 2000,
  "botCurrentBet": 0,
  "bigBlind": 10,
  "position": "BTN",
  "activePlayersCount": 4,
  "legalActions": ["FOLD", "CALL", "RAISE"],
  "minRaise": 20,
  "maxRaise": 2000,
  "previousActions": []
}
```

### Формат B — очередь с `visibleState`

```json
{
  "jobId": "optional",
  "turnId": "…",
  "botId": "…",
  "tableId": "…",
  "handId": "…",
  "street": "TURN",
  "gameType": "NLH",
  "actingSeat": 2,
  "visibleState": {
    "botHoleCards": ["As", "Kd"],
    "boardCards": ["2d", "3c", "4h", "9s"],
    "potSize": 500,
    "currentBet": 50,
    "botStack": 2000,
    "botCurrentBet": 0,
    "bigBlind": 10,
    "legalActions": ["CHECK", "BET"],
    "minRaise": 20,
    "maxRaise": 2000,
    "activePlayersCount": 3,
    "position": "CO",
    "players": [
      {
        "id": "bot-user-id",
        "seatIndex": 2,
        "stack": 2000,
        "currentBet": 0,
        "holeCards": ["As", "Kd"],
        "isBot": true
      }
    ]
  }
}
```

Bot-server нормализует алиасы: `holeCards`, `board`, `communityCards`, `betToCall`, `stack`, `bb`, и т.д.

---

## 5. `gameType` и количество карт

| `gameType` | Карт в `botHoleCards` | Правило комбинации (на стороне engine) |
|------------|----------------------|----------------------------------------|
| `NLH`, `NO_LIMIT_HOLDEM`, `TEXAS_HOLDEM` | **2** | лучшие 5 из 7 |
| `OMAHA_4` | **4** | ровно 2 hole + 3 board |
| `OMAHA_5` | **5** | ровно 2 hole + 3 board |
| `OMAHA_6` | **6** | ровно 2 hole + 3 board |
| `OMAHA_7` | **7** | ровно 2 hole + 3 board |

Алиасы при нормализации: `PLO`, `PLO4` → `OMAHA_4`, `PLO5` → `OMAHA_5`, и т.д.

**Ошибка bot-server 422**, если:
- `gameType` не из таблицы;
- число hole-карт не совпадает с типом стола;
- `boardCards` не 0 / 3 / 4 / 5 для `PREFLOP` / `FLOP` / `TURN` / `RIVER`.

**Тип стола в БД** должен совпадать с `gameType` в job. Не шли `NLH` + 5 карт на Omaha-столе.

---

## 6. Карты

Формат: **2 символа** — ранг + масть.

- Ранг: `2–9`, `T`, `J`, `Q`, `K`, `A`
- Масть: `h`, `d`, `c`, `s`

Примеры: `"As"`, `"Td"`, `"9h"`.

**Обязательно** передавай **только карты бота** в `botHoleCards`, никогда карты оппонентов.

---

## 7. Поля `visibleState` / job (чеклист)

| Поле | Обязательно | Описание |
|------|-------------|----------|
| `botId` | да | ID пользователя-бота |
| `tableId` | да | ID стола |
| `handId` | да | ID раздачи |
| `turnId` | да | Уникальный ID хода (для идемпотентности) |
| `street` | да | `PREFLOP`, `FLOP`, `TURN`, `RIVER` |
| `gameType` | да | см. таблицу выше |
| `botHoleCards` | да | 2 / 4 / 5 / 6 / 7 карт |
| `boardCards` | да | `[]` или 3/4/5 карт |
| `potSize` | да | размер банка (int, ≥ 0) |
| `currentBet` | да | текущая ставка для колла (int) |
| `botStack` | да | стек бота |
| `botCurrentBet` | да | ставка бота в текущем раунде торгов |
| `legalActions` | да | массив из `FOLD`, `CHECK`, `CALL`, `BET`, `RAISE`, `ALL_IN` |
| `activePlayersCount` | да | число активных игроков ≥ 1 |
| `bigBlind` | рекомендуется | для sizing preflop |
| `minRaise` | если есть RAISE/BET | мин. рейз |
| `maxRaise` | опционально | кэп рейза |
| `position` | рекомендуется | `BTN`, `CO`, `SB`, `BB`, `UTG`, … |
| `previousActions` | опционально | история улицы |

---

## 8. Модель игрока за столом

В snapshot для UI и логики:

```json
{
  "id": "user-id",
  "displayName": "BOT Alpha",
  "isBot": true,
  "seatIndex": 2,
  "stack": 2000
}
```

- `isBot: true` — всегда для ботов;
- displayName желательно с префиксом `BOT `.

---

## 9. Поток жизненного цикла бота

1. Админ: dashboard → `POST /bots/{botId}/join` на bot-server → `POST /internal/bot-join` на game backend.
2. Backend сажает бота, помечает `isBot`, рассылает стол.
3. Раздача: когда ход бота → `POST /bots/action` с полным job.
4. Bot-server → `POST /internal/bot-action`.
5. Backend валидирует, применяет, рассылает новое состояние.
6. Удаление: dashboard → `POST /bots/{botId}/leave` → `POST /internal/bot-leave`.

---

## 10. Ошибки и диагностика

| Симптом | Причина | Fix |
|---------|---------|-----|
| `Internal bot service token is disabled` | `INTERNAL_BOT_*` не в env контейнера | `env_file` + `environment` в compose, `--force-recreate` |
| 502 на Connect to Game | join отклонён backend | починить токен + `bot-join` |
| Бот «замирает» на ходе | backend не вызывает `/bots/action` | добавить вызов при `isBot` turn |
| Бот играет плохо на Omaha | в job `NLH` + 2 карты | передать `OMAHA_5` + 5 карт |
| 422 от bot-server | неверное число карт / street | сверить таблицу §5 |

**Тест join вручную:**

```bash
curl -s -X POST "https://playesop.net/api/internal/bot-join" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"botId":"test","tableId":"<real-table-id>","isBot":true}'
```

Ожидается `"ok": true`.

**Тест action job:**

```bash
curl -s -X POST "https://bot.playesop.net/bots/action" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d @sample-job.json
```

Ожидается `202` и `"queued": true`.

---

## 11. Что НЕ нужно делать в game backend

- Не считать силу руки / equity для бота — это делает bot-server для **предложения**; showdown считает engine.
- Не открывать `SERVICE_TOKEN` в браузере.
- Не использовать Redis bot-server как общую очередь без HTTP, если bot-server на **другом** сервере (используй `POST /bots/action`).
- Не блокировать стол ожиданием ответа bot-server > 30s — ход придёт асинхронно.

---

## 12. Acceptance criteria (готово, когда)

- [ ] `printenv` в контейнере backend показывает `INTERNAL_BOT_SERVICE_ENABLED=true`
- [ ] `curl bot-join` → `ok: true` для реального `tableId`
- [ ] На ходе бота уходит `POST /bots/action` с корректным `gameType` и hole-картами
- [ ] `POST /internal/bot-action` применяет ход и обновляет стол
- [ ] UI показывает бейдж BOT и «думает…» на `currentActor` бота
- [ ] Hold'em (2 карты) и Omaha 4/5/6/7 (4–7 карт) работают на соответствующих столах
- [ ] Токен на bot-server и game backend **одинаковый**

---

## 13. Ссылка на реализацию bot-server

Репозиторий: `bot-server` (Python FastAPI).

Ключевые файлы для сверки контракта:
- `app/schemas/bot_job_schema.py` — валидация job
- `app/workers/job_normalizer.py` — маппинг `visibleState`
- `app/integrations/game_engine_client.py` — исходящие вызовы на `/internal/*`
- `app/decision/game_rules.py` — `gameType` и число hole-карт
- `deploy/DEPLOY-bot.playesop.net.md` — production URLs

---

*Версия контракта: bot-server с поддержкой Hold'em + Omaha 4/5/6/7, internal bot join/leave/action.*
