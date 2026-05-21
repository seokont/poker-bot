"""Estimate villain range strings for equity calculation."""

from __future__ import annotations

from app.decision.action_history import analyze_action_history
from app.decision.pot_odds import call_amount
from app.schemas.bot_job_schema import BotTurnJob
from app.schemas.game_state_schema import Street

_TIGHT_ORDER = [
    "QQ+,AKs,AKo",
    "TT+,AQs+,AKo",
    "99+,AJs+,KQs,AQo+",
    "88+,ATs+,KJs+,QJs,AJo+,KQo",
    "66+,A9s+,KTs+,QTs+,JTs,AJo+,KQo",
    "22+,A5s+,K9s+,Q9s+,J9s+,T9s,98s,A9o+,KTo+,QJo",
]


def estimate_villain_range(job: BotTurnJob) -> str:
    from app.config import get_settings

    settings = get_settings()
    heuristic = _heuristic_range(job)
    if not settings.bot_use_action_history:
        return heuristic

    insight = analyze_action_history(job)
    if insight.range_spec:
        return _merge_ranges(insight.range_spec, heuristic, insight.aggression_score)
    return heuristic


def _merge_ranges(history_spec: str, heuristic_spec: str, aggression: float) -> str:
    if aggression >= 0.55:
        return _tighter_of(history_spec, heuristic_spec)
    if aggression <= 0.2:
        return _wider_of(history_spec, heuristic_spec)
    return history_spec


def _tighter_of(first: str, second: str) -> str:
    first_rank = _tightness_rank(first)
    second_rank = _tightness_rank(second)
    return first if first_rank <= second_rank else second


def _wider_of(first: str, second: str) -> str:
    first_rank = _tightness_rank(first)
    second_rank = _tightness_rank(second)
    return first if first_rank >= second_rank else second


def _tightness_rank(spec: str) -> int:
    try:
        return _TIGHT_ORDER.index(spec)
    except ValueError:
        return len(_TIGHT_ORDER)


def _heuristic_range(job: BotTurnJob) -> str:
    call_cost = call_amount(job.current_bet, job.bot_current_bet, job.bot_stack)
    pressure = call_cost / max(1, job.pot_size)
    multiway = job.active_players_count >= 3

    if job.street == Street.PREFLOP:
        return _preflop_villain_range(job, pressure, multiway)
    return _postflop_villain_range(job, pressure, multiway)


def _preflop_villain_range(job: BotTurnJob, pressure: float, multiway: bool) -> str:
    if job.current_bet <= job.big_blind:
        return "22+,A9s+,KTs+,QTs+,JTs,AJo+,KQo" if not multiway else "88+,AJs+,KQs,AQo+"
    if pressure >= 0.75:
        return "QQ+,AKs,AKo"
    if pressure >= 0.45:
        return "TT+,AQs+,AKo" if multiway else "99+,AJs+,KQs,AQo+"
    return "88+,ATs+,KJs+,QJs,AJo+,KQo" if multiway else "66+,A9s+,KTs+,QTs+,JTs,AJo+,KQo"


def _postflop_villain_range(job: BotTurnJob, pressure: float, multiway: bool) -> str:
    if pressure <= 0.01:
        return "22+,A5s+,K9s+,Q9s+,J9s+,T9s,98s,A9o+,KTo+,QJo" if not multiway else "88+,AJs+,KQs,QJs,AJo+"
    if pressure >= 0.85:
        return "QQ+,AKs,AKo"
    if pressure >= 0.55:
        return "TT+,AQs+,AKo" if multiway else "99+,AJs+,KQs,AQo+"
    if pressure >= 0.30:
        return "88+,ATs+,KJs+,QJs,AJo+,KQo"
    return "66+,A9s+,KTs+,QTs+,JTs,AJo+,KQo" if not multiway else "77+,AJs+,KQs,QJs,AJo+"
