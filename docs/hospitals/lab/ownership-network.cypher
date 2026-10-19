// 1. Graph identities by category; hospital includes historical report identities.
// Renal/CMHC units are enrollments, not validated physical sites.
MATCH (f:Facility) RETURN f.category AS category,count(f) AS graphIdentities ORDER BY category;

// 2. Reported role counts; neutral associations are neither ownership nor control.
MATCH (f:Facility)-[:HAS_OWNERSHIP_ASSERTION]->(a:OwnershipAssertion)
RETURN f.category AS category,a.relationshipKind AS interpretedRole,a.role AS reportedRole,
 count(DISTINCT a) AS assertions ORDER BY category,assertions DESC;

// 3. Exact organizational owners reported across multiple provider categories.
MATCH (f:Facility)-[:REPORTED_OWNERSHIP_INTEREST]->(o:Organization)
WITH o,collect(DISTINCT f.category) AS categories,count(DISTINCT f) AS identities
WHERE size(categories)>1
RETURN o.associateId AS cmsAssociateId,o.name AS organization,categories,identities
ORDER BY size(categories) DESC,identities DESC LIMIT 30;

// 4. Inspect reported ownership paths for a target hospital.
MATCH p=(h:Hospital {id:'460010'})-[:REPORTED_OWNERSHIP_INTEREST]->(o:Organization)
OPTIONAL MATCH q=(o)<-[:REPORTED_OWNERSHIP_INTEREST]-(f:Facility)
RETURN p,q LIMIT 100;

// 5. Dated hospital change-of-ownership events; not continuous ownership intervals.
MATCH (h:Hospital {id:'150056'})-[:HAS_OWNERSHIP_EVENT]->(e:OwnershipEvent)
MATCH (e)-[:FROM_SOURCE]->(s:SourceSnapshot)
RETURN DISTINCT h.id AS ccn,e.effectiveDate,e.eventType,e.buyerName,e.sellerName,s.vintage,s.url
ORDER BY e.effectiveDate DESC;

// 6. Actual reported buyer/seller organization paths.
MATCH p=(e:OwnershipEvent)-[:REPORTED_BUYER|REPORTED_SELLER]->(o:Organization)
WHERE e.buyerCcn='150056' OR e.sellerCcn='150056'
RETURN p;

// 7. Inspect an owner's role, percentage and source snapshot in each category.
MATCH (f:Facility)-[:HAS_OWNERSHIP_ASSERTION]->(a:OwnershipAssertion)
      -[:ASSOCIATE]->(o:Organization {associateId:'1850209420'})
MATCH (a)-[:FROM_SOURCE]->(s:SourceSnapshot)
RETURN f.category,f.id,f.name,a.role,a.percentage,s.vintage,s.queriedAt,s.url
ORDER BY f.category,f.id LIMIT 100;

// 8. Check that neutral hospital associations have not been promoted to control.
MATCH (:Hospital)-[r:REPORTED_CONTROL_ROLE]->()
WHERE NOT toUpper(r.role) CONTAINS 'OPERATIONAL/MANAGERIAL CONTROL'
RETURN count(r) AS incorrectlyPromotedAssociations;

// 9. Available dated events by year: reporting coverage, not a complete M&A census.
MATCH (e:OwnershipEvent)
RETURN e.effectiveDate.year AS year,e.eventType,count(e) AS reportedEvents
ORDER BY year,e.eventType;

// 10. Preserve unknown ownership percentages, not zero interests.
MATCH (f:Facility)-[:HAS_OWNERSHIP_ASSERTION]->(a:OwnershipAssertion)
RETURN f.category AS category,count(a) AS assertions,
 count(CASE WHEN a.percentage IS NULL THEN 1 END) AS unknownPercentage
ORDER BY category;
