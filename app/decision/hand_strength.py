from collections import Counter

from app.decision.hand_evaluator import (
    classify_omaha_starting_hand,
    combined_strength,
    evaluate_holdem_made_hand,
    evaluate_holdem_preflop_hole,
    evaluate_street_hand,
    card_rank,
    card_suit,
    rank_value,
)
from app.decision.hand_types import (
    HandEvaluation,
    HandRank,
    RANK_ORDER,
    RANK_VALUE,
    clamp,
)
from app.schemas.game_state_schema import GameType, Street

evaluate_made_hand = evaluate_holdem_made_hand
evaluate_preflop_hole = evaluate_holdem_preflop_hole


def evaluate_preflop_strength(hole_cards: list[str], position: str, active_players: int) -> float:
    evaluation = evaluate_preflop_hole(hole_cards)
    score = evaluation.strength

    if position in {"BTN", "CO", "BUTTON", "LATE"}:
        score += 0.07
    elif position in {"SB", "BB", "UTG", "SMALL_BLIND", "BIG_BLIND", "EARLY"}:
        score -= 0.04

    if active_players <= 3:
        score += 0.06

    return clamp(score)


def evaluate_postflop_strength(
    hole_cards: list[str],
    board_cards: list[str],
    street: Street | None = None,
    game_type: GameType = GameType.NLH,
) -> tuple[float, str]:
    evaluation = evaluate_street_hand(hole_cards, board_cards, street or Street.FLOP, game_type)
    return evaluation.strength, evaluation.label


def evaluate_hand(
    hole_cards: list[str],
    board_cards: list[str],
    street: Street,
    game_type: GameType,
) -> HandEvaluation:
    return evaluate_street_hand(hole_cards, board_cards, street, game_type)


def evaluate_draw_strength(hole_cards: list[str], board_cards: list[str]) -> float:
    cards = hole_cards + board_cards
    suits = [card_suit(card) for card in cards]
    ranks = [rank_value(card) for card in cards]
    flush_draw = max(Counter(suits).values(), default=0) == 4
    straight_draw = has_near_straight(ranks)
    return (0.18 if flush_draw else 0.0) + (0.14 if straight_draw else 0.0)


def has_straight(values: list[int]) -> bool:
    unique = sorted(set(values))
    if 14 in unique:
        unique.insert(0, 1)
    return any(unique[i + 4] - unique[i] == 4 for i in range(max(0, len(unique) - 4)))


def has_near_straight(values: list[int]) -> bool:
    unique = sorted(set(values))
    if 14 in unique:
        unique.insert(0, 1)
    return any(unique[i + 3] - unique[i] <= 4 for i in range(max(0, len(unique) - 3)))


__all__ = [
    "HandRank",
    "HandEvaluation",
    "RANK_ORDER",
    "RANK_VALUE",
    "card_rank",
    "card_suit",
    "rank_value",
    "evaluate_preflop_strength",
    "evaluate_postflop_strength",
    "evaluate_hand",
    "evaluate_draw_strength",
    "combined_strength",
    "has_straight",
    "has_near_straight",
    "clamp",
    "classify_omaha_starting_hand",
]
