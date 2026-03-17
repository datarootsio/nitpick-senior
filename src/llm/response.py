"""Pydantic models for structured LLM responses."""

from typing import Literal

from pydantic import BaseModel, Field


class ReviewComment(BaseModel):
    """A single inline review comment."""

    file: str = Field(description="File path relative to repo root")
    line: int = Field(description="Line number in the file (from the new version)")
    body: str = Field(description="Comment explaining the issue")
    suggestion: str | None = Field(
        default=None, description="Optional code suggestion to fix the issue"
    )
    severity: Literal["info", "warning", "error"] = Field(
        default="warning", description="Severity level of the issue"
    )


class ReviewResponse(BaseModel):
    """Complete review response from the LLM."""

    summary: str = Field(description="Brief summary of the PR changes (2-3 sentences)")
    comments: list[ReviewComment] = Field(
        default_factory=list, description="List of inline review comments"
    )
