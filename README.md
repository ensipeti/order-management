# Order Management System

A Python/FastAPI API for adding and removing orders and calculating prices. It keeps separate in-memory Buy and Sell books for each instrument. Buy quotes use the lowest prices first; Sell quotes use the highest. Quotes can span multiple orders and do not change the book.

The repository also contains a proposed cloud architecture with diagrams, decision records, Terraform and Helm configuration. That deployment has not been run; its distributed service source code and images are not included.

## Run locally

Requires Python 3.13+.

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
uvicorn order_management.order_api:app --host 127.0.0.1 --port 8000
```

Open [Swagger UI](http://127.0.0.1:8000/docs) to try the API. The local server uses one process; restarting it clears all orders. It has no authentication, so keep it bound to loopback.

## Use the API

```sh
curl -X POST http://127.0.0.1:8000/orders \
  -H 'Content-Type: application/json' \
  -d '{"order_id":1,"symbol":"ABC","side":"Buy","amount":10,"price":100}'

curl -X POST http://127.0.0.1:8000/prices \
  -H 'Content-Type: application/json' \
  -d '{"symbol":"ABC","side":"Buy","amount":5}'

curl -X DELETE http://127.0.0.1:8000/orders/1
```

`POST /orders` adds an order, `DELETE /orders/{id}` removes it, `GET /orders/{id}` retrieves it, and `POST /prices` calculates a read-only quote. Duplicate IDs and insufficient quantity return `409`; unknown order IDs return `404`. Sample CSV orders and expected-price cases are in the [test fixtures](tests/fixtures/README.md).

## Verify

```sh
pytest -q
ruff check src tests
ruff format --check src tests
mypy src/order_management
```

With the local server running, use `python tests/benchmark.py` to measure pricing. In one run with 1,000 orders and 2,000 sequential requests, p99 was **0.0655 ms** for the order-book calculation and **0.9979 ms** for the local HTTP round trip. These measurements do not include the proposed cloud infrastructure or concurrent load.

## Architecture design

The proposed deployment uses PostgreSQL for durable orders, Kafka for updates, GCS for batch files and recovery snapshots, and GKE in London and Belgium.

Diagrams: [system context](part2-architecture-docs/diagrams/c4-system-context.png), [application containers](part2-architecture-docs/diagrams/c4-container.png), [cloud deployment](part2-architecture-docs/diagrams/cloud-deployment.png), and the [editable draw.io source](part2-architecture-docs/diagrams/OMS.drawio).

Decision records: [persistence and events](part2-architecture-docs/adr/001-persistence-event-driven.md), [pricing and partitioning](part2-architecture-docs/adr/002-in-memory-pricing.md), [batch ingestion](part2-architecture-docs/adr/003-batch-ingestion.md), [API security](part2-architecture-docs/adr/004-api-security.md), and [deployment and resilience](part2-architecture-docs/adr/005-deployment-resilience.md).

The [infrastructure notes](part2-architecture-docs/infra/README.md) explain the Terraform and Helm configuration and its remaining deployment requirements.
