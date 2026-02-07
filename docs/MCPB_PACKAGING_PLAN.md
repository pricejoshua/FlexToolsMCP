# MCPB Packaging Plan

Package FlexTools MCP as an `.mcpb` (MCP Bundle) for one-click installation in Claude Desktop.

---

## Background

Claude Desktop supports three ways to add MCP servers:
1. **Remote MCP server** (URL) -- requires hosting
2. **MCPB** (MCP Bundle) -- local installable package (double-click to install)
3. **.DXT** (legacy name for MCPB)

MCPB is the best fit because:
- All tools work locally (including `run_module`/`run_operation` which need FieldWorks)
- No hosting infrastructure needed
- Users double-click a file to install
- UV runtime manages Python + dependencies automatically (no user Python install required)

**Reference:** https://github.com/modelcontextprotocol/mcpb

---

## Prerequisites

- Node.js (for the `mcpb` CLI tool -- packaging only)
- `npm install -g @anthropic-ai/mcpb`

---

## Phase 1: Create `pyproject.toml`

The UV runtime uses `pyproject.toml` to resolve dependencies. We need to create one that:
- Declares `mcp>=1.0.0` as the core dependency
- Makes `sentence-transformers`, `faiss-cpu` optional (semantic search)
- Makes `pythonnet` optional (only needed for LibLCM extraction, not serving)
- Sets `requires-python = ">=3.10"`

```toml
[project]
name = "flextools-mcp"
version = "1.0.0"
description = "MCP server for AI-assisted FlexTools scripting for FieldWorks"
requires-python = ">=3.10"
dependencies = [
    "mcp>=1.0.0",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
semantic = [
    "sentence-transformers>=2.2.0",
    "faiss-cpu>=1.7.4",
    "numpy",
]
extraction = [
    "pythonnet>=3.0.0",
]
```

**Decision:** Only include core deps in the MCPB. Semantic search is nice-to-have but adds ~500MB+ to the install. Keyword search works well enough for the packaged version.

---

## Phase 2: Create `manifest.json`

```json
{
  "manifest_version": "0.4",
  "name": "flextools-mcp",
  "display_name": "FlexTools MCP",
  "version": "1.0.0",
  "description": "AI-assisted FlexTools scripting for FieldWorks lexicons. Provides searchable API documentation for LibLCM and FlexLibs, code generation, and direct script execution.",
  "long_description": "Enables AI assistants to help users write FlexTools scripts for editing FieldWorks lexicons. Includes indexed documentation of LibLCM (C# data model) and FlexLibs 2.0 (Python wrappers), semantic search, navigation path finding, code examples, and direct module execution against FieldWorks projects.",
  "author": {
    "name": "mattgyverlee",
    "url": "https://github.com/mattgyverlee/FlexToolsMCP"
  },
  "repository": {
    "type": "git",
    "url": "https://github.com/mattgyverlee/FlexToolsMCP"
  },
  "license": "MIT",
  "server": {
    "type": "uv",
    "entry_point": "src/server.py"
  },
  "tools_generated": true,
  "keywords": [
    "fieldworks",
    "flextools",
    "linguistics",
    "lexicon",
    "liblcm",
    "flexlibs",
    "sil"
  ],
  "compatibility": {
    "claude_desktop": ">=0.10.0",
    "platforms": ["win32"],
    "runtimes": {
      "python": ">=3.10"
    }
  },
  "user_config": {
    "default_project": {
      "type": "string",
      "title": "Default FieldWorks Project",
      "description": "Name of the default FieldWorks project for run_module/run_operation (e.g., 'Sena 3'). Can be overridden per tool call.",
      "required": false
    }
  }
}
```

### Key decisions:

- **`server.type: "uv"`** -- UV runtime manages Python automatically. Requires manifest_version 0.4.
- **`platforms: ["win32"]`** -- FieldWorks only runs on Windows. The documentation tools would work anywhere, but `run_module`/`run_operation` need FieldWorks DLLs. We can expand to other platforms later if we split tools.
- **`tools_generated: true`** -- Our tools are defined dynamically in `list_tools()`, not statically in the manifest.
- **`user_config`** -- Lets users set a default FieldWorks project name through the Claude Desktop UI. The value is accessible via `${user_config.default_project}` and could be passed as an env var.

---

## Phase 3: Adapt `server.py` for MCPB

Minimal changes needed:

### 3.1: Index path resolution
Currently `get_index_dir()` uses `Path(__file__).parent.parent / "index"`. This should work as-is since `${__dirname}` in MCPB points to the extension install directory, preserving the relative structure. **Verify this works after packaging.**

### 3.2: User config for default project
Read `default_project` from environment variable (set by MCPB from `user_config`):

```python
# In manifest.json, add to server.mcp_config.env:
# "DEFAULT_PROJECT": "${user_config.default_project}"

# In server.py, read it:
DEFAULT_PROJECT = os.environ.get("DEFAULT_PROJECT", "")
```

Then use as fallback in `run_module`/`run_operation` when `project_name` is not provided.

### 3.3: Graceful degradation for semantic search
Already handled -- `SEMANTIC_SEARCH_AVAILABLE` flag exists. When packaged without `sentence-transformers`, keyword search is used automatically. No changes needed.

### 3.4: Graceful handling when FieldWorks is not installed
`run_module` and `run_operation` currently fail with an import error if FlexLibs isn't available. Add a friendlier error message:

```python
# In handle_run_module / handle_run_operation:
# Check if flexlibs is importable before attempting execution
```

---

## Phase 4: Package and Test

### 4.1: Initialize and validate
```bash
cd FlexToolsMCP
mcpb init          # or just create manifest.json manually
mcpb validate .    # check manifest against schema
```

### 4.2: Create `.mcpbignore`
Exclude files that shouldn't be in the bundle:

```
.git/
.env
.env.example
docs/
tests/
*.pyc
__pycache__/
index/embeddings/       # Large semantic search files (~50MB)
.venv/
node_modules/
```

### 4.3: Pack the bundle
```bash
mcpb pack .
# Produces: flextools-mcp-1.0.0.mcpb
```

### 4.4: Test installation
1. Double-click `flextools-mcp-1.0.0.mcpb`
2. Claude Desktop should prompt to install
3. Verify all tools appear in tool list
4. Test `list_categories` (no FieldWorks needed)
5. Test `search_by_capability` with a query
6. Test `run_operation` against a real project (if available)

---

## Phase 5: Distribution

### 5.1: GitHub Releases
- Add `.mcpb` file to GitHub releases
- Users download and double-click to install
- Auto-update when new versions are released

### 5.2: README updates
- Add "Install in Claude Desktop" section with download link
- Keep existing Claude Code / manual config instructions
- Document `user_config` options

---

## File Checklist

Files to create:
- [ ] `pyproject.toml`
- [ ] `manifest.json`
- [ ] `.mcpbignore`

Files to modify:
- [ ] `src/server.py` -- Add user_config env var reading, improve error messages for missing FieldWorks
- [ ] `README.md` -- Add installation instructions

Files bundled in `.mcpb`:
- `manifest.json`
- `pyproject.toml`
- `src/server.py`
- `src/refresh.py` (optional -- not needed for serving)
- `index/liblcm/flex-api-enhanced.json` (~3.8 MB)
- `index/flexlibs/flexlibs2_api.json` (~2.7 MB)
- `index/flexlibs/flexlibs_api.json`
- `index/navigation_graph.json`
- `index/common_patterns.json`
- `index/reverse_mapping.json`

**Estimated bundle size:** ~7-8 MB (JSON indexes only, no semantic search embeddings)

---

## Open Questions

1. **Semantic search in MCPB?** The embeddings + model add ~500MB+. Probably not worth bundling. Keyword search is good enough. Could offer a "full" variant later.

2. **Platform restriction?** Currently `win32` only since FieldWorks is Windows-only. The docs/search tools work anywhere though. Could offer a cross-platform "docs only" variant.

3. **Auto-update indexes?** The MCPB format supports auto-updates for the extension itself. When upstream repos change, we'd publish a new version with updated indexes. Users get it automatically.

4. **Should `run_module`/`run_operation` be included?** They require FlexLibs/FieldWorks on the user's machine. If the user doesn't have them, those tools just return an error. This is fine -- the 6 documentation tools still provide value on their own.
