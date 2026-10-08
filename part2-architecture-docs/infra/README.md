# Part 2: deployment configuration

Terraform and Helm describe the two-region architecture shown in the diagrams. These files are configuration only: no cloud resources have been deployed, and the Part 2 services have no source code in this repository.

## Layout

```text
terraform/
  main.tf                  VPC, regional GKE, PostgreSQL and object storage
  edge.tf                  HTTPS load balancer, WAF and gateway backends
  runtime.tf               Service accounts, IAM database users and Secret Manager
  variables.tf             Project, DNS and gateway inputs
  outputs.tf               Connection names, buckets, identities and public address
  production.example.tfvars
helm/
  platform/                Strimzi and KEDA operator dependencies
  order-management/        Application workloads, Kong, Kafka and replication
    values/london.yaml
    values/belgium.yaml
    values/batch.example.yaml
    values/secrets.example.yaml
```

## Diagram coverage

| Diagram component | Configuration |
| --- | --- |
| Global HTTPS load balancer and WAF | Terraform managed certificate, global backend service and Cloud Armor |
| London and Belgium regional multi-zone GKE | One shared VPC; separate regional subnets, NAT and private GKE clusters |
| Order API and instrument router | Two containers in the same Deployment/pod, with separate internal Service ports |
| Partitioned Order Book Service | Separate Deployment and headless discovery Service; regional Kafka consumer group |
| Batch worker | Optional Kubernetes Job with object URI, unique run ID, retries and deadline |
| Regional Kong gateways | Pinned official chart; JWT signature/audience checks, read/write scopes, rate limiting and rolling updates |
| Independent Kafka clusters | Three brokers per region, TLS users/ACLs, 12 partitions and replication factor three |
| Event replication | MirrorMaker 2 in Belgium reads London and publishes the local `orders.v1` topic |
| PostgreSQL | London authoritative writer and Belgium asynchronous cross-region replica |
| Regional object storage | Private GCS buckets; batch-read and snapshot-write IAM |
| Scaling and resilience | API/gateway HPA; book KEDA; probes, spread constraints, PDBs and graceful shutdown windows |

One application chart is reused in both regions. Kong is a dependency of that chart; Strimzi and KEDA are dependencies of the platform chart.

## Image and configuration inputs

Replace the example `registry.example.com` image references with separately supplied **Part 2** images for the API, router, book service and batch worker. The Part 1 in-memory API is not a distributed service image and must not be substituted for all those workloads.

The deployment image contracts are:

- API: serve order writes/status on port 8000; persist to the configured PostgreSQL writer and publish to the configured writer Kafka cluster. `/health` and `/health/ready` report serving readiness; `/health/live` reports liveness.
- Router: serve pricing on port 8001; discover book pods through `BOOK_DISCOVERY_ADDRESS` and route to their current ready partition owner. Discovery must not treat a recovering pod as a ready partition owner.
- Book: serve internal pricing/ownership on port 8000; consume its regional group; restore snapshots and replay before readiness. Shutdown must revoke ownership and preserve recoverable offsets/state.
- Batch: read `ORDER_FILE_URI` and use the same durable command behaviour as the API. Progress/idempotency must make Job retries safe.

These contracts describe what the external images must implement; Helm probes and environment variables do not implement those behaviours. The chart uses native sidecar init containers for the Cloud SQL Auth Proxy, allowing the batch Job to finish when its worker exits.

Set project/service-account names, database IAM usernames, bucket names, image versions and identity-provider discovery/audience/scopes from your environment. Terraform outputs provide the cloud resource values. Create the `oms` namespace in each cluster and run the platform operators in a separate namespace that watches it. Review the pinned Strimzi/KEDA versions against the selected GKE release; static rendering was checked with Kubernetes 1.33.0.

## Regional writes and recovery

Both regional API/batch workloads connect to the London PostgreSQL instance through a private Cloud SQL Auth Proxy with IAM authentication. Both publish to London Kafka while London is the writer. Belgium's `writer.kafkaBootstrapServers` and replication source address must be replaced with London's private Kafka bootstrap Service address; the sample IP is illustrative.

Each region has independent book ownership and Kafka consumer offsets. MirrorMaker preserves topic names and partition numbers; offsets and snapshots remain local to each cluster. It does not synchronise consumer groups or ACLs. Asynchronous replication can lag and lose recent events during failure.

Controlled writer failover requires fencing the old writer, assessing replication gaps, promoting the replica, and changing both writer connections and replication direction. The replication source/target aliases and TLS references are configurable. Avoid two simultaneous writers or mirroring the same topic in a loop. Availability, replay and failover have not been tested in the cloud.

API/router and gateway Deployments use HPA. KEDA manages the book Deployment, capped at 12 replicas for 12 partitions. A Helm render fails if that cap exceeds the partition count. HPA and KEDA do not target the same workload.

## Secrets, networking and provisioning order

Kong OIDC requires an Enterprise license referenced by the Kubernetes Secret `kong-enterprise-license` and a reachable external identity provider. Strimzi generates regional TLS user Secrets. Copy London's CA/writer/mirror credentials securely into the Belgium namespace using the names in its values file. No secret values are committed.

Terraform creates regional Secret Manager secret containers and access grants without adding secret versions. `values/secrets.example.yaml` demonstrates optional file mounts through the GKE Secret Manager add-on. Supply versions separately. The license and cross-region Kafka Kubernetes Secrets must also be supplied separately; CSI mounts do not automatically synchronise them.

Application Services remain ClusterIP/headless. Network policies limit API ingress to Kong and book ingress to API/router pods, with explicit DNS, Kafka, SQL, HTTPS and workload-identity egress. Kafka's cross-region listener uses private load balancers restricted to the two cluster address ranges.

GKE control-plane endpoints are private, so administration requires VPC access. The provisioning sequence is regional cloud resources, operators, regional workload/gateway configuration, then global ingress. Terraform's edge data sources require the six standalone Kong NEGs to exist before resolving them; the Helm regional values use the same NEG names as the Terraform example. DNS must point at the HTTPS address before its certificate can activate.

The supplied production service images must provide their database schema/migrations and SQL grants. Terraform creates the database and IAM users; it does not define application tables. Cloud SQL deletion protection, private connectivity, backups and point-in-time recovery are configured.

## Validation without deployment

From the repository root:

```sh
terraform -chdir=part2-architecture-docs/infra/terraform fmt -check
terraform -chdir=part2-architecture-docs/infra/terraform init -backend=false
terraform -chdir=part2-architecture-docs/infra/terraform validate

helm dependency build part2-architecture-docs/infra/helm/platform
helm dependency build part2-architecture-docs/infra/helm/order-management
helm lint part2-architecture-docs/infra/helm/platform --strict
helm lint part2-architecture-docs/infra/helm/order-management --strict

helm template platform part2-architecture-docs/infra/helm/platform --namespace platform --include-crds
helm template oms part2-architecture-docs/infra/helm/order-management --namespace oms \
  -f part2-architecture-docs/infra/helm/order-management/values/london.yaml
helm template oms part2-architecture-docs/infra/helm/order-management --namespace oms \
  -f part2-architecture-docs/infra/helm/order-management/values/belgium.yaml \
  -f part2-architecture-docs/infra/helm/order-management/values/batch.example.yaml
```

Use a different `batch.runId` for each new file import. The batch Job is disabled unless explicitly enabled through values. Downloaded chart archives are ignored; dependency locks are committed.

These commands check Terraform configuration and render the Helm charts. They do not verify the missing service images, TLS material, IAM runtime access, replication, regional failover or the 5 ms latency target. No cloud resources have been deployed.

References: [GKE standalone NEGs](https://docs.cloud.google.com/kubernetes-engine/docs/how-to/standalone-neg), [Strimzi configuration](https://strimzi.io/docs/operators/0.47.0/configuring), [Kong OIDC](https://developer.konghq.com/plugins/openid-connect/), [KEDA Kafka scaling](https://keda.sh/docs/2.18/scalers/apache-kafka/).
