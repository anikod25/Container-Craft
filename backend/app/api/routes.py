from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse
from typing import List
from pydantic import BaseModel

from app.models import (
    ComposeConfig,
    ServiceConfig,
    ValidationError,
    ValidationResponse,
)
from app.core.yaml_generator import YAMLGenerator
from app.core.yaml_parser import parse_compose_yaml, YAMLParseError

router = APIRouter()
generator = YAMLGenerator()

class ImportYAMLRequest(BaseModel):
    """Request body for POST /api/import-yaml"""
    yaml_content: str
 
 
class ImportYAMLResponse(BaseModel):
    """Response body for POST /api/import-yaml"""
    services: List[ServiceConfig]
    warnings: List[str]

@router.post(
    "/compose/generate",
    response_class=PlainTextResponse,
    summary="Generate docker-compose YAML",
    description="Accepts a full ComposeConfig and returns a docker-compose.yml string.",
)
def generate_compose(compose_config: ComposeConfig) -> str:
    """
    Generate a docker-compose.yml from the provided configuration.

    - Validates that all `depends_on` references point to services that exist
      in the same ComposeConfig (enforced by the model validator).
    - Returns plain-text YAML ready to be saved as docker-compose.yml.
    """
    try:
        yaml_output = generator.generate_yaml(compose_config)
        return yaml_output
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"YAML generation failed: {str(e)}")


@router.post(
    "/compose/validate",
    response_model=ValidationResponse,
    summary="Validate a ComposeConfig",
    description="Validates the compose configuration and returns errors/warnings.",
)
def validate_compose(compose_config: ComposeConfig) -> ValidationResponse:
    """
    Validate a ComposeConfig without generating YAML.

    Checks performed:
    - Unique service names
    - Valid port formats
    - All `depends_on` entries reference existing services
    - Circular dependency detection
    """
    errors: List[ValidationError] = []
    warnings: List[ValidationError] = []

    service_names = {s.name for s in compose_config.services}

    for service in compose_config.services:
        # --- depends_on validation ---
        for dep in service.depends_on:
            if dep not in service_names:
                errors.append(
                    ValidationError(
                        service=service.name,
                        type="missing_dependency",
                        field="depends_on",
                        message=f"Depends on '{dep}' which is not defined in this compose config.",
                        severity="error",
                    )
                )
            if dep == service.name:
                errors.append(
                    ValidationError(
                        service=service.name,
                        type="missing_dependency",
                        field="depends_on",
                        message=f"Service '{service.name}' cannot depend on itself.",
                        severity="error",
                    )
                )

        # --- warn if service has no networks but depends on services that do ---
        if service.depends_on and not service.networks:
            warnings.append(
                ValidationError(
                    service=service.name,
                    type="network_inconsistency",
                    field="networks",
                    message=(
                        f"Service '{service.name}' has depends_on but no shared network "
                        "with its dependencies — they may not be able to communicate."
                    ),
                    severity="warning",
                )
            )

    # --- circular dependency detection (DFS) ---
    dep_map = {s.name: s.depends_on for s in compose_config.services}
    cycles = _detect_cycles(dep_map)
    for cycle in cycles:
        cycle_str = " -> ".join(cycle)
        errors.append(
            ValidationError(
                service=cycle[0],
                type="circular_dependency",
                field="depends_on",
                message=f"Circular dependency detected: {cycle_str}",
                severity="error",
            )
        )

    return ValidationResponse(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


@router.post(
    "/compose/preview",
    response_class=PlainTextResponse,
    summary="Preview YAML for a single service",
    description="Returns a YAML snippet for a single ServiceConfig (useful for live editor preview).",
)
def preview_service(service: ServiceConfig) -> str:
    """
    Generate a YAML preview for a single service block.
    Wraps the service in a minimal ComposeConfig so the generator can be reused.
    """
    try:
        single_service_compose = ComposeConfig(version="3.8", services=[service])
        return generator.generate_yaml(single_service_compose)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))

@router.post(
    "/api/import-yaml",
    response_model=ImportYAMLResponse,
    summary="Import a docker-compose YAML string",
    description=(
        "Parses a raw docker-compose.yml string and converts it into "
        "ContainerCraft's internal ServiceConfig format. "
        "Returns parsed services and a list of warnings for any unsupported "
        "or complex features that were simplified or ignored."
    ),
)

def import_yaml(request: ImportYAMLRequest) -> ImportYAMLResponse:
    """
    Import a docker-compose YAML string.
 
    Handles:
    - Invalid YAML syntax          → 400 with clear error message
    - Missing services block       → 400 with clear error message
    - Unsupported features         → parsed best-effort, listed in warnings
    - Complex network configs      → simplified to named networks, listed in warnings
    - environment list syntax      → converted to dict
    - depends_on condition syntax  → converted to plain list
    - build short syntax           → converted to BuildConfig object
    - deploy.resources.limits      → mapped to cpu_limit / memory_limit
    """
    try:
        services, warnings = parse_compose_yaml(request.yaml_content)
    except YAMLParseError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error during import: {str(e)}")
 
    return ImportYAMLResponse(services=services, warnings=warnings)

def _detect_cycles(dep_map: dict) -> List[List[str]]:
    """
    Detect cycles in the dependency graph using DFS.
    Returns a list of cycles, where each cycle is a list of service names.
    """
    visited = set()
    rec_stack = set()
    cycles = []

    def dfs(node: str, path: List[str]):
        visited.add(node)
        rec_stack.add(node)
        path.append(node)

        for neighbour in dep_map.get(node, []):
            if neighbour not in dep_map:
                continue  # unknown service — caught by earlier validation
            if neighbour not in visited:
                dfs(neighbour, path)
            elif neighbour in rec_stack:
                # found a cycle — slice the path from where the cycle starts
                cycle_start = path.index(neighbour)
                cycles.append(path[cycle_start:] + [neighbour])

        path.pop()
        rec_stack.discard(node)

    for node in dep_map:
        if node not in visited:
            dfs(node, [])

    return cycles