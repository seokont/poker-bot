"""NLH preflop charts (range strings) validated via PokerKit parse_range."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from pokerkit.analysis import parse_range

from app.decision.hand_notation import combo_label, hole_cards_to_combo
from app.decision.pot_odds import call_amount
from app.schemas.bot_job_schema import BotTurnJob
from app.schemas.game_state_schema import Position

_CHARTS_PATH = Path(__file__).resolve().parent / "data" / "nlh_preflop_charts.json"


@dataclass(frozen=True)
class PreflopChartAdvice:
    action: str
    chart_key: str
    combo: str
    reason: str


def lookup_preflop_chart(job: BotTurnJob) -> PreflopChartAdvice:
    charts = _load_charts()
    combo = combo_label(job.bot_hole_cards)
    hero = hole_cards_to_combo(job.bot_hole_cards)
    position_key = _position_bucket(job.position)
    call_cost = call_amount(job.current_bet, job.bot_current_bet, job.bot_stack)
    facing_raise = job.current_bet > job.big_blind
    in_position = _is_in_position(job)
    call_bb = call_cost / max(1, job.big_blind)

    if not facing_raise:
        return _advice(
            hero,
            combo,
            _chart_spec(charts, "open", position_key, "LATE"),
            "OPEN",
            f"open.{position_key}",
            f"Preflop chart open ({position_key})",
        )

    if _is_bb_vs_steal(job, call_bb):
        steal_key = "vs_BUTTON" if job.active_players_count <= 2 else "vs_SMALL_BLIND"
        spec = _chart_spec(charts, "bb_defend_vs_steal", steal_key, "DEFAULT")
        return _advice(
            hero,
            combo,
            spec,
            "CALL",
            f"bb_defend_vs_steal.{steal_key}",
            "Preflop chart BB defend vs steal",
        )

    if call_bb >= 8:
        spec = _chart_spec(charts, "four_bet_call", "IP" if in_position else "DEFAULT", "DEFAULT")
        return _advice(hero, combo, spec, "CALL", "four_bet_call", "Preflop chart vs 4-bet+")

    if call_bb >= 5:
        key = "IP" if in_position else "OOP"
        spec = _chart_spec(charts, "facing_large_raise", key, "DEFAULT")
        return _advice(hero, combo, spec, "CALL", f"facing_large_raise.{key}", "Preflop chart vs large raise")

    if call_cost >= job.big_blind * 8 and job.active_players_count <= 3:
        key = "IP" if in_position else "OOP"
        if in_position:
            spec = _chart_spec(charts, "three_bet_ip", position_key, "DEFAULT")
        else:
            spec = _chart_spec(charts, "three_bet_oop", position_key, "DEFAULT")
        if hero in parse_range(spec):
            return PreflopChartAdvice(
                action="THREE_BET",
                chart_key=f"three_bet_{key.lower()}",
                combo=combo,
                reason=f"Preflop chart 3-bet ({key}): {combo} in {spec}",
            )

    if in_position:
        spec = _chart_spec(charts, "facing_raise_ip", position_key, "DEFAULT")
        return _advice(hero, combo, spec, "CALL", f"facing_raise_ip.{position_key}", "Preflop chart IP defend")

    spec = _chart_spec(charts, "facing_raise_oop", position_key, "DEFAULT")
    if hero not in parse_range(spec):
        spec = _chart_spec(charts, "facing_raise", position_key, "LATE")
    return _advice(hero, combo, spec, "CALL", f"facing_raise_oop.{position_key}", "Preflop chart OOP defend")


def _advice(hero, combo: str, spec: str, action_if_in: str, chart_key: str, label: str) -> PreflopChartAdvice:
    in_range = hero in parse_range(spec)
    action = action_if_in if in_range else "FOLD"
    return PreflopChartAdvice(
        action=action,
        chart_key=chart_key,
        combo=combo,
        reason=f"{label}: {combo} {'in' if in_range else 'outside'} range",
    )


def _chart_spec(charts: dict, section: str, key: str, fallback: str) -> str:
    block = charts.get(section, {})
    return block.get(key) or block.get(fallback) or block.get("DEFAULT", "QQ+,AKs,AKo")


def _is_in_position(job: BotTurnJob) -> bool:
    if job.position in {Position.BUTTON, Position.BTN, Position.LATE, Position.CO}:
        return True
    if job.position in {Position.BIG_BLIND, Position.BB}:
        return job.current_bet > job.big_blind
    return False


def _is_bb_vs_steal(job: BotTurnJob, call_bb: float) -> bool:
    if job.position not in {Position.BIG_BLIND, Position.BB}:
        return False
    if job.current_bet <= job.big_blind:
        return False
    return call_bb <= 3.5 and job.active_players_count <= 3


def _position_bucket(position: Position) -> str:
    if position in {Position.EARLY, Position.UTG}:
        return "UTG"
    if position in {Position.MIDDLE, Position.MP}:
        return "MIDDLE"
    if position in {Position.LATE, Position.CO}:
        return "LATE"
    if position in {Position.BUTTON, Position.BTN}:
        return "BUTTON"
    if position in {Position.SMALL_BLIND, Position.SB}:
        return "SMALL_BLIND"
    if position in {Position.BIG_BLIND, Position.BB}:
        return "BIG_BLIND"
    return "LATE"


@lru_cache
def _load_charts() -> dict:
    with _CHARTS_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)
