"""Pydantic models for structured LLM responses."""

from typing import Literal

from pydantic import BaseModel, Field


class FileOverview(BaseModel):
    """Summary of changes to a single file."""

    file: str = Field(description="File path relative to repo root")
    overview: str = Field(description="Brief description of what changed")
    change_type: Literal[
        "Enhancement", "Bug fix", "Refactoring", "Configuration", "Documentation", "Tests"
    ] = Field(default="Enhancement", description="Type of change")


class ReviewComment(BaseModel):
    """A single inline review comment."""

    file: str = Field(description="File path relative to repo root")
    line: int = Field(description="Line number in the file (from the new version)")
    body: str = Field(
        description="Comment explaining WHAT is wrong and WHY it's a problem. "
        "Focus on the root cause, not surface symptoms. Do NOT suggest how to fix it."
    )
    why: str | None = Field(
        default=None,
        description="Explain the underlying reason this is problematic. "
        "What assumption is violated? What edge case breaks? What architectural flaw exists?",
    )
    severity: Literal["info", "warning", "error"] = Field(
        default="warning", description="Severity level of the issue"
    )
    category: Literal["Security", "Bug", "Reliability", "Performance", "Correctness"] | None = (
        Field(default=None, description="Issue category for grouping")
    )


class ReviewResponse(BaseModel):
    """Complete review response from the LLM."""

    summary: str = Field(description="Brief summary of the PR changes (2-3 sentences)")
    confidence: Literal[1, 2, 3, 4, 5] = Field(
        default=5,
        description="Confidence: 5=safe, 4=minor, 3=concerns, 2=significant, 1=critical",
    )
    important_files: list[FileOverview] = Field(
        default_factory=list, description="Overview of important changed files"
    )
    comments: list[ReviewComment] = Field(
        default_factory=list, description="List of inline review comments"
    )
