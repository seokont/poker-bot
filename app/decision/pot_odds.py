def call_amount(current_bet: int, bot_current_bet: int, bot_stack: int) -> int:
    return min(max(0, current_bet - bot_current_bet), bot_stack)


def calculate_pot_odds(pot_size: int, call_cost: int) -> float:
    if call_cost <= 0:
        return 0.0
    return call_cost / (pot_size + call_cost)
