# AWS Neo4j inspection graph

The final phase deploys Neo4j Community in Docker on an AWS EC2 `t3.medium` (4 GB) with a 20 GB encrypted volume. No inbound ports are allowed. Neo4j HTTP and Bolt are bound to host loopback and reached through authenticated AWS Systems Manager tunnels. A generated password is stored in Secrets Manager and never committed or printed in deployment output.

Compute was verified through the AWS Pricing API at $0.0416/hour in Ohio on October 18, 2026: about $30/month if continuously running, plus disk, public-IP, secret-storage and usage charges. Stop the instance between inspections to stop compute charges; disk and other retained resources can still incur charges. This is an inspection server, not a production HA database.

## Contents and evidence rules

- Hospitals: the union of historical HCRIS facilities and current CMS hospital enrollment CCNs.
- Cost reports: 48,193 selected 2017–2024 facility-year observations, native fiscal periods, eligibility, raw selected measures and 14 computed semantic metrics.
- Semantic catalog, metric definitions and 29 source-field mappings; reports link to the catalog used for interpretation.
- Source snapshots and checksums; report IDs include the snapshot hash.
- State/county/city observations, preserving source spelling and state scope.
- Organizational associates, CMS provider enrollments, NPI references and 16,044 source-reported organizational ownership/control assertions.
- Current ownership assertions retain role, disclosed percentage, association date, source vintage, observation timestamp and source lineage. Direct convenience edges remain distinct for ownership interests versus control roles.
- A bounded NPPES sample and exact-associate CMS provider enrollments demonstrate taxonomy and cross-category reach. Unenriched NPI identifiers are explicitly marked; they are not claimed to be complete NPPES records.

CMS percentages are retained in their reported 0–100 units, not financial-metric fractions. Do not add direct/indirect interests or assume totals equal 100%. CMS disclosures are not audited ultimate-parent ownership. Do not apply current associations across every historical financial year. A shared disclosed associate is not proof of ultimate common control. No name-based ownership edges are fabricated.

## Build and deploy

1. Run the hospital/API and organizational ingestion documented under `hospitals/` and `ai/`.
2. Run `python graph/seed_providers.py` for a bounded exact-ID enrichment sample.
3. Run `python graph/build_graph.py` and `python graph/test_graph.py`.
4. Run `python graph/build_infra.py`, validate `graph/neo4j-aws.json`, then run `python graph/deploy.py` with an authorized AWS session.
5. The bootstrap imports the CSVs transactionally and writes verification totals on the instance. Inspect the existing stack before retrying a failed or partial import. `MERGE` operations and unique constraints make repeated imports idempotent for the same snapshot.

Generated CSVs, archive, deployment IDs and enrichment results are ignored under `graph/build/`. Graph artifacts are uploaded only to the private project artifact bucket. The app does not yet execute Neo4j queries from public AI prompts. Future graph-assisted AI should use parameterized read-only tools, not unrestricted model-generated Cypher.

`inspect.cypher` contains schema, ownership, provider-category, NPPES, financial-history and metric-lineage examples. The browser connection uses `bolt://localhost:7687` after both tunnels are active.

## Access and lifecycle

Run `python graph/open_inspection.py` in this checkout after deployment. It opens two authenticated port-forward sessions and prints the local browser address and AWS console link to the login secret. The login name is `neo4j`. Retrieve the password through your own AWS Secrets Manager access; it is not in the repository or chat. Keep the tunnel command running while inspecting and stop it when done.

Stopping the EC2 instance preserves its disk. Terminating it or deleting the stack can delete the root disk; retain the private import archive and any desired database backup first. The deployment script deliberately refuses to overwrite an existing Neo4j stack. Refreshes and ownership restatements need explicit snapshot/version handling.

References: [Neo4j Docker](https://neo4j.com/docs/operations-manual/current/docker/introduction/), [LOAD CSV](https://neo4j.com/docs/cypher-manual/current/clauses/load-csv/), [AWS Session Manager port forwarding](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-sessions-start.html).

## Workforce update

`python3 graph/update.py` imports the rebuilt versioned artifact into this existing instance with MERGE and checks workforce properties. It retains prior catalog lineage and ownership evidence. An initially stopped instance is temporarily started and restored to stopped afterward. New report properties include payrollFte, residentFte, salaries and seven metric_ properties; WORKFORCE_FROM_SOURCE preserves separate API refresh lineage. Run the six queries in `graph/workforce.cypher`. See `planning/WORKFORCE.md` for limitations.

## Cross-category organizational network

The extension adds Facility and OwnershipEvent labels, role-specific organizational links and source snapshots. Run `graph/ownership-network.cypher` for inspection. Only operational/managerial-control disclosures create control edges; security, mortgage, ADP, trustee and other roles remain neutral associations. Previous incorrectly promoted hospital convenience edges are reclassified while retaining their assertion evidence. Network coverage is a mixture of retained CCNs and institutional enrollment identities, not a complete physical-site census. Dated CHOW events are not continuous ownership history. See `planning/VALIDATION_OWNERSHIP.md`.
