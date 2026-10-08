from dataclasses import dataclass
from enum import StrEnum


class Side(StrEnum):
    BUY = "Buy"
    SELL = "Sell"


@dataclass
class Order:
    """Order details, with quantity and unit price represented as integers."""

    order_id: int
    symbol: str
    side: Side
    amount: int
    price: int


class DuplicateOrder(Exception):
    pass


class UnknownOrder(Exception):
    pass


class InsufficientLiquidity(Exception):
    pass
