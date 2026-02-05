# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the FlexLibs 2.0 analyzer (if updating extractions)
python src/flexlibs2_analyzer.py --flexlibs2-path D:/Github/flexlibs2 --output index/flexlibs/flexlibs2_api.json

# Test the MCP server loads correctly
python -c "from src.server import APIIndex, get_index_dir; i=APIIndex.load(get_index_dir()); print(f'Loaded {len(i.flexlibs2.get(\"entities\",{}))} FlexLibs2 entities')"

# Run the MCP server (for Claude Code integration)
python src/server.py
```

## Project Overview

FlexTools MCP is an MCP server that enables AI assistants (Claude Code, Copilot, Gemini CLI) to help users write FlexTools scripts for editing FieldWorks lexicons. The server provides indexed, searchable documentation of the LibLCM and FlexLibs APIs with usage examples.

### Architecture Stack
```
User Request -> AI Assistant -> MCP Server -> Indexed Documentation
                    |
            Generated FlexTools Script
                    |
            FLExTools (IronPython)
                    |
            FlexLibs 2.0 (Python wrappers)
                    |
            LibLCM (C# library)
                    |
            FieldWorks Database
```

## Related Repositories

These external repositories are dependencies and documentation sources (located in D:\Github\):

| Repository | Purpose | Local Path |
|------------|---------|------------|
| **FieldWorks** | User-facing GUI for managing lexicons | D:\Github\Fieldworks |
| **LibLCM** | C# data model and API for FieldWorks databases | D:\Github\liblcm |
| **FlexLibs** (stable) | Shallow IronPython wrapper (~40 functions) | D:\Github\flexlibs |
| **FlexLibs 2.0** | Deep IronPython wrapper (~90% coverage) | D:\Github\flexlibs2 |
| **FlexTools** | GUI app for running Python macros | D:\Github\FlexTools |
| **FLExTools-Generator** | Existing work extracting LibLCM/FlexLibs info (reference) | D:\Github\FLExTools-Generator |

## Technology Stack

- **Python 3.10+** for MCP server and agents
- **ast module** for Python parsing
- **Roslyn or C# reflection** for C# parsing
- **sentence-transformers** for semantic search
- **FAISS or Chroma** for vector storage
- **pytest** for test suite

## Expected Project Structure

```
/index
  /liblcm           # Parsed C# API documentation
  /flexlibs         # Python wrapper mappings
  /examples         # Usage patterns from FieldWorks
  /tests            # Test suite and coverage reports
  metadata.json
  version.json

/mcp_server
  server.py         # Main MCP server
  search.py         # Semantic search implementation
  validation.py     # Script validation
  requirements.txt
```

## MCP Server Tools

The server will expose these tools:
- `get_object_api(object_type, include_flexlibs, abstraction_level)` - Get methods/properties for objects like ILexSense
- `search_by_capability(query, max_results)` - Semantic search for methods
- `get_navigation_path(from_object, to_object)` - Find navigation paths between objects
- `find_examples(method_name, operation_type)` - Get real usage examples
- `validate_script(script_text)` - Check if script uses valid API calls

## API Abstraction Levels

Scripts can target three API levels:
1. **LibLCM (C#)**: Direct calls, most powerful, most verbose
2. **FlexLibs Light**: Limited (~40 functions), stable
3. **FlexLibs 2.0**: Comprehensive (~90% coverage), Pythonic, beta

Default behavior is "auto" - use FlexLibs 2.0 when available, fall back to LibLCM.

## Key Technical Decisions

- **Static analysis primary**: Parse C#/Python source with AST tools, not heavy AI
- **AI for enrichment only**: Use AI for missing descriptions, semantic categorization, C# to IronPython conversion
- **Object-centric organization**: Index is organized around objects (ILexEntry, ILexSense, etc.) with their methods, properties, and relationships
- **Validation-first**: Multiple validation layers between phases, test against real FieldWorks database
