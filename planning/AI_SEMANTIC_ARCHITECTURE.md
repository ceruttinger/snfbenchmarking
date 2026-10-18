# Evidence Lab: semantic analytics, provider identity and relationship graph

The draft keeps numeric computation in a deterministic, read-only semantic engine. A Bedrock model translates language into an allowlisted JSON query. It never generates executable SQL, calculates reported values, or supplies unsupported ownership claims. The response exposes the plan, source URLs, snapshot timestamps, report periods, coverage, catalog version and checksums.

## Implemented semantic contract

`docs/hospitals/lab/semantic.json` defines 14 metrics, 29 physical field mappings, 2017–2024 coverage, grain (CCN × CMS source dataset), report-selection policy, scope, missing-value rules, units, peer eligibility and aggregation. `metadata.json` includes the publisher, source dictionary link, source years and refresh/provenance metadata. `ai/build_semantics.py` rebuilds these from the ingestion contract and retained snapshots. Ownership/enrollment metadata is included when the derived provider layer is available.

Queries support one to three measures; target-versus-peer trends, endpoint comparison, market ranking, definitions, coverage and current organizational disclosures. Fixed, dynamic and balanced peers have the same meaning as in the dashboard. Market rankings include the target when it matches; peer benchmarks exclude the target. Numeric compound conditions use explicit value/change basis and fraction units for percentages. All geography must have a matching scope. Unsupported input fails closed. No arbitrary code, SQL, URLs, database tools or writes are exposed to the model.

The planner uses deterministic business-intent rules for explicit fixed/reselected peers, historical comparisons and improvement ordering. These rules are visible in interpretation notes. The initial 11-case gate tests the intended query, not prose fluency. It is a prototype gate, not a guarantee of correctness for all new language. Users can inspect the parsed query. Add a larger independently authored holdout set and human-reviewed failure samples before treating the chatbot as production decision support.

## Provider and ownership layers

CMS Hospital Enrollments provides exact enrollment-ID / CCN / NPI / associate-ID crosswalks. CMS Hospital All Owners provides source-reported organizational ownership interests and control roles, joined on enrollment ID. Published derived data omits individual-owner records and home addresses. The first ingestion retained 5,962 hospital CCNs and 16,044 organizational disclosures. Financial and ownership snapshots have different vintages.

Source-reported interests are distinct from audited ownership, control, legal registrant identity and ultimate health-system parent. Association dates have no inferred termination dates. Current disclosures must not be applied across 2017–2024 as ownership history. Matching names or addresses alone never produces a verified ownership edge. If we add candidate links, store them as `INFERRED_AFFILIATION` with evidence features, a calibrated score, model/rule version, review status and explicit separation from source-reported edges.

NPPES v2.1 enrichment looks up exact CMS-reported NPIs and retains organization (NPI-2) identity, taxonomy, update date and business locality. NPI-1 records are not published by this prototype. It does not bulk ingest all NPPES records. Lookups are bounded and cached within each runtime; UI reports the lookup limit and partial failures.

The Medicare Fee-for-Service Public Provider Enrollment API is queried on exact PECOS associate ID to discover organizational enrollments across provider categories. It is a provider-identity/enrollment layer, not a substitute for missing HCRIS financial APIs and not proof of clinician employment. Per-associate results are bounded to 200 records and explicitly marked if potentially truncated. A shared disclosed associate is not automatically an ultimate common parent.

## AI components to use

1. **Schema-constrained semantic planner:** implemented with Bedrock; select model by interpretation evaluations. Smaller models failed fixed-peer/ranking-direction tests. The deployed candidate is the model recorded in the evaluation artifact.
2. **Metadata retrieval:** implemented as a compact authoritative catalog in the planner context. Search metric definitions, units and source lineage directly. Add document retrieval for CMS instructions/RAND codebooks as the corpus grows; citations and document version must accompany retrieved passages. Embeddings are for documentation discovery, never numeric truth.
3. **Entity resolution and evidence review:** exact CCN/enrollment/NPI/associate joins first. Add probabilistic candidates with manual review only where identifiers are absent. Keep legal-entity identity and ownership assertions separate.
4. **Graph-assisted retrieval:** use reviewed parameterized Neo4j queries for organizational relationships and category reach. Do not let a public chatbot execute unrestricted generated Cypher. Historical ownership analysis needs dated edges.
5. **Data-quality and change detection:** extend existing schema, duplicate-report, denominator, missing-value and temporal checks with distribution shifts and restatement detection. Flags support investigation; they are not assertions of fraud or poor quality.
6. **Evidence-bound narratives:** current answers and numbers are rendered from validated results. Later executive summaries should cite immutable result IDs and verify every numeric assertion against the result object.
7. **Evaluation and monitoring:** model/semantic/snapshot versions, query latency, failure categories, aggregate usage and controlled regression sets. Avoid logging full user prompts by default. Add human feedback and independently reviewed holdout cases.

Fine-tuning and a large vector database are not prerequisites for this draft. A multi-agent reasoning system would add failure modes before basic semantic interpretation is reliable. Forecasting and causal acquisition analysis should wait for validated outcomes, temporal identity resolution, sufficient data and explicit study designs.

## AWS deployment

`infra/hcris-draft.json` creates an isolated draft stack: private encrypted S3, CloudFront origin access control, API Gateway HTTP API, Python Lambda, a role limited to the selected Bedrock model and the quota table, seven-day operational logs and DynamoDB counters. No production DNS changes are made. The service has a global cap of 50 AI requests and 2,000 API requests per UTC day, plus API throttling. This is a prototype abuse/cost limit, not an authenticated user entitlement system. A malicious user can exhaust the shared allowance; add authentication, per-user quotas, WAF and account-level budgets for a broader launch.

No API key or AWS credential is shipped to a browser. CMS API financial responses remain in memory; only derived caches are retained. Neo4j deployment is a separate final phase after the application and GitHub integration pass verification. Existing benchmark routes remain available.

## Validation

Run `python ai/test_analytics.py`, `node hospitals/test_metrics.cjs`, `node hospitals/test_history.cjs`, and `python hospitals/test_api.py`. Semantic formulas were cross-checked against 2,016 observations from the existing JavaScript engine. Run live `ai/eval_planner.py` only with an authorized model/budget; it writes its result under ignored `infra/build/`. All package and snapshot hashes are retained. Browser QA must include a compound question, ambiguity, source metadata and NPPES/ownership inspection.
