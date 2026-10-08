import json
import random
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from order_management.order_api import create_app
from order_management.order_book import OrderBook
from order_management.orders import DuplicateOrder, InsufficientLiquidity, Order, Side

VALID_FILES = [
    "orders.csv",
    "equal_prices.csv",
    "multi_instrument.csv",
    "price_levels.csv",
    "large_quantities.csv",
]


def reference_price(orders: list[Order], symbol: str, side: Side, amount: int) -> int:
    candidates = sorted(
        (order for order in orders if order.symbol == symbol and order.side == side),
        key=lambda order: order.price,
        reverse=side == Side.SELL,
    )
    remaining, total = amount, 0
    for order in candidates:
        take = min(order.amount, remaining)
        total += take * order.price
        remaining -= take
    if remaining:
        raise InsufficientLiquidity(symbol)
    return total


@pytest.mark.parametrize("filename", VALID_FILES)
def test_every_fixture_through_api(
    filename: str, orders_from_file: Callable[[str], list[Order]]
) -> None:
    orders = orders_from_file(filename)
    random.Random(20).shuffle(orders)
    with TestClient(create_app()) as client:
        for order in orders:
            response = client.post("/orders", json=asdict(order))
            assert response.status_code == 201
            assert client.get(f"/orders/{order.order_id}").json() == response.json()
        keys = {(order.symbol, order.side) for order in orders}
        for symbol, side in keys:
            available = sum(
                order.amount for order in orders if (order.symbol, order.side) == (symbol, side)
            )
            for amount in {1, max(1, available // 2), available}:
                expected = reference_price(orders, symbol, side, amount)
                request = {"symbol": symbol, "side": side, "amount": amount}
                for _ in range(2):
                    assert client.post("/prices", json=request).json()["total_price"] == expected
            assert (
                client.post(
                    "/prices", json={"symbol": symbol, "side": side, "amount": available + 1}
                ).status_code
                == 409
            )
        for order in orders:
            assert client.delete(f"/orders/{order.order_id}").status_code == 204
            assert client.get(f"/orders/{order.order_id}").status_code == 404
        for symbol, side in keys:
            assert (
                client.post(
                    "/prices", json={"symbol": symbol, "side": side, "amount": 1}
                ).status_code
                == 409
            )


@pytest.mark.parametrize("filename", ["equal_prices.csv", "price_levels.csv"])
def test_removals_keep_remaining_prices_correct(
    filename: str, orders_from_file: Callable[[str], list[Order]]
) -> None:
    orders = orders_from_file(filename)
    book = OrderBook()
    for order in orders:
        book.add(order)
    for removed in orders[::2]:
        book.remove(removed.order_id)
    remaining = orders[1::2]
    for symbol, side in {(order.symbol, order.side) for order in remaining}:
        amount = sum(
            order.amount for order in remaining if (order.symbol, order.side) == (symbol, side)
        )
        assert book.calculate_price(symbol, side, amount) == reference_price(
            remaining, symbol, side, amount
        )


def test_empty_csv(orders_from_file: Callable[[str], list[Order]]) -> None:
    assert orders_from_file("empty.csv") == []


def test_duplicate_ids_across_instruments(orders_from_file: Callable[[str], list[Order]]) -> None:
    first, duplicate = orders_from_file("duplicate_ids.csv")
    book = OrderBook()
    book.add(first)
    with pytest.raises(DuplicateOrder):
        book.add(duplicate)
    assert book.get(first.order_id) == first


def test_symbol_case_and_sides_are_isolated(populated_book: OrderBook) -> None:
    assert populated_book.calculate_price("AAPL", Side.BUY, 10) == 1790
    assert populated_book.calculate_price("AAPL", Side.SELL, 10) == 1850
    assert populated_book.calculate_price("aapl", Side.BUY, 8) == 7992
    with pytest.raises(InsufficientLiquidity):
        populated_book.calculate_price("UNKNOWN", Side.BUY, 1)


def test_random_books_against_independent_reference() -> None:
    for seed in range(12):
        generator = random.Random(seed)
        orders = [
            Order(
                i,
                f"INSTRUMENT-{generator.randrange(6)}",
                generator.choice(list(Side)),
                generator.randint(1, 100),
                generator.randint(1, 1000),
            )
            for i in range(150)
        ]
        book = OrderBook()
        for order in orders:
            book.add(order)
        generator.shuffle(orders)
        for order in orders[:40]:
            book.remove(order.order_id)
        remaining = orders[40:]
        for symbol, side in {(order.symbol, order.side) for order in remaining}:
            available = sum(
                order.amount for order in remaining if (order.symbol, order.side) == (symbol, side)
            )
            amount = generator.randint(1, available)
            assert book.calculate_price(symbol, side, amount) == reference_price(
                remaining, symbol, side, amount
            )


PRICE_CASES = json.loads((Path(__file__).parent / "fixtures" / "price_requests.json").read_text())


@pytest.mark.parametrize("case", PRICE_CASES)
def test_documented_price_examples(
    case: dict, orders_from_file: Callable[[str], list[Order]]
) -> None:
    book = OrderBook()
    for order in orders_from_file(case["orders_file"]):
        book.add(order)
    request = case["request"]
    assert (
        book.calculate_price(request["symbol"], Side(request["side"]), request["amount"])
        == case["total_price"]
    )
