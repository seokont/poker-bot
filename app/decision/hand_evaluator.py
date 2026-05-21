"""Hand evaluation for Texas Hold'em and Omaha (4/5/6/7 hole cards) via PokerKit 0.7.3."""

from __future__ import annotations

from collections import Counter
from itertools import combinations

from app.decision.game_rules import GameType, game_type_label, is_holdem, is_omaha
from app.decision.hand_types import (
    HandEvaluation,
    HandRank,
    RANK_NAMES,
    RANK_ORDER,
    RANK_VALUE,
    clamp,
    hand_rank_to_strength,
    street_label,
)
from app.decision.pokerkit_adapter import evaluate_holdem_with_pokerkit, evaluate_omaha_with_pokerkit
from app.schemas.game_state_schema import Street


def card_rank(card: str) -> str:
    return card[0].upper()


def card_suit(card: str) -> str:
    return card[1].lower()


def rank_value(card: str) -> int:
    return RANK_VALUE[card_rank(card)]


def evaluate_street_hand(
    hole_cards: list[str],
    board_cards: list[str],
    street: Street,
    game_type: GameType,
) -> HandEvaluation:
    if is_holdem(game_type):
        if street == Street.PREFLOP or not board_cards:
            return evaluate_holdem_preflop_hole(hole_cards)
        return evaluate_holdem_made_hand(hole_cards, board_cards, street)

    if is_omaha(game_type):
        if street == Street.PREFLOP or len(board_cards) < 3:
            return evaluate_omaha_preflop_hole(hole_cards, game_type)
        return evaluate_omaha_made_hand(hole_cards, board_cards, street, game_type)

    return evaluate_holdem_preflop_hole(hole_cards)


def evaluate_holdem_preflop_hole(hole_cards: list[str]) -> HandEvaluation:
    first, second = hole_cards[:2]
    high = max(rank_value(first), rank_value(second))
    low = min(rank_value(first), rank_value(second))
    suited = card_suit(first) == card_suit(second)
    pair = high == low

    if pair:
        compare_key = (HandRank.PAIR, high)
        strength = 0.50 + (high / 14) * 0.42
        label = f"Hold'em preflop: pair of {RANK_NAMES[high]}s"
    else:
        compare_key = (HandRank.HIGH_CARD, high, low, 1 if suited else 0)
        strength = (high / 14) * 0.38 + (low / 14) * 0.22 + (0.08 if suited else 0.0)
        if abs(high - low) <= 2:
            strength += 0.05
        high_name = RANK_NAMES[high]
        low_name = RANK_NAMES[low]
        suited_text = " suited" if suited else ""
        label = f"Hold'em preflop: {high_name}-{low_name}{suited_text}"

    return HandEvaluation(
        rank=HandRank.PAIR if pair else HandRank.HIGH_CARD,
        compare_key=compare_key,
        strength=clamp(strength),
        label=label,
        street=Street.PREFLOP,
    )


def evaluate_holdem_made_hand(hole_cards: list[str], board_cards: list[str], street: Street | None = None) -> HandEvaluation:
    if len(hole_cards) + len(board_cards) < 5:
        return evaluate_holdem_preflop_hole(hole_cards)
    return evaluate_holdem_with_pokerkit(hole_cards, board_cards, street)


def evaluate_omaha_made_hand(
    hole_cards: list[str],
    board_cards: list[str],
    street: Street | None,
    game_type: GameType,
) -> HandEvaluation:
    if len(board_cards) < 3:
        return evaluate_omaha_preflop_hole(hole_cards, game_type)
    return evaluate_omaha_with_pokerkit(hole_cards, board_cards, street, game_type_label(game_type))


def combined_strength(
    evaluation: HandEvaluation,
    draw_equity: float,
    street: Street,
) -> float:
    if street == Street.RIVER:
        return evaluation.strength
    weight = {Street.FLOP: 0.55, Street.TURN: 0.35, Street.PREFLOP: 0.0}.get(street, 0.0)
    return clamp(evaluation.strength + draw_equity * weight)


def evaluate_omaha_preflop_hole(hole_cards: list[str], game_type: GameType) -> HandEvaluation:
    ranks = [rank_value(card) for card in hole_cards]
    rank_counts = Counter(ranks)
    pairs = sorted((rank for rank, count in rank_counts.items() if count >= 2), reverse=True)
    suits = Counter(card_suit(card) for card in hole_cards)
    double_suited = sum(1 for count in suits.values() if count >= 2) >= 2
    max_suited = max(suits.values(), default=0)
    connectivity = _omaha_connectivity_score(ranks)
    top_rank = max(ranks)

    strength = 0.22 + (top_rank / 14) * 0.18
    strength += min(0.22, len(pairs) * 0.09 + (pairs[0] / 14) * 0.08 if pairs else 0)
    strength += 0.10 if double_suited else (0.05 if max_suited >= 3 else 0.0)
    strength += connectivity * 0.12
    if len(hole_cards) >= 5:
        strength += 0.03
    if len(hole_cards) >= 6:
        strength += 0.02

    if pairs and pairs[0] >= 12 and (double_suited or connectivity >= 0.55):
        rank = HandRank.TWO_PAIR
        label = f"{game_type_label(game_type)} preflop: premium double-suited/connected, pair of {RANK_NAMES[pairs[0]]}s"
    elif pairs and pairs[0] >= 11:
        rank = HandRank.PAIR
        label = f"{game_type_label(game_type)} preflop: strong pair of {RANK_NAMES[pairs[0]]}s with backup cards"
    elif double_suited and connectivity >= 0.5:
        rank = HandRank.HIGH_CARD
        label = f"{game_type_label(game_type)} preflop: coordinated double-suited rundown"
    elif pairs:
        rank = HandRank.PAIR
        label = f"{game_type_label(game_type)} preflop: pair of {RANK_NAMES[pairs[0]]}s"
    else:
        rank = HandRank.HIGH_CARD
        label = f"{game_type_label(game_type)} preflop: uncoordinated high-card hand"

    compare_key = (rank, top_rank, pairs[0] if pairs else 0, int(double_suited), int(connectivity * 100))
    return HandEvaluation(
        rank=rank,
        compare_key=compare_key,
        strength=clamp(strength),
        label=label,
        street=Street.PREFLOP,
    )


def classify_omaha_starting_hand(hole_cards: list[str], game_type: GameType) -> str:
    evaluation = evaluate_omaha_preflop_hole(hole_cards, game_type)
    if evaluation.strength >= 0.72:
        return "PREMIUM"
    if evaluation.strength >= 0.58:
        return "VERY_STRONG"
    if evaluation.strength >= 0.46:
        return "MEDIUM"
    if evaluation.strength >= 0.34:
        return "SPECULATIVE"
    if evaluation.strength >= 0.26:
        return "WEAK"
    return "TRASH"


def _omaha_connectivity_score(ranks: list[int]) -> float:
    unique = sorted(set(ranks))
    if 14 in unique:
        unique = [1] + unique
    best_gap = 99
    for combo in combinations(unique, min(4, len(unique))):
        span = max(combo) - min(combo)
        best_gap = min(best_gap, span - (len(combo) - 1))
    if best_gap <= 2:
        return 0.85
    if best_gap <= 4:
        return 0.55
    if best_gap <= 6:
        return 0.30
    return 0.10


evaluate_preflop_hole = evaluate_holdem_preflop_hole
evaluate_made_hand = evaluate_holdem_made_hand
