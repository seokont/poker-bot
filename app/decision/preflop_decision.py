import random

from app.bots.bot_profiles import BotProfile, BotProfileType
from app.decision.bet_sizing import all_in_amount
from app.decision.bluff_logic import should_make_mistake
from app.decision.game_rules import is_omaha
from app.decision.omaha_preflop_charts import lookup_omaha_preflop_chart
from app.decision.preflop_charts import lookup_preflop_chart
from app.decision.hand_strength import card_rank, card_suit, evaluate_preflop_strength
from app.decision.hand_evaluator import classify_omaha_starting_hand, evaluate_omaha_preflop_hole
from app.decision.pot_odds import calculate_pot_odds, call_amount
from app.schemas.bot_action_schema import BotAction, BotActionProposal
from app.schemas.bot_job_schema import BotTurnJob
from app.schemas.game_state_schema import Position


def decide_preflop(job: BotTurnJob, profile: BotProfile) -> BotActionProposal:
    if is_omaha(job.game_type):
        chart_proposal = _try_preflop_chart(job, profile, lookup_omaha_preflop_chart)
        if chart_proposal is not None:
            return chart_proposal
    else:
        chart_proposal = _try_preflop_chart(job, profile, lookup_preflop_chart)
        if chart_proposal is not None:
            return chart_proposal

    if is_omaha(job.game_type):
        hand_group = classify_omaha_starting_hand(job.bot_hole_cards, job.game_type)
        hand_group = _adjust_omaha_preflop_group(hand_group, job)
    else:
        hand_group = classify_starting_hand(job.bot_hole_cards)
        hand_group = _adjust_preflop_group(hand_group, job)
    call_cost = call_amount(job.current_bet, job.bot_current_bet, job.bot_stack)
    odds = calculate_pot_odds(job.pot_size, call_cost)
    short_stack = job.bot_stack <= job.big_blind * 10
    deep_stack = job.bot_stack >= job.big_blind * 40
    facing_raise = job.current_bet > job.big_blind
    unopened_or_blinds_only = not facing_raise
    late_position = job.position in {Position.LATE, Position.BUTTON}
    blind_position = job.position in {Position.SMALL_BLIND, Position.BIG_BLIND}
    aggressive = profile.profile_type in {BotProfileType.TIGHT_AGGRESSIVE, BotProfileType.LOOSE_AGGRESSIVE}
    loose = profile.profile_type in {BotProfileType.LOOSE_PASSIVE, BotProfileType.LOOSE_AGGRESSIVE, BotProfileType.BEGINNER}
    mistake = should_make_mistake(profile)

    if short_stack and BotAction.ALL_IN in job.legal_actions:
        if hand_group in {"PREMIUM", "VERY_STRONG"} or (hand_group == "MEDIUM" and aggressive):
            return BotActionProposal(
                action=BotAction.ALL_IN,
                amount=all_in_amount(job.bot_stack, job.max_raise),
                reason=f"Short-stack push/fold with {hand_group.lower()} hand",
            )

    if unopened_or_blinds_only:
        if job.position == Position.BIG_BLIND and call_cost == 0 and BotAction.CHECK in job.legal_actions:
            return BotActionProposal(action=BotAction.CHECK, amount=None, reason="Big blind checks option with no raise")

        if hand_group == "PREMIUM" and BotAction.RAISE in job.legal_actions:
            amount = _open_raise_amount(job, 3.2, 4.0 if aggressive else 3.5)
            return BotActionProposal(
                action=BotAction.RAISE,
                amount=amount,
                reason="Premium hand opens for 3-4 big blinds",
            )

        if hand_group == "VERY_STRONG" and BotAction.RAISE in job.legal_actions:
            if job.position == Position.EARLY and not aggressive and random.random() < 0.25:
                return _call_or_check(job, "Tighter early-position line with very strong hand")
            return BotActionProposal(
                action=BotAction.RAISE,
                amount=_open_raise_amount(job, 2.5, 3.5),
                reason="Very strong hand opens standard preflop size",
            )

        if hand_group == "MEDIUM":
            if late_position or aggressive:
                if BotAction.RAISE in job.legal_actions:
                    return BotActionProposal(
                        action=BotAction.RAISE,
                        amount=_open_raise_amount(job, 2.4, 3.2),
                        reason="Medium hand opens wider in position/profile",
                    )
            if BotAction.CALL in job.legal_actions and (loose or odds <= 0.25):
                return BotActionProposal(action=BotAction.CALL, amount=call_cost, reason="Medium hand continues cheaply")

        if hand_group == "SPECULATIVE":
            if deep_stack and BotAction.CALL in job.legal_actions and call_cost <= job.big_blind:
                return BotActionProposal(action=BotAction.CALL, amount=call_cost, reason="Deep-stack speculative hand calls cheaply")
            if late_position and BotAction.RAISE in job.legal_actions and (aggressive or random.random() < profile.looseness):
                return BotActionProposal(
                    action=BotAction.RAISE,
                    amount=_open_raise_amount(job, 2.3, 3.0),
                    reason="Late-position speculative steal/open",
                )

        if hand_group == "WEAK":
            steal_spot = late_position and job.active_players_count <= 2 and BotAction.RAISE in job.legal_actions
            if steal_spot and (profile.profile_type == BotProfileType.LOOSE_AGGRESSIVE or random.random() < profile.bluff_frequency):
                return BotActionProposal(
                    action=BotAction.RAISE,
                    amount=_open_raise_amount(job, 2.2, 2.8),
                    reason="Profile-selected late-position steal with weak playable hand",
                )
            if BotAction.CALL in job.legal_actions and profile.profile_type == BotProfileType.LOOSE_PASSIVE and call_cost <= job.big_blind:
                return BotActionProposal(action=BotAction.CALL, amount=call_cost, reason="Loose-passive cheap call mistake/range")

        if hand_group == "TRASH":
            if mistake and BotAction.CALL in job.legal_actions and profile.profile_type == BotProfileType.BEGINNER and call_cost <= job.big_blind:
                return BotActionProposal(action=BotAction.CALL, amount=call_cost, reason="Beginner mistake calls too wide")
            if BotAction.CHECK in job.legal_actions:
                return BotActionProposal(action=BotAction.CHECK, amount=None, reason="Trash hand checks when free")
            return _fold_or_check(job, "Trash hand folds preflop")

        return _fold_or_check(job, f"{hand_group.lower()} hand does not meet opening criteria")

    if hand_group == "PREMIUM":
        if BotAction.ALL_IN in job.legal_actions and (short_stack or profile.profile_type in {BotProfileType.BEGINNER, BotProfileType.LOOSE_AGGRESSIVE}):
            return BotActionProposal(action=BotAction.ALL_IN, amount=all_in_amount(job.bot_stack, job.max_raise), reason="Premium hand can stack off")
        if BotAction.RAISE in job.legal_actions and profile.profile_type != BotProfileType.TIGHT_PASSIVE:
            return BotActionProposal(action=BotAction.RAISE, amount=_three_bet_amount(job), reason="Premium hand re-raises facing action")
        if BotAction.CALL in job.legal_actions:
            return BotActionProposal(action=BotAction.CALL, amount=call_cost, reason="Premium hand continues facing raise")

    if hand_group == "VERY_STRONG":
        large_raise_pressure = call_cost >= job.big_blind * 6
        if large_raise_pressure and profile.profile_type in {BotProfileType.TIGHT_PASSIVE, BotProfileType.BALANCED}:
            return _fold_or_call_small(job, call_cost, odds, "Tight profile respects large re-raise")
        if BotAction.RAISE in job.legal_actions and aggressive and random.random() < 0.55 + profile.aggression * 0.25:
            return BotActionProposal(action=BotAction.RAISE, amount=_three_bet_amount(job), reason="Aggressive profile re-raises very strong hand")
        if BotAction.CALL in job.legal_actions:
            return BotActionProposal(action=BotAction.CALL, amount=call_cost, reason="Very strong hand calls facing raise")

    if hand_group == "MEDIUM":
        if BotAction.CALL in job.legal_actions and deep_stack and odds <= 0.28 and not short_stack:
            return BotActionProposal(action=BotAction.CALL, amount=call_cost, reason="Medium hand calls with deep stack and fair price")
        if mistake and loose and BotAction.CALL in job.legal_actions and odds <= 0.38:
            return BotActionProposal(action=BotAction.CALL, amount=call_cost, reason="Loose/beginner mistake calls medium hand too wide")
        return _fold_or_check(job, "Medium hand folds to pressure")

    if hand_group == "SPECULATIVE":
        if BotAction.CALL in job.legal_actions and deep_stack and call_cost <= job.big_blind * 2 and odds <= 0.22:
            return BotActionProposal(action=BotAction.CALL, amount=call_cost, reason="Speculative hand calls only cheap with implied odds")
        return _fold_or_check(job, "Speculative hand folds to raise pressure")

    if hand_group == "WEAK" and mistake and loose and BotAction.CALL in job.legal_actions and call_cost <= job.big_blind:
        return BotActionProposal(action=BotAction.CALL, amount=call_cost, reason="Loose profile calls weak hand too wide")

    return _fold_or_check(job, f"{hand_group.lower()} hand folds facing raise")


def _try_preflop_chart(job: BotTurnJob, profile: BotProfile, lookup_fn) -> BotActionProposal | None:
    advice = lookup_fn(job)
    call_cost = call_amount(job.current_bet, job.bot_current_bet, job.bot_stack)
    facing_raise = job.current_bet > job.big_blind
    aggressive = profile.profile_type in {BotProfileType.TIGHT_AGGRESSIVE, BotProfileType.LOOSE_AGGRESSIVE}

    if advice.action == "FOLD":
        if facing_raise or advice.chart_key.startswith("open."):
            return _fold_or_check(job, advice.reason)
        return None

    if advice.action == "OPEN":
        if not facing_raise and BotAction.RAISE in job.legal_actions:
            return BotActionProposal(
                action=BotAction.RAISE,
                amount=_open_raise_amount(job, 2.4, 3.5),
                reason=advice.reason,
            )
        if not facing_raise and BotAction.CHECK in job.legal_actions and job.position == Position.BIG_BLIND:
            return BotActionProposal(action=BotAction.CHECK, amount=None, reason=advice.reason)
        return None

    if advice.action == "CALL":
        if BotAction.CALL in job.legal_actions:
            return BotActionProposal(action=BotAction.CALL, amount=call_cost, reason=advice.reason)
        return _fold_or_check(job, advice.reason)

    if advice.action == "THREE_BET" and aggressive and BotAction.RAISE in job.legal_actions:
        return BotActionProposal(
            action=BotAction.RAISE,
            amount=_three_bet_amount(job),
            reason=advice.reason,
        )
    if advice.action == "THREE_BET" and BotAction.CALL in job.legal_actions:
        return BotActionProposal(action=BotAction.CALL, amount=call_cost, reason=f"{advice.reason}; flat instead of 3-bet")

    return None


def _adjust_omaha_preflop_group(hand_group: str, job: BotTurnJob) -> str:
    evaluation = evaluate_omaha_preflop_hole(job.bot_hole_cards, job.game_type)
    if evaluation.strength >= 0.70 and hand_group not in {"PREMIUM"}:
        return "VERY_STRONG"
    if evaluation.strength < 0.30 and hand_group in {"MEDIUM", "SPECULATIVE"}:
        return "WEAK"
    return hand_group


def _adjust_preflop_group(hand_group: str, job: BotTurnJob) -> str:
    strength = evaluate_preflop_strength(
        job.bot_hole_cards,
        job.position.value,
        job.active_players_count,
    )
    if strength >= 0.82 and hand_group not in {"PREMIUM"}:
        return "VERY_STRONG"
    if strength >= 0.68 and hand_group in {"WEAK", "SPECULATIVE"}:
        return "MEDIUM"
    if strength < 0.28 and hand_group in {"MEDIUM", "SPECULATIVE"}:
        return "WEAK"
    return hand_group


def classify_starting_hand(hole_cards: list[str]) -> str:
    ranks = sorted((card_rank(card) for card in hole_cards), key="23456789TJQKA".index, reverse=True)
    suited = card_suit(hole_cards[0]) == card_suit(hole_cards[1])
    pair = ranks[0] == ranks[1]
    combo = "".join(ranks) + ("s" if suited else "o")

    if pair and ranks[0] in {"A", "K", "Q"}:
        return "PREMIUM"
    if combo in {"AKs", "AKo"}:
        return "PREMIUM"
    if pair and ranks[0] in {"J", "T"}:
        return "VERY_STRONG"
    if combo in {"AQs", "AQo", "AJs", "KQs"}:
        return "VERY_STRONG"
    if pair and ranks[0] in {"9", "8", "7", "6"}:
        return "MEDIUM"
    if combo in {"ATs", "KJs", "QJs", "JTs", "T9s"}:
        return "MEDIUM"
    if pair and ranks[0] in {"5", "4", "3", "2"}:
        return "SPECULATIVE"
    if combo in {"98s", "87s", "76s", "65s", "54s", "A5s", "A4s", "A3s", "A2s"}:
        return "SPECULATIVE"
    if combo in {"K9s", "Q9s", "J9s", "T8s", "A9o", "KJo", "QJo"}:
        return "WEAK"
    if combo in {"72o", "83o", "94o", "J3o", "T2o", "Q4o"}:
        return "TRASH"
    if not suited and abs("23456789TJQKA".index(ranks[0]) - "23456789TJQKA".index(ranks[1])) >= 5:
        return "TRASH"
    return "WEAK" if not suited else "SPECULATIVE"


def _open_raise_amount(job: BotTurnJob, min_bb: float, max_bb: float) -> int:
    target = round(job.big_blind * random.uniform(min_bb, max_bb))
    return min(job.bot_current_bet + job.bot_stack, max(target, job.current_bet + (job.min_raise or job.big_blind)))


def _three_bet_amount(job: BotTurnJob) -> int:
    target = max(job.current_bet * 3, job.current_bet + (job.min_raise or job.big_blind))
    pressure = 1.15 if job.active_players_count <= 2 else 1.0
    return min(job.bot_current_bet + job.bot_stack, round(target * pressure))


def _call_or_check(job: BotTurnJob, reason: str) -> BotActionProposal:
    call_cost = call_amount(job.current_bet, job.bot_current_bet, job.bot_stack)
    if BotAction.CALL in job.legal_actions and call_cost > 0:
        return BotActionProposal(action=BotAction.CALL, amount=call_cost, reason=reason)
    if BotAction.CHECK in job.legal_actions:
        return BotActionProposal(action=BotAction.CHECK, amount=None, reason=reason)
    return _fold_or_check(job, reason)


def _fold_or_call_small(job: BotTurnJob, call_cost: int, odds: float, reason: str) -> BotActionProposal:
    if BotAction.CALL in job.legal_actions and call_cost <= job.big_blind * 2 and odds <= 0.20:
        return BotActionProposal(action=BotAction.CALL, amount=call_cost, reason=reason)
    return _fold_or_check(job, reason)


def _fold_or_check(job: BotTurnJob, reason: str) -> BotActionProposal:
    if BotAction.CHECK in job.legal_actions:
        return BotActionProposal(action=BotAction.CHECK, amount=None, reason=reason)
    if BotAction.FOLD in job.legal_actions:
        return BotActionProposal(action=BotAction.FOLD, amount=None, reason=reason)
    action = job.legal_actions[0]
    amount = None if action in {BotAction.CHECK, BotAction.FOLD} else max(0, job.current_bet - job.bot_current_bet)
    return BotActionProposal(action=action, amount=amount, reason=reason)
