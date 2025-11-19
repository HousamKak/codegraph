# CodeGraph Schema – Current vs. Suggested

The previous comparison document highlighted several gaps (no CallSite nodes, no variable tracking, no decorator representation, etc.). Those gaps are now closed. This page records how the implementation maps to the originally suggested schema so the team can audit coverage quickly.

## Node Coverage

| Suggested Node | Implemented? | Notes |
|----------------|--------------|-------|
| Module         | ✅ | Includes `is_external` flag for imported placeholders |
| Class          | ✅ | Bases + decorators tracked |
| Function       | ✅ | All signature metadata + decorators |
| Parameter      | ✅ | Ordered, typed, defaulted |
| Variable       | ✅ | Module/Class/Function scopes with read/write edges |
| CallSite       | ✅ | Every invocation modeled with arg metadata |
| Type           | ✅ | Builtins + inferred project types |
| Decorator      | ✅ | New node type replacing “decorators as strings” |

## Relationship Coverage

| Suggested Relationship | Implemented? | Notes |
|------------------------|--------------|-------|
| DECLARES / DEFINES     | ✅ | Module/Class declarations |
| CONTAINS               | ✅ | Scope hierarchy (new) |
| HAS_PARAMETER          | ✅ | Ordered |
| CALLS / HAS_CALLSITE   | ✅ | Function → CallSite → Function |
| INHERITS               | ✅ | Base class edges |
| IMPORTS                | ✅ | Resolves to placeholder modules so edges never drop |
| HAS_TYPE / RETURNS_TYPE / IS_SUBTYPE_OF | ✅ | Parameter/Variable/Function → Type + builtin hierarchy |
| ASSIGNS_TO / READS_FROM | ✅ | Captures writes vs reads |
| REFERENCES             | ✅ | Provides generic symbol-level linkage with `access_type` metadata |
| HAS_DECORATOR / DECORATES | ✅ | Newly added to expose decorator usage |

## What Changed Since the Last Audit?

1. **Scope & Variable Awareness**
   - Parser now creates `Variable` nodes for module/class/function scopes and emits `ASSIGNS_TO`, `READS_FROM`, and `REFERENCES` edges during AST traversal.
   - Enables unused-variable detection, write-before-read checks, and richer conservation-law enforcement.

2. **Robust Import Graph**
   - Every `import` and `from ... import ...` statement synthesizes a placeholder `Module` node marked `is_external=true`.
   - `IMPORTS` edges therefore persist even if the imported file is not indexed, keeping the graph closed for reference-integrity checks.

3. **Decorators as First-Class Citizens**
   - Each decorator usage now becomes a `Decorator` node with `HAS_DECORATOR`/`DECORATES` edges and an automatic `REFERENCES` edge to the underlying decorator function/class if it can be resolved.

4. **Documentation Sync**
   - `backend/schema.md` rewritten from scratch and `SCHEMA_STATUS.md` reflects full coverage, so Claude Code / MCP clients see the same schema described in markdown and delivered by the Neo4j instance.

## Next Frontier (Beyond Schema)

With structural parity achieved, future work shifts from “missing nodes” to analytics:

- Integrate type inference (pyright/mypy) to enrich `Type` nodes beyond annotations.
- Add higher-level workflows (e.g., dead-store detection) that leverage the new `READS_FROM`/`ASSIGNS_TO` edges.
- Surface unresolved placeholder imports in validation reports using the preserved `IMPORTS` graph.
