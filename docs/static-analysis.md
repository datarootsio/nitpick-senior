# Static Analysis Integration

Nitpick Senior can incorporate findings from static analysis tools like [Semgrep](https://semgrep.dev/) to provide more informed code reviews. Instead of running static analysis internally, you run your preferred tools separately in CI and pass the results to the reviewer.

## Why External Static Analysis?

- **Flexibility**: Use any semgrep rules or configuration you prefer
- **Performance**: No additional ~100MB added to the Docker image
- **Control**: Run static analysis with your existing CI setup
- **Caching**: Leverage CI caching for faster subsequent runs

## How It Works

```
┌─────────────────┐     ┌─────────────────────┐
│ Run Semgrep     │────►│ semgrep-results.json│
│ (official image)│     └──────────┬──────────┘
└─────────────────┘                │
                                   ▼
┌─────────────────────────────────────────────────────┐
│ Nitpick Senior                                      │
│                                                     │
│  1. Parse semgrep JSON output                       │
│  2. Filter to only files changed in the PR         │
│  3. Sort findings by severity (ERROR > WARNING)     │
│  4. Add to LLM prompt (within token budget)         │
│  5. LLM considers findings when reviewing code      │
└─────────────────────────────────────────────────────┘
```

The LLM receives static analysis findings as additional context, allowing it to:
- Confirm or expand on detected issues
- Provide deeper explanations of why something is problematic
- Correlate static analysis warnings with other code quality concerns

## Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `INPUT_STATIC_ANALYSIS_FILE` | No | None | Path to semgrep JSON output file |

## Usage Examples

### GitHub Actions

```yaml
name: AI Code Review

on:
  pull_request:
    types: [opened, synchronize, reopened]

permissions:
  contents: read
  pull-requests: write

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Run Semgrep
        uses: returntocorp/semgrep-action@v1
        with:
          config: auto
          generateSarif: false
        env:
          SEMGREP_RULES: p/security-audit p/python

      - name: AI Code Review
        uses: datarootsio/nitpick-senior@v1
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          model: gpt-4o
          static_analysis_file: semgrep.json
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
```

### Azure DevOps

```yaml
trigger: none

pr:
  branches:
    include:
      - main

pool:
  vmImage: ubuntu-latest

steps:
  - checkout: self

  - script: |
      docker run --rm -v $(pwd):/src returntocorp/semgrep \
        semgrep --config=auto --json -o /src/semgrep.json /src
    displayName: 'Run Semgrep'

  - task: Docker@2
    displayName: 'AI Code Review'
    inputs:
      command: 'run'
      arguments: |
        -v $(pwd)/semgrep.json:/semgrep.json:ro
        -e INPUT_STATIC_ANALYSIS_FILE=/semgrep.json
        -e INPUT_MODEL=gpt-4o
        -e INPUT_PROVIDER=azure-devops
        -e OPENAI_API_KEY=$(OPENAI_API_KEY)
        -e SYSTEM_COLLECTIONURI=$(System.CollectionUri)
        -e SYSTEM_TEAMPROJECT=$(System.TeamProject)
        -e BUILD_REPOSITORY_NAME=$(Build.Repository.Name)
        -e SYSTEM_PULLREQUESTID=$(System.PullRequest.PullRequestId)
        -e SYSTEM_ACCESSTOKEN=$(System.AccessToken)
        ghcr.io/datarootsio/nitpick-senior:latest
```

### GitLab CI

```yaml
ai-review:
  stage: review
  image: docker:latest
  services:
    - docker:dind
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
  script:
    # Run semgrep
    - docker run --rm -v $PWD:/src returntocorp/semgrep
        semgrep --config=auto --json -o /src/semgrep.json /src

    # Run AI review with static analysis
    - |
      docker run --rm \
        -v $PWD/semgrep.json:/semgrep.json:ro \
        -e INPUT_STATIC_ANALYSIS_FILE=/semgrep.json \
        -e INPUT_MODEL=gpt-4o \
        -e INPUT_PROVIDER=gitlab \
        -e OPENAI_API_KEY=$OPENAI_API_KEY \
        -e CI_SERVER_URL=$CI_SERVER_URL \
        -e CI_PROJECT_PATH=$CI_PROJECT_PATH \
        -e CI_MERGE_REQUEST_IID=$CI_MERGE_REQUEST_IID \
        -e GITLAB_TOKEN=$GITLAB_TOKEN \
        ghcr.io/datarootsio/nitpick-senior:latest
```

## Semgrep JSON Format

Nitpick Senior expects the standard semgrep JSON output format:

```json
{
  "results": [
    {
      "path": "src/foo.py",
      "start": {"line": 42},
      "check_id": "python.lang.security.audit.dangerous-exec",
      "extra": {
        "message": "Dangerous use of exec detected",
        "severity": "WARNING"
      }
    }
  ]
}
```

### Supported Fields

| Field | Description |
|-------|-------------|
| `path` | File path (relative to repo root) |
| `start.line` | Line number of the finding |
| `check_id` | Semgrep rule ID |
| `extra.message` | Human-readable description |
| `extra.severity` | `ERROR`, `WARNING`, or `INFO` |

## How Findings Appear in Reviews

Static analysis findings are included in the LLM prompt under a "Static Analysis Findings" section:

```
### Static Analysis Findings

The following issues were detected by static analysis tools.
Consider these when reviewing the code changes:

- **src/foo.py:42** [WARNING] `python.lang.security.audit.dangerous-exec`: Dangerous use of exec detected
- **src/bar.py:10** [ERROR] `python.lang.security.audit.eval`: Use of eval is dangerous
```

The LLM can then reference these findings in its review comments, providing additional context or confirming the severity of detected issues.

## Token Budget

Static analysis findings are included within the overall context token budget (`context_max_tokens`). If findings exceed the available budget, they will be skipped with a warning in the logs.

Findings are sorted by severity (ERROR first, then WARNING, then INFO) to prioritize critical issues when token space is limited.

## Troubleshooting

### Findings not appearing in review

1. **Check the file path**: Ensure the `INPUT_STATIC_ANALYSIS_FILE` path is correct and accessible
2. **Check file format**: Verify the JSON follows the semgrep format
3. **Check changed files**: Only findings for files changed in the PR are included
4. **Check logs**: Look for "Added X static analysis findings" or warnings about token budget

### Path matching issues

Semgrep may output paths with leading `./` or absolute paths. Nitpick Senior normalizes paths for matching, but ensure your changed files list uses consistent formatting.

## Future Extensions

Support for additional static analysis tools (SonarQube, ESLint JSON output, etc.) may be added in future versions via format auto-detection.
