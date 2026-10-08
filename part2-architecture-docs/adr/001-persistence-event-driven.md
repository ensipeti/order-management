# ADR-001 — Order Persistence & Event Distribution

## Context

Order ingestion needs durable storage and asynchronous updates for pricing and other services.

## Decision

The Order API and Batch Ingestion Worker persist orders in PostgreSQL and publish events directly to Kafka, keyed by instrument symbol. The Order Book Service consumes these updates. Auxiliary services can subscribe through independent consumer groups for enrichment, checks, audit or analytics.

## Alternatives Considered

- Transactional outbox: stronger publication reliability, with a separate publisher.
- Service to service communication: Avoids a messaging platform, but creates tighter coupling between services and makes independent scaling more difficult.

## Rationale

PostgreSQL provides durable, queryable state. Kafka decouples consumers, supports replay and allows new services without changing ingestion.

## Trade-offs

Database persistence and Kafka publication are independent operations, introducing a risk of inconsistency if one succeeds and the other fails. Retries, idempotent processing and reconciliation are needed to manage these failures. Kafka also introduces additional infrastructure and operational overhead, while consumer lag and event retention limits can affect data freshness and replayability.
