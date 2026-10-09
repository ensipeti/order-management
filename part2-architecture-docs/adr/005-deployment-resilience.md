# ADR-005 — Deployment, Scalability & Resilience

## Context

The OMS needs continuous availability, demand-based scaling and zero-downtime updates.

## Decision

Run multi-zone GKE clusters in London (`europe-west2`) and Belgium (`europe-west1`), with active API/router pods, partitioned book services, batch Jobs, regional Kafka and GCS. Global ingress routes traffic to regional gateways; both regions serve local pricing.

London hosts the PostgreSQL primary; Belgium holds an asynchronous replica. Orders from either region persist to the London PostgreSQL primary, while Kafka events are published locally and replicated between both regions. Use HPA/KEDA, readiness checks, graceful shutdown and rolling deployments. Terraform and Helm define the infrastructure.

## Alternatives Considered

- Single multi-zone region: simpler and cheaper, but provides no regional failover option.
- Active-passive regions: simpler coordination, but less use of secondary capacity.
- Independent regional writers: better local write availability, but requires conflict resolution.

## Rationale

Regional serving and multi-zone placement reduce reliance on individual regions, zones and nodes. One writer avoids conflicting updates; replication supports recovery.

## Trade-offs

Two regions increase cost and complexity. Replication can lag or lose recent writes. Writer failover requires fencing and controlled promotion; partition recovery can interrupt pricing. Zero downtime, freshness and latency require testing.
