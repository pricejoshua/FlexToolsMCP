#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FlexLibs 2.0 Analyzer

Analyzes the FlexLibs 2.0 Python source code to extract API structure,
including all operations classes, their methods, and mappings to LibLCM.

Output follows the unified-api-doc/2.0 schema for consistency with
existing FLExTools-Generator extractions.
"""

import ast
import json
import os
import sys
import re
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple


def extract_docstring(node) -> str:
    """Extract docstring from a node if it exists."""
    if (hasattr(node, 'body') and node.body and
        isinstance(node.body[0], ast.Expr) and
        isinstance(node.body[0].value, ast.Constant) and
        isinstance(node.body[0].value.value, str)):
        return node.body[0].value.value.strip()
    elif (hasattr(node, 'body') and node.body and
          isinstance(node.body[0], ast.Expr) and
          isinstance(node.body[0].value, ast.Str)):
        return node.body[0].value.s.strip()
    return ""


def parse_docstring(docstring: str) -> Dict[str, Any]:
    """Parse a docstring to extract Args, Returns, Raises, Example sections."""
    result = {
        "summary": "",
        "description": "",
        "args": {},
        "returns": "",
        "raises": [],
        "example": ""
    }

    if not docstring:
        return result

    lines = docstring.split('\n')
    current_section = "description"
    current_arg = None

    for line in lines:
        stripped = line.strip()

        # Check for section headers
        if stripped.startswith("Args:"):
            current_section = "args"
            continue
        elif stripped.startswith("Returns:") or stripped.startswith("Yields:"):
            current_section = "returns"
            continue
        elif stripped.startswith("Raises:"):
            current_section = "raises"
            continue
        elif stripped.startswith("Example:"):
            current_section = "example"
            continue
        elif stripped.startswith("Note:") or stripped.startswith("Notes:"):
            current_section = "notes"
            continue

        # Process content based on section
        if current_section == "description":
            if result["description"]:
                result["description"] += "\n" + stripped
            else:
                result["description"] = stripped
        elif current_section == "args":
            # Parse argument: "arg_name (type): description" or "arg_name: description"
            arg_match = re.match(r'^(\w+)(?:\s*\(([^)]+)\))?:\s*(.*)$', stripped)
            if arg_match:
                arg_name = arg_match.group(1)
                arg_type = arg_match.group(2) or ""
                arg_desc = arg_match.group(3)
                result["args"][arg_name] = {"type": arg_type, "description": arg_desc}
                current_arg = arg_name
            elif current_arg and stripped:
                # Continuation of previous arg description
                result["args"][current_arg]["description"] += " " + stripped
        elif current_section == "returns":
            if result["returns"]:
                result["returns"] += " " + stripped
            else:
                result["returns"] = stripped
        elif current_section == "raises":
            if stripped:
                result["raises"].append(stripped)
        elif current_section == "example":
            if result["example"]:
                result["example"] += "\n" + line  # Preserve indentation
            else:
                result["example"] = line

    # Extract summary (first line of description)
    if result["description"]:
        first_para = result["description"].split('\n\n')[0]
        result["summary"] = first_para.split('.')[0] + '.' if '.' in first_para else first_para

    return result


def get_function_signature(node) -> Tuple[List[str], List[Dict]]:
    """Extract function signature and parameter details."""
    params = []
    param_details = []

    # Regular arguments
    defaults_start = len(node.args.args) - len(node.args.defaults)

    for i, arg in enumerate(node.args.args):
        if arg.arg == 'self':
            continue

        param_info = {"name": arg.arg, "type": "", "default": None}
        param_str = arg.arg

        # Type annotation
        if hasattr(arg, 'annotation') and arg.annotation:
            if isinstance(arg.annotation, ast.Name):
                param_info["type"] = arg.annotation.id
                param_str += f": {arg.annotation.id}"
            elif isinstance(arg.annotation, ast.Constant):
                param_info["type"] = str(arg.annotation.value)
                param_str += f": {arg.annotation.value}"
            elif isinstance(arg.annotation, ast.Subscript):
                # Handle Optional[X], List[X], etc.
                param_info["type"] = ast.unparse(arg.annotation) if hasattr(ast, 'unparse') else "complex"

        # Default value
        default_idx = i - defaults_start
        if default_idx >= 0 and default_idx < len(node.args.defaults):
            default = node.args.defaults[default_idx]
            if isinstance(default, ast.Constant):
                param_info["default"] = default.value
                param_str += f"={repr(default.value)}"
            elif isinstance(default, ast.Name):
                param_info["default"] = default.id
                param_str += f"={default.id}"

        params.append(param_str)
        param_details.append(param_info)

    return params, param_details


def extract_lcm_imports(tree) -> List[Dict[str, str]]:
    """Extract all SIL.LCModel imports from a module."""
    imports = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module.startswith("SIL"):
                for alias in node.names:
                    imports.append({
                        "module": module,
                        "name": alias.name,
                        "alias": alias.asname
                    })

    return imports


def analyze_method(node, class_name: str) -> Optional[Dict[str, Any]]:
    """Analyze a method definition and extract its API information."""
    if node.name.startswith('_') and node.name != '__init__':
        return None  # Skip private methods except __init__

    params, param_details = get_function_signature(node)
    docstring = extract_docstring(node)
    parsed_doc = parse_docstring(docstring)

    # Merge docstring arg info with parameter details
    for param in param_details:
        if param["name"] in parsed_doc["args"]:
            doc_arg = parsed_doc["args"][param["name"]]
            if doc_arg["type"] and not param["type"]:
                param["type"] = doc_arg["type"]
            param["description"] = doc_arg["description"]

    # Check for decorators
    is_property = False
    is_classmethod = False
    is_staticmethod = False

    for decorator in node.decorator_list:
        if isinstance(decorator, ast.Name):
            if decorator.id == "property":
                is_property = True
            elif decorator.id == "classmethod":
                is_classmethod = True
            elif decorator.id == "staticmethod":
                is_staticmethod = True

    method_info = {
        "name": node.name,
        "signature": f"{node.name}({', '.join(params)})",
        "summary": parsed_doc["summary"],
        "description": parsed_doc["description"],
        "parameters": param_details,
        "returns": parsed_doc["returns"],
        "raises": parsed_doc["raises"],
        "example": parsed_doc["example"],
        "is_property": is_property,
        "is_classmethod": is_classmethod,
        "is_staticmethod": is_staticmethod
    }

    return method_info


def analyze_class(node, module_path: str, lcm_imports: List[Dict]) -> Dict[str, Any]:
    """Analyze a class definition and extract its API information."""
    docstring = extract_docstring(node)
    parsed_doc = parse_docstring(docstring)

    # Extract base classes
    base_classes = []
    for base in node.bases:
        if isinstance(base, ast.Name):
            base_classes.append(base.id)
        elif isinstance(base, ast.Attribute):
            base_classes.append(f"{ast.unparse(base)}" if hasattr(ast, 'unparse') else base.attr)

    methods = []
    properties = []

    for item in node.body:
        if isinstance(item, ast.FunctionDef):
            method_info = analyze_method(item, node.name)
            if method_info:
                if method_info["is_property"]:
                    properties.append(method_info)
                else:
                    methods.append(method_info)

    # Determine category from module path
    category = "general"
    if "Lexicon" in module_path:
        category = "lexicon"
    elif "Grammar" in module_path:
        category = "grammar"
    elif "TextsWords" in module_path:
        category = "texts"
    elif "Notebook" in module_path:
        category = "notebook"
    elif "Lists" in module_path:
        category = "lists"
    elif "System" in module_path:
        category = "system"
    elif "Scripture" in module_path:
        category = "scripture"
    elif "Discourse" in module_path:
        category = "discourse"
    elif "Reversal" in module_path:
        category = "reversal"
    elif "Wordform" in module_path:
        category = "wordform"

    return {
        "name": node.name,
        "type": "class",
        "namespace": f"FlexLibs2.{module_path.replace('/', '.')}",
        "source_file": module_path,
        "category": category,
        "summary": parsed_doc["summary"],
        "description": parsed_doc["description"],
        "example": parsed_doc["example"],
        "base_classes": base_classes,
        "methods": sorted(methods, key=lambda m: m["name"]),
        "properties": properties,
        "lcm_dependencies": [imp["name"] for imp in lcm_imports if imp["module"].startswith("SIL.LCModel")],
        "tags": [category, "operations"] if "Operations" in node.name else [category]
    }


def analyze_python_file(file_path: Path, base_path: Path) -> Optional[Dict[str, Any]]:
    """Analyze a single Python file and extract its API structure."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        tree = ast.parse(content)

        # Get relative path for module identification
        rel_path = file_path.relative_to(base_path)
        module_path = str(rel_path.with_suffix('')).replace('\\', '/')

        lcm_imports = extract_lcm_imports(tree)

        file_info = {
            "file": str(rel_path),
            "module_path": module_path,
            "docstring": extract_docstring(tree),
            "classes": [],
            "lcm_imports": lcm_imports
        }

        # Find top-level classes
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                class_info = analyze_class(node, module_path, lcm_imports)
                file_info["classes"].append(class_info)

        return file_info

    except Exception as e:
        print(f"[WARN] Error analyzing {file_path}: {e}")
        return None


def analyze_flexlibs2(flexlibs2_path: str) -> Dict[str, Any]:
    """Analyze the entire FlexLibs 2.0 codebase."""
    base_path = Path(flexlibs2_path) / "flexlibs" / "code"

    if not base_path.exists():
        raise FileNotFoundError(f"FlexLibs 2.0 code directory not found: {base_path}")

    print(f"[INFO] Analyzing FlexLibs 2.0 at: {base_path}")

    result = {
        "_schema": "unified-api-doc/2.0",
        "_generated_at": datetime.now(timezone.utc).isoformat(),
        "_source": {
            "type": "flexlibs2",
            "path": str(flexlibs2_path),
            "description": "FlexLibs 2.0 - Deep Python wrapper for LibLCM (~90% coverage)"
        },
        "metadata": {
            "total_classes": 0,
            "total_methods": 0,
            "total_properties": 0,
            "files_analyzed": 0,
            "categories": {},
            "lcm_interfaces_used": set()
        },
        "entities": {},
        "categories": {},
        "lcm_mapping": {}  # Maps FlexLibs2 methods to LibLCM interfaces
    }

    # Analyze all Python files recursively
    for py_file in base_path.rglob("*.py"):
        if py_file.name.startswith("__"):
            continue

        file_info = analyze_python_file(py_file, base_path)
        if file_info and file_info["classes"]:
            result["metadata"]["files_analyzed"] += 1

            for class_info in file_info["classes"]:
                entity_id = class_info["name"]
                result["entities"][entity_id] = class_info
                result["metadata"]["total_classes"] += 1
                result["metadata"]["total_methods"] += len(class_info["methods"])
                result["metadata"]["total_properties"] += len(class_info["properties"])

                # Track categories
                cat = class_info["category"]
                if cat not in result["metadata"]["categories"]:
                    result["metadata"]["categories"][cat] = 0
                result["metadata"]["categories"][cat] += 1

                # Track LCM dependencies
                for dep in class_info["lcm_dependencies"]:
                    result["metadata"]["lcm_interfaces_used"].add(dep)

                # Build LCM mapping
                for method in class_info["methods"]:
                    method_key = f"{entity_id}.{method['name']}"
                    result["lcm_mapping"][method_key] = {
                        "class": entity_id,
                        "method": method["name"],
                        "lcm_deps": class_info["lcm_dependencies"]
                    }

    # Convert set to list for JSON serialization
    result["metadata"]["lcm_interfaces_used"] = sorted(list(result["metadata"]["lcm_interfaces_used"]))

    # Build category index
    for entity_id, entity in result["entities"].items():
        cat = entity["category"]
        if cat not in result["categories"]:
            result["categories"][cat] = {
                "description": f"Operations related to {cat}",
                "entities": []
            }
        result["categories"][cat]["entities"].append(entity_id)

    return result


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Analyze FlexLibs 2.0 Python API")
    parser.add_argument("--flexlibs2-path",
                        default=r"D:\Github\flexlibs2",
                        help="Path to FlexLibs 2.0 repository")
    parser.add_argument("--output", "-o",
                        default="flexlibs2_api.json",
                        help="Output JSON file")

    args = parser.parse_args()

    try:
        api_data = analyze_flexlibs2(args.flexlibs2_path)

        print(f"[INFO] Writing results to: {args.output}")
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(api_data, f, indent=2, ensure_ascii=False)

        # Print summary
        print(f"\n[DONE] FlexLibs 2.0 Analysis Complete")
        print(f"  Classes: {api_data['metadata']['total_classes']}")
        print(f"  Methods: {api_data['metadata']['total_methods']}")
        print(f"  Properties: {api_data['metadata']['total_properties']}")
        print(f"  Files analyzed: {api_data['metadata']['files_analyzed']}")
        print(f"  LCM interfaces referenced: {len(api_data['metadata']['lcm_interfaces_used'])}")
        print(f"\n  Categories:")
        for cat, count in sorted(api_data['metadata']['categories'].items()):
            print(f"    {cat}: {count} classes")

    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
