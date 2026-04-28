# ADR-010: Tavily as Web Search Fallback for CRAG

## Status
Accepted

## Context
The CRAG pattern (ADR-004) requires a web search fallback when the Grader node determines all retrieved chunks score below `GRADER_THRESHOLD = 0.5`. The platform needed a web search service that supports async-compatible usage, returns structured results containing URL and content, requires only a simple API key with no Azure SDK dependency, and is purpose-built for LLM-augmented retrieval. The fallback is invoked exclusively on the Grader→Retriever corrective path when `retrieval_strategy == "web"` is written into `AgentState`; all other retrievals bypass it entirely.

## Decision
Use Tavily via the `tavily-python` package as the web search fallback in the Retriever node. A `TavilyClient` instance is constructed once in the graph builder using the lifespan singleton pattern and injected into the Retriever node via closure, avoiding per-request client construction overhead. Because `TavilyClient.search()` is synchronous, all calls are dispatched with `asyncio.to_thread()` to avoid blocking the event loop. `TAVILY_API_KEY` is stored as `SecretStr` in the `Settings` model; `.get_secret_value()` is called only at client construction in the builder, never inside node functions. Web-sourced results are flagged by the `web_fallback_used: bool` field in `AgentState`, which downstream nodes use to distinguish them from local retrieval results.

## Alternatives Considered

**Bing Search API (Azure Cognitive Search):** Stays within the Azure trust boundary but requires provisioning an additional Azure resource, a separate SDK, and carries higher per-query cost at low query volumes. Tavily's API is simpler to integrate and is purpose-built for RAG use cases, making it the lower-friction choice for this phase.

**SerpAPI:** Offers broader search engine coverage but at significantly higher cost and with results that require additional post-processing to extract content suitable for the LLM context. Tavily returns pre-extracted content fields directly, reducing the retrieval-to-generation pipeline complexity.

**No web fallback:** Accept low-confidence local-only answers when retrieval fails. Rejected because the CRAG pattern (ADR-004) explicitly requires a corrective path; without a fallback, the graph would proceed to the Generator with chunks that the Grader already scored as irrelevant, undermining answer quality guarantees.

**LangChain `TavilySearchResults` tool:** The LangChain wrapper introduces abstraction overhead and makes the result schema opaque to callers. Direct `tavily-python` usage keeps the result structure explicit, making it straightforward to test and to map fields into the canonical `Document` schema.

## Consequences

Queries that trigger CRAG will send query text to Tavily's servers outside the Azure trust boundary; these queries may be logged by Tavily per their privacy policy, which must be disclosed to end users. `TAVILY_API_KEY` is a new required secret that must be added to `.env`, `.env.example`, and Azure Key Vault before deploying the CRAG path. Tavily imposes rate limits and per-query costs; high-traffic deployments must account for these in capacity planning and may need to implement a circuit breaker or query budget. Web results pass through the same Grader → Generator → Critic quality pipeline as local results, so the hallucination and relevance gates remain active regardless of retrieval source. The `web_fallback_used` flag in `AgentState` is the authoritative signal for any future telemetry, evaluation, or routing logic that needs to distinguish web-sourced from locally-sourced answers.
