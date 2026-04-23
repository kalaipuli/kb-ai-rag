# ADR-002: Azure AI Foundry for LLM and Embedding Endpoints

## Status
Accepted

## Context
The platform requires two AI model capabilities:
1. LLM inference: GPT-4o for answer generation, a cheaper model (GPT-4o-mini) for routing and grading
2. Embedding generation: text-embedding-3-large for converting document chunks and queries into dense vectors

The primary audience for this portfolio project is enterprise AI Architect roles where Azure fluency is a stated requirement. The LLM integration must support enterprise concerns: data residency, compliance, audit logging, and cost tracking — not just API convenience.

The langchain-openai package supports both raw OpenAI and Azure OpenAI via the same interface; only the connection parameters differ.

## Decision
Use Azure AI Foundry (Azure OpenAI Service) for all LLM and embedding calls. Connect via the langchain-openai AzureChatOpenAI and AzureOpenAIEmbeddings classes, which expose an OpenAI-compatible endpoint.

## Alternatives Considered

**Raw OpenAI API (api.openai.com)**: Functionally equivalent for MVP. Rejected because it does not demonstrate Azure fluency (a key portfolio objective), does not provide enterprise data residency guarantees, and the migration from raw OpenAI to Azure OpenAI is trivial (change base_url + add api_version) — so there is no technical cost to starting with Azure.

**HuggingFace local models**: Open-weight models (Llama, Mistral) running locally. Rejected because: (a) no local model matches GPT-4o generation quality for the portfolio demo, (b) the operational complexity of serving large models distracts from the RAG architecture showcase, (c) Azure OpenAI is the stated requirement for the target role.

**Ollama (local model server)**: Rejected for the same reasons as HuggingFace local models. Suitable for offline development but not for a cloud-deployed portfolio system.

**Azure AI Studio direct inference**: Considered as an alternative to Azure OpenAI Service. Not selected because Azure AI Foundry provides the Azure OpenAI Service endpoint that langchain-openai natively supports without additional integration code.

## Consequences

**Positive:**
- langchain-openai works identically against Azure OpenAI endpoints — the AzureChatOpenAI class is a drop-in replacement for ChatOpenAI with three additional parameters (azure_endpoint, azure_deployment, api_version)
- Azure data residency: all prompt and completion data stays within the selected Azure region
- SOC 2 Type II compliance inherited from Azure
- Azure Monitor and Application Insights integration available for token cost tracking and latency observability (Phase 5)
- The API key (AZURE_OPENAI_API_KEY) can be replaced with Azure Managed Identity in production (Phase 6)

**Negative:**
- Requires an Azure subscription and a separate Azure OpenAI access request (not automatic)
- Azure OpenAI API version must be pinned (AZURE_OPENAI_API_VERSION) and updated when new features are needed
- Azure quota limits apply; GPT-4o capacity may be constrained in some regions
- Adds a cloud dependency that blocks development if Azure credentials are unavailable; mitigation: the config abstraction allows substituting a mock LLM for unit tests
