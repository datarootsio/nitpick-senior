"""Pydantic models for repository context data."""

from pydantic import BaseModel


class RelatedFile(BaseModel):
    """A file related to the PR changes."""

    path: str
    content: str
    reason: str  # "import", "config", "readme", "explicit"


class RepoContext(BaseModel):
    """Repository context collected for a PR review."""

    readme: str | None = None
    related_files: list[RelatedFile] = []
    total_tokens: int = 0

    def is_empty(self) -> bool:
        """Check if context has any content."""
        return self.readme is None and len(self.related_files) == 0
