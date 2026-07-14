from enum import Enum
import json
import os
import sys
from typing import Annotated, List, Optional
from uuid import UUID, uuid4

from google import genai
from google.genai import types
from pydantic import BaseModel, Field, TypeAdapter


class Group(str, Enum):
    features = "features"
    fixes = "fixes"
    docs = "docs"
    refactor = "refactor"
    chore = "chore"
    other = "other"


class Scope(str, Enum):
    harvey = "harvey"
    mcp = "mcp"
    prime = "prime"
    csp = "csp"
    amint = "amint"
    ui = "ui"


class Commit(BaseModel):
    id: str = Field(description="SHA256 of a commit.")
    message: str = Field(
        description="Description of the commit message according to the Conventional Commits spec."
    )
    group: Group = Field(description="Type of the commit.")
    scope: Annotated[
        Scope,
        Field(
            description="Scope of the commit according to the Conventional Commits spec."
        ),
    ] = None
    raw_message: str = Field(
        description="The raw message of the commit that follows Conventional Commits spec (i.e. <type>[optional scope]: <description>)."
    )


class Release(BaseModel):
    version: str = Field(description="Release version of the software using SemVer.")
    timestamp: int = Field(description="Unix epoch of the release.")
    message: str = Field(description="Summary of the git tag of the release.")
    commit_id: str = Field(description="SHA256 of the tagged commit.")
    commits: List[Commit] = Field(
        description="List of commits that belongs to the release."
    )


class Change(BaseModel):
    """
    Expected structured output of the LLM
    """

    id: str = Field(
        description="SHA256 of a commit or UUID v4 (i.e. 3feebd0e-7710-4ee3-95d0-15cd214661fd) of a summarized change by LLM.",
        max_length=40,
    )
    message: str = Field(description="Description of the change summarized by LLM.")
    group: Group = Field(description="Type of the commit.")
    scope: Annotated[Scope, Field(description="Scope of the summarized commit.")] = None


adapter = TypeAdapter(List[Change])

SYSTEM_INSTRUCTION = (
    "You are a technical writer creating a public changelog. "
    "Your task is to summarize a list of technical changes into clear, concise, and user-friendly updates."
)


def get_prompt(json_input: str):
    return f"""
    # Task Goal
    Given the list of commit messages of a particular release, generate a changelog containing the summarized
    changes between releases. You should generate the fewest number of entries to give a clear overview of the
    features and fixes introduced between releases.

    ## Processing Rules

    ### Classification & Merging

    1. Extraction: Read the commit messages located at the .commits JQ path.
    2. Classification: Classify every resulting entry strictly as either a `feat` or a `fix`.
    3. Semantic Merging: Summarize two or more commits if they are semantically identical or redundant
    (e.g. "fix deployment" and "deployment is now working" should be merged into one entry).
    4. ID Generation: If an entry represents a single, unsummarized commit, retain its commit hash.
    If you summarize two or more commits together, generate an unique UUID v4 for that new entry.
    5. Feature/Change inference: Summarize those commits that semantically contributes to the same feature or change, i.e,
    infer a feature or change entry given a sequence of commit messages.

    ### Restrictions

    - Never summarize a feat and a fix together.
    - Never summarize commits with different scopes (e.g. `feat(harvey)` and `feat(mcp)` must remain separate).
    - Never generate more output entries that the total number of commits provided in the input.
    - You MUST NOT generate more than 50 entries in a feat or fix block.

    ### Examples

    Given the following commit messages:
    ```
    fix: server statics
    fix: server statics
    fix: auth tests
    fix: slug tests
    ```

    Good summaries:
    ```
    fix: server statics
    fix: fix broken test suite
    ```

    Bad summaries:
    ```
    fix: server statics, server statics
    fix: auth tests, slug tests
    ```

    # Input JSON Schema
    ```json
    {json.dumps(Release.model_json_schema())}
    ```

    # JSON Input
    ```json
    {json_input}
    ```
    """


if __name__ == "__main__":
    """
    The following models support structured output:
    - Gemini 3.5 Flash
    - Gemini 3.1 Pro Preview
    - Gemini 3.1 Flash-Lite
    - Gemini 3.1 Flash-Lite Preview
    - Gemini 2.5 Pro
    - Gemini 2.5 Flash
    - Gemini 2.5 Flash-Lite
    """

    input_data = sys.stdin.read()
    client = genai.Client()
    response = client.models.generate_content(
        model=os.getenv("GEMINI_MODEL_ID"),
        contents=get_prompt(input_data),
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            response_json_schema=adapter.json_schema(),
        ),
    )
    summarized_changes = adapter.validate_json(response.text)
    print(adapter.dump_json(summarized_changes).decode("utf-8"))
