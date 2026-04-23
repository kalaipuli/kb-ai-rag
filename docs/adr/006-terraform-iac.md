# ADR-006: Terraform for Infrastructure as Code

## Status
Accepted

## Context
Phase 7 requires provisioning and managing Azure infrastructure — Container Apps environment, Azure Container Registry, Key Vault, Service Bus, and App Insights — in a repeatable, version-controlled way. Two credible options exist for Azure IaC: Terraform (HashiCorp) and Bicep (Microsoft-native ARM DSL). A choice must be made before Phase 7 work begins.

## Decision
Use **Terraform** (`infra/terraform/`) as the IaC tool for all Azure infrastructure. Bicep will not be used.

## Alternatives Considered

**Bicep**
Microsoft's native ARM DSL, compiled to ARM templates. Tight Azure integration, no state file to manage, first-class Azure Portal support. Rejected because it is Azure-only — it cannot manage non-Azure resources (GitHub repo settings, DNS providers, monitoring SaaS), limits future portability, and is a narrower portfolio signal than a cloud-agnostic tool.

**Pulumi**
General-purpose IaC using real programming languages (Python, TypeScript). Richer abstractions and testability than Terraform HCL. Rejected because the ecosystem is smaller, the Azure provider lags Terraform's, and the additional language runtime adds operational complexity with no material gain for this project's scope.

**ARM Templates (raw JSON)**
The underlying format Bicep compiles to. Verbose, no type safety, no DRY primitives. Rejected immediately.

## Consequences

**Easier:**
- Single tool manages Azure resources, GitHub Actions OIDC trust, and any future non-Azure resources (e.g., Cloudflare DNS, Datadog).
- `terraform plan` provides an explicit diff before every apply — strong safety for a portfolio project where there is no separate staging/ops team.
- Remote state stored in Azure Blob Storage with state locking; safe for CI/CD pipelines.
- Large community: modules for every Azure resource on the Terraform Registry.
- Demonstrates cloud-agnostic IaC competency, which is a stronger portfolio signal than Azure-only tooling.

**Harder:**
- Terraform state must be bootstrapped (a storage account + container must exist before `terraform init`). A one-time `bootstrap/` script handles this.
- HCL is not a full programming language; complex logic requires workarounds. Not a concern for this project's infra scope.

**New file layout:**
```
infra/
├── docker-compose.yml        (unchanged — local dev)
└── terraform/
    ├── main.tf               # provider config, backend
    ├── variables.tf
    ├── outputs.tf
    ├── modules/
    │   ├── container_apps/
    │   ├── acr/
    │   ├── keyvault/
    │   └── servicebus/
    └── environments/
        ├── dev.tfvars
        └── prod.tfvars
```
