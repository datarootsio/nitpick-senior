# Bitbucket Setup

Nitpick Senior can run in Bitbucket Pipelines to review Pull Requests. This guide covers setup for Bitbucket Cloud.

## Prerequisites

- A Bitbucket Cloud repository with Pipelines enabled
- An App Password with appropriate permissions
- An LLM API key (OpenAI, Anthropic, Azure OpenAI, or AWS Bedrock)

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `BITBUCKET_TOKEN` | Yes | App Password for API access |
| `BITBUCKET_USERNAME` | Yes | Bitbucket username (for authentication) |
| `BITBUCKET_WORKSPACE` | Auto | Workspace ID (auto-set in Pipelines) |
| `BITBUCKET_REPO_SLUG` | Auto | Repository slug (auto-set in Pipelines) |
| `BITBUCKET_PR_ID` | Auto | PR number (auto-set in PR pipelines) |
| `INPUT_MODEL` | Yes | LiteLLM model string |
| `OPENAI_API_KEY` | Conditional | Required for OpenAI models |

## Configuration

### Step 1: Create an App Password

1. Go to **Personal settings** > **App passwords**
2. Click **Create app password**
3. Configure permissions:
   - **Repositories**: Read, Write
   - **Pull requests**: Read, Write
4. Copy the generated password

### Step 2: Add Repository Variables

1. Go to **Repository settings** > **Repository variables**
2. Add variables:
   - `BITBUCKET_USERNAME` - Your Bitbucket username
   - `BITBUCKET_TOKEN` - Your App Password (mark as **Secured**)
   - `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` (mark as **Secured**)

### Step 3: Create the Pipeline Configuration

Create or update `bitbucket-pipelines.yml`:

```yaml
image: atlassian/default-image:4

pipelines:
  pull-requests:
    '**':
      - step:
          name: AI Code Review
          image: ghcr.io/datarootsio/nitpick-senior:latest
          script:
            - export INPUT_PROVIDER=bitbucket
            - export INPUT_MODEL=gpt-4o
            - python -m src.main
```

## Full Configuration Example

```yaml
image: atlassian/default-image:4

definitions:
  steps:
    - step: &ai-review
        name: AI Code Review
        image: ghcr.io/datarootsio/nitpick-senior:latest
        script:
          - export INPUT_PROVIDER=bitbucket
          - export INPUT_MODEL=anthropic/claude-sonnet-4-5-20250929
          - export INPUT_POST_SUMMARY=true
          - export INPUT_POST_INLINE_COMMENTS=true
          - export INPUT_MAX_COMMENTS=15
          - export INPUT_MIN_SEVERITY=warning
          - export INPUT_CONTEXT_ENABLED=true
          - export INPUT_CONTEXT_MAX_TOKENS=5000
          - python -m src.main

pipelines:
  pull-requests:
    '**':
      - step: *ai-review

    # Or target specific branches
    feature/*:
      - step: *ai-review

    bugfix/*:
      - step: *ai-review
```

## Using Docker Run

If you prefer explicit Docker commands:

```yaml
image: atlassian/default-image:4

pipelines:
  pull-requests:
    '**':
      - step:
          name: AI Code Review
          services:
            - docker
          script:
            - |
              docker run --rm \
                -e INPUT_PROVIDER=bitbucket \
                -e BITBUCKET_TOKEN=${BITBUCKET_TOKEN} \
                -e BITBUCKET_USERNAME=${BITBUCKET_USERNAME} \
                -e BITBUCKET_WORKSPACE=${BITBUCKET_WORKSPACE} \
                -e BITBUCKET_REPO_SLUG=${BITBUCKET_REPO_SLUG} \
                -e BITBUCKET_PR_ID=${BITBUCKET_PR_ID} \
                -e INPUT_MODEL=gpt-4o \
                -e OPENAI_API_KEY=${OPENAI_API_KEY} \
                ghcr.io/datarootsio/nitpick-senior:latest

definitions:
  services:
    docker:
      memory: 2048
```

## Predefined Variables Reference

Bitbucket provides these variables automatically in PR pipelines:

| Variable | Description |
|----------|-------------|
| `BITBUCKET_WORKSPACE` | Workspace ID |
| `BITBUCKET_REPO_SLUG` | Repository slug |
| `BITBUCKET_PR_ID` | Pull Request ID |
| `BITBUCKET_PR_DESTINATION_BRANCH` | Target branch |
| `BITBUCKET_BRANCH` | Source branch |
| `BITBUCKET_COMMIT` | Current commit SHA |

## Configuring for Specific File Types

Review only when certain files change:

```yaml
pipelines:
  pull-requests:
    '**':
      - step:
          name: AI Code Review
          image: ghcr.io/datarootsio/nitpick-senior:latest
          condition:
            changesets:
              includePaths:
                - "src/**"
                - "**/*.py"
                - "**/*.js"
                - "**/*.ts"
          script:
            - export INPUT_PROVIDER=bitbucket
            - export INPUT_MODEL=gpt-4o
            - python -m src.main
```

## Using with Self-Hosted Runners

For self-hosted runners behind a firewall:

```yaml
pipelines:
  pull-requests:
    '**':
      - step:
          name: AI Code Review
          runs-on:
            - self.hosted
            - linux
          image: ghcr.io/datarootsio/nitpick-senior:latest
          script:
            - export INPUT_PROVIDER=bitbucket
            - export INPUT_MODEL=gpt-4o
            - python -m src.main
```

Ensure your runner can reach:
- Bitbucket API (`api.bitbucket.org`)
- Your LLM provider's API
- Container registry (`ghcr.io`)

## Troubleshooting

### "401 Unauthorized" or "403 Forbidden"

Your App Password needs the correct permissions:
1. **Repositories**: Read, Write
2. **Pull requests**: Read, Write

Create a new App Password with the correct scopes.

### "Repository not found"

Verify:
- `BITBUCKET_WORKSPACE` matches your workspace ID exactly
- `BITBUCKET_REPO_SLUG` matches your repository slug
- The App Password owner has access to the repository

### Pipeline doesn't run on PR

1. Ensure your `bitbucket-pipelines.yml` has a `pull-requests` section
2. Check that Pipelines are enabled in **Repository settings** > **Pipelines** > **Settings**
3. Verify the pipeline file is in the default branch

### Comments not appearing

1. Check pipeline logs for API errors
2. Verify `BITBUCKET_PR_ID` is set (only in PR pipelines)
3. Ensure the App Password has pull request write permissions

### "Build minutes exceeded"

Bitbucket Cloud has build minute limits on free plans. Consider:
- Upgrading your plan
- Reducing `max_comments` to speed up execution
- Using a self-hosted runner

### Docker image pull fails

If `ghcr.io` is blocked:
1. Mirror the image to a registry you control
2. Or use Docker Hub: `datarootsio/nitpick-senior:latest`

## Limitations

Bitbucket has some limitations compared to other providers:

1. **No comment minimization**: Bitbucket doesn't support hiding outdated comments
2. **Limited markdown**: Some advanced markdown features may not render
3. **Rate limits**: Bitbucket API has stricter rate limits on free plans

The action handles these gracefully, but you may notice some differences in behavior compared to GitHub.
