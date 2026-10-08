# ADR-002 — In-Memory Pricing & Partitioning

## Context

Pricing is the most frequent operation and needs low latency as the workload grows.

## Decision

The Order Book Service maintains sorted in-memory books by symbol and side. Buy uses the lowest prices first; Sell uses the highest. Quotes combine quantities across levels without changing orders.

Kafka partitions updates by symbol. Within each region, the instrument router sends quotes to the ready partition owner. Object-store snapshots and Kafka replay restore book state after reassignment.

## Alternatives Considered

- Database-backed pricing: less application state, but adds database work to each quote.
- Fully replicated books: simpler routing, but every instance stores and processes the whole book.

## Rationale

Pricing avoids database and broker round trips; partitioning distributes book ownership and update processing.

## Trade-offs

Reassigned partitions must recover before serving quotes. Memory, hot instruments and partition count constrain scaling. Consumer lag affects freshness, and the 5 ms target requires measurement.
