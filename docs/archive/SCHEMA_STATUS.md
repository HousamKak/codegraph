# CodeGraph Schema Implementation Status

## Coverage Snapshot (Dec 2024)

| Category        | Implemented | Total | Coverage |
|-----------------|-------------|-------|----------|
| Node Types      | 8           | 8     | **100%** |
| Relationship Types | 15       | 15    | **100%** |
| Conservation Laws | 4         | 4     | **100%** |

## Node Types

| Node           | Status | Notes |
|----------------|--------|-------|
| Module         | ✅ | Includes `is_external` placeholders for unresolved imports |
| Class          | ✅ | Tracks bases, docstrings, decorators |
| Function       | ✅ | Full signature metadata + decorator list |
| Parameter      | ✅ | Position, kind, defaults |
| Variable       | ✅ | Module/class/function scope variables with annotations when present |
| CallSite       | ✅ | Every callsite modeled explicitly with arg metadata |
| Type           | ✅ | Builtins + project-defined types with subtype edges |
| Decorator      | ✅ | Per-usage nodes linked to both the target and referenced decorator |

## Relationship Types

| Relationship   | Status | Description |
|----------------|--------|-------------|
| DECLARES       | ✅ | Module/Class -> Class/Function (declaration relationships) |
| HAS_PARAMETER  | ✅ | Function → Parameter (ordered) |
| RESOLVES_TO    | ✅ | CallSite → Function (call resolution) |
| HAS_CALLSITE   | ✅ | Function → CallSite |
| INHERITS       | ✅ | Class → Base class |
| IMPORTS        | ✅ | Module → Module (placeholders created for external imports) |
| RETURNS_TYPE   | ✅ | Function → Type |
| HAS_TYPE       | ✅ | Variable/Parameter → Type |
| IS_SUBTYPE_OF  | ✅ | Type → Type |
| ASSIGNS_TO     | ✅ | Function → Variable write sites |
| READS_FROM     | ✅ | Function → Variable read sites |
| REFERENCES     | ✅ | Generic Function/Class/Decorator references to any entity (access_type tagged) |
| HAS_DECORATOR / DECORATES | ✅ | Bidirectional decorator linkage |

## Recent Improvements

1. **Scope-aware Variable Tracking**
   - Local, class, and module variables become first-class nodes with `ASSIGNS_TO` and `READS_FROM` edges.
   - `REFERENCES` relationships now distinguish read vs write via `access_type`.

2. **Comprehensive Import Coverage**
   - Placeholder Module nodes (`is_external = true`) created for every import target so `IMPORTS` edges never dangle.
   - Allows validators to reason about unresolved imports and circle detection in pure-Cypher.

3. **Decorator Modeling**
   - Each decorator is represented as a `Decorator` node connected to both its target (`HAS_DECORATOR`/`DECORATES`) and the underlying function/class it references (`REFERENCES`).

4. **Documentation Alignment**
   - `backend/schema.md` rewritten to describe the true schema, ensuring MCP + docs + Cypher examples stay in sync.

## Remaining Opportunities

The core schema is now complete. Future enhancements can focus on higher-level analyses rather than missing primitives:

- **Type inference ingestion** (e.g., pyright output) to enrich Type nodes with inferred facts.
- **Flow-sensitive analysis** that leverages the new `ASSIGNS_TO/READS_FROM/REFERENCES` edges to detect unused values, side-effects, etc.
- **Import resolution** hooks to annotate placeholder modules with package metadata from lock files or `pip show`.
