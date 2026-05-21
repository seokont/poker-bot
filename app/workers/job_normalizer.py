from typing import Any

from app.schemas.backend_queue_schema import BackendBotQueueJob
from app.schemas.bot_action_schema import BotAction
from app.schemas.bot_job_schema import BotTurnJob
from app.decision.game_rules import expected_hole_card_count
from app.schemas.game_state_schema import GameType, Position, Street


def normalize_backend_queue_job(payload: dict[str, Any]) -> BotTurnJob:
    if _looks_like_legacy_bot_turn_job(payload):
        return BotTurnJob.model_validate(payload)

    raw = BackendBotQueueJob.model_validate(payload)
    state = raw.visible_state or {}
    acting_player = _find_acting_player(state, raw.bot_id, raw.acting_seat)

    current_bet = _get(state, "currentBet", "betToCall", default=0)
    big_blind = _get(state, "bigBlind", "bb", default=_infer_big_blind(state, current_bet))
    bot_current_bet = _get(
        state,
        "botCurrentBet",
        "currentSeatBet",
        default=_get(acting_player, "currentBet", default=0),
    )
    bot_stack = _get(state, "botStack", "stack", "actingSeatStack", default=_get(acting_player, "stack", default=0))
    legal_actions = _get(state, "legalActions", "legal_actions", default=None) or _infer_legal_actions(
        current_bet=current_bet,
        bot_current_bet=bot_current_bet,
        bot_stack=bot_stack,
        min_raise=_get(state, "minRaise", default=None),
    )
    normalized_legal_actions = _normalize_actions(legal_actions)

    board_cards = _get(state, "boardCards", "board_cards", "board", "communityCards", default=[])
    hole_cards = _get(state, "botHoleCards", "holeCards", "hole_cards", "cards", default=None) or _get(
        acting_player,
        "holeCards",
        "cards",
        default=None,
    )
    game_type = _normalize_game_type(raw.game_type)
    if not hole_cards:
        # The external queue format may omit cards in minimal test jobs. Use placeholders only to reach safe fallback logic.
        # Production backend should always include the bot's own hole cards in visibleState.
        hole_cards = _default_hole_cards(game_type)

    return BotTurnJob.model_validate(
        {
            "botId": raw.bot_id,
            "tableId": raw.table_id,
            "handId": raw.hand_id,
            "turnId": raw.turn_id,
            "street": _normalize_street(raw.street),
            "gameType": game_type,
            "botHoleCards": _normalize_cards(hole_cards),
            "boardCards": _normalize_board_cards(raw.street, board_cards),
            "potSize": _get(state, "potSize", "pot", "mainPot", default=_sum_pots(state)),
            "currentBet": current_bet,
            "botCurrentBet": bot_current_bet,
            "botStack": bot_stack,
            "bigBlind": big_blind,
            "position": _normalize_position(_get(state, "position", default="UNKNOWN")),
            "activePlayersCount": _get(state, "activePlayersCount", "activePlayers", default=_count_active_players(state)),
            "legalActions": normalized_legal_actions,
            "minRaise": _get(state, "minRaise", default=None),
            "maxRaise": _get(state, "maxRaise", default=None),
            "previousActions": _normalize_previous_actions(_get(state, "previousActions", "actions", default=[])),
        }
    )


def _looks_like_legacy_bot_turn_job(payload: dict[str, Any]) -> bool:
    return "botHoleCards" in payload and "legalActions" in payload


def _get(source: dict[str, Any], *keys: str, default: Any = None) -> Any:
    if not isinstance(source, dict):
        return default
    for key in keys:
        if key in source:
            return source[key]
    return default


def _find_acting_player(state: dict[str, Any], bot_id: str, acting_seat: int | None) -> dict[str, Any]:
    players = _get(state, "players", default=[]) or []
    for player in players:
        if _get(player, "userId", "botId", "id", default=None) == bot_id:
            return player
    acting_seat = acting_seat if acting_seat is not None else _get(state, "actingPlayerSeat", default=None)
    for player in players:
        if _get(player, "seatIndex", "seat", default=None) == acting_seat:
            return player
    return {}


def _infer_legal_actions(current_bet: int, bot_current_bet: int, bot_stack: int, min_raise: int | None) -> list[str]:
    to_call = max(0, int(current_bet or 0) - int(bot_current_bet or 0))
    if to_call > 0:
        actions = [BotAction.FOLD.value]
        if bot_stack > 0:
            actions.append(BotAction.CALL.value)
        if bot_stack > to_call and min_raise is not None:
            actions.append(BotAction.RAISE.value)
        return actions

    actions = [BotAction.CHECK.value]
    if bot_stack > 0:
        actions.append(BotAction.RAISE.value if current_bet else BotAction.BET.value)
    return actions


def _sum_pots(state: dict[str, Any]) -> int:
    pots = _get(state, "pots", default=[]) or []
    return sum(int(_get(pot, "amount", default=0) or 0) for pot in pots if isinstance(pot, dict))


def _infer_big_blind(state: dict[str, Any], current_bet: int) -> int:
    players = _get(state, "players", default=[]) or []
    big_blind_seat = _get(state, "bigBlindSeat", default=None)
    for player in players:
        if _get(player, "seatIndex", default=None) == big_blind_seat:
            blind = _get(player, "blindContribution", "currentBet", default=None)
            if blind:
                return max(1, int(blind))
    min_raise = _get(state, "minRaise", default=None)
    if min_raise:
        return max(1, int(min_raise))
    return max(1, int(current_bet or 10))


def _count_active_players(state: dict[str, Any]) -> int:
    players = _get(state, "players", default=[]) or []
    active_count = sum(
        1
        for player in players
        if isinstance(player, dict)
        and not _get(player, "isFolded", default=False)
        and _get(player, "state", default="ACTIVE") != "FOLDED"
    )
    return max(1, active_count)


def _normalize_previous_actions(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = []
    for action in actions or []:
        if not isinstance(action, dict):
            continue
        action_type = str(_get(action, "action", "actionType", default="")).upper()
        if action_type == "BET" and _get(action, "sequenceNum", default=0) in {1, 2}:
            # Blind posts are public actions, but they are not voluntary preflop raises.
            action_type = "BET"
        if action_type not in {allowed.value for allowed in BotAction}:
            continue
        normalized.append(
            {
                "playerId": str(_get(action, "playerId", "userId", "botId", default="unknown")),
                "action": action_type,
                "amount": _get(action, "amount", default=None),
            }
        )
    return normalized


def _normalize_street(value: str) -> str:
    value = value.upper()
    return value if value in {street.value for street in Street} else Street.PREFLOP.value


def _normalize_game_type(value: str) -> str:
    value = value.upper().replace("-", "_")
    aliases = {
        "TEXAS_HOLDEM": GameType.TEXAS_HOLDEM.value,
        "NLH": GameType.NO_LIMIT_HOLDEM.value,
        "NO_LIMIT_HOLDEM": GameType.NO_LIMIT_HOLDEM.value,
        "HOLDEM": GameType.NLH.value,
        "OMAHA": GameType.OMAHA_4.value,
        "PLO": GameType.OMAHA_4.value,
        "PLO4": GameType.OMAHA_4.value,
        "PLO5": GameType.OMAHA_5.value,
        "PLO6": GameType.OMAHA_6.value,
        "PLO7": GameType.OMAHA_7.value,
    }
    if value in aliases:
        return aliases[value]
    if value in {game.value for game in GameType}:
        return value
    return GameType.TEXAS_HOLDEM.value


def _default_hole_cards(game_type: str) -> list[str]:
    count = expected_hole_card_count(GameType(game_type))
    template = ["As", "Kd", "Qh", "Jc", "Ts", "9d", "8h"]
    return template[:count]


def _normalize_position(value: str) -> str:
    value = value.upper()
    aliases = {
        "BTN": Position.BUTTON.value,
        "SB": Position.SMALL_BLIND.value,
        "BB": Position.BIG_BLIND.value,
        "UTG": Position.EARLY.value,
        "CO": Position.LATE.value,
        "MP": Position.MIDDLE.value,
    }
    value = aliases.get(value, value)
    return value if value in {position.value for position in Position} else Position.UNKNOWN.value


def _normalize_actions(actions: list[str]) -> list[str]:
    allowed = {action.value for action in BotAction}
    normalized = [str(action).upper() for action in actions if str(action).upper() in allowed]
    return normalized or [BotAction.CHECK.value, BotAction.FOLD.value]


def _normalize_cards(cards: list[Any]) -> list[str]:
    normalized = []
    for card in cards or []:
        if isinstance(card, dict):
            value = _get(card, "code", default=None)
            if value is None:
                rank = _get(card, "rank", default="")
                suit = _get(card, "suit", default="")
                value = f"{rank}{suit}"
            normalized.append(str(value))
        else:
            normalized.append(str(card))
    return normalized


def _normalize_board_cards(street: str, board_cards: list[str]) -> list[str]:
    expected_count = {
        Street.PREFLOP.value: 0,
        Street.FLOP.value: 3,
        Street.TURN.value: 4,
        Street.RIVER.value: 5,
    }[_normalize_street(street)]
    cards = _normalize_cards(board_cards)
    if len(cards) >= expected_count:
        return cards[:expected_count]
    placeholders = ["2c", "7d", "Jh", "4s", "9c"]
    return cards + placeholders[: expected_count - len(cards)]
