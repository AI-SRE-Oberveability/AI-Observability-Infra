# Personal Azure infrastructure plan

Status: design only. No Terraform apply, subscription discovery, Azure login or cloud deployment has run. Unknown values are in `personal-targets.example.json`. These must be matched to the user's exact personal account before any cloud operation; cached accounts are not authorization.

Terraform is the user's confirmed Azure IaC choice. Verified public repository: `AI-SRE-Oberveability/AI-Observability-Infra`; reviewed source is published under the organization; initial receipts remain in the lab evidence. Follow the lab's engineering standards for module boundaries, provider locks, protected state, checks and concrete plan review. Helm/Kubernetes manifests remain with the owning workload/observability repositories.

Bootstrap with the confirmed personal identity creates a dedicated state resource group, private Azure Blob state storage and narrowly scoped CI identity/federation. Bootstrap owns these resources; ongoing component states cannot create their own prerequisites. Record backend ownership and recovery before handing routine changes to OIDC identities.

Planned Terraform states/modules:

1. `bootstrap`: state storage/access, federated identities and scoped role assignments.
2. `platform`: tagged lab resource groups, networking, ACR, Key Vault, AKS with workload identity, cost budget notifications.
3. `managed` (gated): vendor-approved dedicated hosts, disks, DNS/TLS/connectivity, backup and supported installation automation. Keep the backend distinct from the AKS Operator/OneAgent installation.

Pin Terraform/provider versions after region and resource design selection; generate and commit provider locks from successful initialization. No invented lockfile, VM sizing or deployable Managed module is supplied here. Never place licence secrets or credentials in tfvars or plan artifacts. State can hold secrets and must be protected even when outputs are sensitive.

Deployment sequence: PR checks -> reviewed IaC plan -> authorized apply -> pinned observability configuration -> image digest rollout -> smoke/telemetry contracts -> sanitized evidence. Apply and destroy share an environment concurrency key. Fork code gets no cloud credentials. Verify actual GitHub OIDC subject configuration and plan support before creating federation or relying on environment reviewers. Choose runners that can reach private AKS/Managed endpoints; authentication alone does not provide network access.

Cost estimate worksheet (amounts intentionally unset): AKS nodes and disks; load balancer/public IP/NAT and traffic; ACR; state and Key Vault; approved model usage; Collector resources; Managed licence, approved nodes/disks, backups and retention; private runner lifecycle. Record region, currency, dated retail rates, hours, quantities and idle costs. Budget alerts are notifications, not a guaranteed spending cutoff. Do not reuse enterprise negotiated rates.

Teardown design: inventory only the dedicated lab resource IDs, review the destroy plan, retain evidence, remove workloads/monitoring, destroy dependent platform and optional Managed components, then deliberately retain or remove bootstrap/state. Stopping AKS is not a full teardown. No cloud destroy command is implemented before its exact owned scope exists.
