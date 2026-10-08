# ADR-003 — Batch Order Ingestion

## Context

Orders arrive as files in object storage as well as through REST submissions.

## Decision

A Python Batch Ingestion Worker runs as a Kubernetes Job, reads files from Google Cloud Storage and processes them in chunks. It follows the same write path as the Order API: persist to PostgreSQL and publish events directly to Kafka.

## Alternatives Considered

- Long-running notification-driven worker: suits continuous arrivals, but requires persistent worker capacity and queue management.
- Managed batch service: reduces execution management, but adds integration work for shared order-processing logic.

## Rationale

Jobs isolate bulk workloads from online requests and provide resources, retries and completion status for each import.

## Trade-offs

Partial imports require progress tracking and duplicate-safe retries. Database and event writes have the consistency limitations described in ADR-001. Startup overhead and batch throughput must be managed.
