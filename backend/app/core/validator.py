import re
from typing import List
from app.models import ServiceConfig, ValidationError, ValidationResponse

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