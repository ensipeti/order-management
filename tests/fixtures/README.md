# Order fixtures

The CSV files provide order data for the tests. The test loader reads the columns `order_id,symbol,side,amount,price`, and tests add each order through the normal REST API or order book.

| File | Purpose |
| --- | --- |
| `orders/orders.csv` | Original JPM/GOOG/AMZN example, including the JPM total of 442 |
| `orders/multi_instrument.csv` | Both sides, several symbols, case sensitivity and custom instrument names |
| `orders/equal_prices.csv` | Several orders at the same price |
| `orders/price_levels.csv` | Unsorted input spanning several Buy/Sell price levels |
| `orders/large_quantities.csv` | Large integer quantities and totals |
| `orders/empty.csv` | A valid header with no orders |
| `orders/duplicate_ids.csv` | Duplicate IDs across instruments; the second order is rejected |

`price_requests.json` contains 19 request/expected-total pairs. Tests also generate books with different instruments, quantities and prices, and compare pricing against an independent reference calculation.

Run the fixture tests from the repository root:

```sh
pytest -q tests/test_order_fixtures.py
```

The fixture API tests add orders, verify prices, then remove the orders and check the remaining state. Generated order sets also compare pricing against an independent reference calculation.
