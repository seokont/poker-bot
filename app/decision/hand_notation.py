"""Hole-card notation for chart lookup (e.g. AKs, TT, 76o)."""

from pokerkit import Card

from app.decision.hand_evaluator import card_rank, card_suit


def hole_cards_to_combo(hole_cards: list[str]) -> frozenset:
    return frozenset(list(Card.parse("".join(_normalize(card) for card in hole_cards))))


def hole_summary(hole_cards: list[str]) -> str:
    if len(hole_cards) == 2:
        return combo_label(hole_cards)
    return f"{len(hole_cards)}-card {hole_cards[0]}{hole_cards[1]}+{hole_cards[-2]}{hole_cards[-1]}"


def combo_label(hole_cards: list[str]) -> str:
    ranks = sorted((card_rank(card) for card in hole_cards), key="23456789TJQKA".index, reverse=True)
    suited = card_suit(hole_cards[0]) == card_suit(hole_cards[1])
    if ranks[0] == ranks[1]:
        return f"{ranks[0]}{ranks[1]}"
    return "".join(ranks) + ("s" if suited else "o")


def _normalize(card: str) -> str:
    text = card.strip()
    return text[0].upper() + text[1].lower()
