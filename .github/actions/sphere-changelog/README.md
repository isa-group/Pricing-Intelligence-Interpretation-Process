This custom GitHub action generates a changelog containing a list of changes
since the latest tag uploaded to the repository. If the number of commits exceeds
the commit threshold, they will be summarized using an LLM (Gemini). Finally,
a draft release is created and the changelog data is attached to the release as an asset.

> [!NOTE]
> This action is specifically designed for use in projects related to [SPHERE](https://github.com/Alex-GF/SPHERE)
> like:
> - [Alex-GF/SPHERE](https://github.com/Alex-GF/SPHERE)
> - [isa-group/space](https://github.com/isa-group/space)
> - [isa-group/Pricing-Intelligence-Interpretation-Process](https://github.com/isa-group/Pricing-Intelligence-Interpretation-Process)
>
> We are not responsible for any damage caused by the use of this software.

## Usage

### Prerequisites
Before using this action, you must:
- Use the [Conventional Commits specification](https://www.conventionalcommits.org/en/v1.0.0/)
to write your commit messages. If you already have a Conventional Commit style guide use that instead.
- Configure `permissions` with `contents: read` in your workflow.
- Use `actions/checkout` as the first step in your workflow with `fetch-depth: 0` to fetch all tags.

### Requirements

To use this action, you need to:
1. [Get a Gemini API key](https://ai.google.dev/gemini-api/docs/api-key).
2. [Store the Gemini API key in your repository secrets](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets) (example: GEMINI_API_KEY).
3. Configure a Gemini model compatible with [Structured outputs](https://ai.google.dev/gemini-api/docs/structured-output) (Gemini 3.5 Flash is used by default).

> [!WARNING]
> This action reads the Git commit history, so `actions/checkout` workflow step must be executed first.

> [!NOTE]
> This action works best with `on.push.tags` event which is triggered only when a tagged commit is pushed.
> See [the documentation](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#push).

### Examples

Minimal example:
```yaml
name: Generate changelog
on:
  push:
    tags:
      - '*'

permissions:
  contents: read

jobs:
  changelog:
    name: Generate changelog
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@9c091bb21b7c1c1d1991bb908d89e4e9dddfe3e0 #v7.0.0
        with:
          fetch-depth: 0
      - name: Generate changelog
        uses: isa-group/Pricing-Intelligence-Interpretation-Process/.github/actions/sphere-changelog@main
        with:
          gemini_api_key: ${{ secrets.GEMINI_API_KEY }}
```

Configure a different Gemini model (MUST support Structured outputs): 
```yaml
- uses: isa-group/Pricing-Intelligence-Interpretation-Process/.github/actions/sphere-changelog@main
  with:
    gemini_model_id: gemini-2.5-flash-lite
    gemini_api_key: ${{ secrets.GEMINI_API_KEY }}
```

Configure commit threshold:
```yaml
- uses: isa-group/Pricing-Intelligence-Interpretation-Process/.github/actions/sphere-changelog@main
  with:
    commit_threshold: 30
    gemini_api_key: ${{ secrets.GEMINI_API_KEY }}
```

## Inputs

### `gemini_api_key`

**Required**: The Gemini API key used to summarize commits.

### `gemini_model_id`

**Optional**: The Gemini model to use (defaults to Gemini 3.5 Flash). [See supported models](https://ai.google.dev/gemini-api/docs/structured-output).

### `commit_threshold`

**Optional**: Summarizes commit messages when the total count exceeds this limit (defaults to 10).

## How it works

1. Read the commits of the latest tag and save all the data to a JSON file.
2. Process that file and extract all relevant information.
3. If the number of commits exceeds the threshold (commit_threshold), proceed to step 4; otherwise, skip to step 5.
4. Summarize the collected commits using an LLM (specifically Gemini).
5. Save the original or summarized commit data to `changelog-<tag>.json`, where `<tag>` is the name of the
tag (e.g. `changelog-v1.0.0.json`).
6. Create a draft release and upload the changelog file as an asset.

### Prompt Structure

The prompt consists of three main components:
1. The system prompt description.
2. A reduced JSON Schema defining the [`git cliff` context](https://git-cliff.org/docs/templating/context) (see `prompt-input.schema.json` for details).
3. Cleaned, reduced output from running `git cliff --context --latest`.

The `summarize.py` script assembles these inputs and sends them to the LLM.

### LLM Output

Upon completion, the LLM returns a JSON response conforming to the schema defined in `llm-output.schema.json`.

## Output

The GitHub action automatically attaches the generated JSON changelog (typically `changelog-<tag>.json`)
to a GitHub release in draft mode.

**Example Output:**
```json
{
  "version": "2.1.3",
  "release_date": "2026-07-24T20:41:14Z",
  "description": "FIX: HARVEY playground mode",
  "commit_id": "4578268fc73cbe12682076fbb73fc7e84ae2db71",
  "sections": [
    {
      "name": "harvey",
      "features": [],
      "fixes": [
        {
          "id": "4578268fc73cbe12682076fbb73fc7e84ae2db71",
          "message": "Fix HARVEY playground mode"
        }
      ]
    },
    {
      "name": "ui",
      "features": [],
      "fixes": [
        {
          "id": "4578268fc73cbe12682076fbb73fc7e84ae2db71",
          "message": "Fix organization selector in API Key configuration"
        }
      ]
    }
  ]
}
```

The exact TypeScript interfaces defining this JSON structure can be found in
[types.ts](https://github.com/Alex-GF/SPHERE/blob/main/frontend/src/modules/presentation/pages/changelog/types.ts).
