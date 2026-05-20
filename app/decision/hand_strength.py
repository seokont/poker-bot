from collections import Counter

RANK_ORDER = "23456789TJQKA"
RANK_VALUE = {rank: index + 2 for index, rank in enumerate(RANK_ORDER)}


def card_rank(card: str) -> str:
    return card[0].upper()


def card_suit(card: str) -> str:
    return card[1].lower()


def rank_value(card: str) -> int:
    return RANK_VALUE[card_rank(card)]


def evaluate_preflop_strength(hole_cards: list[str], position: str, active_players: int) -> float:
    first, second = hole_cards
    high = max(rank_value(first), rank_value(second))
    low = min(rank_value(first), rank_value(second))
    suited = card_suit(first) == card_suit(second)
    pair = high == low
    gap = high - low

    if pair:
        score = 0.48 + (high / 14) * 0.45
    else:
        score = (high / 14) * 0.42 + (low / 14) * 0.24
        if suited:
            score += 0.08
        if gap <= 2:
            score += 0.06
        elif gap >= 5:
            score -= 0.08

    if position in {"BTN", "CO"}:
        score += 0.07
    elif position in {"SB", "BB", "UTG"}:
        score -= 0.04

    if active_players <= 3:
        score += 0.06

    return clamp(score)


def evaluate_postflop_strength(hole_cards: list[str], board_cards: list[str]) -> tuple[float, str]:
    cards = hole_cards + board_cards
    ranks = [card_rank(card) for card in cards]
    suits = [card_suit(card) for card in cards]
    counts = Counter(ranks)
    count_values = sorted(counts.values(), reverse=True)
    flush = max(Counter(suits).values(), default=0) >= 5
    straight = has_straight([RANK_VALUE[rank] for rank in ranks])

    if straight and flush:
        return 0.98, "straight flush or very strong made hand"
    if count_values[0] == 4:
        return 0.94, "four of a kind"
    if count_values[0] == 3 and len(count_values) > 1 and count_values[1] >= 2:
        return 0.88, "full house"
    if flush:
        return 0.82, "flush"
    if straight:
        return 0.76, "straight"
    if count_values[0] == 3:
        return 0.66, "three of a kind"
    if count_values[0] == 2 and len(count_values) > 1 and count_values[1] == 2:
        return 0.56, "two pair"
    if count_values[0] == 2:
        pair_rank = max(RANK_VALUE[rank] for rank, count in counts.items() if count == 2)
        return 0.42 + pair_rank / 100, "pair"
    high_card = max(RANK_VALUE[rank] for rank in ranks)
    return 0.15 + high_card / 100, "high card"


def evaluate_draw_strength(hole_cards: list[str], board_cards: list[str]) -> float:
    cards = hole_cards + board_cards
    suits = [card_suit(card) for card in cards]
    ranks = [RANK_VALUE[card_rank(card)] for card in cards]
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


def clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))
