# Repository guidelines

This repository contains a runnable, in-memory order API and a separate cloud deployment design. Follow the scope of the current task; a component in a diagram is not necessarily implemented here.

## Sources and scope

- The challenge specification defines required behaviour. The diagrams show the proposed system boundaries, and the ADRs explain the architectural choices and trade-offs. Flag conflicts rather than silently changing those decisions.
- `src/order_management/` is the local FastAPI application. It stores orders in one process and has no PostgreSQL, Kafka, batch worker or cloud runtime.
- `part2-architecture-docs/` contains diagrams, ADRs, Terraform and Helm configuration. The distributed service source and container images are not in this repository. Keep design claims separate from implemented behaviour.
- Prefer focused changes over new frameworks, services or abstractions that the current task does not need.

## Application code

- Keep order storage and price calculation independent of FastAPI. Use Pydantic models at the HTTP boundary and plain domain objects inside the order book.
- Preserve unique order IDs, separate books by symbol and side, lowest-price-first Buy quotes, highest-price-first Sell quotes, and read-only price calculations. Keep concurrent reads and updates consistent.
- Use clear names, type annotations and small functions. Avoid needless duplication, speculative validation and unnecessary layers.
- Comment non-obvious rules or invariants briefly and objectively. Do not narrate obvious statements or refer to the challenge prompt in code comments.
- Keep dependencies pinned and credentials out of code and logs.

## Tests and verification

- Cover behaviour through public methods and API responses. Keep tests fast and deterministic; avoid assertions about private storage details or duplicate scenario suites.
- CSV files under `tests/fixtures/` are test inputs, not a batch-ingestion feature of the local application. Keep representative examples and an independent pricing reference for broader cases.
- Run `pytest -q`, `ruff check src tests`, `ruff format --check src tests` and `mypy src/order_management` for Python changes. For documentation-only changes, check links and `git diff --check`.
- `tests/benchmark.py` measures one local process and HTTP client. State the workload and measured path; do not present its results as proof of cloud latency or availability.

## Architecture documentation and infrastructure

- Keep Terraform, Helm, diagrams and ADRs consistent with the proposed London/Belgium deployment. ADRs should remain concise and explain decisions, alternatives and limitations.
- The design uses independent PostgreSQL and Kafka writes, asynchronous regional replication and controlled writer failover. Do not imply atomic publication, automatic cross-region write failover or zero data loss without an implemented and tested mechanism.
- Keep cloud credentials out of the repository and use example values or secret references. Do not provision or deploy cloud resources unless the task explicitly requests it; static validation is permitted.
- Do not claim zero-downtime updates, regional recovery or the 5 ms API target has been demonstrated by configuration alone. Update documentation when a design changes, and change the supplied diagrams only when explicitly requested.
