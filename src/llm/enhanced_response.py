"""Enhanced Pydantic models to match Qodo/Greptile output quality."""

from typing import Literal

from pydantic import BaseModel, Field


class FileOverview(BaseModel):
    """Summary of changes to a single file."""

    file: str = Field(description="File path relative to repo root")
    overview: str = Field(description="Brief description of what changed and why")
    change_type: Literal["Enhancement", "Bug fix", "Refactoring", "Configuration", "Documentation", "Tests"] = Field(
        default="Enhancement",
        description="Type of change"
    )


class EnhancedReviewComment(BaseModel):
    """A single inline review comment with Qodo/Greptile-style categorization."""

    file: str = Field(description="File path relative to repo root")
    line: int = Field(description="Line number in the file (from the new version)")

    # Enhanced categorization (like Qodo)
    category: Literal["Security", "Bug", "Reliability", "Performance", "Correctness"] = Field(
        description="Issue category"
    )
    severity: Literal["error", "warning", "info"] = Field(
        default="warning",
        description="Severity level"
    )

    # Content
    body: str = Field(description="Description of the issue")
    evidence: str | None = Field(
        default=None,
        description="Code path or reasoning that demonstrates the issue"
    )
    suggestion: str | None = Field(
        default=None,
        description="Code suggestion to fix the issue"
    )

    # Qodo-style agent prompt
    fix_prompt: str | None = Field(
        default=None,
        description="Prompt that can be given to an AI to fix this issue"
    )


class EnhancedReviewResponse(BaseModel):
    """Complete review response matching Qodo/Greptile quality."""

    # Summary section
    summary: str = Field(description="Brief 2-3 sentence summary of the PR")

    # Greptile-style confidence
    confidence: Literal[1, 2, 3, 4, 5] = Field(
        default=5,
        description="Confidence score: 5=safe, 4=minor issues, 3=concerns, 2=significant, 1=critical"
    )
    confidence_reason: str | None = Field(
        default=None,
        description="Brief explanation of confidence score"
    )

    # Qodo-style file walkthrough
    important_files: list[FileOverview] = Field(
        default_factory=list,
        description="Overview of important changed files"
    )

    # Optional Mermaid diagram (like both tools provide)
    diagram: str | None = Field(
        default=None,
        description="Mermaid diagram showing data flow or architecture (if applicable)"
    )

    # Comments
    comments: list[EnhancedReviewComment] = Field(
        default_factory=list,
        description="List of inline review comments"
    )


# Badge/emoji mappings for formatting
CATEGORY_BADGES = {
    "Security": ("🔒", "Security"),
    "Bug": ("🐞", "Bug"),
    "Reliability": ("⚡", "Reliability"),
    "Performance": ("📈", "Performance"),
    "Correctness": ("✓", "Correctness"),
}

SEVERITY_EMOJI = {
    "error": "🔴",
    "warning": "🟡",
    "info": "🔵",
}

CONFIDENCE_LABELS = {
    5: "✅ Safe to merge - no issues found",
    4: "✅ Safe to merge - minor issues only",
    3: "⚠️ Review recommended - some concerns",
    2: "⚠️ Changes needed - significant issues",
    1: "🛑 Do not merge - critical issues",
}


def format_enhanced_summary(response: EnhancedReviewResponse) -> str:
    """Format the enhanced review as a GitHub comment (Qodo/Greptile style)."""
    lines = []

    # Header
    lines.append("## 🤓 Nitpick Senior Review")
    lines.append("")

    # Summary
    lines.append(response.summary)
    lines.append("")

    # Confidence score (Greptile-style)
    lines.append(f"### Confidence: {response.confidence}/5")
    lines.append(CONFIDENCE_LABELS.get(response.confidence, ""))
    if response.confidence_reason:
        lines.append(f"_{response.confidence_reason}_")
    lines.append("")

    # Important files (Qodo-style)
    if response.important_files:
        lines.append("### Important Files")
        lines.append("")
        lines.append("| File | Type | Overview |")
        lines.append("|------|------|----------|")
        for f in response.important_files:
            lines.append(f"| `{f.file}` | {f.change_type} | {f.overview} |")
        lines.append("")

    # Diagram (if present)
    if response.diagram:
        lines.append("### Architecture")
        lines.append("")
        lines.append("```mermaid")
        lines.append(response.diagram)
        lines.append("```")
        lines.append("")

    # Issue summary
    if response.comments:
        lines.append("### Issues Found")
        lines.append("")

        # Group by category
        by_category: dict[str, list[EnhancedReviewComment]] = {}
        for c in response.comments:
            by_category.setdefault(c.category, []).append(c)

        for category, comments in by_category.items():
            emoji, label = CATEGORY_BADGES.get(category, ("", category))
            lines.append(f"**{emoji} {label}**: {len(comments)} issue(s)")

        lines.append("")
    else:
        lines.append("✅ No issues found!")
        lines.append("")

    # Footer
    lines.append("---")
    lines.append("_Reviewed by [Nitpick Senior](https://github.com/datarootsio/github-reviewer)_")

    return "\n".join(lines)
