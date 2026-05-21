from app.bots.bot_profiles import BotProfile, BotProfileType
from app.decision.bet_sizing import BetSize, all_in_amount, size_bet
from app.decision.bluff_logic import should_bluff, should_make_mistake
from app.decision.board_texture import BoardTexture, classify_board_texture
from app.decision.draw_detector import detect_draws
from app.decision.game_rules import is_omaha
from app.decision.hand_types import HandRank
from app.decision.hand_strength import combined_strength, evaluate_draw_strength, evaluate_hand
from app.decision.equity_calculator import calculate_hero_equity
from app.decision.pot_odds import calculate_pot_odds, call_amount
from app.schemas.bot_action_schema import BotAction, BotActionProposal
from app.schemas.bot_job_schema import BotTurnJob
from app.schemas.game_state_schema import Street


def decide_postflop(job: BotTurnJob, profile: BotProfile) -> BotActionProposal:
    evaluation = evaluate_hand(job.bot_hole_cards, job.board_cards, job.street, job.game_type)
    hand_label = evaluation.label
    raw_draw_strength = evaluate_draw_strength(job.bot_hole_cards, job.board_cards)
    draws = detect_draws(job.bot_hole_cards, job.board_cards, job.game_type)
    draw_strength = 0.0 if job.street == Street.RIVER else max(raw_draw_strength, draws.equity_estimate * 0.5)
    total_strength = combined_strength(evaluation, draw_strength, job.street)
    made_strength = evaluation.strength
    call_cost = call_amount(job.current_bet, job.bot_current_bet, job.bot_stack)
    odds = calculate_pot_odds(job.pot_size, call_cost)
    texture = classify_board_texture(job.board_cards)
    heads_up = job.active_players_count <= 2
    multiway = job.active_players_count >= 3
    aggressive = profile.profile_type in {BotProfileType.TIGHT_AGGRESSIVE, BotProfileType.LOOSE_AGGRESSIVE}
    passive = profile.profile_type in {BotProfileType.TIGHT_PASSIVE, BotProfileType.LOOSE_PASSIVE}
    board_danger = _board_danger(texture, draws)

    if should_make_mistake(profile):
        total_strength = max(0.0, min(1.0, total_strength + (-0.12 if random_bool(0.65) else 0.10)))

    if is_omaha(job.game_type):
        total_strength *= 0.94
        if multiway:
            total_strength *= 0.90

    made_category = _made_category(evaluation.rank, made_strength, is_omaha(job.game_type))
    strong_draw = draws.combo_draw or draws.nut_flush_draw or (draws.flush_draw and draws.open_ended_straight_draw)

    if BotAction.ALL_IN in job.legal_actions and job.bot_stack <= max(job.pot_size, call_cost * 3):
        if made_category in {"MONSTER", "VERY_STRONG"} or (
            strong_draw and aggressive and job.street.value in {"FLOP", "TURN"}
        ):
            return BotActionProposal(
                action=BotAction.ALL_IN,
                amount=all_in_amount(job.bot_stack, job.max_raise),
                reason=f"Short-stack all-in with {hand_label} / strong draw pressure",
            )

    if call_cost == 0:
        if BotAction.BET in job.legal_actions and made_category in {"MONSTER", "VERY_STRONG"}:
            size = BetSize.LARGE if texture in {BoardTexture.WET, BoardTexture.DANGEROUS, BoardTexture.MONOTONE} else BetSize.MEDIUM
            return BotActionProposal(
                action=BotAction.BET,
                amount=size_bet(job.pot_size, job.bot_stack, job.min_raise, job.max_raise, size),
                reason=f"Value/protection bet with {hand_label} on {texture.value.lower()} board",
            )

        if BotAction.BET in job.legal_actions and made_category == "STRONG_ONE_PAIR":
            size = BetSize.MEDIUM if texture in {BoardTexture.WET, BoardTexture.DANGEROUS} else BetSize.SMALL
            return BotActionProposal(
                action=BotAction.BET,
                amount=size_bet(job.pot_size, job.bot_stack, job.min_raise, job.max_raise, size),
                reason=f"Thin value/control bet with {hand_label}",
            )

        if BotAction.BET in job.legal_actions and made_category == "MEDIUM" and not multiway and texture == BoardTexture.DRY:
            return BotActionProposal(
                action=BotAction.BET,
                amount=size_bet(job.pot_size, job.bot_stack, job.min_raise, job.max_raise, BetSize.SMALL),
                reason=f"Small protection bet with medium showdown value ({hand_label})",
            )

        if BotAction.BET in job.legal_actions and draw_strength >= 0.22 and (aggressive or heads_up):
            size = BetSize.MEDIUM if strong_draw else BetSize.SMALL
            return BotActionProposal(
                action=BotAction.BET,
                amount=size_bet(job.pot_size, job.bot_stack, job.min_raise, job.max_raise, size),
                reason="Semi-bluff/value pressure with draw equity",
            )

        bluff_ok = heads_up and not multiway and texture in {BoardTexture.DRY, BoardTexture.PAIRED}
        if BotAction.BET in job.legal_actions and bluff_ok and should_bluff(profile, board_danger, 0.35):
            return BotActionProposal(
                action=BotAction.BET,
                amount=size_bet(job.pot_size, job.bot_stack, job.min_raise, job.max_raise, BetSize.SMALL),
                reason="Profile-selected bluff on favorable board texture",
            )

        if BotAction.CHECK in job.legal_actions:
            return BotActionProposal(action=BotAction.CHECK, amount=None, reason=f"Checks {hand_label} without pressure")

    pressure_ratio = call_cost / max(1, job.pot_size)

    if made_category == "MONSTER" and BotAction.RAISE in job.legal_actions:
        size = BetSize.LARGE if texture in {BoardTexture.WET, BoardTexture.DANGEROUS, BoardTexture.MONOTONE} else BetSize.MEDIUM
        return BotActionProposal(
            action=BotAction.RAISE,
            amount=size_bet(job.pot_size + call_cost, job.bot_stack, job.min_raise, job.max_raise, size),
            reason=f"Raises monster/nut-class hand ({hand_label})",
        )

    if made_category == "VERY_STRONG":
        if BotAction.RAISE in job.legal_actions and (aggressive or pressure_ratio <= 0.45):
            return BotActionProposal(
                action=BotAction.RAISE,
                amount=size_bet(job.pot_size + call_cost, job.bot_stack, job.min_raise, job.max_raise, BetSize.MEDIUM),
                reason=f"Raises/counters pressure with very strong hand ({hand_label})",
            )
        if BotAction.CALL in job.legal_actions:
            return BotActionProposal(action=BotAction.CALL, amount=call_cost, reason=f"Calls with very strong hand ({hand_label})")

    if strong_draw and BotAction.RAISE in job.legal_actions and aggressive and draws.equity_estimate >= odds:
        return BotActionProposal(
            action=BotAction.RAISE,
            amount=size_bet(job.pot_size + call_cost, job.bot_stack, job.min_raise, job.max_raise, BetSize.MEDIUM),
            reason="Aggressive semi-bluff with strong combo/nut draw",
        )

    if made_category == "STRONG_ONE_PAIR":
        if BotAction.CALL in job.legal_actions and (pressure_ratio <= 0.45 or (heads_up and profile.looseness > 0.45)):
            return BotActionProposal(action=BotAction.CALL, amount=call_cost, reason=f"Calls manageable pressure with {hand_label}")
        return _fold_or_check(job, f"Strong one-pair hand slows down to large pressure on {texture.value.lower()} board")

    equity_estimate = max(total_strength * (0.80 + profile.looseness * 0.20), draws.equity_estimate if job.street.value != "RIVER" else 0.0)
    if multiway and made_category in {"MEDIUM", "WEAK"}:
        equity_estimate *= 0.80

    mc_equity, range_source = calculate_hero_equity(job)
    if mc_equity is not None:
        equity_estimate = max(equity_estimate, mc_equity)

    if BotAction.CALL in job.legal_actions and equity_estimate >= odds:
        equity_note = f" MC {mc_equity:.0%}" if mc_equity is not None else ""
        range_note = f" vs {range_source}" if range_source else " vs range"
        return BotActionProposal(
            action=BotAction.CALL,
            amount=call_cost,
            reason=f"Pot odds OK; equity {equity_estimate:.0%}{range_note}{equity_note}",
        )

    if passive and BotAction.CALL in job.legal_actions and made_category == "MEDIUM" and pressure_ratio <= 0.22:
        return BotActionProposal(action=BotAction.CALL, amount=call_cost, reason="Tight-passive profile controls pot")

    if job.street.value == "RIVER" and made_category in {"WEAK", "MEDIUM"}:
        return _fold_or_check(job, f"River discipline with {hand_label}; no draw equity remains")

    return _fold_or_check(job, f"Insufficient equity with {hand_label}")


def _made_category(rank: HandRank, made_strength: float, omaha: bool = False) -> str:
    bump = 0.04 if omaha else 0.0
    if rank >= HandRank.FULL_HOUSE:
        return "MONSTER"
    if rank >= HandRank.STRAIGHT or made_strength >= 0.72 + bump:
        return "VERY_STRONG"
    if rank >= HandRank.THREE_OF_A_KIND or made_strength >= 0.62 + bump:
        return "VERY_STRONG"
    if rank == HandRank.TWO_PAIR or made_strength >= 0.54 + bump:
        return "STRONG_ONE_PAIR"
    if rank == HandRank.PAIR and made_strength >= 0.48 + bump:
        return "STRONG_ONE_PAIR"
    if rank == HandRank.PAIR or made_strength >= 0.40 + bump:
        return "MEDIUM"
    return "WEAK"


def _board_danger(texture: BoardTexture, draws) -> float:
    danger = {
        BoardTexture.DRY: 0.15,
        BoardTexture.PAIRED: 0.35,
        BoardTexture.WET: 0.55,
        BoardTexture.MONOTONE: 0.70,
        BoardTexture.DANGEROUS: 0.80,
    }[texture]
    if draws.combo_draw:
        danger += 0.10
    return min(1.0, danger)


def _fold_or_check(job: BotTurnJob, reason: str) -> BotActionProposal:
    if BotAction.CHECK in job.legal_actions:
        return BotActionProposal(action=BotAction.CHECK, amount=None, reason=reason)
    if BotAction.FOLD in job.legal_actions:
        return BotActionProposal(action=BotAction.FOLD, amount=None, reason=reason)
    action = job.legal_actions[0]
    amount = None if action in {BotAction.FOLD, BotAction.CHECK} else max(0, job.current_bet - job.bot_current_bet) or job.min_raise or job.bot_stack
    return BotActionProposal(action=action, amount=amount, reason="Fallback legal action")


def random_bool(probability: float) -> bool:
    import random

    return random.random() < probability
