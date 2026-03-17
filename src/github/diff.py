"""Diff fetching and parsing utilities."""

from dataclasses import dataclass

from unidiff import PatchSet


@dataclass
class FileChange:
    """Represents changes to a single file."""

    path: str
    added_lines: list[tuple[int, str]]  # (line_number, content)
    removed_lines: list[tuple[int, str]]
    patch: str  # Raw patch content


def get_pr_diff(github_client, pr_number: int) -> str:
    """Fetch the PR diff using the GitHub client."""
    return github_client.get_pr_diff(pr_number)


def parse_diff(diff_content: str) -> list[FileChange]:
    """Parse a unified diff into structured file changes.

    Args:
        diff_content: Unified diff string

    Returns:
        List of FileChange objects
    """
    if not diff_content.strip():
        return []

    try:
        patch_set = PatchSet(diff_content)
    except Exception:
        # If parsing fails, return empty list
        return []

    changes = []
    for patched_file in patch_set:
        added_lines = []
        removed_lines = []

        for hunk in patched_file:
            for line in hunk:
                if line.is_added:
                    added_lines.append((line.target_line_no, line.value.rstrip("\n")))
                elif line.is_removed:
                    removed_lines.append((line.source_line_no, line.value.rstrip("\n")))

        # Build patch string for this file
        patch_lines = []
        for hunk in patched_file:
            patch_lines.append(str(hunk.section_header).strip())
            for line in hunk:
                patch_lines.append(str(line).rstrip("\n"))

        changes.append(
            FileChange(
                path=patched_file.path,
                added_lines=added_lines,
                removed_lines=removed_lines,
                patch="\n".join(patch_lines),
            )
        )

    return changes


def get_changed_line_numbers(diff_content: str, file_path: str) -> set[int]:
    """Get the set of added line numbers for a specific file.

    Used to validate that inline comments target actual changed lines.
    """
    changes = parse_diff(diff_content)
    for change in changes:
        if change.path == file_path:
            return {line_no for line_no, _ in change.added_lines}
    return set()
