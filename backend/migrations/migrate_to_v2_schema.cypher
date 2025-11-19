// ============================================================================
// CodeGraph Schema Migration: v1 → v2
// ============================================================================
//
// This script migrates existing CodeGraph databases to the new optimized schema
//
// Changes:
// 1. Remove CALLS relationships (replaced by RESOLVES_TO)
// 2. Rename DEFINES relationships to DECLARES
// 3. Remove CONTAINS relationships (redundant with DECLARES)
//
// Backup your database before running this script!
//
// Usage:
//   1. Open Neo4j Browser (http://localhost:7474)
//   2. Copy and paste each section below
//   3. Run sections one at a time
//   4. Verify counts after each step
// ============================================================================

// ----------------------------------------------------------------------------
// Step 1: Verify current state
// ----------------------------------------------------------------------------

// Count existing relationships
MATCH ()-[r]->()
RETURN type(r) as relationship_type, count(r) as count
ORDER BY count DESC;

// Expected output: You should see CALLS, DEFINES, CONTAINS if migrating from v1


// ----------------------------------------------------------------------------
// Step 2: Remove old CALLS relationships
// ----------------------------------------------------------------------------

// CALLS has been replaced by RESOLVES_TO (with CallSite intermediate nodes)
// The new parser creates RESOLVES_TO relationships automatically

MATCH ()-[r:CALLS]->()
WITH count(r) as old_calls_count
RETURN old_calls_count;

// Delete CALLS relationships (they should not exist in new schema)
MATCH ()-[r:CALLS]->()
DELETE r;

// Verify deletion
MATCH ()-[r:CALLS]->()
RETURN count(r) as remaining_calls;
// Expected: 0


// ----------------------------------------------------------------------------
// Step 3: Rename DEFINES to DECLARES
// ----------------------------------------------------------------------------

// DEFINES relationships are now called DECLARES for theory alignment

MATCH (source)-[old:DEFINES]->(target)
WITH source, target, old, properties(old) as props
CREATE (source)-[new:DECLARES]->(target)
SET new = props
DELETE old;

// Verify migration
MATCH ()-[r:DEFINES]->()
RETURN count(r) as remaining_defines;
// Expected: 0

MATCH ()-[r:DECLARES]->()
RETURN count(r) as new_declares;
// Should match old DEFINES count


// ----------------------------------------------------------------------------
// Step 4: Remove CONTAINS relationships
// ----------------------------------------------------------------------------

// CONTAINS was created but never queried - redundant with DECLARES
// Safe to delete as semantic containment is implied by DECLARES

MATCH ()-[r:CONTAINS]->()
WITH count(r) as old_contains_count
RETURN old_contains_count;

// Delete CONTAINS relationships
MATCH ()-[r:CONTAINS]->()
DELETE r;

// Verify deletion
MATCH ()-[r:CONTAINS]->()
RETURN count(r) as remaining_contains;
// Expected: 0


// ----------------------------------------------------------------------------
// Step 5: Verify new schema
// ----------------------------------------------------------------------------

// Check all relationship types - should only see v2 types
MATCH ()-[r]->()
RETURN type(r) as relationship_type, count(r) as count
ORDER BY count DESC;

// Expected v2 relationships (14 types):
// - RESOLVES_TO
// - DECLARES (not DEFINES)
// - HAS_CALLSITE
// - HAS_PARAMETER
// - HAS_TYPE
// - RETURNS_TYPE
// - INHERITS
// - IMPORTS
// - ASSIGNS_TO
// - READS_FROM
// - REFERENCES
// - IS_SUBTYPE_OF
// - HAS_DECORATOR
// - DECORATES

// Should NOT see:
// - CALLS (removed)
// - DEFINES (renamed to DECLARES)
// - CONTAINS (removed)


// ----------------------------------------------------------------------------
// Step 6: Optional - Add performance indexes
// ----------------------------------------------------------------------------

// Add index on CallSite resolution_status for faster unresolved call queries
CREATE INDEX callsite_resolution_idx IF NOT EXISTS
FOR (cs:CallSite) ON (cs.resolution_status);

// Add index on CallSite for change tracking
CREATE INDEX callsite_changed_idx IF NOT EXISTS
FOR (cs:CallSite) ON (cs.changed);


// ----------------------------------------------------------------------------
// Step 7: Verify graph integrity
// ----------------------------------------------------------------------------

// Check for orphaned CallSite nodes (should have both HAS_CALLSITE and RESOLVES_TO)
MATCH (cs:CallSite)
WHERE NOT ()-[:HAS_CALLSITE]->(cs)
RETURN count(cs) as orphaned_callsites;
// Expected: 0 (all CallSites should have incoming HAS_CALLSITE)

// Check for unresolved calls
MATCH (cs:CallSite)
WHERE cs.resolution_status = 'unresolved'
RETURN count(cs) as unresolved_calls;
// This is OK - shows broken references in code

// Check DECLARES relationships
MATCH (source)-[:DECLARES]->(target)
WHERE NOT (source:Module OR source:Class)
RETURN count(*) as invalid_declares_sources;
// Expected: 0 (only Module and Class can DECLARES)


// ----------------------------------------------------------------------------
// Migration Complete!
// ----------------------------------------------------------------------------

// Summary: Count nodes and edges
MATCH (n)
RETURN count(n) as total_nodes;

MATCH ()-[r]->()
RETURN count(r) as total_edges;

MATCH ()-[r]->()
RETURN type(r) as edge_type, count(r) as count
ORDER BY count DESC;

// You should see:
// - 30-40% fewer edges than before migration
// - Only 14 relationship types
// - No CALLS, DEFINES, or CONTAINS relationships

// ============================================================================
// Notes:
// - Re-parsing your codebase is recommended to ensure full v2 compliance
// - The new parser will create CallSite nodes and RESOLVES_TO relationships
// - All queries in documentation have been updated to v2 patterns
// ============================================================================
