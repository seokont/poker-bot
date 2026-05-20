from collections import Counter
from enum import StrEnum

from app.decision.hand_strength import RANK_VALUE, card_rank, card_suit


class BoardTexture(StrEnum):
    DRY = "DRY"
    WET = "WET"
    PAIRED = "PAIRED"
    MONOTONE = "MONOTONE"
    DANGEROUS = "DANGEROUS"


def classify_board_texture(board_cards: list[str]) -> BoardTexture:
    if len(board_cards) < 3:
        return BoardTexture.DRY

    ranks = [RANK_VALUE[card_rank(card)] for card in board_cards]
    suits = [card_suit(card) for card in board_cards]
    rank_counts = Counter(ranks)

    if max(rank_counts.values(), default=0) >= 2:
        return BoardTexture.PAIRED

    suitedness = max(Counter(suits).values(), default=0)
    connected = max(ranks) - min(ranks) <= 5
    high_scary = max(ranks) >= 13 and len(board_cards) >= 4

    if suitedness >= 3 and len(board_cards) == 3:
        return BoardTexture.MONOTONE
    if suitedness >= 3 or (connected and suitedness >= 2):
        return BoardTexture.DANGEROUS
    if suitedness == 2 or connected or high_scary:
        return BoardTexture.WET
    return BoardTexture.DRY
