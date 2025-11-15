# CodeGraph System Diagrams

This directory contains three D2 diagrams documenting the complete CodeGraph system architecture and workflow.

## Diagrams

### 1. architecture.d2
**Complete System Architecture**

Shows:
- Main components (LLM, MCP Server, FastAPI, Neo4j)
- All 13 MCP tools organized by category
- Core components (Parser, Builder, Validator, SnapshotManager)
- Neo4j graph structure (nodes and relationships)
- LLM workflow steps (1-7)
- Data flow connections
- Key features
- Example violation structure

**Best for:** Understanding the overall system structure and component interactions.

### 2. workflow.d2
**LLM Code Editing Workflow**

Shows:
- 6 phases from initial state to self-correction
- Main actors (LLM, Codebase, Graph DB)
- Decision tree for default vs required parameters
- Two paths: Valid (green) and Invalid (red)
- Self-correction loop
- System metrics
- 4 Conservation Laws

**Best for:** Understanding how an LLM uses CodeGraph to safely edit code.

### 3. technical_flow.d2
**Technical Data Flow & Implementation**

Shows:
- 6 layers: Interface → Protocol → Server → Core → Database → Filesystem
- Indexing data flow (solid lines)
- Validation data flow (dashed lines)
- Snapshot data flow (purple lines)
- REST API parallel path (orange)
- Key data structures (Entity, Violation, Snapshot)
- Performance and design notes

**Best for:** Understanding the technical implementation and data flow.

## How to View

### Option 1: Online D2 Playground (Easiest)

1. Go to https://play.d2lang.com/
2. Copy the contents of any `.d2` file
3. Paste into the editor
4. View the interactive diagram

### Option 2: Install D2 Locally

**Install D2:**
```bash
# macOS
brew install d2

# Linux/WSL
curl -fsSL https://d2lang.com/install.sh | sh -s --

# Windows (WSL recommended)
curl -fsSL https://d2lang.com/install.sh | sh -s --
```

**Generate SVG diagrams:**
```bash
# From project root
d2 architecture.d2 architecture.svg
d2 workflow.d2 workflow.svg
d2 technical_flow.d2 technical_flow.svg

# Open in browser (macOS)
open architecture.svg

# Open in browser (Linux)
xdg-open architecture.svg

# Open in browser (Windows)
start architecture.svg
```

**Generate PNG diagrams:**
```bash
d2 architecture.d2 architecture.png
d2 workflow.d2 workflow.png
d2 technical_flow.d2 technical_flow.png
```

## Diagram Color Coding

**architecture.d2:**
- 🟢 Green: LLM/User Interface
- 🔵 Blue: MCP Server (Read-Only Tools)
- 🟠 Orange: FastAPI Backend
- 🟣 Purple: Neo4j Database
- 🔴 Pink: Core Components
- 🟡 Yellow: Workflow Steps

**workflow.d2:**
- 🔵 Blue: Initial state
- 🟢 Green: LLM editing and valid paths
- 🟡 Yellow: Re-indexing and comparison
- 🟠 Orange: Validation
- 🔴 Red: Invalid/error paths
- 🟣 Purple: Self-correction

**technical_flow.d2:**
- 🟢 Green: Interface layer
- 🔵 Blue: Protocol layer
- 🟠 Orange: Server layer
- 🔴 Pink: Core components
- 🟣 Purple: Database layer
- 🟡 Yellow: Filesystem layer

## Key Concepts Illustrated

### The Workflow We Invented

All three diagrams show different aspects of our LLM-driven code editing workflow:

```
1. LLM edits code (using Edit/Write tools)
2. Call index_codebase (re-index modified file)
3. Call create_snapshot (capture new state)
4. Call compare_snapshots (detect what changed)
5. Call validate_codebase (check for violations)
6. LLM reviews violations (file:line:column)
7. LLM fixes code if needed
8. Repeat from step 2 until clean
```

### Smart Parameter Counting

The workflow diagram shows the decision tree for handling default parameters:

- **Has default value?** → Valid (caller can omit the parameter)
- **Required parameter?** → Error (caller must provide it)

Formula: `required_params ≤ arg_count ≤ total_params`

### 4 Conservation Laws

All diagrams reference the 4 conservation laws that ensure code integrity:

1. **Signature Conservation** - Function signatures match call sites
2. **Reference Integrity** - All identifiers resolve
3. **Data Flow Consistency** - Types are compatible
4. **Structural Integrity** - Graph structure is valid

### Clean Re-Indexing

The technical flow shows how we prevent duplicates:

1. Delete old nodes from file
2. MERGE new nodes (idempotent)
3. No duplicates guaranteed

## System Statistics

As shown in the diagrams:
- ✅ 14 Functions indexed
- ✅ 15 Parameters (1 with default value)
- ✅ 28 Relationships tracked
- ✅ 0 duplicate nodes
- ✅ 13 MCP tools available
- ✅ 100% accurate validation

## Related Documentation

- **SYSTEM_SUMMARY.md** - Complete written documentation
- **README.md** - Project overview and quick start
- **DOCKER_COMMANDS.md** - Docker reference

## Diagram Source

All diagrams are written in D2 (Declarative Diagrams), a modern diagram scripting language.

- D2 Website: https://d2lang.com/
- D2 Documentation: https://d2lang.com/tour/intro
- D2 Playground: https://play.d2lang.com/

## Updates

These diagrams are accurate as of the latest system implementation:
- **Date:** 2025-11-15
- **Version:** 1.0.0
- **Status:** Production Ready ✅
