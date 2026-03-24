"""Environment variable utilities."""

import os


def resolve_token() -> str:
    """Resolve authentication token from various environment variables.

    Checks multiple token sources for backward compatibility:
    - INPUT_TOKEN (primary)
    - INPUT_GITHUB_TOKEN (legacy)
    - Provider-specific: GITHUB_TOKEN, GITLAB_TOKEN, AZURE_DEVOPS_TOKEN, BITBUCKET_TOKEN

    Returns:
        Authentication token or empty string if not found
    """
    return (
        os.environ.get("INPUT_TOKEN")
        or os.environ.get("INPUT_GITHUB_TOKEN")
        or os.environ.get("GITHUB_TOKEN")
        or os.environ.get("GITLAB_TOKEN")
        or os.environ.get("AZURE_DEVOPS_TOKEN")
        or os.environ.get("BITBUCKET_TOKEN")
        or ""
    )


def parse_int_env(key: str, default: int) -> int:
    """Parse an integer from an environment variable with a default.

    Args:
        key: Environment variable name
        default: Default value if env var is missing or invalid

    Returns:
        Parsed integer or default
    """
    try:
        return int(os.environ.get(key, str(default)))
    except ValueError:
        return default
