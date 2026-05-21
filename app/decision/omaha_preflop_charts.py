"""Omaha (4–7) preflop charts using 2-card combo hits from hole cards."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from itertools import combinations
from pathlib import Path

from pokerkit import Card
from pokerkit.analysis import parse_range

from app.decision.game_rules import game_type_label
from app.decision.hand_notation import hole_summary
from app.decision.pot_odds import call_amount
from app.decision.preflop_charts import PreflopChartAdvice, _is_bb_vs_steal, _is_in_position, _position_bucket
from app.schemas.bot_job_schema import BotTurnJob

_CHARTS_PATH = Path(__file__).resolve().parent / "data" / "omaha_preflop_charts.json"


@dataclass(frozen=True)
class OmahaChartRule:
    min_combo_hits: int
    range: str


def lookup_omaha_preflop_chart(job: BotTurnJob) -> PreflopChartAdvice:
    charts = _load_charts()
    combo = hole_summary(job.bot_hole_cards)
    position_key = _position_bucket(job.position)
    call_cost = call_amount(job.current_bet, job.bot_current_bet, job.bot_stack)
    facing_raise = job.current_bet > job.big_blind
    in_position = _is_in_position(job)
    call_bb = call_cost / max(1, job.big_blind)
    game = game_type_label(job.game_type)

    if not facing_raise:
        rule = _get_rule(charts, "open", position_key, "LATE")
        hits = _count_combo_hits(job.bot_hole_cards, rule.range)
        action = "OPEN" if hits >= rule.min_combo_hits else "FOLD"
        return _make_advice(action, f"open.{position_key}", combo, game, rule, hits)

    if _is_bb_vs_steal(job, call_bb):
        rule = _get_rule(charts, "bb_defend_vs_steal", "DEFAULT", "DEFAULT")
        hits = _count_combo_hits(job.bot_hole_cards, rule.range)
        action = "CALL" if hits >= rule.min_combo_hits else "FOLD"
        return _make_advice(action, "bb_defend_vs_steal", combo, game, rule, hits)

    if call_bb >= 5:
        rule = _get_rule(charts, "facing_large_raise", "DEFAULT", "DEFAULT")
        hits = _count_combo_hits(job.bot_hole_cards, rule.range)
        action = "CALL" if hits >= rule.min_combo_hits else "FOLD"
        return _make_advice(action, "facing_large_raise", combo, game, rule, hits)

    if call_cost >= job.big_blind * 8 and job.active_players_count <= 3:
        rule = _get_rule(charts, "three_bet", "DEFAULT", "DEFAULT")
        hits = _count_combo_hits(job.bot_hole_cards, rule.range)
        if hits >= rule.min_combo_hits:
            return _make_advice("THREE_BET", "three_bet", combo, game, rule, hits)

    key = "IP" if in_position else "OOP"
    rule = _get_rule(charts, "facing_raise", key, "DEFAULT")
    hits = _count_combo_hits(job.bot_hole_cards, rule.range)
    action = "CALL" if hits >= rule.min_combo_hits else "FOLD"
    return _make_advice(action, f"facing_raise_{key.lower()}", combo, game, rule, hits)


def _count_combo_hits(hole_cards: list[str], range_spec: str) -> int:
    parsed = parse_range(range_spec)
    hits = 0
    for pair in combinations(hole_cards, 2):
        combo = frozenset(list(Card.parse("".join(pair))))
        if combo in parsed:
            hits += 1
    return hits


def _get_rule(charts: dict, section: str, key: str, fallback: str) -> OmahaChartRule:
    block = charts.get(section, {})
    raw = block.get(key) or block.get(fallback) or block.get("DEFAULT", {"min_combo_hits": 2, "range": "QQ+,AKs,AKo"})
    return OmahaChartRule(min_combo_hits=int(raw["min_combo_hits"]), range=str(raw["range"]))


def _make_advice(action: str, chart_key: str, combo: str, game: str, rule: OmahaChartRule, hits: int) -> PreflopChartAdvice:
    return PreflopChartAdvice(
        action=action,
        chart_key=chart_key,
        combo=combo,
        reason=(
            f"{game} preflop chart ({chart_key}): {combo} has {hits} combos in "
            f"{rule.range} (need {rule.min_combo_hits})"
        ),
    )


@lru_cache
def _load_charts() -> dict:
    with _CHARTS_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)
