from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

from app.schemas.game_state_schema import Street


class HandRank(IntEnum):
    HIGH_CARD = 0
    PAIR = 1
    TWO_PAIR = 2
    THREE_OF_A_KIND = 3
    STRAIGHT = 4
    FLUSH = 5
    FULL_HOUSE = 6
    FOUR_OF_A_KIND = 7
    STRAIGHT_FLUSH = 8


HAND_RANK_LABELS = {
    HandRank.HIGH_CARD: "high card",
    HandRank.PAIR: "pair",
    HandRank.TWO_PAIR: "two pair",
    HandRank.THREE_OF_A_KIND: "three of a kind",
    HandRank.STRAIGHT: "straight",
    HandRank.FLUSH: "flush",
    HandRank.FULL_HOUSE: "full house",
    HandRank.FOUR_OF_A_KIND: "four of a kind",
    HandRank.STRAIGHT_FLUSH: "straight flush",
}

RANK_ORDER = "23456789TJQKA"
RANK_VALUE = {rank: index + 2 for index, rank in enumerate(RANK_ORDER)}

RANK_NAMES = {
    14: "ace",
    13: "king",
    12: "queen",
    11: "jack",
    10: "ten",
    9: "nine",
    8: "eight",
    7: "seven",
    6: "six",
    5: "five",
    4: "four",
    3: "three",
    2: "deuce",
}


@dataclass(frozen=True)
class HandEvaluation:
    rank: HandRank
    compare_key: tuple[int, ...]
    strength: float
    label: str
    street: Street | None = None

    @property
    def rank_name(self) -> str:
        return HAND_RANK_LABELS[self.rank]


def clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


def street_label(board_len: int) -> str:
    return {0: "preflop", 3: "flop", 4: "turn", 5: "river"}.get(board_len, "board")


def hand_rank_to_strength(rank: HandRank, kickers: tuple[int, ...]) -> float:
    base = {
        HandRank.HIGH_CARD: 0.12,
        HandRank.PAIR: 0.38,
        HandRank.TWO_PAIR: 0.52,
        HandRank.THREE_OF_A_KIND: 0.64,
        HandRank.STRAIGHT: 0.72,
        HandRank.FLUSH: 0.78,
        HandRank.FULL_HOUSE: 0.86,
        HandRank.FOUR_OF_A_KIND: 0.93,
        HandRank.STRAIGHT_FLUSH: 0.98,
    }[rank]
    top = kickers[0] if kickers else 2
    if top > 14:
        top = 14
    return clamp(base + (top / 14) * 0.08)
