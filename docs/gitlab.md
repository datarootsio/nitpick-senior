# GitLab Setup

Nitpick Senior can run in GitLab CI/CD to review Merge Requests. This guide covers setup for both GitLab.com (SaaS) and self-managed GitLab instances.

## Prerequisites

- A GitLab project with CI/CD enabled
- A Personal Access Token or Project Access Token with `api` scope
- An LLM API key (OpenAI, Anthropic, Azure OpenAI, or AWS Bedrock)
- A GitLab Runner with Docker support

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GITLAB_TOKEN` | Yes | Personal/Project Access Token with `api` scope |
| `GITLAB_URL` | No | GitLab instance URL (default: `https://gitlab.com`) |
| `GITLAB_PROJECT` | Auto | Project path (auto-set via `CI_PROJECT_PATH`) |
| `CI_MERGE_REQUEST_IID` | Auto | MR number (auto-set in MR pipelines) |
| `INPUT_MODEL` | Yes | LiteLLM model string |
| `OPENAI_API_KEY` | Conditional | Required for OpenAI models |

## Configuration

### Step 1: Create an Access Token

**Option A: Project Access Token (Recommended)**

1. Go to **Settings** > **Access Tokens**
2. Create a token with:
   - Name: `nitpick-senior`
   - Role: **Developer** or higher
   - Scopes: **api**
3. Copy the token

**Option B: Personal Access Token**

1. Go to **User Settings** > **Access Tokens**
2. Create a token with **api** scope
3. Copy the token

### Step 2: Add CI/CD Variables

1. Go to **Settings** > **CI/CD** > **Variables**
2. Add variables:
   - `GITLAB_TOKEN` (masked, protected optional)
   - `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` (masked)

### Step 3: Create the CI Configuration

Add to your `.gitlab-ci.yml`:

```yaml
ai-code-review:
  stage: test
  image: ghcr.io/datarootsio/nitpick-senior:latest
  variables:
    INPUT_PROVIDER: gitlab
    INPUT_MODEL: gpt-4o
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
  script:
    - python -m src.main
```

## Full Configuration Example

```yaml
stages:
  - review
  - test
  - build

ai-code-review:
  stage: review
  image: ghcr.io/datarootsio/nitpick-senior:latest
  variables:
    # Provider configuration
    INPUT_PROVIDER: gitlab
    GITLAB_URL: ${CI_SERVER_URL}
    GITLAB_PROJECT: ${CI_PROJECT_PATH}

    # Model configuration
    INPUT_MODEL: anthropic/claude-sonnet-4-5-20250929

    # Review settings
    INPUT_POST_SUMMARY: "true"
    INPUT_POST_INLINE_COMMENTS: "true"
    INPUT_MAX_COMMENTS: "15"
    INPUT_MIN_SEVERITY: "warning"

    # Context settings
    INPUT_CONTEXT_ENABLED: "true"
    INPUT_CONTEXT_MAX_TOKENS: "5000"
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
  script:
    - python -m src.main
  allow_failure: true  # Don't block MR on review failures
```

## Self-Managed GitLab

For self-managed GitLab instances, set the `GITLAB_URL` variable:

```yaml
ai-code-review:
  stage: review
  image: ghcr.io/datarootsio/nitpick-senior:latest
  variables:
    INPUT_PROVIDER: gitlab
    GITLAB_URL: https://gitlab.mycompany.com
    INPUT_MODEL: gpt-4o
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
  script:
    - python -m src.main
```

## Using Docker-in-Docker

If your runner doesn't support direct image execution:

```yaml
ai-code-review:
  stage: review
  image: docker:latest
  services:
    - docker:dind
  variables:
    DOCKER_HOST: tcp://docker:2375
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
  script:
    - |
      docker run --rm \
        -e INPUT_PROVIDER=gitlab \
        -e GITLAB_TOKEN=${GITLAB_TOKEN} \
        -e GITLAB_URL=${CI_SERVER_URL} \
        -e GITLAB_PROJECT=${CI_PROJECT_PATH} \
        -e CI_MERGE_REQUEST_IID=${CI_MERGE_REQUEST_IID} \
        -e INPUT_MODEL=gpt-4o \
        -e OPENAI_API_KEY=${OPENAI_API_KEY} \
        ghcr.io/datarootsio/nitpick-senior:latest
```

## LLM Provider Examples

### OpenAI

```yaml
ai-code-review:
  stage: review
  image: ghcr.io/datarootsio/nitpick-senior:latest
  variables:
    INPUT_PROVIDER: gitlab
    INPUT_MODEL: gpt-4o
    OPENAI_API_KEY: ${OPENAI_API_KEY}
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
  script:
    - python -m src.main
```

### Anthropic

```yaml
ai-code-review:
  stage: review
  image: ghcr.io/datarootsio/nitpick-senior:latest
  variables:
    INPUT_PROVIDER: gitlab
    INPUT_MODEL: anthropic/claude-sonnet-4-5-20250929
    ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
  script:
    - python -m src.main
```

### Azure OpenAI

```yaml
ai-code-review:
  stage: review
  image: ghcr.io/datarootsio/nitpick-senior:latest
  variables:
    INPUT_PROVIDER: gitlab
    INPUT_MODEL: azure/gpt-4o
    AZURE_OPENAI_API_KEY: ${AZURE_OPENAI_API_KEY}
    AZURE_OPENAI_ENDPOINT: ${AZURE_OPENAI_ENDPOINT}
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
  script:
    - python -m src.main
```

### OpenRouter

Access 200+ models through OpenRouter's unified API:

```yaml
ai-code-review:
  stage: review
  image: ghcr.io/datarootsio/nitpick-senior:latest
  variables:
    INPUT_PROVIDER: gitlab
    INPUT_MODEL: openrouter/anthropic/claude-3.5-sonnet
    OPENROUTER_API_KEY: ${OPENROUTER_API_KEY}
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
  script:
    - python -m src.main
```

Browse available models at [openrouter.ai/models](https://openrouter.ai/models).

## Predefined Variables Reference

GitLab provides these variables automatically in MR pipelines:

| Variable | Description |
|----------|-------------|
| `CI_SERVER_URL` | GitLab instance URL |
| `CI_PROJECT_PATH` | Project path (e.g., `group/project`) |
| `CI_MERGE_REQUEST_IID` | Merge Request number |
| `CI_PIPELINE_SOURCE` | Pipeline trigger source |
| `CI_MERGE_REQUEST_TARGET_BRANCH_NAME` | Target branch |
| `CI_MERGE_REQUEST_SOURCE_BRANCH_NAME` | Source branch |

## Advanced: Review Only Changed Files

To run the review only when specific files change:

```yaml
ai-code-review:
  stage: review
  image: ghcr.io/datarootsio/nitpick-senior:latest
  variables:
    INPUT_PROVIDER: gitlab
    INPUT_MODEL: gpt-4o
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
      changes:
        - "**/*.py"
        - "**/*.js"
        - "**/*.ts"
  script:
    - python -m src.main
```

## Troubleshooting

### "401 Unauthorized"

Your token doesn't have the correct permissions:
1. Ensure the token has `api` scope
2. For Project Access Tokens, ensure the role is Developer or higher
3. Check if the token has expired

### "404 Project Not Found"

Verify:
- `GITLAB_PROJECT` matches your project path exactly (case-sensitive)
- The token has access to the project
- For private projects, ensure the token owner has project access

### Pipeline doesn't run on MR

1. Ensure you have the correct `rules`:
   ```yaml
   rules:
     - if: $CI_PIPELINE_SOURCE == "merge_request_event"
   ```
2. Check that MR pipelines are enabled in **Settings** > **CI/CD** > **General pipelines**

### Comments not appearing on MR

1. Check job logs for errors
2. Verify `CI_MERGE_REQUEST_IID` is set (only in MR pipelines)
3. Ensure the token has write access to discussions

### "Detached pipeline" issues

For MR pipelines, GitLab runs in "detached" mode. Ensure your job uses:
```yaml
rules:
  - if: $CI_PIPELINE_SOURCE == "merge_request_event"
```

Not:
```yaml
only:
  - merge_requests  # Deprecated syntax
```
