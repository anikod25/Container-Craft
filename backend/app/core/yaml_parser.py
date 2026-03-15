import yaml
from typing import List, Tuple, Dict, Any
 
from app.models import ServiceConfig, RestartPolicy, HealthCheck, BuildConfig

SUPPORTED_SERVICE_KEYS = {
    "image", "ports", "environment", "volumes", "networks",
    "depends_on", "restart", "command", "healthcheck", "build",
    "network_mode", "cpu_limit", "memory_limit",
}

SUPPORTED_TOP_LEVEL_KEYS = {"version", "services", "networks", "volumes"}

COMPLEX_NETWORK_KEYS = {"ipam", "driver_opts", "labels", "attachable", "internal"}

class YAMLParseError(Exception):
    """Raised when the YAML string cannot be parsed or is structurally invalid."""
    pass

def parse_compose_yaml(yaml_string: str) -> Tuple[List[ServiceConfig], List[str]]:
    """
    Parse a docker-compose YAML string into a list of ServiceConfig objects.
 
    argument:: yaml_string: Raw docker-compose.yml content as a string
    returns::  Tuple of:
               - List[ServiceConfig]: parsed services
               - List[str]: warnings about unsupported/ignored features
 
    raises::   YAMLParseError if the YAML is syntactically invalid or missing
               the required 'services' block
    """
    warnings: List[str] = []

    try:
        compose_dict = yaml.safe_load(yaml_string)
    except yaml.YAMLError as e:
        raise YAMLParseError(f"Invalid YAML syntax: {e}")
 
    if not isinstance(compose_dict, dict):
        raise YAMLParseError("YAML content is not a valid docker-compose structure.")
 
    for key in compose_dict:
        if key not in _SUPPORTED_TOP_LEVEL_KEYS:
            warnings.append(
                f"Top-level key '{key}' is not supported by ContainerCraft and was ignored."
            )

    
