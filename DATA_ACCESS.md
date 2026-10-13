# Data access policy

Use official APIs to retrieve HCRIS-derived data. Do not download raw CMS CSV or ZIP distributions, and do not silently fall back to bulk downloads. Hospital public-use records are queried through CMS's paginated JSON API with explicit dataset IDs, selected columns, stable ordering and schema checks. Responses are processed in memory. Only the derived dashboard cache and source manifest are retained for static hosting.

If a provider's raw cost-report family has no verified API, document that coverage gap and leave its metrics unavailable. Provider directory/quality APIs do not substitute for raw financial cost-report data.
