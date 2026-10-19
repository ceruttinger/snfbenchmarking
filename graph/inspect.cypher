// 1. See the loaded graph schema.
CALL db.schema.visualization();

// 2. A hospital, its enrollment identity, NPI and reported organizations.
MATCH (h:Hospital {id:'460010'})
OPTIONAL MATCH p=(h)-[:ENROLLED_AS]->(:ProviderEnrollment)-[:HAS_REPORTED_NPI]->(:NPI)
OPTIONAL MATCH q=(h)-[:HAS_OWNERSHIP_ASSERTION]->(:OwnershipAssertion)-[:ASSOCIATE]->(:Organization)
RETURN h,p,q;

// 3. Source-reported interests (not ultimate-parent ownership).
MATCH (h:Hospital)-[r:REPORTED_OWNERSHIP_INTEREST]->(o:Organization)
RETURN o.name, count(DISTINCT h) AS hospitals, collect(DISTINCT r.sourceVintage) AS disclosureVintages
ORDER BY hospitals DESC LIMIT 25;

// 4. Shared disclosed organizational associate across provider categories.
MATCH (h:Hospital {id:'460010'})-[:HAS_OWNERSHIP_ASSERTION]->(:OwnershipAssertion)-[:ASSOCIATE]->(o:Organization)
MATCH (o)-[:HAS_REPORTED_ENROLLMENT]->(e:ProviderEnrollment)
RETURN o.name, e.providerType, count(DISTINCT e) AS enrollments
ORDER BY enrollments DESC;

// 5. Exact-NPI organization enrichment and taxonomy (bounded sample).
MATCH (e:ProviderEnrollment)-[:HAS_REPORTED_NPI]->(n:NPI {enumerationType:'NPI-2'})
OPTIONAL MATCH (n)-[:HAS_TAXONOMY]->(t:Taxonomy)
RETURN e.legalName, n.id, n.legalName, collect(DISTINCT t.description), n.queriedAt, n.source LIMIT 25;

// 6. Hospital financial history, with its actual periods and sources.
MATCH (h:Hospital {id:'460010'})-[:HAS_COST_REPORT]->(r:CostReport)-[:FROM_SOURCE]->(s:SourceSnapshot)
RETURN r.datasetYear,r.fiscalBegin,r.fiscalEnd,r.eligible,r.metric_occupancy,r.metric_totalMargin,s.url,s.sha256
ORDER BY r.datasetYear;

// 7. Explain a metric using the same semantic catalog as the chatbot.
MATCH p=(c:SemanticCatalog)-[:DEFINES]->(m:MetricDefinition {key:'totalMargin'})-[:USES_FIELD]->(:DataField)
RETURN p;

// 8. Preserve disclosures and their provenance; do not infer an end date.
MATCH (h:Hospital {id:'460010'})-[:HAS_OWNERSHIP_ASSERTION]->(a:OwnershipAssertion)-[:FROM_SOURCE]->(s:SourceSnapshot)
RETURN h.name,a.role,a.percentage,a.associationDate,a.evidenceStatus,a.sourceVintage,s.url;

// 9. Validate totals against graph-manifest.json.
MATCH (r:CostReport) RETURN count(r) AS costReports;
MATCH (a:OwnershipAssertion) RETURN count(a) AS ownershipAssertions;
