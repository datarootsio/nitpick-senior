# Multi-Provider Setup Guide

Nitpick Senior supports multiple Git providers. Choose your platform below for setup instructions.

## Supported Providers

| Provider | Status | Documentation |
|----------|--------|---------------|
| GitHub | Full Support | [Setup Guide](./github.md) |
| Azure DevOps | Full Support | [Setup Guide](./azure-devops.md) |
| GitLab | Full Support | [Setup Guide](./gitlab.md) |
| Bitbucket | Full Support | [Setup Guide](./bitbucket.md) |

## Quick Comparison

| Feature | GitHub | Azure DevOps | GitLab | Bitbucket |
|---------|--------|--------------|--------|-----------|
| Inline comments | Yes | Yes | Yes | Yes |
| Summary comments | Yes | Yes | Yes | Yes |
| Comment minimization | Yes | No | No | No |
| Edit existing comments | Yes | Limited | Limited | Limited |
| Native CI integration | GitHub Actions | Azure Pipelines | GitLab CI | Bitbucket Pipelines |

## Provider Auto-Detection

When running the Docker image, the provider is automatically detected based on environment variables:

| Environment Variable | Detected Provider |
|---------------------|-------------------|
| `AZURE_DEVOPS_ORG` or `SYSTEM_TEAMPROJECT` | Azure DevOps |
| `CI_SERVER_URL` or `GITLAB_URL` | GitLab |
| `BITBUCKET_WORKSPACE` | Bitbucket |
| Default | GitHub |

You can also explicitly set the provider:

```bash
-e INPUT_PROVIDER=gitlab
```

## Common Configuration

All providers share these configuration options:

| Variable | Default | Description |
|----------|---------|-------------|
| `INPUT_MODEL` | Required | LiteLLM model string |
| `INPUT_POST_SUMMARY` | `true` | Post summary comment |
| `INPUT_POST_INLINE_COMMENTS` | `true` | Post inline comments |
| `INPUT_MAX_COMMENTS` | `10` | Max inline comments |
| `INPUT_MIN_SEVERITY` | `warning` | Minimum severity level |
| `INPUT_CONTEXT_ENABLED` | `true` | Include repo context |
| `INPUT_CONTEXT_MAX_TOKENS` | `5000` | Max context tokens |

## Docker Image

The same Docker image works for all providers:

```bash
docker pull ghcr.io/datarootsio/nitpick-senior:latest
```

## Need Help?

- Check the provider-specific documentation linked above
- Open an issue at [GitHub Issues](https://github.com/datarootsio/nitpick-senior/issues)
