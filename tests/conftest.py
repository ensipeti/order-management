import csv
from collections.abc import Callable
from pathlib import Path

import pytest

from order_management.orders import Order, Side

FIXTURES = Path(__file__).parent / "fixtures" / "orders"


@pytest.fixture
def orders_from_file() -> Callable[[str], list[Order]]:
    def load(name: str) -> list[Order]:
        with (FIXTURES / name).open(encoding="utf-8") as source:
            return [
                Order(
                    order_id=int(row["order_id"]),
                    symbol=row["symbol"],
                    side=Side(row["side"]),
                    amount=int(row["amount"]),
                    price=int(row["price"]),
                )
                for row in csv.DictReader(source)
            ]

    return load
