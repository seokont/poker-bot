"""PokerKit 0.7.3 adapter for bot-server hand evaluation."""

from __future__ import annotations

from pokerkit.hands import OmahaHoldemHand, StandardHighHand
from pokerkit.lookups import Label

from app.decision.hand_types import HandEvaluation, HandRank, clamp, street_label
from app.schemas.game_state_schema import Street

PK_LABEL_TO_HAND_RANK: dict[Label, HandRank] = {
    Label.HIGH_CARD: HandRank.HIGH_CARD,
    Label.ONE_PAIR: HandRank.PAIR,
    Label.TWO_PAIR: HandRank.TWO_PAIR,
    Label.THREE_OF_A_KIND: HandRank.THREE_OF_A_KIND,
    Label.STRAIGHT: HandRank.STRAIGHT,
    Label.FLUSH: HandRank.FLUSH,
    Label.FULL_HOUSE: HandRank.FULL_HOUSE,
    Label.FOUR_OF_A_KIND: HandRank.FOUR_OF_A_KIND,
    Label.STRAIGHT_FLUSH: HandRank.STRAIGHT_FLUSH,
}

_PK_INDEX_CEILING = 7461


def join_cards(cards: list[str]) -> str:
    return "".join(_normalize_card(card) for card in cards)


def _normalize_card(card: str) -> str:
    text = card.strip()
    if len(text) != 2:
        raise ValueError(f"invalid card token: {card!r}")
    return text[0].upper() + text[1].lower()


def pokerkit_hand_to_evaluation(
    pokerkit_hand: StandardHighHand | OmahaHoldemHand,
    game_label: str,
    board_cards: list[str],
    street: Street | None,
) -> HandEvaluation:
    rank = PK_LABEL_TO_HAND_RANK[pokerkit_hand.entry.label]
    compare_key = (rank, pokerkit_hand.entry.index)
    strength = clamp(0.12 + (pokerkit_hand.entry.index / _PK_INDEX_CEILING) * 0.86)
    return HandEvaluation(
        rank=rank,
        compare_key=compare_key,
        strength=strength,
        label=f"{game_label} {street_label(len(board_cards))}: {pokerkit_hand}",
        street=street,
    )


def evaluate_holdem_with_pokerkit(
    hole_cards: list[str],
    board_cards: list[str],
    street: Street | None,
) -> HandEvaluation:
    pokerkit_hand = StandardHighHand.from_game(join_cards(hole_cards), join_cards(board_cards))
    return pokerkit_hand_to_evaluation(pokerkit_hand, "Hold'em", board_cards, street)


def evaluate_omaha_with_pokerkit(
    hole_cards: list[str],
    board_cards: list[str],
    street: Street | None,
    game_label: str,
) -> HandEvaluation:
    pokerkit_hand = OmahaHoldemHand.from_game(join_cards(hole_cards), join_cards(board_cards))
    return pokerkit_hand_to_evaluation(pokerkit_hand, game_label, board_cards, street)
