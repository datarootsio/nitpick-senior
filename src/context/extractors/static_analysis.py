"""Parser for static analysis tool outputs."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from src.context.models import StaticAnalysisFinding

logger = logging.getLogger(__name__)

# Severity ordering for sorting (higher priority first)
SEVERITY_ORDER = {"ERROR": 0, "WARNING": 1, "INFO": 2}


def parse_semgrep_json(
    file_path: str,
    changed_files: list[str],
) -> list[StaticAnalysisFinding]:
    """Parse semgrep JSON output, filtering to only changed files.

    Args:
        file_path: Path to the semgrep JSON output file
        changed_files: List of changed file paths to filter results

    Returns:
        List of StaticAnalysisFinding sorted by severity (ERROR first)
    """
    path = Path(file_path)
    if not path.exists():
        logger.warning(f"Static analysis file not found: {file_path}")
        return []

    try:
        with open(path) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse static analysis JSON: {e}")
        return []

    results = data.get("results", [])
    if not results:
        logger.info("No static analysis findings in file")
        return []

    # Normalize changed files for comparison
    changed_set = {_normalize_path(f) for f in changed_files}

    findings: list[StaticAnalysisFinding] = []
    for result in results:
        file_path_result = result.get("path", "")
        normalized_path = _normalize_path(file_path_result)

        # Filter to only changed files
        if normalized_path not in changed_set:
            continue

        line = result.get("start", {}).get("line", 0)
        rule_id = result.get("check_id", "unknown")
        extra = result.get("extra", {})
        message = extra.get("message", "")
        severity = extra.get("severity", "WARNING").upper()

        # Normalize severity
        if severity not in SEVERITY_ORDER:
            severity = "WARNING"

        findings.append(
            StaticAnalysisFinding(
                file=file_path_result,
                line=line,
                rule_id=rule_id,
                message=message,
                severity=severity,
            )
        )

    # Sort by severity (ERROR first, then WARNING, then INFO)
    findings.sort(key=lambda f: SEVERITY_ORDER.get(f.severity, 99))

    logger.info(f"Parsed {len(findings)} static analysis findings for changed files")
    return findings


def format_findings(findings: list[StaticAnalysisFinding]) -> str:
    """Format findings as text for token estimation.

    Args:
        findings: List of static analysis findings

    Returns:
        Formatted string representation
    """
    if not findings:
        return ""

    lines = ["### Static Analysis Findings"]
    for f in findings:
        lines.append(f"- **{f.file}:{f.line}** [{f.severity}] `{f.rule_id}`: {f.message}")
    return "\n".join(lines)


def _normalize_path(path: str) -> str:
    """Normalize a file path for comparison.

    Removes leading ./ or / to allow matching between different path formats.
    """
    path = path.lstrip("./")
    path = path.lstrip("/")
    return path
