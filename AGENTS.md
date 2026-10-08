# Repository Guidelines

This file defines standing conventions for contributors and coding agents working on the Order Management System (OMS). It is not a delivery plan or task specification. Follow the scope of the current task while maintaining the standards below.

## Sources of truth

- Follow the functional specification for required behaviour and the final System Context, Container and Cloud Deployment diagrams for architectural boundaries.
- Use the architecture decision records (ADRs) for the rationale and trade-offs behind those boundaries.
- Keep code, documentation, configuration and diagrams consistent. If sources conflict or a significant decision is missing, flag it rather than silently changing the architecture.
- Do not introduce additional services, frameworks or patterns merely to make the solution appear more sophisticated.

## Engineering principles

- Prefer the simplest maintainable implementation that satisfies the requirement. Avoid speculative features and premature abstractions.
- Follow **DRY**, **KISS** and separation of concerns. Share domain logic between REST ingestion and batch processing; do not duplicate pricing algorithms, persistence rules or event schemas.
- Keep the core order-book model and pricing algorithm independent of FastAPI, PostgreSQL, Kafka and cloud SDKs.
- Use descriptive names, small cohesive functions and explicit interfaces where they improve clarity. Prefer composition over elaborate inheritance hierarchies.
- Keep the implementation proportionate to the problem: straightforward functions, classes and data structures are preferable to generic frameworks, extra layers or abstractions with only one use case.
- Prefer code that explains itself through names, types and structure. Introduce an abstraction only when it simplifies real duplication, isolates an external dependency or clarifies a meaningful boundary.
- Preserve existing project conventions when editing. Make focused changes and avoid unrelated refactoring.
- Treat correctness, reliability and testability as more important than adding technology or features.

## Documentation and comments in code

- Write comments and docstrings in a professional, objective engineering style. Explain non-obvious business rules, invariants, concurrency or ordering constraints, important trade-offs, and surprising implementation choices.
- Do not narrate obvious code, repeat function names, or add boilerplate explanations at the start of each file, class or function. Prefer expressive naming over comments that merely describe what the next statement does.
- Use concise docstrings where they clarify a public contract, parameters, return values, failure behaviour or important side effects. Internal helpers do not need docstrings when their purpose is already clear.
- Keep comments accurate as the implementation changes. Avoid promotional language, tutorial-style narration, and any references to task prompts, instructions, or how the code was produced.
- Write clear, idiomatic code rather than introducing complexity to demonstrate particular patterns. Comments are not a substitute for understandable design.

## Python conventions

- Use modern Python with type annotations, PEP 8 formatting and consistent imports.
- Use Pydantic for API contracts and typed settings; keep HTTP request/response models separate from domain models where appropriate.
- Use clear exception types and predictable API error responses. Do not silently swallow failures.
- Use structured logging with correlation/request IDs. Never log credentials, access tokens or other secrets.
- Set explicit timeouts and bounded retries for external operations; make shutdown and cancellation safe.
- Prefer well-maintained libraries and a small dependency footprint. Pin dependencies and provide reproducible development tooling.

## Architecture boundaries

- **Order API:** Python/FastAPI handles order submission, removal and status. It persists orders in PostgreSQL and publishes order events directly to Kafka, as represented in the final Container diagram.
- **Order-book service:** Maintains sorted buy/sell order books in memory and handles price calculations. Pricing must not synchronously query PostgreSQL or Kafka.
- **Instrument router:** Routes pricing requests to the ready instance that owns the relevant instrument partition.
- **Kafka:** Order events are keyed by instrument symbol. Consumers must tolerate redelivery; partition ownership, recovery and readiness must be handled deliberately.
- **Batch worker:** Reads files from object storage and uses the same domain, persistence and event-publication behaviour as REST ingestion.
- **Object storage:** Holds batch input and order-book snapshots used for recovery, together with sufficient metadata to resume event replay safely.
- **API edge:** Internet access is mediated by HTTPS load balancing, a WAF and an API gateway with token validation and authorisation. Internal application services are not exposed directly.

PostgreSQL and Kafka writes are independent operations, not an atomic transaction. Keep failure handling, retries, idempotency and reconciliation explicit; never report guarantees the implementation cannot provide. Preserve the functional specification's buy/sell price priority and read-only calculation semantics.

## Infrastructure and configuration

- Terraform is the source of truth for cloud infrastructure; Helm/Kubernetes manifests describe application deployment.
- The target topology is **two GCP regions: London (`europe-west2`) and Belgium (`europe-west1`)**. Keep regional configuration parameterised and use reusable modules rather than copied infrastructure definitions.
- Represent regional multi-zone GKE, independent Kafka clusters and cross-region event replication, PostgreSQL primary/replica with controlled writer failover, object storage, global ingress/security and autoscaling consistently with the deployment diagram.
- Use HPA/KEDA where appropriate. Configure health/readiness probes, graceful shutdown, rolling updates and suitable replica placement.
- Apply least-privilege IAM and network permissions. Keep credentials and secrets out of source control and Terraform defaults; use secret references and example configuration instead.
- **Do not provision or deploy cloud resources unless explicitly authorised.** Never run `terraform apply`, `terraform destroy`, Helm install/upgrade or other mutating cloud commands on your own initiative. Static validation and local tests are permitted.
- Do not claim multi-region failover, zero downtime or a latency target has been demonstrated merely because its configuration exists.

## Testing and performance

- Add or update tests alongside behaviour changes. Keep domain tests fast and deterministic; use integration tests for PostgreSQL, Kafka, API and batch boundaries.
- Cover order insertion/removal, equal price levels, correct buy/sell ordering, multi-level pricing, insufficient volume, repeated read-only calculations and concurrent updates.
- Cover event duplicates, partial failures, replay, snapshot restoration and ownership readiness where those behaviours are implemented.
- Mock external infrastructure in unit tests; use containers or isolated test infrastructure for integration tests. Avoid dependencies on a live cloud account for routine verification.
- Treat **5 ms p99 server-side pricing latency** as a measurement target, not a presumed guarantee. Record test conditions and precisely which hops a benchmark includes.
- Run the relevant formatter, linter, type checker, tests and infrastructure validation before considering a change complete. Report checks that could not be run.

## Documentation and change discipline

- Keep the README focused on setup, architecture, API usage, verification and operational assumptions. Document what is implemented separately from what is only designed.
- Maintain five focused ADRs under `part2-architecture-docs/adr/` covering: (1) persistence and event-driven architecture, (2) in-memory pricing and partitioning, (3) batch ingestion, (4) API exposure and security, and (5) deployment, scalability and resilience.
- ADRs should explain context, decision, alternatives and trade-offs concisely; favour architectural approaches over product-versus-product comparisons.
- Update relevant tests and documentation when modifying contracts, event schemas, deployment configuration or architectural behaviour.
- Do not change final architecture diagrams without explicit direction. If a necessary implementation detail differs, surface the discrepancy for review.
- Be transparent about unverified assumptions, known limitations and remaining risks; do not mark unfinished functionality as complete.
