"""Hand evaluation for Texas Hold'em and Omaha (4/5/6/7 hole cards)."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from enum import IntEnum
from itertools import combinations

from app.decision.game_rules import GameType, game_type_label, is_holdem, is_omaha
from app.schemas.game_state_schema import Street

RANK_ORDER = "23456789TJQKA"
RANK_VALUE = {rank: index + 2 for index, rank in enumerate(RANK_ORDER)}


def card_rank(card: str) -> str:
    return card[0].upper()


def card_suit(card: str) -> str:
    return card[1].lower()


def rank_value(card: str) -> int:
    return RANK_VALUE[card_rank(card)]


def clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


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
    cards = hole_cards + board_cards
    if len(cards) < 5:
        return evaluate_holdem_preflop_hole(hole_cards)

    best_key, _ = _best_of_combinations((combo for combo in combinations(cards, 5)))
    return _evaluation_from_key(best_key, hole_cards, board_cards, street, "Hold'em")


def evaluate_omaha_made_hand(
    hole_cards: list[str],
    board_cards: list[str],
    street: Street | None,
    game_type: GameType,
) -> HandEvaluation:
    if len(board_cards) < 3:
        return evaluate_omaha_preflop_hole(hole_cards, game_type)

    combos = (
        list(hole_pair) + list(board_triple)
        for hole_pair in combinations(hole_cards, 2)
        for board_triple in combinations(board_cards, 3)
    )
    best_key, _ = _best_of_combinations(combos)
    label_game = game_type_label(game_type)
    return _evaluation_from_key(best_key, hole_cards, board_cards, street, label_game)


def _best_of_combinations(card_groups) -> tuple[tuple[int, ...], list[str]]:
    best_key: tuple[int, ...] | None = None
    best_cards: list[str] | None = None
    for group in card_groups:
        cards = list(group)
        key = score_five_cards(cards)
        if best_key is None or key > best_key:
            best_key = key
            best_cards = cards
    assert best_key is not None and best_cards is not None
    return best_key, best_cards


def _evaluation_from_key(
    best_key: tuple[int, ...],
    hole_cards: list[str],
    board_cards: list[str],
    street: Street | None,
    game_label: str,
) -> HandEvaluation:
    rank = HandRank(best_key[0])
    strength = hand_rank_to_strength(rank, best_key[1:])
    label = describe_hand(rank, best_key[1:], len(board_cards), game_label)
    return HandEvaluation(rank=rank, compare_key=best_key, strength=strength, label=label, street=street)


def score_five_cards(cards: list[str]) -> tuple[int, ...]:
    ranks = sorted((rank_value(card) for card in cards), reverse=True)
    suits = [card_suit(card) for card in cards]
    counts = Counter(ranks)
    ordered = sorted(counts.items(), key=lambda item: (-item[1], -item[0]))
    is_flush = len(set(suits)) == 1
    straight_high = straight_high_card(ranks)

    if is_flush and straight_high:
        return (HandRank.STRAIGHT_FLUSH, straight_high)
    if ordered[0][1] == 4:
        quad_rank = ordered[0][0]
        kicker = max(rank for rank in ranks if rank != quad_rank)
        return (HandRank.FOUR_OF_A_KIND, quad_rank, kicker)
    if ordered[0][1] == 3 and len(ordered) > 1 and ordered[1][1] >= 2:
        return (HandRank.FULL_HOUSE, ordered[0][0], ordered[1][0])
    if is_flush:
        return (HandRank.FLUSH, *ranks)
    if straight_high:
        return (HandRank.STRAIGHT, straight_high)
    if ordered[0][1] == 3:
        kickers = sorted((rank for rank in ranks if rank != ordered[0][0]), reverse=True)
        return (HandRank.THREE_OF_A_KIND, ordered[0][0], *kickers[:2])
    if ordered[0][1] == 2 and len(ordered) > 1 and ordered[1][1] == 2:
        high_pair, low_pair = sorted((ordered[0][0], ordered[1][0]), reverse=True)
        kicker = max(rank for rank in ranks if rank not in {high_pair, low_pair})
        return (HandRank.TWO_PAIR, high_pair, low_pair, kicker)
    if ordered[0][1] == 2:
        pair_rank = ordered[0][0]
        kickers = sorted((rank for rank in ranks if rank != pair_rank), reverse=True)
        return (HandRank.PAIR, pair_rank, *kickers[:3])
    return (HandRank.HIGH_CARD, *ranks)


def straight_high_card(ranks: list[int]) -> int:
    unique = sorted(set(ranks))
    if 14 in unique:
        unique = [1] + unique
    best = 0
    for index in range(len(unique) - 4):
        window = unique[index : index + 5]
        if len(window) == 5 and window[-1] - window[0] == 4:
            best = max(best, window[-1] if window[-1] != 1 else 5)
    return best


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
    return clamp(base + (top / 14) * 0.08)


def describe_hand(rank: HandRank, kickers: tuple[int, ...], board_len: int, game_label: str) -> str:
    street = _street_label(board_len)
    prefix = f"{game_label} {street}"
    if rank == HandRank.STRAIGHT_FLUSH:
        return f"{prefix}: straight flush ({_rank_word(kickers[0])}-high)"
    if rank == HandRank.FOUR_OF_A_KIND:
        return f"{prefix}: four of a kind, {_rank_plural(kickers[0])}"
    if rank == HandRank.FULL_HOUSE:
        return f"{prefix}: full house, {_rank_plural(kickers[0])} full of {_rank_plural(kickers[1])}"
    if rank == HandRank.FLUSH:
        return f"{prefix}: flush, {_rank_word(kickers[0])}-high"
    if rank == HandRank.STRAIGHT:
        return f"{prefix}: straight, {_rank_word(kickers[0])}-high"
    if rank == HandRank.THREE_OF_A_KIND:
        return f"{prefix}: three of a kind, {_rank_plural(kickers[0])}"
    if rank == HandRank.TWO_PAIR:
        return f"{prefix}: two pair, {_rank_plural(kickers[0])} and {_rank_plural(kickers[1])}"
    if rank == HandRank.PAIR:
        return f"{prefix}: pair of {_rank_plural(kickers[0])}, {_rank_word(kickers[1])} kicker"
    return f"{prefix}: high card {_rank_word(kickers[0])}"


def _street_label(board_len: int) -> str:
    return {0: "preflop", 3: "flop", 4: "turn", 5: "river"}.get(board_len, "board")


def _rank_word(value: int) -> str:
    return RANK_NAMES.get(value, str(value))


def _rank_plural(value: int) -> str:
    name = _rank_word(value)
    if name == "ace":
        return "aces"
    if name == "deuce":
        return "deuces"
    return f"{name}s"


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


# Backward-compatible aliases
evaluate_preflop_hole = evaluate_holdem_preflop_hole
evaluate_made_hand = evaluate_holdem_made_hand
