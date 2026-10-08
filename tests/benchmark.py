"""Run against a fresh local API: python tests/benchmark.py."""

import argparse
import json
import math
import platform
import time

import httpx

from order_management.order_book import OrderBook
from order_management.orders import Order, Side


def percentiles(samples: list[float]) -> dict[str, float]:
    samples.sort()
    return {
        f"p{p}_ms": round(samples[math.ceil(len(samples) * p / 100) - 1], 4) for p in [50, 95, 99]
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--samples", type=int, default=2000)
    args = parser.parse_args()
    book = OrderBook()
    symbol = f"BENCH-{time.time_ns()}"
    orders = [Order(i, symbol, Side.BUY, 100, 10 + i % 100) for i in range(1000)]
    for order in orders:
        book.add(order)
    domain_times: list[float] = []
    for _ in range(args.samples):
        start = time.perf_counter_ns()
        assert book.calculate_price(symbol, Side.BUY, 100_000) == 5_950_000
        domain_times.append((time.perf_counter_ns() - start) / 1_000_000)

    api_times: list[float] = []
    # A unique ID range allows repeat runs without clearing another user's orders.
    first_id = time.time_ns()
    with httpx.Client(base_url=args.url, timeout=5, trust_env=False) as client:
        for order in orders:
            client.post(
                "/orders",
                json={
                    "order_id": first_id + order.order_id,
                    "symbol": symbol,
                    "side": "Buy",
                    "amount": order.amount,
                    "price": order.price,
                },
            ).raise_for_status()
        request = {"symbol": symbol, "side": "Buy", "amount": 100_000}
        for _ in range(100):
            client.post("/prices", json=request).raise_for_status()
        for _ in range(args.samples):
            start = time.perf_counter_ns()
            response = client.post("/prices", json=request)
            elapsed = (time.perf_counter_ns() - start) / 1_000_000
            response.raise_for_status()
            assert response.json()["total_price"] == 5_950_000
            api_times.append(elapsed)
        for order in orders:
            client.delete(f"/orders/{first_id + order.order_id}").raise_for_status()
    print(
        json.dumps(
            {
                "environment": (
                    f"Python {platform.python_version()}, {platform.system()} {platform.machine()}"
                ),
                "orders": 1000,
                "price_levels": 100,
                "requested_amount": 100_000,
                "samples": args.samples,
                "concurrency": 1,
                "domain": percentiles(domain_times),
                "http_round_trip": percentiles(api_times),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
