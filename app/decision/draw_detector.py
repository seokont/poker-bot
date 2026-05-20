from collections import Counter
from dataclasses import dataclass

from app.decision.hand_strength import RANK_VALUE, card_rank, card_suit, has_near_straight


@dataclass(frozen=True)
class DrawInfo:
    flush_draw: bool
    nut_flush_draw: bool
    open_ended_straight_draw: bool
    gutshot_straight_draw: bool
    combo_draw: bool
    overcards: int
    backdoor_draw: bool
    equity_estimate: float


def detect_draws(hole_cards: list[str], board_cards: list[str]) -> DrawInfo:
    cards = hole_cards + board_cards
    suits = Counter(card_suit(card) for card in cards)
    ranks = sorted(set(RANK_VALUE[card_rank(card)] for card in cards))
    board_high = max((RANK_VALUE[card_rank(card)] for card in board_cards), default=0)

    flush_draw = max(suits.values(), default=0) == 4
    nut_flush_draw = flush_draw and any(card_rank(card) == "A" for card in hole_cards)
    open_ended = _has_open_ended_draw(ranks)
    near_straight = has_near_straight(ranks)
    gutshot = near_straight and not open_ended
    overcards = sum(1 for card in hole_cards if RANK_VALUE[card_rank(card)] > board_high)
    backdoor = max(suits.values(), default=0) == 3 or _has_three_card_run(ranks)
    combo = flush_draw and (open_ended or gutshot or overcards >= 1)

    equity = 0.0
    if flush_draw:
        equity += 0.34 if len(board_cards) == 3 else 0.19
    if open_ended:
        equity += 0.31 if len(board_cards) == 3 else 0.17
    if gutshot:
        equity += 0.16 if len(board_cards) == 3 else 0.09
    equity += overcards * 0.04
    if combo:
        equity += 0.10

    return DrawInfo(flush_draw, nut_flush_draw, open_ended, gutshot, combo, overcards, backdoor, min(0.85, equity))


def _has_open_ended_draw(ranks: list[int]) -> bool:
    wheel = [1 if rank == 14 else rank for rank in ranks] + ranks
    unique = sorted(set(wheel))
    return any(unique[i + 3] - unique[i] == 3 for i in range(max(0, len(unique) - 3)))


def _has_three_card_run(ranks: list[int]) -> bool:
    unique = sorted(set(ranks))
    return any(unique[i + 2] - unique[i] <= 3 for i in range(max(0, len(unique) - 2)))
