import re
from typing import List
from models import ServiceConfig, ValidationError, ValidationResponse

def validate_compose_config(services: List[ServiceConfig]) -> ValidationResponse:
    """
    Validate a list of ServiceConfig objects for common issues.
    Checks: port conflicts, image name validity, network consistency.
    
    argument:: services: List of ServiceConfig objects
    returns:: ValidationResponse with valid flag, errors, and warnings
    """
    errors: List[ValidationError] = []
    warnings: List[ValidationError] = []

    check_port_conflicts(services, errors)
    check_image_names(services, errors)
    check_network_consistency(services, warnings)
    check_environment_variables(services, warnings)
    check_healthcheck(services, errors)
    check_command(services, warnings)
    check_build_config(services, errors)
    check_volume_paths(services, errors)        
    check_network_mode(services, errors)        
    check_resource_limits(services, errors) 

    return ValidationResponse(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings
    )

def check_port_conflicts(services: List[ServiceConfig], errors: List[ValidationError]) -> None:
    """
    Check if multiple services bind to the same host port.
    
    argument:: services: List of ServiceConfig
    argument:: errors: List to append ValidationError objects into
    """
    seen_ports: dict = {}  # host_port -> service_name

    for service in services:
        for port_mapping in service.ports:
            # port_mapping is like "80:80" or "8080:80"
            host_port = port_mapping.split(":")[0]

            if host_port in seen_ports:
                errors.append(ValidationError(
                    service=service.name,
                    field="ports",
                    message=(
                        f"Port {host_port} is already used by service "
                        f"'{seen_ports[host_port]}'. Each host port must be unique."
                    ),
                    severity="error"
                ))
            else:
                seen_ports[host_port] = service.name

def check_image_names(services: List[ServiceConfig], errors: List[ValidationError]) -> None:
    """
    Validate that image names follow Docker naming conventions.
    Valid formats: nginx, nginx:latest, myrepo/image:tag, registry.io/image:v1.0
    
    argument:: services: List of ServiceConfig
    argument:: errors: List to append ValidationError objects into
    """
    # Matches: optional registry prefix, image name, optional tag
    image_pattern = re.compile(
        r'^[a-zA-Z0-9]([a-zA-Z0-9._\-/]*[a-zA-Z0-9])?(:[a-zA-Z0-9._\-]+)?$'
    )

    for service in services:
        image = service.image.strip()

        if not image:
            errors.append(ValidationError(
                service=service.name,
                field="image",
                message="Image name cannot be empty.",
                severity="error"
            ))
            continue

        if not image_pattern.match(image):
            errors.append(ValidationError(
                service=service.name,
                field="image",
                message=(
                    f"'{image}' is not a valid Docker image name. "
                    f"Expected format: 'image', 'image:tag', or 'registry/image:tag'."
                ),
                severity="error"
            ))

def check_network_consistency(services: List[ServiceConfig], warnings: List[ValidationError]) -> None:
    """
    Check that services which depend on each other share at least one network.
    If they don't share a network, they likely can't communicate.
    
    argument:: services: List of ServiceConfig
    argument:: warnings: List to append ValidationError (warning severity) objects into
    """
    # Build a lookup map: service_name -> ServiceConfig
    service_map = {s.name: s for s in services}

    for service in services:
        for dep_name in service.depends_on:
            dep_service = service_map.get(dep_name)
            if not dep_service:
                # Missing dependency — already caught by Pydantic validator in models.py
                continue

            # Only warn if BOTH services have explicit networks defined
            # If neither specifies networks, Docker puts them on the default network
            if service.networks and dep_service.networks:
                shared = set(service.networks) & set(dep_service.networks)
                if not shared:
                    warnings.append(ValidationError(
                        service=service.name,
                        field="networks",
                        message=(
                            f"'{service.name}' depends on '{dep_name}' but they share no "
                            f"common networks. '{service.name}' is on {service.networks}, "
                            f"'{dep_name}' is on {dep_service.networks}. "
                            f"They may not be able to communicate."
                        ),
                        severity="warning"
                    ))

def check_environment_variables(services: List[ServiceConfig], warnings: List[ValidationError]) -> None:
    """
    Sanitize environment variables for common issues:
    1. Empty values — likely a misconfiguration
    2. Sensitive keys in plaintext — PASSWORD, SECRET, KEY, TOKEN should use Docker secrets
    3. Invalid key names — must be UPPER_SNAKE_CASE, no spaces or special characters

    argument:: services: List of ServiceConfig
    argument:: warnings: List to append ValidationError (warning severity) objects into
    """
    SENSITIVE_KEYWORDS = {"PASSWORD", "SECRET", "KEY", "TOKEN", "API_KEY", "PRIVATE"}

    # Valid env var name: starts with letter or underscore, only alphanumeric + underscore
    valid_key_pattern = re.compile(r'^[A-Z_][A-Z0-9_]*$')

    for service in services:
        for key, value in service.environment.items():

            # Check 1: invalid key name format
            if not valid_key_pattern.match(key):
                warnings.append(ValidationError(
                    service=service.name,
                    field="environment",
                    message=(
                        f"Environment variable '{key}' has an invalid name. "
                        f"Keys should be UPPER_SNAKE_CASE (e.g. 'DATABASE_URL')."
                    ),
                    severity="warning"
                ))

            # Check 2: empty value
            if value == "" or value is None:
                warnings.append(ValidationError(
                    service=service.name,
                    field="environment",
                    message=(
                        f"Environment variable '{key}' has an empty value. "
                        f"This may cause unexpected behavior."
                    ),
                    severity="warning"
                ))

            # Check 3: sensitive key with a plaintext value
            key_upper = key.upper()
            if any(keyword in key_upper for keyword in SENSITIVE_KEYWORDS) and value:
                warnings.append(ValidationError(
                    service=service.name,
                    field="environment",
                    message=(
                        f"'{key}' appears to contain sensitive data in plaintext. "
                        f"Consider using Docker secrets or a .env file instead."
                    ),
                    severity="warning"
                ))

def check_healthcheck(services: List[ServiceConfig], errors: List[ValidationError]) -> None:
    """
    Validate healthcheck fields if defined on a service.
    Checks: duration format for interval/timeout/start_period, retries >= 1, test not empty.
    """
    duration_pattern = re.compile(r'^\d+(s|m|h)$')

    for service in services:
        if not service.healthcheck:
            continue

        hc = service.healthcheck

        for field_name, value in [
            ("interval", hc.interval),
            ("timeout", hc.timeout),
            ("start_period", hc.start_period)
        ]:
            if not duration_pattern.match(value):
                errors.append(ValidationError(
                    service=service.name,
                    field=f"healthcheck.{field_name}",
                    message=f"'{value}' is not a valid duration. Use format like '30s', '1m', '2h'.",
                    severity="error"
                ))

        if hc.retries < 1:
            errors.append(ValidationError(
                service=service.name,
                field="healthcheck.retries",
                message="retries must be at least 1.",
                severity="error"
            ))

        if not hc.test:
            errors.append(ValidationError(
                service=service.name,
                field="healthcheck.test",
                message="healthcheck.test must not be empty.",
                severity="error"
            ))

def check_command(services: List[ServiceConfig], warnings: List[ValidationError]) -> None:
    """
    Warn if command is an empty string (None is fine, empty string is likely a mistake).
    """
    for service in services:
        if service.command is not None and not service.command.strip():
            warnings.append(ValidationError(
                service=service.name,
                field="command",
                message=(
                    "Command is set but empty. Either provide a valid command "
                    "or remove it to use the image default."
                ),
                severity="warning"
            ))

def check_build_config(services: List[ServiceConfig], errors: List[ValidationError]) -> None:
    """
    Validate build context if defined on a service.
    Checks: context is not empty, dockerfile name is not empty.
    """
    for service in services:
        if not service.build:
            continue

        if not service.build.context.strip():
            errors.append(ValidationError(
                service=service.name,
                field="build.context",
                message="Build context path cannot be empty.",
                severity="error"
            ))

        if not service.build.dockerfile.strip():
            errors.append(ValidationError(
                service=service.name,
                field="build.dockerfile",
                message="Dockerfile name cannot be empty. Defaults to 'Dockerfile' if not specified.",
                severity="error"
            ))

def check_volume_paths(services: List[ServiceConfig], errors: List[ValidationError]) -> None:
    """
    Validate volume mapping format and paths.
    Checks:
    1. Must contain ':' separator
    2. Container path (right side) must be absolute (start with '/')
    3. If a mode is specified (3rd part), must be 'ro' or 'rw'

    argument:: services: List of ServiceConfig
    argument:: errors: List to append ValidationError objects into
    """
    valid_modes = {"ro", "rw"}

    for service in services:
        for volume in service.volumes:
            parts = volume.split(":")

            # Check 1: must have at least source:target
            if len(parts) < 2:
                errors.append(ValidationError(
                    service=service.name,
                    field="volumes",
                    message=(
                        f"Volume '{volume}' is missing a ':' separator. "
                        f"Expected format: 'source:target' or 'source:target:mode'."
                    ),
                    severity="error"
                ))
                continue

            container_path = parts[1]

            # Check 2: container path must be absolute
            if not container_path.startswith("/"):
                errors.append(ValidationError(
                    service=service.name,
                    field="volumes",
                    message=(
                        f"Volume '{volume}' has an invalid container path '{container_path}'. "
                        f"Container path must be absolute (start with '/')."
                    ),
                    severity="error"
                ))

            # Check 3: if mode is specified, must be 'ro' or 'rw'
            if len(parts) == 3:
                mode = parts[2]
                if mode not in valid_modes:
                    errors.append(ValidationError(
                        service=service.name,
                        field="volumes",
                        message=(
                            f"Volume '{volume}' has an invalid mode '{mode}'. "
                            f"Allowed modes are 'ro' (read-only) or 'rw' (read-write)."
                        ),
                        severity="error"
                    ))

def check_network_mode(services: List[ServiceConfig], errors: List[ValidationError]) -> None:
    """
    Validate network_mode if set on a service.
    Checks:
    1. Must be one of: bridge, host, none, container:<n>
    2. 'host' mode is incompatible with port mappings
    3. network_mode is mutually exclusive with networks list

    argument:: services: List of ServiceConfig
    argument:: errors: List to append ValidationError objects into
    """
    simple_valid_modes = {"bridge", "host", "none"}

    for service in services:
        if not service.network_mode:
            continue

        mode = service.network_mode.strip()

        # Check 1: valid mode value
        is_container_mode = mode.startswith("container:")
        if mode not in simple_valid_modes and not is_container_mode:
            errors.append(ValidationError(
                service=service.name,
                field="network_mode",
                message=(
                    f"'{mode}' is not a valid network mode. "
                    f"Valid values are: 'bridge', 'host', 'none', 'container:<n>'."
                ),
                severity="error"
            ))

        # Check 2: host mode + ports is a conflict
        if mode == "host" and service.ports:
            errors.append(ValidationError(
                service=service.name,
                field="network_mode",
                message=(
                    f"'network_mode: host' shares the host's network stack — "
                    f"port mappings are ignored. Remove 'ports' or change network_mode."
                ),
                severity="error"
            ))

        # Check 3: network_mode and networks are mutually exclusive
        if service.networks:
            errors.append(ValidationError(
                service=service.name,
                field="network_mode",
                message=(
                    f"'network_mode: {mode}' cannot be used together with 'networks'. "
                    f"Remove one or the other."
                ),
                severity="error"
            ))

def check_resource_limits(services: List[ServiceConfig], errors: List[ValidationError]) -> None:
    """
    Validate cpu_limit and memory_limit if set on a service.
    Checks:
    1. cpu_limit must be a float between 0.0 and 64.0
    2. memory_limit must match Docker memory format: 512M, 1G, 256m, 1.5g, etc.

    argument:: services: List of ServiceConfig
    argument:: errors: List to append ValidationError objects into
    """
    memory_pattern = re.compile(r'^\d+(\.\d+)?[bBkKmMgG]$')

    for service in services:

        # CPU limit check
        if service.cpu_limit is not None:
            if service.cpu_limit <= 0:
                errors.append(ValidationError(
                    service=service.name,
                    field="cpu_limit",
                    message=(
                        f"cpu_limit must be greater than 0. Got '{service.cpu_limit}'."
                    ),
                    severity="error"
                ))
            elif service.cpu_limit > 64.0:
                errors.append(ValidationError(
                    service=service.name,
                    field="cpu_limit",
                    message=(
                        f"cpu_limit of '{service.cpu_limit}' seems unreasonably high. "
                        f"Maximum allowed is 64.0 cores."
                    ),
                    severity="error"
                ))

        # Memory limit check
        if service.memory_limit is not None:
            if not memory_pattern.match(service.memory_limit):
                errors.append(ValidationError(
                    service=service.name,
                    field="memory_limit",
                    message=(
                        f"'{service.memory_limit}' is not a valid memory limit. "
                        f"Use format like '512M', '1G', '256m', '1.5g'."
                    ),
                    severity="error"
                ))