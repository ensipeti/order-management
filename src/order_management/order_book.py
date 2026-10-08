from bisect import insort
from copy import copy
from threading import RLock

from order_management.orders import (
    DuplicateOrder,
    InsufficientLiquidity,
    Order,
    Side,
    UnknownOrder,
)


class OrderBook:
    """Store orders by ID and sorted (price, ID) lists per symbol and side."""

    def __init__(self) -> None:
        self._orders: dict[int, Order] = {}
        self._books: dict[tuple[str, Side], list[tuple[int, int]]] = {}
        # Allow remove() to call get() while holding the lock.
        self._lock = RLock()

    def add(self, order: Order) -> None:
        """Add an order, rejecting duplicate IDs."""
        with self._lock:
            if order.order_id in self._orders:
                raise DuplicateOrder(order.order_id)
            # Prevent caller changes from affecting stored orders.
            order = copy(order)
            key = (order.symbol, order.side)
            book = self._books.setdefault(key, [])
            insort(book, (order.price, order.order_id))
            self._orders[order.order_id] = order

    def remove(self, order_id: int) -> None:
        """Remove an order and its sorted entry."""
        with self._lock:
            order = self.get(order_id)
            key = (order.symbol, order.side)
            book = self._books[key]
            book.remove((order.price, order_id))
            if not book:
                del self._books[key]
            del self._orders[order_id]

    def get(self, order_id: int) -> Order:
        """Return an order copy, or raise UnknownOrder."""
        with self._lock:
            try:
                return copy(self._orders[order_id])
            except KeyError as exc:
                raise UnknownOrder(order_id) from exc

    def calculate_price(self, symbol: str, side: Side, amount: int) -> int:
        """Return the total price without changing orders."""
        # Keep the quote consistent with concurrent updates.
        with self._lock:
            key = (symbol, side)
            book = self._books.get(key, [])
            # Buy uses lowest prices first; Sell uses highest.
            priority = book if side == Side.BUY else reversed(book)
            remaining, total = amount, 0
            for price, order_id in priority:
                order = self._orders[order_id]
                quantity = min(remaining, order.amount)
                total += quantity * price
                remaining -= quantity
                if remaining == 0:
                    return total
            if remaining:
                raise InsufficientLiquidity(f"Insufficient {side} quantity for {symbol}")
            return total
