# Azure DevOps Setup

Nitpick Senior can run in Azure DevOps Pipelines to review Pull Requests. This guide covers setup for both Azure DevOps Services (cloud) and Azure DevOps Server (on-premises).

## Prerequisites

- An Azure DevOps project with Pipelines enabled
- A Personal Access Token (PAT) with **Code (Read & Write)** permissions
- An LLM API key (OpenAI, Anthropic, Azure OpenAI, or AWS Bedrock)
- Docker-enabled pipeline agent

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `AZURE_DEVOPS_TOKEN` | Yes | Personal Access Token for API access |
| `AZURE_DEVOPS_ORG` | Yes | Organization URL (e.g., `https://dev.azure.com/myorg`) |
| `AZURE_DEVOPS_PROJECT` | Yes | Project name |
| `AZURE_DEVOPS_REPOSITORY` | Yes | Repository name |
| `SYSTEM_PULLREQUESTID` | Auto | PR number (automatically set in PR pipelines) |
| `INPUT_MODEL` | Yes | LiteLLM model string |
| `OPENAI_API_KEY` | Conditional | Required for OpenAI models |

## Configuration

### Step 1: Create a Personal Access Token

1. Go to **User Settings** > **Personal Access Tokens**
2. Click **New Token**
3. Configure:
   - Name: `nitpick-senior`
   - Scopes: **Code** > **Read & Write**
4. Copy the token and save it securely

### Step 2: Add Pipeline Variables

1. Go to **Pipelines** > **Library** > **Variable groups**
2. Create a new variable group named `nitpick-senior`
3. Add variables:
   - `AZURE_DEVOPS_TOKEN` (mark as secret)
   - `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` (mark as secret)

### Step 3: Create the Pipeline

Create `azure-pipelines-review.yml` in your repository:

```yaml
trigger: none

pr:
  branches:
    include:
      - main
      - develop

pool:
  vmImage: 'ubuntu-latest'

variables:
  - group: nitpick-senior

steps:
  - task: Docker@2
    displayName: 'Run AI Code Review'
    inputs:
      command: 'run'
      arguments: |
        --rm
        -e INPUT_PROVIDER=azure_devops
        -e AZURE_DEVOPS_TOKEN=$(AZURE_DEVOPS_TOKEN)
        -e AZURE_DEVOPS_ORG=$(System.CollectionUri)
        -e AZURE_DEVOPS_PROJECT=$(System.TeamProject)
        -e AZURE_DEVOPS_REPOSITORY=$(Build.Repository.Name)
        -e SYSTEM_PULLREQUESTID=$(System.PullRequest.PullRequestId)
        -e INPUT_MODEL=gpt-4o
        -e OPENAI_API_KEY=$(OPENAI_API_KEY)
        ghcr.io/datarootsio/nitpick-senior:latest
```

### Step 4: Enable Build Validation

1. Go to **Repos** > **Branches**
2. Click the **...** menu on your target branch > **Branch policies**
3. Under **Build Validation**, add your pipeline
4. Configure to run on PR creation and updates

## Full Configuration Example

```yaml
trigger: none

pr:
  branches:
    include:
      - main
      - develop
      - release/*

pool:
  vmImage: 'ubuntu-latest'

variables:
  - group: nitpick-senior

stages:
  - stage: CodeReview
    displayName: 'AI Code Review'
    jobs:
      - job: Review
        displayName: 'Run Nitpick Senior'
        condition: eq(variables['Build.Reason'], 'PullRequest')
        steps:
          - task: Docker@2
            displayName: 'AI Code Review'
            inputs:
              command: 'run'
              arguments: |
                --rm
                -e INPUT_PROVIDER=azure_devops
                -e AZURE_DEVOPS_TOKEN=$(AZURE_DEVOPS_TOKEN)
                -e AZURE_DEVOPS_ORG=$(System.CollectionUri)
                -e AZURE_DEVOPS_PROJECT=$(System.TeamProject)
                -e AZURE_DEVOPS_REPOSITORY=$(Build.Repository.Name)
                -e SYSTEM_PULLREQUESTID=$(System.PullRequest.PullRequestId)
                -e INPUT_MODEL=anthropic/claude-sonnet-4-5-20250929
                -e INPUT_POST_SUMMARY=true
                -e INPUT_POST_INLINE_COMMENTS=true
                -e INPUT_MAX_COMMENTS=15
                -e INPUT_MIN_SEVERITY=warning
                -e INPUT_CONTEXT_ENABLED=true
                -e ANTHROPIC_API_KEY=$(ANTHROPIC_API_KEY)
                ghcr.io/datarootsio/nitpick-senior:latest
```

## Using with Azure OpenAI

If you're using Azure OpenAI instead of OpenAI directly:

```yaml
arguments: |
  --rm
  -e INPUT_PROVIDER=azure_devops
  -e AZURE_DEVOPS_TOKEN=$(AZURE_DEVOPS_TOKEN)
  -e AZURE_DEVOPS_ORG=$(System.CollectionUri)
  -e AZURE_DEVOPS_PROJECT=$(System.TeamProject)
  -e AZURE_DEVOPS_REPOSITORY=$(Build.Repository.Name)
  -e SYSTEM_PULLREQUESTID=$(System.PullRequest.PullRequestId)
  -e INPUT_MODEL=azure/gpt-4o
  -e AZURE_API_KEY=$(AZURE_OPENAI_API_KEY)
  -e AZURE_API_BASE=https://your-resource.openai.azure.com
  -e AZURE_API_VERSION=2024-02-15-preview
  ghcr.io/datarootsio/nitpick-senior:latest
```

## Azure DevOps Server (On-Premises)

For Azure DevOps Server, ensure:

1. Your agent has Docker installed
2. The agent can reach your LLM provider (or use a local LLM)
3. Set `AZURE_DEVOPS_ORG` to your server URL (e.g., `https://tfs.company.com/tfs/DefaultCollection`)

## Predefined Variables Reference

Azure DevOps provides these variables automatically in PR pipelines:

| Variable | Description |
|----------|-------------|
| `System.CollectionUri` | Organization URL |
| `System.TeamProject` | Project name |
| `Build.Repository.Name` | Repository name |
| `System.PullRequest.PullRequestId` | PR number |
| `Build.Reason` | Build trigger reason |

## Troubleshooting

### "TF401027: You need the Git 'PullRequestContribute' permission"

Your PAT needs **Code > Read & Write** scope. Create a new token with the correct permissions.

### "The requested resource does not exist"

Verify:
- `AZURE_DEVOPS_ORG` includes the full URL with collection
- `AZURE_DEVOPS_PROJECT` matches your project name exactly
- `AZURE_DEVOPS_REPOSITORY` matches your repo name exactly

### Pipeline doesn't trigger on PR

1. Ensure you have a `pr:` trigger in your YAML
2. Add the pipeline as a build validation policy on the branch
3. Verify the pipeline is enabled

### Comments not appearing

1. Check the pipeline logs for errors
2. Verify the PAT has write permissions
3. Ensure `System.PullRequest.PullRequestId` is set (only in PR pipelines)
