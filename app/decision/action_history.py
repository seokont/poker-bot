"""Infer villain line strength from previousActions in the bot job."""

from __future__ import annotations

from dataclasses import dataclass

from app.schemas.bot_action_schema import BotAction
from app.schemas.bot_job_schema import BotTurnJob
from app.schemas.game_state_schema import Street

_AGGRESSIVE_ACTIONS = {BotAction.RAISE, BotAction.BET, BotAction.ALL_IN}
_PASSIVE_ACTIONS = {BotAction.CALL, BotAction.CHECK}


@dataclass(frozen=True)
class ActionHistoryInsight:
    villain_raises: int
    villain_bets: int
    limp_count: int
    aggression_score: float
    range_spec: str | None
    source: str


def analyze_action_history(job: BotTurnJob) -> ActionHistoryInsight:
    villain_raises = 0
    villain_bets = 0
    limp_count = 0

    for action in job.previous_actions:
        if action.player_id == job.bot_id:
            continue
        if action.action in _AGGRESSIVE_ACTIONS:
            if action.action == BotAction.RAISE:
                villain_raises += 1
            else:
                villain_bets += 1
        elif action.action == BotAction.CALL and (action.amount or 0) <= job.big_blind:
            limp_count += 1

    aggression = min(1.0, villain_raises * 0.35 + villain_bets * 0.25)
    range_spec = _range_from_aggression(job, villain_raises, villain_bets, limp_count)
    source = "action_history" if range_spec else "none"

    return ActionHistoryInsight(
        villain_raises=villain_raises,
        villain_bets=villain_bets,
        limp_count=limp_count,
        aggression_score=aggression,
        range_spec=range_spec,
        source=source,
    )


def _range_from_aggression(
    job: BotTurnJob,
    villain_raises: int,
    villain_bets: int,
    limp_count: int,
) -> str | None:
    if not job.previous_actions:
        return None

    multiway = job.active_players_count >= 3

    if villain_raises >= 2:
        return "QQ+,AKs,AKo" if job.street == Street.PREFLOP else "TT+,AQs+,AKo"

    if villain_raises == 1 and villain_bets == 0:
        if job.street == Street.PREFLOP:
            call_bb = max(0, job.current_bet - job.bot_current_bet) / max(1, job.big_blind)
            if call_bb >= 8:
                return "QQ+,AKs,AKo"
            if call_bb >= 4:
                return "TT+,AQs+,AKo" if multiway else "99+,AJs+,KQs,AQo+"
            return "88+,ATs+,KJs+,QJs,AJo+,KQo" if multiway else "66+,A9s+,KTs+,QTs+,JTs,AJo+,KQo"
        if job.street == Street.RIVER:
            return "88+,AJs+,KQs,AQo+"
        return "99+,AJs+,KQs,AQo+" if multiway else "88+,ATs+,KJs+,QJs,AJo+,KQo"

    if villain_bets >= 1 and villain_raises == 0:
        if job.street == Street.PREFLOP:
            return "77+,AJs+,KQs,QJs,AJo+"
        return "66+,A9s+,KTs+,QTs+,JTs,AJo+,KQo" if not multiway else "77+,AJs+,KQs,QJs,AJo+"

    if limp_count >= 2 and villain_raises == 0:
        return "22+,A5s+,K9s+,Q9s+,J9s+,T9s,98s,A9o+,KTo+,QJo" if not multiway else "55+,A9s+,KTs+,QTs+,JTs,AJo+,KQo"

    if len(job.previous_actions) >= 2:
        return "66+,A9s+,KTs+,QTs+,JTs,AJo+,KQo"

    return None
