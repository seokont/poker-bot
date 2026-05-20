from enum import StrEnum


class BetSize(StrEnum):
    SMALL = "SMALL"
    MEDIUM = "MEDIUM"
    LARGE = "LARGE"


def size_bet(pot_size: int, stack: int, min_raise: int | None, max_raise: int | None, size: BetSize) -> int:
    fraction = {
        BetSize.SMALL: 0.35,
        BetSize.MEDIUM: 0.60,
        BetSize.LARGE: 0.90,
    }[size]
    amount = max(1, round(pot_size * fraction))
    if min_raise is not None:
        amount = max(amount, min_raise)
    amount = min(amount, stack)
    if max_raise is not None:
        amount = min(amount, max_raise)
    return max(0, amount)


def all_in_amount(stack: int, max_raise: int | None = None) -> int:
    if max_raise is None:
        return stack
    return min(stack, max_raise)
