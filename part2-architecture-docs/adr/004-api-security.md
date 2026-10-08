# ADR-004 — API Exposure & Security

## Context

Clients need an internet-accessible API while application and data services remain private.

## Decision

A global HTTPS load balancer and WAF front regional Kong gateways. Clients obtain OAuth2 JWT access tokens from an external identity provider. Kong validates signatures and claims using its public signing keys, enforces route scopes and rate limits, then forwards requests to private FastAPI services. Order-specific access rules remain in the application.

## Alternatives Considered

- Load balancer/WAF with application token validation: fewer components, but distributed policy management.
- Managed API gateway: less gateway administration, with provider-specific capabilities and configuration.

## Rationale

A shared gateway centralises access policies; cached signing keys avoid an identity-provider call per request.

## Trade-offs

The gateway adds operational responsibility and latency. Key rotation and regional policy consistency need management. The configured Kong OIDC plugin requires an Enterprise license.
