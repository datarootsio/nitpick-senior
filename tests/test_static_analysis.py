"""Tests for static analysis parser."""

import json
import tempfile
from pathlib import Path

import pytest

from src.context.extractors.static_analysis import (
    format_findings,
    parse_semgrep_json,
)
from src.context.models import StaticAnalysisFinding


class TestParseSemgrepJson:
    """Tests for parse_semgrep_json function."""

    def test_parses_valid_semgrep_output(self, tmp_path: Path) -> None:
        """Test parsing valid semgrep JSON output."""
        semgrep_data = {
            "results": [
                {
                    "path": "src/foo.py",
                    "start": {"line": 42},
                    "check_id": "python.lang.security.audit.dangerous-exec",
                    "extra": {
                        "message": "Dangerous use of exec",
                        "severity": "WARNING",
                    },
                },
                {
                    "path": "src/bar.py",
                    "start": {"line": 10},
                    "check_id": "python.lang.security.audit.eval",
                    "extra": {
                        "message": "Use of eval is dangerous",
                        "severity": "ERROR",
                    },
                },
            ]
        }

        json_file = tmp_path / "semgrep.json"
        json_file.write_text(json.dumps(semgrep_data))

        changed_files = ["src/foo.py", "src/bar.py"]
        findings = parse_semgrep_json(str(json_file), changed_files)

        assert len(findings) == 2
        # ERROR should come first (sorted by severity)
        assert findings[0].severity == "ERROR"
        assert findings[0].file == "src/bar.py"
        assert findings[0].line == 10
        assert findings[1].severity == "WARNING"
        assert findings[1].file == "src/foo.py"

    def test_filters_to_changed_files_only(self, tmp_path: Path) -> None:
        """Test that only findings for changed files are returned."""
        semgrep_data = {
            "results": [
                {
                    "path": "src/changed.py",
                    "start": {"line": 1},
                    "check_id": "rule1",
                    "extra": {"message": "Issue 1", "severity": "WARNING"},
                },
                {
                    "path": "src/unchanged.py",
                    "start": {"line": 1},
                    "check_id": "rule2",
                    "extra": {"message": "Issue 2", "severity": "WARNING"},
                },
            ]
        }

        json_file = tmp_path / "semgrep.json"
        json_file.write_text(json.dumps(semgrep_data))

        changed_files = ["src/changed.py"]
        findings = parse_semgrep_json(str(json_file), changed_files)

        assert len(findings) == 1
        assert findings[0].file == "src/changed.py"

    def test_handles_missing_file(self) -> None:
        """Test handling of missing JSON file."""
        findings = parse_semgrep_json("/nonexistent/path.json", ["src/foo.py"])
        assert findings == []

    def test_handles_invalid_json(self, tmp_path: Path) -> None:
        """Test handling of invalid JSON content."""
        json_file = tmp_path / "invalid.json"
        json_file.write_text("not valid json")

        findings = parse_semgrep_json(str(json_file), ["src/foo.py"])
        assert findings == []

    def test_handles_empty_results(self, tmp_path: Path) -> None:
        """Test handling of empty results array."""
        semgrep_data = {"results": []}

        json_file = tmp_path / "empty.json"
        json_file.write_text(json.dumps(semgrep_data))

        findings = parse_semgrep_json(str(json_file), ["src/foo.py"])
        assert findings == []

    def test_normalizes_paths(self, tmp_path: Path) -> None:
        """Test that paths are normalized for matching."""
        semgrep_data = {
            "results": [
                {
                    "path": "./src/foo.py",  # With leading ./
                    "start": {"line": 1},
                    "check_id": "rule1",
                    "extra": {"message": "Issue", "severity": "WARNING"},
                },
            ]
        }

        json_file = tmp_path / "semgrep.json"
        json_file.write_text(json.dumps(semgrep_data))

        # Changed file without leading ./
        changed_files = ["src/foo.py"]
        findings = parse_semgrep_json(str(json_file), changed_files)

        assert len(findings) == 1

    def test_sorts_by_severity(self, tmp_path: Path) -> None:
        """Test that findings are sorted by severity."""
        semgrep_data = {
            "results": [
                {
                    "path": "a.py",
                    "start": {"line": 1},
                    "check_id": "r1",
                    "extra": {"message": "Info", "severity": "INFO"},
                },
                {
                    "path": "b.py",
                    "start": {"line": 1},
                    "check_id": "r2",
                    "extra": {"message": "Error", "severity": "ERROR"},
                },
                {
                    "path": "c.py",
                    "start": {"line": 1},
                    "check_id": "r3",
                    "extra": {"message": "Warning", "severity": "WARNING"},
                },
            ]
        }

        json_file = tmp_path / "semgrep.json"
        json_file.write_text(json.dumps(semgrep_data))

        changed_files = ["a.py", "b.py", "c.py"]
        findings = parse_semgrep_json(str(json_file), changed_files)

        assert len(findings) == 3
        assert findings[0].severity == "ERROR"
        assert findings[1].severity == "WARNING"
        assert findings[2].severity == "INFO"

    def test_normalizes_unknown_severity(self, tmp_path: Path) -> None:
        """Test that unknown severity is normalized to WARNING."""
        semgrep_data = {
            "results": [
                {
                    "path": "src/foo.py",
                    "start": {"line": 1},
                    "check_id": "rule1",
                    "extra": {"message": "Issue", "severity": "UNKNOWN"},
                },
            ]
        }

        json_file = tmp_path / "semgrep.json"
        json_file.write_text(json.dumps(semgrep_data))

        findings = parse_semgrep_json(str(json_file), ["src/foo.py"])

        assert len(findings) == 1
        assert findings[0].severity == "WARNING"


class TestFormatFindings:
    """Tests for format_findings function."""

    def test_formats_findings(self) -> None:
        """Test formatting findings as text."""
        findings = [
            StaticAnalysisFinding(
                file="src/foo.py",
                line=42,
                rule_id="rule1",
                message="An issue",
                severity="ERROR",
            ),
            StaticAnalysisFinding(
                file="src/bar.py",
                line=10,
                rule_id="rule2",
                message="Another issue",
                severity="WARNING",
            ),
        ]

        text = format_findings(findings)

        assert "### Static Analysis Findings" in text
        assert "**src/foo.py:42** [ERROR]" in text
        assert "`rule1`" in text
        assert "An issue" in text
        assert "**src/bar.py:10** [WARNING]" in text

    def test_empty_findings(self) -> None:
        """Test formatting empty findings list."""
        text = format_findings([])
        assert text == ""
