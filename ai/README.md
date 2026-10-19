# Evidence Lab draft

Generate the semantic catalog: `python ai/build_semantics.py`.

Run the local site and read-only API: `BEDROCK_MODEL_ID=mistral.mistral-large-3-675b-instruct python ai/app.py`. Open `/hospitals/lab/` on port 8765. AWS SSO credentials stay outside the repository. Without a model configured, structured queries still work; the UI does not pretend an offline demo is an AI answer.

`POST /api/chat` accepts a question and context. `POST /api/query` accepts an allowlisted structured query. `POST /api/provider` accepts a CCN. `GET /api/health` exposes semantic version and availability. Numeric values are always calculated by `analytics.py`; the model never provides them. Unsupported or invalid requests fail closed. All reads use derived API snapshots; no generated SQL is executed.

`build_providers.py` queries CMS Hospital Enrollments and Hospital All Owners through paginated APIs. It retains organizational evidence, not individual owners. `providers.py` adds exact-NPI NPPES organization lookups and exact-associate CMS enrollment lookups across categories, with limits shown in results. Current organizational disclosures are not ownership histories.

Build the deployment template with `python infra/build_template.py`, package with `python infra/package.py`, then deploy the isolated AWS draft with `python infra/deploy.py`. Deployment outputs and evaluation artifacts stay in ignored `infra/build/`. The deployment script does not alter DNS or GitHub Pages.

See `planning/AI_SEMANTIC_ARCHITECTURE.md` for semantics, limits, next AI components and validation.

Coverage analysis currently reports dataset-wide metadata totals. Historical-owner questions are refused; the current disclosure snapshot does not establish past ownership. Questions are interpreted as individual requests using explicit UI context; typed multi-turn result-set follow-ups are future work.
