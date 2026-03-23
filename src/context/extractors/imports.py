"""Extract imports from source code files."""

import os
import re


def extract_imports(content: str, language: str) -> list[str]:
    """Extract import statements from source code.

    Args:
        content: Source code content
        language: Programming language ("python", "javascript", "typescript", "go")

    Returns:
        List of imported module/file names
    """
    imports = []

    if language == "python":
        imports = _extract_python_imports(content)
    elif language in ("javascript", "typescript"):
        imports = _extract_js_imports(content)
    elif language == "go":
        imports = _extract_go_imports(content)

    return imports


def _extract_python_imports(content: str) -> list[str]:
    """Extract imports from Python code."""
    imports = []

    # Match: from x import y, from x.y import z
    from_pattern = r"^from\s+([\w.]+)\s+import"
    # Match: import x, import x.y
    import_pattern = r"^import\s+([\w.]+)"

    for line in content.split("\n"):
        line = line.strip()

        match = re.match(from_pattern, line)
        if match:
            imports.append(match.group(1))
            continue

        match = re.match(import_pattern, line)
        if match:
            # Handle: import x, y, z
            modules = match.group(1).split(",")
            imports.extend(m.strip().split()[0] for m in modules)

    return imports


def _extract_js_imports(content: str) -> list[str]:
    """Extract imports from JavaScript/TypeScript code."""
    imports = []

    # Match: import x from 'path' or import x from "path"
    # Match: import { x } from 'path'
    # Match: import 'path'
    # Match: require('path')
    patterns = [
        r"import\s+.*?\s+from\s+['\"]([^'\"]+)['\"]",
        r"import\s+['\"]([^'\"]+)['\"]",
        r"require\s*\(\s*['\"]([^'\"]+)['\"]\s*\)",
    ]

    for pattern in patterns:
        matches = re.findall(pattern, content)
        imports.extend(matches)

    return imports


def _extract_go_imports(content: str) -> list[str]:
    """Extract imports from Go code."""
    imports = []

    # Match single import: import "path"
    single_pattern = r'import\s+"([^"]+)"'
    # Match import block
    block_pattern = r"import\s*\(([\s\S]*?)\)"

    # Single imports
    imports.extend(re.findall(single_pattern, content))

    # Block imports
    for block in re.findall(block_pattern, content):
        # Extract paths from block
        paths = re.findall(r'"([^"]+)"', block)
        imports.extend(paths)

    return imports


def resolve_import_path(import_name: str, source_file: str, language: str) -> str | None:
    """Resolve an import name to a file path within the repo.

    Args:
        import_name: The imported module/file name
        source_file: Path of the file containing the import
        language: Programming language

    Returns:
        Resolved file path or None if not resolvable
    """
    source_dir = os.path.dirname(source_file)

    if language == "python":
        return _resolve_python_import(import_name, source_dir)
    elif language in ("javascript", "typescript"):
        return _resolve_js_import(import_name, source_dir)

    return None


def _resolve_python_import(import_name: str, source_dir: str) -> str | None:
    """Resolve Python import to file path."""
    # Skip standard library and third-party packages
    if not import_name.startswith(".") and "." not in import_name:
        # Likely stdlib or third-party
        return None

    # Convert relative imports
    if import_name.startswith("."):
        # Relative import: .foo -> foo, ..foo -> ../foo
        dots = len(import_name) - len(import_name.lstrip("."))
        module = import_name.lstrip(".")
        if dots == 1:
            path_prefix = source_dir
        else:
            path_prefix = os.path.normpath(os.path.join(source_dir, *[".."] * (dots - 1)))
    else:
        # Absolute import from project root
        path_prefix = ""
        module = import_name

    # Convert module.name to module/name
    module_path = module.replace(".", "/")

    # Try different file patterns
    candidates = [
        f"{os.path.join(path_prefix, module_path)}.py",
        f"{os.path.join(path_prefix, module_path)}/__init__.py",
    ]

    # Return first candidate (actual existence check happens during fetch)
    return candidates[0] if candidates else None


def _resolve_js_import(import_name: str, source_dir: str) -> str | None:
    """Resolve JavaScript/TypeScript import to file path."""
    # Skip node_modules
    if not import_name.startswith(".") and not import_name.startswith("/"):
        return None

    # Resolve relative path
    if import_name.startswith("."):
        resolved = os.path.normpath(os.path.join(source_dir, import_name))
    else:
        resolved = import_name.lstrip("/")

    # Add extension if missing
    if not os.path.splitext(resolved)[1]:
        # Try common extensions
        return f"{resolved}.ts"  # Default to .ts, will try others during fetch

    return resolved


def detect_language(file_path: str) -> str | None:
    """Detect programming language from file extension."""
    ext = os.path.splitext(file_path)[1].lower()
    extension_map = {
        ".py": "python",
        ".js": "javascript",
        ".jsx": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".go": "go",
    }
    return extension_map.get(ext)
