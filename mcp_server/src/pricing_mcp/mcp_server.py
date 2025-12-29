from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse, quote

import httpx
from mcp.server.fastmcp import FastMCP  # type: ignore[import]

from .container import container
from .logging import get_logger

settings = container.settings
mcp = FastMCP(settings.mcp_server_name)
logger = get_logger(__name__)

# Event names for structured logs
TOOL_INVOKED = "mcp.tool.invoked"
TOOL_COMPLETED = "mcp.tool.completed"
RESOURCE_REQUEST = "mcp.resource.request"
RESOURCE_RESPONSE = "mcp.resource.response"
RESOURCE_ID = "resource://pricing/specification"
VALID_SOLVERS = {"minizinc", "choco"}
INVALID_SOLVER_ERROR = "solver must be either 'minizinc' or 'choco'."

_PRICING2YAML_SPEC_PATH = Path(__file__).resolve().parent.joinpath("docs", "pricing2YamlSpecification.md")
try:
    _PRICING2YAML_SPEC = _PRICING2YAML_SPEC_PATH.read_text(encoding="utf-8")
except FileNotFoundError:  # pragma: no cover - deployment safeguard
    _PRICING2YAML_SPEC = ""

@mcp.tool()
async def summary(
    pricing_url: Optional[str] = None,
    pricing_yaml: Optional[str] = None,
    refresh: bool = False,
) -> Dict[str, Any]:
    """Return contextual pricing summary data."""

    if not (pricing_url or pricing_yaml):
        raise ValueError("Either pricing_url or pricing_yaml must be provided for summary.")
    logger.info(
        TOOL_INVOKED,
        tool="summary",
        pricing_url=pricing_url,
        has_pricing_yaml=bool(pricing_yaml),
        refresh=refresh,
    )

    result = await container.workflow.run_summary(
        url=pricing_url,
        yaml_content=pricing_yaml,
        refresh=refresh,
    )
    logger.info(TOOL_COMPLETED, tool="summary", result_keys=list(result.keys()))
    return result


@mcp.tool()
async def subscriptions(
    pricing_url: Optional[str] = None,
    pricing_yaml: Optional[str] = None,
    filters: Optional[Dict[str, Any]] = None,
    solver: str = "minizinc",
    refresh: bool = False,
) -> Dict[str, Any]:
    """Enumerate subscriptions within the pricing configuration space."""

    if not (pricing_url or pricing_yaml):
        raise ValueError(
            "subscriptions requires pricing_url or pricing_yaml to define the configuration space."
        )

    if solver not in VALID_SOLVERS:
        raise ValueError(INVALID_SOLVER_ERROR)
    logger.info(
        TOOL_INVOKED,
        tool="subscriptions",
        pricing_url=pricing_url,
        has_pricing_yaml=bool(pricing_yaml),
        filters=filters,
        solver=solver,
        refresh=refresh,
    )

    result = await container.workflow.run_subscriptions(
        url=pricing_url or "",
        filters=filters,
        solver=solver,
        refresh=refresh,
        yaml_content=pricing_yaml,
    )
    # Log cardinality if present to make configuration-space size visible in logs
    cardinality = result.get("cardinality") if isinstance(result, dict) else None
    logger.info(TOOL_COMPLETED, tool="subscriptions", cardinality=cardinality)
    return result


@mcp.tool()
async def optimal(
    pricing_url: Optional[str] = None,
    pricing_yaml: Optional[str] = None,
    filters: Optional[Dict[str, Any]] = None,
    solver: str = "minizinc",
    objective: str = "minimize",
    refresh: bool = False,
) -> Dict[str, Any]:
    """Compute the optimal subscription under the provided constraints."""

    if not (pricing_url or pricing_yaml):
        raise ValueError("optimal requires pricing_url or pricing_yaml to run analysis.")

    if solver not in VALID_SOLVERS:
        raise ValueError(INVALID_SOLVER_ERROR)

    if objective not in {"minimize", "maximize"}:
        raise ValueError("objective must be 'minimize' or 'maximize'.")
    logger.info(
        TOOL_INVOKED,
        tool="optimal",
        pricing_url=pricing_url,
        has_pricing_yaml=bool(pricing_yaml),
        filters=filters,
        solver=solver,
        objective=objective,
        refresh=refresh,
    )

    result = await container.workflow.run_optimal(
        url=pricing_url or "",
        filters=filters,
        solver=solver,
        objective=objective,
        refresh=refresh,
        yaml_content=pricing_yaml,
    )
    logger.info(TOOL_COMPLETED, tool="optimal", keys=list(result.keys()))
    return result


@mcp.tool()
async def validate(
    pricing_url: Optional[str] = None,
    pricing_yaml: Optional[str] = None,
    solver: str = "minizinc",
    refresh: bool = False,
) -> Dict[str, Any]:
    """Validate the pricing configuration against the selected solver."""

    if not (pricing_url or pricing_yaml):
        raise ValueError("validate requires pricing_url or pricing_yaml to run analysis.")

    if solver not in VALID_SOLVERS:
        raise ValueError(INVALID_SOLVER_ERROR)

    logger.info(
        TOOL_INVOKED,
        tool="validate",
        pricing_url=pricing_url,
        has_pricing_yaml=bool(pricing_yaml),
        solver=solver,
        refresh=refresh,
    )

    result = await container.workflow.run_validation(
        url=pricing_url,
        solver=solver,
        refresh=refresh,
        yaml_content=pricing_yaml,
    )

    validation_status = None
    if isinstance(result, dict):
        validation_status = result.get("result", {}).get("valid")

    logger.info(TOOL_COMPLETED, tool="validate", valid=validation_status)
    return result


@mcp.tool(name="iPricing")
async def ipricing(
    pricing_url: Optional[str] = None,
    pricing_yaml: Optional[str] = None,
    refresh: bool = False,
) -> Dict[str, Any]:
    """Return the canonical Pricing2Yaml (iPricing) document."""

    if not (pricing_url or pricing_yaml):
        raise ValueError("iPricing requires pricing_url or pricing_yaml to produce an output.")

    logger.info(
        TOOL_INVOKED,
        tool="iPricing",
        pricing_url=pricing_url,
        has_pricing_yaml=bool(pricing_yaml),
        refresh=refresh,
    )

    result = await container.workflow.get_ipricing(
        url=pricing_url,
        yaml_content=pricing_yaml,
        refresh=refresh,
    )
    yaml_content = result.get("pricing_yaml", "")
    upload_transformed_pricing(pricing_url, yaml_content)
    notify_pricing_upload(pricing_url, yaml_content)
    pricing_yaml_len = len(yaml_content) if isinstance(result, dict) else None
    logger.info(TOOL_COMPLETED, tool="iPricing", pricing_yaml_length=pricing_yaml_len)
    return result

def upload_transformed_pricing(pricing_url: str, yaml_content: str):
    try:
        data = {"pricing_url": pricing_url,  "yaml_content": yaml_content}
        response = httpx.post(f"{settings.harvey_base_url}/upload/url", json=data)
        response.raise_for_status()
        logger.info(f"Upload of {pricing_url}  has been completed")
    except httpx.RequestError as exc:
        logger.error(f"An error occurred while requesting {exc.request.url!r}.")
    except httpx.HTTPStatusError as exc:
        logger.error(f"Upload failed with status {exc.response.status_code} while requesting {exc.request.url!r}.")

def notify_pricing_upload(pricing_url: str, yaml_content: str):
    try:
        response = httpx.post(f"{settings.harvey_base_url}/events/url-transform", json={"pricing_url": pricing_url, "yaml_content": yaml_content})
        response.raise_for_status()
        logger.info(f"Notifying HARVEY that transformation of {pricing_url} was completed")
    except httpx.RequestError as exc:
        logger.error(f"An error occurred while requesting {exc.request.url!r}.")
    except httpx.HTTPStatusError as exc:
        logger.error(f"Notifying HARVEY failed with status {exc.response.status_code} while requesting {exc.request.url!r}.")

@mcp.resource("resource://pricing/specification")
async def pricing2yaml_specification() -> str:
    """Expose the Pricing2Yaml specification excerpt as a reusable resource."""
    logger.info(RESOURCE_REQUEST, resource=RESOURCE_ID)
    logger.info(RESOURCE_RESPONSE, resource=RESOURCE_ID, length=len(_PRICING2YAML_SPEC))
    return _PRICING2YAML_SPEC


def main() -> None:
    mcp.run(transport=settings.mcp_transport)


if __name__ == "__main__":
    main()
