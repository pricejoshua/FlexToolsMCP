#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FlexTools MCP Server

An MCP server that provides AI assistants with searchable documentation
of the LibLCM and FlexLibs APIs for generating FlexTools scripts.
"""

import json
import asyncio
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    CallToolResult,
)


@dataclass
class APIIndex:
    """Holds the loaded API documentation indexes."""
    liblcm: dict = None
    flexlibs2: dict = None

    @classmethod
    def load(cls, index_dir: Path) -> "APIIndex":
        """Load all API indexes from the index directory."""
        index = cls()

        # Load LibLCM
        liblcm_path = index_dir / "liblcm" / "flex-api-enhanced.json"
        if liblcm_path.exists():
            with open(liblcm_path, "r", encoding="utf-8") as f:
                index.liblcm = json.load(f)

        # Load FlexLibs 2.0
        flexlibs2_path = index_dir / "flexlibs" / "flexlibs2_api.json"
        if flexlibs2_path.exists():
            with open(flexlibs2_path, "r", encoding="utf-8") as f:
                index.flexlibs2 = json.load(f)

        return index


# Initialize the MCP server
server = Server("flextools-mcp")

# Global index (loaded on startup)
api_index: Optional[APIIndex] = None


def get_index_dir() -> Path:
    """Get the index directory path."""
    return Path(__file__).parent.parent / "index"


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="get_object_api",
            description="Get all methods and properties for a FlexTools/LibLCM object like ILexEntry, LexSenseOperations, etc. Returns object-centric documentation including methods, properties, and relationships.",
            inputSchema={
                "type": "object",
                "properties": {
                    "object_type": {
                        "type": "string",
                        "description": "The object type to look up (e.g., 'ILexEntry', 'LexEntryOperations', 'ILexSense')"
                    },
                    "include_flexlibs2": {
                        "type": "boolean",
                        "description": "Include FlexLibs 2.0 wrapper methods (default: true)",
                        "default": True
                    },
                    "include_liblcm": {
                        "type": "boolean",
                        "description": "Include raw LibLCM interface info (default: true)",
                        "default": True
                    }
                },
                "required": ["object_type"]
            }
        ),
        Tool(
            name="search_by_capability",
            description="Search for methods/functions by what they do. Use natural language queries like 'add gloss to sense', 'create new entry', 'get all entries'.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language description of what you want to do"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 10)",
                        "default": 10
                    },
                    "source": {
                        "type": "string",
                        "enum": ["all", "flexlibs2", "liblcm"],
                        "description": "Which API source to search (default: all)",
                        "default": "all"
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="get_navigation_path",
            description="Find how to navigate from one object type to another in the FieldWorks data model. For example, how to get from ILexEntry to ILexExampleSentence.",
            inputSchema={
                "type": "object",
                "properties": {
                    "from_object": {
                        "type": "string",
                        "description": "Starting object type (e.g., 'ILexEntry')"
                    },
                    "to_object": {
                        "type": "string",
                        "description": "Target object type (e.g., 'ILexExampleSentence')"
                    }
                },
                "required": ["from_object", "to_object"]
            }
        ),
        Tool(
            name="find_examples",
            description="Find code examples for a specific method or operation type.",
            inputSchema={
                "type": "object",
                "properties": {
                    "method_name": {
                        "type": "string",
                        "description": "Specific method name to find examples for"
                    },
                    "operation_type": {
                        "type": "string",
                        "enum": ["create", "read", "update", "delete", "iterate", "search"],
                        "description": "Type of operation to find examples for"
                    },
                    "object_type": {
                        "type": "string",
                        "description": "Object type to filter examples (e.g., 'LexEntry', 'Sense')"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of examples to return (default: 5)",
                        "default": 5
                    }
                }
            }
        ),
        Tool(
            name="list_categories",
            description="List all available API categories (lexicon, grammar, texts, etc.) with their entity counts.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="list_entities_in_category",
            description="List all entities (classes/interfaces) in a specific category.",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Category name (e.g., 'lexicon', 'grammar', 'texts')"
                    }
                },
                "required": ["category"]
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls."""
    global api_index

    if api_index is None:
        api_index = APIIndex.load(get_index_dir())

    if name == "get_object_api":
        return await handle_get_object_api(arguments)
    elif name == "search_by_capability":
        return await handle_search_by_capability(arguments)
    elif name == "get_navigation_path":
        return await handle_get_navigation_path(arguments)
    elif name == "find_examples":
        return await handle_find_examples(arguments)
    elif name == "list_categories":
        return await handle_list_categories(arguments)
    elif name == "list_entities_in_category":
        return await handle_list_entities_in_category(arguments)
    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def handle_get_object_api(args: dict) -> list[TextContent]:
    """Get API documentation for a specific object type."""
    object_type = args["object_type"]
    include_flexlibs2 = args.get("include_flexlibs2", True)
    include_liblcm = args.get("include_liblcm", True)

    result = {"object_type": object_type, "found": False}

    # Search in FlexLibs 2.0
    if include_flexlibs2 and api_index.flexlibs2:
        entities = api_index.flexlibs2.get("entities", {})
        # Try exact match first
        if object_type in entities:
            result["flexlibs2"] = entities[object_type]
            result["found"] = True
        else:
            # Try partial match (e.g., "LexEntry" matches "LexEntryOperations")
            for name, entity in entities.items():
                if object_type.lower() in name.lower():
                    if "flexlibs2_matches" not in result:
                        result["flexlibs2_matches"] = []
                    result["flexlibs2_matches"].append({
                        "name": name,
                        "category": entity.get("category"),
                        "methods_count": len(entity.get("methods", []))
                    })
                    result["found"] = True

    # Search in LibLCM
    if include_liblcm and api_index.liblcm:
        entities = api_index.liblcm.get("entities", {})
        if object_type in entities:
            result["liblcm"] = entities[object_type]
            result["found"] = True
        else:
            # Try partial match
            for name, entity in entities.items():
                if object_type.lower() in name.lower():
                    if "liblcm_matches" not in result:
                        result["liblcm_matches"] = []
                    result["liblcm_matches"].append({
                        "name": name,
                        "type": entity.get("type"),
                        "category": entity.get("category")
                    })
                    if len(result.get("liblcm_matches", [])) >= 10:
                        break
                    result["found"] = True

    if not result["found"]:
        result["message"] = f"No API documentation found for '{object_type}'. Try searching with search_by_capability or list_categories to explore available APIs."

    return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]


async def handle_search_by_capability(args: dict) -> list[TextContent]:
    """Search for methods by capability description."""
    query = args["query"].lower()
    max_results = args.get("max_results", 10)
    source = args.get("source", "all")

    results = []

    # Synonym expansion for common operations
    synonyms = {
        "add": ["add", "set", "create", "insert", "append"],
        "set": ["set", "add", "update", "modify", "assign"],
        "get": ["get", "fetch", "retrieve", "find", "read"],
        "delete": ["delete", "remove", "clear", "erase"],
        "remove": ["remove", "delete", "clear"],
        "create": ["create", "add", "new", "make"],
        "update": ["update", "set", "modify", "change"],
        "find": ["find", "search", "get", "lookup", "query"],
        "list": ["list", "getall", "all", "iterate", "enumerate"],
    }

    # Expand query terms with synonyms
    query_terms = query.split()
    expanded_terms = set(query_terms)
    for term in query_terms:
        if term in synonyms:
            expanded_terms.update(synonyms[term])

    # Search FlexLibs 2.0 (preferred - better documented)
    if source in ["all", "flexlibs2"] and api_index.flexlibs2:
        for entity_name, entity in api_index.flexlibs2.get("entities", {}).items():
            for method in entity.get("methods", []):
                # Score based on term matches in name, description, summary
                score = 0
                text_to_search = f"{method.get('name', '')} {method.get('description', '')} {method.get('summary', '')}".lower()

                for term in expanded_terms:
                    if term in text_to_search:
                        score += 1
                    if term in method.get('name', '').lower():
                        score += 2  # Bonus for name match

                if score > 0:
                    results.append({
                        "score": score,
                        "source": "flexlibs2",
                        "class": entity_name,
                        "method": method.get("name"),
                        "signature": method.get("signature"),
                        "summary": method.get("summary", method.get("description", "")[:100]),
                        "has_example": bool(method.get("example"))
                    })

    # Search LibLCM
    if source in ["all", "liblcm"] and api_index.liblcm:
        for entity_name, entity in api_index.liblcm.get("entities", {}).items():
            for method in entity.get("methods", []):
                score = 0
                text_to_search = f"{method.get('name', '')} {method.get('description', '')}".lower()

                for term in expanded_terms:
                    if term in text_to_search:
                        score += 1
                    if term in method.get('name', '').lower():
                        score += 2

                if score > 0:
                    results.append({
                        "score": score,
                        "source": "liblcm",
                        "class": entity_name,
                        "method": method.get("name"),
                        "signature": method.get("signature"),
                        "summary": method.get("description", "")[:100]
                    })

    # Sort by score and limit results
    results.sort(key=lambda x: x["score"], reverse=True)
    results = results[:max_results]

    return [TextContent(type="text", text=json.dumps({
        "query": query,
        "results_count": len(results),
        "results": results
    }, indent=2))]


async def handle_get_navigation_path(args: dict) -> list[TextContent]:
    """Find navigation path between two object types."""
    from_obj = args["from_object"]
    to_obj = args["to_object"]

    # Common navigation patterns in FieldWorks
    # These are the key relationships in the lexicon model
    navigation_patterns = {
        ("ILexEntry", "ILexSense"): {
            "path": ["ILexEntry", "SensesOS", "ILexSense"],
            "code": "for sense in entry.SensesOS:\n    # work with sense",
            "description": "Entry owns a sequence of senses via SensesOS property"
        },
        ("ILexSense", "ILexEntry"): {
            "path": ["ILexSense", "Entry", "ILexEntry"],
            "code": "entry = sense.Entry",
            "description": "Each sense has a reference back to its owning entry"
        },
        ("ILexSense", "ILexExampleSentence"): {
            "path": ["ILexSense", "ExamplesOS", "ILexExampleSentence"],
            "code": "for example in sense.ExamplesOS:\n    # work with example",
            "description": "Sense owns a sequence of example sentences via ExamplesOS"
        },
        ("ILexEntry", "ILexExampleSentence"): {
            "path": ["ILexEntry", "SensesOS", "ILexSense", "ExamplesOS", "ILexExampleSentence"],
            "code": "for sense in entry.SensesOS:\n    for example in sense.ExamplesOS:\n        # work with example",
            "description": "Navigate through senses to reach example sentences"
        },
        ("ILexEntry", "IMoForm"): {
            "path": ["ILexEntry", "LexemeFormOA", "IMoForm"],
            "code": "lexeme_form = entry.LexemeFormOA\n# or\nfor form in entry.AlternateFormsOS:\n    # work with alternate form",
            "description": "Entry has a primary lexeme form (LexemeFormOA) and alternate forms (AlternateFormsOS)"
        },
    }

    # Normalize object names
    from_normalized = from_obj.replace("Operations", "")
    to_normalized = to_obj.replace("Operations", "")

    # Add 'I' prefix if missing for interfaces
    if not from_normalized.startswith("I"):
        from_normalized = f"I{from_normalized}"
    if not to_normalized.startswith("I"):
        to_normalized = f"I{to_normalized}"

    key = (from_normalized, to_normalized)

    if key in navigation_patterns:
        result = navigation_patterns[key]
        result["from"] = from_obj
        result["to"] = to_obj
        result["found"] = True
    else:
        result = {
            "from": from_obj,
            "to": to_obj,
            "found": False,
            "message": f"No predefined navigation path from {from_obj} to {to_obj}. Try using get_object_api to explore the properties of {from_obj}.",
            "hint": "Look for properties ending in OS (Owning Sequence), OC (Owning Collection), RA (Reference Atomic), etc."
        }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def handle_find_examples(args: dict) -> list[TextContent]:
    """Find code examples for methods or operations."""
    method_name = args.get("method_name")
    operation_type = args.get("operation_type")
    object_type = args.get("object_type")
    max_results = args.get("max_results", 5)

    examples = []

    # Search FlexLibs 2.0 for examples (it has 82% example coverage)
    if api_index.flexlibs2:
        for entity_name, entity in api_index.flexlibs2.get("entities", {}).items():
            # Filter by object type if specified
            if object_type and object_type.lower() not in entity_name.lower():
                continue

            for method in entity.get("methods", []):
                # Filter by method name if specified
                if method_name and method_name.lower() not in method.get("name", "").lower():
                    continue

                # Filter by operation type if specified
                if operation_type:
                    name_lower = method.get("name", "").lower()
                    matches_op = False
                    if operation_type == "create" and any(x in name_lower for x in ["create", "add", "new"]):
                        matches_op = True
                    elif operation_type == "read" and any(x in name_lower for x in ["get", "find", "fetch"]):
                        matches_op = True
                    elif operation_type == "update" and any(x in name_lower for x in ["set", "update", "modify"]):
                        matches_op = True
                    elif operation_type == "delete" and any(x in name_lower for x in ["delete", "remove"]):
                        matches_op = True
                    elif operation_type == "iterate" and any(x in name_lower for x in ["getall", "list", "iterate"]):
                        matches_op = True
                    elif operation_type == "search" and any(x in name_lower for x in ["find", "search", "query"]):
                        matches_op = True

                    if not matches_op:
                        continue

                # Check if method has an example
                if method.get("example"):
                    examples.append({
                        "class": entity_name,
                        "method": method.get("name"),
                        "signature": method.get("signature"),
                        "description": method.get("summary", method.get("description", ""))[:150],
                        "example": method.get("example")
                    })

                    if len(examples) >= max_results:
                        break

            if len(examples) >= max_results:
                break

    return [TextContent(type="text", text=json.dumps({
        "query": {
            "method_name": method_name,
            "operation_type": operation_type,
            "object_type": object_type
        },
        "results_count": len(examples),
        "examples": examples
    }, indent=2))]


async def handle_list_categories(args: dict) -> list[TextContent]:
    """List all available API categories."""
    categories = {}

    # From FlexLibs 2.0
    if api_index.flexlibs2:
        fl2_cats = api_index.flexlibs2.get("categories", {})
        for cat_name, cat_data in fl2_cats.items():
            if cat_name not in categories:
                categories[cat_name] = {"flexlibs2_count": 0, "liblcm_count": 0}
            categories[cat_name]["flexlibs2_count"] = len(cat_data.get("entities", []))

    # From LibLCM
    if api_index.liblcm:
        for entity in api_index.liblcm.get("entities", {}).values():
            cat = entity.get("category", "uncategorized")
            if cat not in categories:
                categories[cat] = {"flexlibs2_count": 0, "liblcm_count": 0}
            categories[cat]["liblcm_count"] += 1

    return [TextContent(type="text", text=json.dumps({
        "categories": categories,
        "total_categories": len(categories)
    }, indent=2))]


async def handle_list_entities_in_category(args: dict) -> list[TextContent]:
    """List all entities in a specific category."""
    category = args["category"].lower()

    entities = {"flexlibs2": [], "liblcm": []}

    # From FlexLibs 2.0
    if api_index.flexlibs2:
        for entity_name, entity in api_index.flexlibs2.get("entities", {}).items():
            if entity.get("category", "").lower() == category:
                entities["flexlibs2"].append({
                    "name": entity_name,
                    "methods_count": len(entity.get("methods", [])),
                    "summary": entity.get("summary", "")[:100]
                })

    # From LibLCM
    if api_index.liblcm:
        for entity_name, entity in api_index.liblcm.get("entities", {}).items():
            if entity.get("category", "").lower() == category:
                entities["liblcm"].append({
                    "name": entity_name,
                    "type": entity.get("type"),
                    "summary": entity.get("summary", entity.get("description", ""))[:100]
                })

    return [TextContent(type="text", text=json.dumps({
        "category": category,
        "entities": entities,
        "counts": {
            "flexlibs2": len(entities["flexlibs2"]),
            "liblcm": len(entities["liblcm"])
        }
    }, indent=2))]


async def main():
    """Run the MCP server."""
    global api_index

    # Pre-load indexes
    print("[INFO] Loading API indexes...", file=__import__("sys").stderr)
    api_index = APIIndex.load(get_index_dir())

    if api_index.liblcm:
        print(f"[OK] LibLCM: {len(api_index.liblcm.get('entities', {}))} entities", file=__import__("sys").stderr)
    else:
        print("[WARN] LibLCM index not found", file=__import__("sys").stderr)

    if api_index.flexlibs2:
        print(f"[OK] FlexLibs 2.0: {len(api_index.flexlibs2.get('entities', {}))} entities", file=__import__("sys").stderr)
    else:
        print("[WARN] FlexLibs 2.0 index not found", file=__import__("sys").stderr)

    print("[INFO] Starting MCP server...", file=__import__("sys").stderr)

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
