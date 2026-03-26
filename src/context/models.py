"""Pydantic models for repository context data."""

from pydantic import BaseModel


class RelatedFile(BaseModel):
    """A file related to the PR changes."""

    path: str
    content: str
    reason: str  # "import", "config", "readme", "explicit"


class StaticAnalysisFinding(BaseModel):
    """A finding from static analysis tools like semgrep."""

    file: str
    line: int
    rule_id: str
    message: str
    severity: str  # "ERROR", "WARNING", "INFO"


class RepoContext(BaseModel):
    """Repository context collected for a PR review."""

    readme: str | None = None
    related_files: list[RelatedFile] = []
    static_analysis: list[StaticAnalysisFinding] = []
    total_tokens: int = 0

    def is_empty(self) -> bool:
        """Check if context has any content."""
        return (
            self.readme is None
            and len(self.related_files) == 0
            and len(self.static_analysis) == 0
        )
