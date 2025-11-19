# Software Physics: A Theory of Codebase Conservation Laws

## Executive Summary

This document summarizes a novel theoretical framework for software engineering that treats codebases as semantic graphs governed by conservation laws. The framework enables safe LLM-driven code evolution by validating every transformation against formal invariants.

---

## 1. Core Concept: Software Physics

The fundamental paradigm shift:

- **The codebase IS a semantic graph** - not just represented by one
- **Conservation laws** define valid states
- **Code evolution = graph transformations** that must preserve invariants
- **LLMs operate inside formal constraints**, receiving immediate feedback on violations

### The Problem This Solves

**Traditional workflow:**
```
Human writes code → Compiler checks → Human fixes errors
LLM writes code → ... delay ... → Compiler checks much later
```

**New workflow:**
```
LLM proposes edit → Graph updated → S/R/T validated → Accept/Reject immediately
```

The graph + conservation laws become a "physics engine" for code that enforces correctness in real-time.

---

## 2. The Three Fundamental Conservation Laws

All software correctness can be reduced to three minimal, language-agnostic invariants:

### 2.1 Structural Validity (S)

**Definition:** The program's structural graph must belong to the valid shape category of the language.

**Constraints include:**
- Edges connect valid node types (e.g., `HAS_PARAMETER` only from `Function` to `Parameter`)
- Multiplicities hold (each parameter belongs to exactly one function)
- No inheritance cycles: `¬∃c. (c →INHERITS+ c)`
- Unique parameter positions per function
- Call arity matches declared arity

**Mathematical form:**
```
∀(u,v) ∈ E. validEdge(u,v)
∀p:Parameter. |{f | f →HAS_PARAMETER p}| = 1
∀f. ∀i. |{p | f →HAS_PARAMETER p ∧ p.position = i}| ≤ 1
```

### 2.2 Referential Coherence (R)

**Definition:** Every reference must resolve to one or more valid declarations according to the language's symbol resolution semantics.

**Constraints include:**
- Every identifier use resolves to exactly one declaration
- All imports point to existing modules/symbols
- Scope and visibility rules are respected
- No dangling references

**Mathematical form:**
```
∀u ∈ U. ∃!d ∈ D. Resolve(u) = d ∧ Visible(u, d)
```

Where:
- `U` = set of identifier uses
- `D` = set of declarations
- `Resolve` = language-specific resolution function
- `Visible` = scope/visibility predicate

### 2.3 Semantic Typing Correctness (T)

**Definition:** All expressions must be type-correct under the language's type system and semantic rules.

**Constraints include:**
- Function arguments match parameter types
- Return values match declared return types
- Variables assigned compatible values
- Data-flow edges respect type constraints

**Mathematical form (λ-calculus style):**
```
T(G) ⟺ ∀e ∈ Expr(G). Γ ⊢_lang e : τ
```

**Function application rule:**
```
Γ ⊢ f : (τ₁,...,τₙ) → τᵣ    Γ ⊢ aᵢ : τᵢ  ∀i
─────────────────────────────────────────────
        Γ ⊢ f(a₁,...,aₙ) : τᵣ
```

### 2.4 Combined Conservation Law

A graph state G is valid if and only if:

```
Valid(G) ⟺ S(G) ∧ R(G) ∧ T(G)
```

### 2.5 Reduction from Original Four Laws

The original four conservation laws collapse into these three:

| Original Law | Reduced To |
|--------------|------------|
| Signature Conservation | T + S |
| Reference Integrity | R |
| Data Flow Consistency | T |
| Graph Structural Integrity | S + R |

---

## 3. The Semantic Graph Model

### 3.1 Node Types

```
:Module      {name, path}
:Class       {name, qualname}
:Function    {name, qualname, is_method, async, lineno}
:Parameter   {name, position, kind, annotation}
:Variable    {name, kind, annotation}
:CallSite    {lineno, col_offset, arg_count, text}
:Type        {name, origin}
```

### 3.2 Edge Types

```
(:Module)-[:DECLARES]->(:Class|:Function|:Variable)
(:Class)-[:DECLARES]->(:Function|:Variable)
(:Function)-[:HAS_PARAMETER]->(:Parameter)
(:Function)-[:RETURNS_TYPE]->(:Type)
(:CallSite)-[:RESOLVES_TO]->(:Function)  # Unified call tracking with resolution status
(:Function)-[:HAS_CALLSITE]->(:CallSite)  # Bidirectional call graph navigation
(:Module)-[:IMPORTS]->(:Module|:Class|:Function)
(:Class)-[:INHERITS]->(:Class)
(:Parameter)-[:HAS_TYPE]->(:Type)
```

**Note:** Implementation now fully aligns with theory. RESOLVES_TO replaces the old CALLS relationship to avoid redundancy while tracking resolution status.

### 3.3 Non-Invertibility and Semantic Compression

**Key insight:** The mapping `Code → Graph` is many-to-one, not bijective.

Multiple codebases can produce the same semantic graph:
```python
# All three map to the same graph:
def add(x, y): return x + y

def add(a, b):
    r = a + b
    return r

def add(x, y):
    # add two numbers
    return (x) + (y)
```

**This is a feature, not a bug:**
- Graph is stable across formatting/style changes
- Semantic versioning tracks actual changes, not noise
- Language-agnostic semantics converge in graph form

---

## 4. Language-Agnostic Generalization

The three laws work across ALL programming languages by parameterizing:

| Law | Language-Specific Component |
|-----|----------------------------|
| S | Grammar and shape rules |
| R | `Resolve_lang()` - resolution algorithm |
| T | `⊢_lang` - type system rules |

### 4.1 Handling Method Overloading

For languages with overloading (C#, Java, C++), the graph model extends:

```
(MG:MethodGroup {name:"Play"})
(F1:Function {params:[int,string]})
(F2:Function {params:[int]})

MG -[:HAS_OVERLOAD]-> F1
MG -[:HAS_OVERLOAD]-> F2

(CallSite) -[:CALLS_NAME]-> (MethodGroup)
(CallSite) -[:RESOLVES_TO]-> (Function)  // after resolution
```

The conservation law becomes:
> Every call must have exactly one valid, well-typed overload under the language's overload resolution algorithm.

---

## 5. Graph-Theoretic Operations for Refactoring

### 5.1 Pure Views (Analysis Without Code Change)

| Operation | Purpose | Use Case |
|-----------|---------|----------|
| **SCC Condensation** | Collapse strongly connected components | Expose cycles, find modularization opportunities |
| **Transitive Reduction** | Remove redundant edges | Identify unnecessary dependencies |
| **Quotient Graphs** | Cluster by equivalence | View architecture at different abstraction levels |
| **Centrality Metrics** | Find highly-connected nodes | Identify "god classes" and hotspots |

### 5.2 Graph Rewrites (Actual Refactors)

| Rewrite | λ-Calculus Equivalent | Code Operation |
|---------|----------------------|----------------|
| **Function Inlining** | β-reduction: `(λx.e) a → e[x:=a]` | Replace call with function body |
| **Wrapper Removal** | η-reduction: `λx.fx → f` | Remove trivial pass-through methods |
| **Node Contraction** | - | Merge equivalent functions/classes |
| **Cut Set Extraction** | - | Introduce interfaces at module boundaries |

**Constraint:** All rewrites must preserve `S(G') ∧ R(G') ∧ T(G')`

---

## 6. The LLM Validation Loop

### 6.1 Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   LLM       │────▶│  Orchestrator │────▶│  Graph DB   │
│  (Proposer) │◀────│  (Validator)  │◀────│  (Neo4j)    │
└─────────────┘     └──────────────┘     └─────────────┘
                           │
                    ┌──────┴──────┐
                    │  Type Checker│
                    │  (pyright)   │
                    └─────────────┘
```

### 6.2 Validation Flow

```
1. Start from valid graph G (snapshot)
2. LLM proposes code patch
3. Apply patch to source files
4. Re-index only changed files → G'
5. Mark changed nodes: SET n.changed = true
6. Run S/R/T queries seeded at changed nodes
7. If violations:
   - Return structured errors to LLM
   - LLM proposes fix
   - Goto step 3
8. If clean:
   - Accept G' as new valid snapshot
   - REMOVE n.changed
```

### 6.3 Structured Feedback Format

```json
{
  "valid": false,
  "violations": [
    {
      "law": "T",
      "node_kind": "CallSite",
      "file": "game.py",
      "line": 123,
      "message": "Call to play has 2 args but function now takes 1"
    },
    {
      "law": "S",
      "node_kind": "Class",
      "file": "models.py",
      "line": 45,
      "message": "Inheritance cycle detected: A → B → C → A"
    }
  ]
}
```

---

## 7. Local-to-Global Soundness Theorem

### 7.1 The Problem

If we only validate locally around changed nodes, how do we know the whole graph is valid?

### 7.2 The Theorem

**Locality Lemma:** If an invariant is of the form `∀x. φ(x)` where `φ(x)` only reads a bounded-radius neighborhood around `x`, then:

If:
- The invariant held in G
- Only region U changed
- The invariant holds for all x in Nbr(U) in G'

Then: The invariant holds globally in G'

### 7.3 Handling Global Properties (Cycles)

For "no cycles" invariants:
- Any new cycle must pass through at least one changed element
- Therefore: check cycles only from changed nodes outward

```cypher
// Check inheritance cycles only from changed classes
MATCH (c:Class)
WHERE c.changed = true
MATCH path = (c)-[:INHERITS*1..]->(c)
RETURN path;
```

### 7.4 Formal Statement

**Global S/R/T Preservation Theorem:**

Assume:
- G satisfies S, R, T
- G' = result of applying update U
- For every S/R/T invariant, local revalidation from U is sound
- Local checks on G' from U find no violation

Then: G' satisfies S, R, and T globally.

---

## 8. Implementation Strategy

### 8.1 Technology Stack (Python MVP)

**Reuse:**
- **Parsing:** tree-sitter or libcst
- **Type checking:** pyright or mypy
- **Graph storage:** Neo4j
- **Patching:** Git + unidiff
- **LLM:** OpenAI/Anthropic API

**Write (Novel Contribution):**
- Graph schema + indexer
- Conservation laws as Cypher queries
- LLM orchestrator with validation loop
- Graph diff UI

### 8.2 Example Cypher Queries

**Structural (S) - Parameter uniqueness:**
```cypher
MATCH (f:Function)-[:HAS_PARAMETER]->(p:Parameter)
WHERE f.changed = true
WITH f, p.position AS pos, count(p) AS c
WHERE c > 1
RETURN f, pos, c;
```

**Referential (R) - Unresolved calls:**
```cypher
MATCH (c:CallSite)
WHERE c.changed = true
OPTIONAL MATCH (c)-[:RESOLVES_TO]->(d:Declaration)
WITH c, count(d) AS targets
WHERE targets <> 1
RETURN c, targets;
```

**Typing (T) - Arity mismatch:**
```cypher
MATCH (c:CallSite)-[:CALLS]->(f:Function)
WHERE c.changed = true OR f.changed = true
OPTIONAL MATCH (f)-[:HAS_PARAMETER]->(p:Parameter)
WITH c, f, count(p) AS param_count
WHERE c.arg_count <> param_count
RETURN c, f, param_count;
```

### 8.3 MVP Timeline

| Week | Deliverable |
|------|-------------|
| 1 | Neo4j schema + libcst indexer (Module, Function, Parameter, CallSite) |
| 2 | Integrate pyright, implement basic S/R/T Cypher queries |
| 3 | Build LLM orchestrator with validation loop |
| 4+ | Snapshots, graph diff UI, additional refactor operations |

---

## 9. Novelty Assessment

### 9.1 Existing Related Work

| Tool/Concept | Coverage |
|--------------|----------|
| **Kythe (Google)** | Language-agnostic graph schema |
| **Code Property Graphs (Joern)** | AST + CFG + DFG unified graph |
| **CodeQL (GitHub)** | Queryable semantic database |
| **SemanticForge (2025)** | Constraint checking for LLM code |
| **Graph Rewriting (Mens et al.)** | Formal refactoring as graph transforms |

### 9.2 What's Genuinely Novel

1. **Explicit S/R/T as mathematical invariants** - not buried in compiler internals
2. **Persistent whole-codebase graph** as the single source of truth
3. **LLM edits validated by graph physics** before acceptance
4. **Unified language-agnostic theory** with pluggable semantics
5. **Local-to-global soundness guarantee** for incremental validation

**Conclusion:** No existing system combines all five. This is a new theoretical framework.

---

## 10. Proposed Field Names

- **Software Physics**
- **Graph-Theoretic Code Semantics (GTCS)**
- **Codebase Conservation Theory**
- **Invariant-Preserving Software Dynamics**
- **Semantic Graph Refactoring Theory**

---

## 11. Academic Paper Structure

1. **Abstract** - Problem, proposal, method, contributions
2. **Introduction** - Motivation, problem statement, key insight
3. **Background & Related Work** - CodeQL, Kythe, CPG, LLM code generation
4. **Semantic Graph Model** - Nodes, edges, non-invertibility
5. **Conservation Laws** - S, R, T formal definitions
6. **Graph Transformations** - Rewrites, preconditions, properties
7. **LLM-Guided Patch Application** - Verification loop, structured feedback
8. **Implementation** - Technologies, schema, performance
9. **Evaluation** - Correctness, efficiency, case studies
10. **Discussion** - Limits, extensions, threats to validity
11. **Conclusion**

---

## 12. Potential Applications

- **Safe LLM code generation** - Every AI edit validated before commit
- **Automated refactoring engines** - Formally guaranteed transformations
- **Architecture enforcement** - No layering violations, no cycles
- **Multi-language monorepo management** - Unified semantic view
- **Code migration tools** - Track semantic changes, not text diffs
- **IDE integration** - Real-time graph-based navigation and validation

---

## 13. Conclusion

This framework introduces a unified semantic-graph foundation for safe LLM-driven code evolution. By treating codebases as mathematical objects governed by conservation laws, we replace "compile-after-the-fact" checking with continuous invariant validation.

The key contributions are:
1. Three minimal, language-agnostic conservation laws (S, R, T)
2. A formal model of code as a semantic graph
3. Graph-theoretic operations mapped to refactoring
4. An LLM orchestration loop with structured feedback
5. A local-to-global soundness theorem for incremental validation

This work opens a new branch of software engineering theory: **Software Physics**.

---

## References

- Borowski et al. "Semantic Code Graph" (2024)
- Kythe Documentation (Google)
- Zhang et al. "SemanticForge" (2025)
- Mens, T. "Graph Transformations for Model Refactoring" (2006)
- Batushkov, V. "Codebase Knowledge Graph" (Neo4j, 2021)

---

*Document generated from analysis of theory and idea.txt*
