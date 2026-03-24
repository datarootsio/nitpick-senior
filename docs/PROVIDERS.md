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

## Known Limitations

### Comment Management

Re-running reviews on the same PR works best on GitHub. Other providers have limitations:

| Capability | GitHub | GitLab | Azure DevOps | Bitbucket |
|------------|--------|--------|--------------|-----------|
| Edit existing comments | Yes | No | No | No |
| Delete outdated comments | Yes | No | Partial* | No |

*Azure DevOps can close/resolve threads but not delete them.

**Impact:** On GitLab, Azure DevOps, and Bitbucket, re-running reviews may create duplicate comments instead of updating existing ones. First-time reviews work correctly on all providers.

### Provider-Specific Notes

**GitHub**
- Full feature support including comment minimization
- Works with GitHub Enterprise (set custom API URL)

**GitLab**
- Inline comments use diff notes API
- Self-hosted instances supported

**Azure DevOps**
- Comments are posted as PR threads
- Diff computed by fetching file content at base/head commits

**Bitbucket**
- Uses Bitbucket Cloud API (atlassian-python-api)
- Workspace and repo slug required

## Need Help?

- Check the provider-specific documentation linked above
- Open an issue at [GitHub Issues](https://github.com/datarootsio/nitpick-senior/issues)
