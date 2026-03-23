"""Tests for import extraction."""

from src.context.extractors.imports import (
    detect_language,
    extract_imports,
    resolve_import_path,
)


class TestDetectLanguage:
    def test_python_files(self):
        assert detect_language("main.py") == "python"
        assert detect_language("src/utils.py") == "python"

    def test_javascript_files(self):
        assert detect_language("index.js") == "javascript"
        assert detect_language("component.jsx") == "javascript"

    def test_typescript_files(self):
        assert detect_language("app.ts") == "typescript"
        assert detect_language("component.tsx") == "typescript"

    def test_go_files(self):
        assert detect_language("main.go") == "go"

    def test_unknown_files(self):
        assert detect_language("style.css") is None
        assert detect_language("data.json") is None
        assert detect_language("README.md") is None


class TestExtractPythonImports:
    def test_simple_import(self):
        code = "import os"
        imports = extract_imports(code, "python")
        assert "os" in imports

    def test_from_import(self):
        code = "from collections import defaultdict"
        imports = extract_imports(code, "python")
        assert "collections" in imports

    def test_relative_import(self):
        code = "from .utils import helper"
        imports = extract_imports(code, "python")
        assert ".utils" in imports

    def test_parent_relative_import(self):
        code = "from ..models import User"
        imports = extract_imports(code, "python")
        assert "..models" in imports

    def test_multiple_imports(self):
        code = """
import os
import sys
from collections import defaultdict
from .utils import helper
"""
        imports = extract_imports(code, "python")
        assert "os" in imports
        assert "sys" in imports
        assert "collections" in imports
        assert ".utils" in imports


class TestExtractJSImports:
    def test_named_import(self):
        code = "import { useState } from 'react'"
        imports = extract_imports(code, "javascript")
        assert "react" in imports

    def test_default_import(self):
        code = "import React from 'react'"
        imports = extract_imports(code, "javascript")
        assert "react" in imports

    def test_relative_import(self):
        code = "import { helper } from './utils'"
        imports = extract_imports(code, "javascript")
        assert "./utils" in imports

    def test_require(self):
        code = "const express = require('express')"
        imports = extract_imports(code, "javascript")
        assert "express" in imports

    def test_side_effect_import(self):
        code = "import './styles.css'"
        imports = extract_imports(code, "javascript")
        assert "./styles.css" in imports

    def test_multiple_imports(self):
        code = """
import React from 'react'
import { useState, useEffect } from 'react'
import { helper } from './utils'
const lodash = require('lodash')
"""
        imports = extract_imports(code, "javascript")
        assert "react" in imports
        assert "./utils" in imports
        assert "lodash" in imports


class TestExtractGoImports:
    def test_single_import(self):
        code = 'import "fmt"'
        imports = extract_imports(code, "go")
        assert "fmt" in imports

    def test_import_block(self):
        code = '''
import (
    "fmt"
    "os"
    "github.com/user/pkg"
)
'''
        imports = extract_imports(code, "go")
        assert "fmt" in imports
        assert "os" in imports
        assert "github.com/user/pkg" in imports


class TestResolvePythonImportPath:
    def test_relative_import_same_dir(self):
        path = resolve_import_path(".utils", "src/main.py", "python")
        assert path == "src/utils.py"

    def test_relative_import_parent_dir(self):
        path = resolve_import_path("..models", "src/api/handlers.py", "python")
        assert path == "src/models.py"

    def test_absolute_import_skipped(self):
        # stdlib imports should return None
        path = resolve_import_path("os", "src/main.py", "python")
        assert path is None


class TestResolveJSImportPath:
    def test_relative_import(self):
        path = resolve_import_path("./utils", "src/main.ts", "typescript")
        assert path is not None
        assert "utils" in path

    def test_node_modules_skipped(self):
        path = resolve_import_path("react", "src/main.tsx", "typescript")
        assert path is None

    def test_scoped_package_skipped(self):
        path = resolve_import_path("@types/node", "src/main.ts", "typescript")
        assert path is None
