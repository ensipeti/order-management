from concurrent.futures import ThreadPoolExecutor

import pytest

from order_management.order_book import OrderBook
from order_management.orders import DuplicateOrder, InsufficientLiquidity, Order, Side, UnknownOrder


def test_jpm_read_only_and_removal() -> None:
    book = OrderBook()
    book.add(Order(1, "JPM", Side.BUY, 20, 20))
    book.add(Order(4, "JPM", Side.BUY, 10, 21))
    for _ in range(3):
        assert book.calculate_price("JPM", Side.BUY, 22) == 442
        assert book.calculate_price("JPM", Side.BUY, 20) == 400
    book.remove(1)
    assert book.calculate_price("JPM", Side.BUY, 10) == 210
    with pytest.raises(InsufficientLiquidity):
        book.calculate_price("JPM", Side.BUY, 11)
    book.remove(4)
    with pytest.raises(InsufficientLiquidity):
        book.calculate_price("JPM", Side.BUY, 1)


@pytest.mark.parametrize("side,expected", [(Side.BUY, 43), (Side.SELL, 70)])
def test_equal_prices_and_priorities(side: Side, expected: int) -> None:
    book = OrderBook()
    for i, (quantity, price) in enumerate([(2, 5), (3, 5), (4, 9), (8, 10)]):
        book.add(Order(i, "X", side, quantity, price))
    assert book.calculate_price("X", side, 7) == expected
    book.remove(0)
    assert book.calculate_price("X", side, 4) == (24 if side == Side.BUY else 40)


def test_isolation_and_errors() -> None:
    book = OrderBook()
    book.add(Order(1, "A", Side.BUY, 3, 4))
    book.add(Order(2, "A", Side.SELL, 6, 7))
    book.add(Order(3, "B", Side.BUY, 9, 10))
    with pytest.raises(DuplicateOrder):
        book.add(Order(1, "B", Side.SELL, 100, 100))
    with pytest.raises(UnknownOrder):
        book.remove(999)
    with pytest.raises(InsufficientLiquidity):
        book.calculate_price("A", Side.BUY, 4)
    assert book.calculate_price("B", Side.BUY, 5) == 50
    assert book.calculate_price("A", Side.SELL, 6) == 42


def test_concurrent_readers_and_writers() -> None:
    book = OrderBook()
    book.add(Order(0, "A", Side.BUY, 100, 5))

    def update(order_id: int) -> None:
        book.add(Order(order_id, "A", Side.BUY, 1, 10))
        assert book.calculate_price("A", Side.BUY, 100) == 500
        book.remove(order_id)

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(update, range(1, 100)))
    assert book.calculate_price("A", Side.BUY, 100) == 500
    with pytest.raises(InsufficientLiquidity):
        book.calculate_price("A", Side.BUY, 101)


def test_caller_changes_do_not_modify_stored_orders() -> None:
    book = OrderBook()
    submitted = Order(1, "JPM", Side.BUY, 20, 20)
    book.add(submitted)
    submitted.order_id = 99
    submitted.symbol = "OTHER"
    submitted.side = Side.SELL
    submitted.amount = 100
    submitted.price = 99

    assert book.get(1) == Order(1, "JPM", Side.BUY, 20, 20)
    assert book.calculate_price("JPM", Side.BUY, 20) == 400

    retrieved = book.get(1)
    retrieved.order_id = 99
    retrieved.symbol = "OTHER"
    retrieved.side = Side.SELL
    retrieved.amount = 100
    retrieved.price = 99

    assert book.get(1) == Order(1, "JPM", Side.BUY, 20, 20)
    assert book.calculate_price("JPM", Side.BUY, 20) == 400
    book.remove(1)
    with pytest.raises(UnknownOrder):
        book.get(1)
    with pytest.raises(InsufficientLiquidity):
        book.calculate_price("JPM", Side.BUY, 1)


def test_zero_quantity_orders_can_be_removed() -> None:
    book = OrderBook()
    book.add(Order(1, "JPM", Side.BUY, 0, 20))
    book.add(Order(2, "JPM", Side.BUY, 0, 20))
    book.remove(1)
    book.remove(2)

    book.add(Order(3, "JPM", Side.BUY, 0, 20))
    book.add(Order(4, "JPM", Side.BUY, 5, 20))
    book.remove(3)
    assert book.calculate_price("JPM", Side.BUY, 5) == 100
    book.add(Order(5, "JPM", Side.BUY, 0, 20))
    book.remove(4)
    book.remove(5)
    assert book.calculate_price("JPM", Side.BUY, 0) == 0
    with pytest.raises(InsufficientLiquidity):
        book.calculate_price("JPM", Side.BUY, 1)
