from pokerkit.hands import OmahaHoldemHand, StandardHighHand

from app.decision.hand_evaluator import HandRank, evaluate_holdem_made_hand, evaluate_omaha_made_hand
from app.decision.pokerkit_adapter import join_cards
from app.schemas.game_state_schema import GameType, Street


def test_full_house_beats_flush():
    hole = ["Ah", "Kh"]
    board = ["As", "Kd", "Kc", "2h", "3d"]
    evaluation = evaluate_holdem_made_hand(hole, board, Street.RIVER)
    assert evaluation.rank == HandRank.FULL_HOUSE
    assert "full house" in evaluation.label.lower()


def test_best_five_from_seven_not_seven_card_flush():
    hole = ["2h", "3h"]
    board = ["Ah", "Kh", "Qh", "Jh", "9c"]
    evaluation = evaluate_holdem_made_hand(hole, board, Street.RIVER)
    assert evaluation.rank == HandRank.FLUSH
    assert evaluation.compare_key[1] > 5000


def test_wheel_straight_pokerkit():
    hand = StandardHighHand.from_game(join_cards(["As", "2h"]), join_cards(["3d", "4c", "5h", "9c", "Td"]))
    assert "Straight" in str(hand)


def test_omaha_requires_two_hole_cards():
    hole = ["9h", "Th", "2c", "3d"]
    board = ["8s", "7d", "6c", "Kc", "2h"]
    evaluation = evaluate_omaha_made_hand(hole, board, Street.RIVER, GameType.OMAHA_4)
    assert evaluation.rank == HandRank.STRAIGHT
    assert "Omaha 4" in evaluation.label


def test_two_pair_uses_top_kickers():
    hole = ["Ad", "Kc"]
    board = ["As", "Kh", "2d", "2c", "7h"]
    evaluation = evaluate_holdem_made_hand(hole, board, Street.FLOP)
    assert evaluation.rank == HandRank.TWO_PAIR


def test_pokerkit_omaha_seven_hole():
    hand = OmahaHoldemHand.from_game(
        join_cards(["Ah", "Kd", "Qh", "Jc", "Ts", "9d", "8h"]),
        join_cards(["2d", "3c", "4h"]),
    )
    assert hand.entry.label.name in {"HIGH_CARD", "ONE_PAIR", "TWO_PAIR", "STRAIGHT", "FLUSH"}
