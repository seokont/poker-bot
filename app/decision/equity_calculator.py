"""Monte Carlo equity vs estimated villain range (PokerKit analysis)."""

from __future__ import annotations

import logging

from pokerkit import Card, Deck
from pokerkit.analysis import calculate_equities, parse_range
from pokerkit.hands import OmahaHoldemHand, StandardHighHand

from app.decision.action_history import analyze_action_history
from app.decision.game_rules import expected_hole_card_count, is_omaha
from app.decision.hand_notation import hole_cards_to_combo
from app.decision.pokerkit_adapter import join_cards
from app.decision.range_estimator import estimate_villain_range
from app.schemas.bot_job_schema import BotTurnJob
from app.schemas.game_state_schema import Street

logger = logging.getLogger(__name__)

_BOARD_CARDS_TOTAL = 5


def calculate_hero_equity(job: BotTurnJob) -> tuple[float | None, str | None]:
    from app.config import get_settings

    settings = get_settings()
    if not settings.bot_equity_enabled:
        return None, None
    if job.street == Street.PREFLOP or len(job.board_cards) < 3:
        return None, None

    try:
        hero_range = {hole_cards_to_combo(job.bot_hole_cards)}
        range_source = "heuristic"
        if settings.bot_use_action_history:
            history = analyze_action_history(job)
            if history.range_spec:
                range_source = history.source

        villain_spec = estimate_villain_range(job)
        villain_range = parse_range(villain_spec)
        if not villain_range:
            return None, None

        board = Card.parse(join_cards(job.board_cards))
        hole_count = expected_hole_card_count(job.game_type)
        hand_types = (OmahaHoldemHand,) if is_omaha(job.game_type) else (StandardHighHand,)

        equities = calculate_equities(
            (hero_range, villain_range),
            board,
            hole_count,
            _BOARD_CARDS_TOTAL,
            Deck.STANDARD,
            hand_types,
            sample_count=settings.bot_equity_sample_count,
        )
        return float(equities[0]), range_source
    except Exception:
        logger.exception("Equity calculation failed for bot %s hand %s", job.bot_id, job.hand_id)
        return None, None
