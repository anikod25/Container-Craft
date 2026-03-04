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

