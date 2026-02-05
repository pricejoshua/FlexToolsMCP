# Architecture & Design Decisions

This document tracks key architectural and design decisions made during the FlexTools MCP project.

---

## Decision 001: Leverage FLExTools-Generator Foundation
**Date:** 2026-02-05
**Status:** Approved

### Context
The FLExTools-Generator repository already contains comprehensive LibLCM extraction (2,295+ entities, unified-api-doc/2.0 schema).

### Decision
Build on top of FLExTools-Generator outputs rather than re-extracting from scratch:
- Use existing `flex-api-enhanced.json` for LibLCM documentation
- Use existing `unified-api-doc/2.0` schema for consistency
- Focus new effort on FlexLibs 2.0 extraction (the gap)

### Consequences
- Faster development (avoid redoing LibLCM extraction)
- Consistent data format across all sources
- Dependency on FLExTools-Generator outputs

---

## Decision 002: FlexLibs 2.0 as Primary API Layer
**Date:** 2026-02-05
**Status:** Approved

### Context
Three API levels exist:
1. LibLCM (C#) - comprehensive but verbose
2. FlexLibs Light - stable but limited (~40 functions)
3. FlexLibs 2.0 - comprehensive (~90% coverage), Pythonic, beta

### Decision
Default to FlexLibs 2.0 when generating scripts:
- "auto" mode uses FlexLibs 2.0 when available
- Falls back to LibLCM for uncovered functionality
- FlexLibs Light supported but not prioritized

### Consequences
- More Pythonic generated scripts
- Some beta instability risk
- FlexLibs 2.0 extraction completed (78 classes, 1,398 methods)

### Quality Comparison (2026-02-05)
| Source | Entities | Descriptions | Returns | Examples |
|--------|----------|-------------|---------|----------|
| LibLCM | 2,295 | 100% | Minimal | 0% |
| FlexLibs 2.0 | 78 classes | 99% | 61% | 82% |

FlexLibs 2.0 has significantly better documentation quality despite being a wrapper.

---

## Decision 003: Static Analysis Primary, AI for Enrichment
**Date:** 2026-02-05
**Status:** Approved

### Context
Could use heavy AI for documentation generation vs. deterministic extraction.

### Decision
Use static analysis (AST parsing) for extraction, AI only for:
- Filling missing descriptions
- Semantic categorization
- C# to IronPython example conversion

### Consequences
- Reproducible, verifiable outputs
- Lower cost (minimal API calls)
- Ground truth remains source code

---

## Decision 004: Object-Centric Index Organization
**Date:** 2026-02-05
**Status:** Approved

### Context
Could organize index by method name, by category, or by object.

### Decision
Organize around objects (ILexEntry, ILexSense, etc.) with:
- Methods and properties per object
- Relationship navigation paths
- FlexLibs 2.0 wrapper mappings

### Consequences
- Natural navigation for object-oriented code
- Easier "how to get from A to B" queries
- Matches how users think about lexicon structure
