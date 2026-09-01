from decimal import Decimal, ROUND_HALF_EVEN
from typing import Iterable


MONEY_QUANTUM = Decimal("0.01")


def money(value: object) -> Decimal:
    """Convert through text so binary floating-point never enters finance logic."""

    return Decimal(str(value)).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_EVEN)


def money_sum(values: Iterable[Decimal]) -> Decimal:
    return sum((money(value) for value in values), Decimal("0.00"))
