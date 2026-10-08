import csv
from collections.abc import Callable
from pathlib import Path

import pytest

from order_management.order_book import OrderBook
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


@pytest.fixture
def populated_book(orders_from_file: Callable[[str], list[Order]]) -> OrderBook:
    book = OrderBook()
    for order in orders_from_file("multi_instrument.csv"):
        book.add(order)
    return book
