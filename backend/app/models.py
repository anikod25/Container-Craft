from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Optional
from enum import Enum

class RestartPolicy(str, Enum):
    """Restart policy options for Docker services"""
    no = "no"
    always = "always"
    on_failure = "on-failure"
    unless_stopped = "unless-stopped"

class HealthCheck(BaseModel):
    test: List[str] = Field(
        ...,
        description = "Test command (e.g., ['CMD', 'curl', '-f', 'http://localhost'])",
        example = ["CMD", "curl", "-f", "http://localhost"]
    )
    interval: str = Field(default = "30s", description = "Time between checks (e.g., '30s', '1m')")
    timeout: str = Field(default = "10s", description = "Max time for a single check (e.g., '10s')")
    retries: int = Field(default = 3, description = "Consecutive failures before marked unhealthy")
    start_period: str = Field(default = "0s", description = "Init time before failures count (e.g., '40s')")


class BuildConfig(BaseModel):
    context: str = Field(
        ...,
        description = "Path to build context (e.g., './backend')",
        example = "./backend"
    )
    dockerfile: str = Field(
        default = "Dockerfile",
        description = "Dockerfile path relative to context",
        example = "Dockerfile.prod"
    )

class ServiceConfig(BaseModel):
    """Model for a single Docker service configuration"""

    #Basic config
    name: str = Field(..., description="Service name (e.g., 'nginx', 'postgres')")
    image: str = Field(..., description="Docker image (e.g., 'nginx:latest')")

    # Port mappings
    ports: List[str] = Field(
        default_factory=list,
        description="Port mappings (e.g., ['80:80', '443:443'])",
        example=["8080:80"]
    )

    # Environment variables
    environment: Dict[str, str] = Field(
        default_factory=dict,
        description="Environment variables",
        example={"POSTGRES_PASSWORD": "secret", "POSTGRES_DB": "mydb"}
    )

    # Volume mappings
    volumes: List[str] = Field(
        default_factory=list,
        description="Volume mappings (e.g., ['./data:/var/lib/postgresql/data'])",
        example=["./nginx.conf:/etc/nginx/nginx.conf:ro"]
    )
    
    # Networks
    networks: List[str] = Field(
        default_factory=list,
        description="Networks this service connects to",
        example=["frontend", "backend"]
    )
    
    # Dependencies
    depends_on: List[str] = Field(
        default_factory=list,
        description="Services this depends on",
        example=["postgres", "redis"]
    )
    
    # Advanced options
    restart: RestartPolicy = Field(
        default=RestartPolicy.unless_stopped,
        description="Restart policy"
    )
    
    command: Optional[str] = Field(
        None,
        description="Override default command",
        example="npm start"
    )

    # needs new fields for healthcheck and build configurations

    healthcheck: Optional[HealthCheck] = Field(
        None,
        description = "Healthcheck configuration for this service"
    )

    build: Optional[BuildConfig] = Field(
        None,
        description = "Build context config (custom Dockerfile). If set, used alongside or instead of image."
    )

    network_mode: Optional[str] = Field(
        None,
        description=(
            "Docker network mode. Valid values: 'bridge', 'host', 'none', 'container:<name>'. "
            "Mutually exclusive with 'networks' and 'ports' when set to 'host'."
        ),
        example="host"
    )

    cpu_limit: Optional[float] = Field(
        None,
        description="Max CPU cores the container can use (e.g., 0.5 = half a core, 2.0 = 2 cores).",
        example=0.5
    )

    memory_limit: Optional[str] = Field(
        None,
        description="Max memory the container can use (e.g., '512M', '1G', '256m').",
        example="512M"
    )
    # Validators
    @field_validator('ports')
    @classmethod
    def validate_ports(cls, v):
        """Ensure ports are in correct format"""
        for port in v:
            if ':' not in port:
                raise ValueError(f"Port must be in format 'host:container', got: {port}")
            parts = port.split(':')
            if len(parts) != 2:
                raise ValueError(f"Invalid port format: {port}")
            # Validate port numbers
            try:
                host_port, container_port = parts
                int(host_port.split('/')[0])  # Handle tcp/udp suffix
                int(container_port.split('/')[0])
            except ValueError:
                raise ValueError(f"Port numbers must be integers: {port}")
        return v
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        """Ensure service name is valid"""
        if not v or not v.strip():
            raise ValueError("Service name cannot be empty")
        # Docker service names: lowercase, alphanumeric, hyphens, underscores
        import re
        if not re.match(r'^[a-z0-9_-]+$', v):
            raise ValueError("Service name must be lowercase alphanumeric with hyphens/underscores")
        return v
    
    @field_validator('image')
    @classmethod
    def validate_image(cls, v):
        """Ensure image name is not empty"""
        if not v or not v.strip():
            raise ValueError("Image name cannot be empty")
        return v

    class Config:
        schema_extra = {
            "example": {
                "name": "nginx",
                "image": "nginx:latest",
                "ports": ["80:80"],
                "environment": {"NGINX_HOST": "localhost"},
                "volumes": ["./html:/usr/share/nginx/html:ro"],
                "networks": ["frontend"],
                "depends_on": [],
                "restart": "unless-stopped",
                "healthcheck": {
                    "test": ["CMD", "curl", "-f", "http://localhost"],
                    "interval": "30s",
                    "timeout": "10s",
                    "retries": 3,
                    "start_period": "0s"
                },
                "build": {
                    "context": "./backend",
                    "dockerfile": "Dockerfile"
                }
            }
        }


class ComposeConfig(BaseModel):
    """Model for complete docker-compose configuration"""
    
    version: str = Field(
        default="3.8",
        description="Docker Compose file version"
    )
    
    services: List[ServiceConfig] = Field(
        ...,
        description="List of services in the compose file",
        min_length=1
    )
    
    @field_validator('services')
    @classmethod
    def validate_unique_names(cls, v):
        """Ensure all service names are unique"""
        names = [service.name for service in v]
        if len(names) != len(set(names)):
            duplicates = [name for name in names if names.count(name) > 1]
            raise ValueError(f"Duplicate service names found: {duplicates}")
        return v
    
    @field_validator('services')
    @classmethod
    def validate_dependencies(cls, v):
        """Ensure depends_on references exist"""
        service_names = {service.name for service in v}
        for service in v:
            for dep in service.depends_on:
                if dep not in service_names:
                    raise ValueError(
                        f"Service '{service.name}' depends on '{dep}' which doesn't exist"
                    )
        return v

    class Config:
        schema_extra = {
            "example": {
                "version": "3.8",
                "services": [
                    {
                        "name": "nginx",
                        "image": "nginx:latest",
                        "ports": ["80:80"],
                        "networks": ["frontend"]
                    },
                    {
                        "name": "postgres",
                        "image": "postgres:14",
                        "environment": {"POSTGRES_PASSWORD": "secret"},
                        "networks": ["backend"]
                    }
                ]
            }
        }

class ValidationError(BaseModel):
    """Model for validation errors"""
    service: str = Field(..., description="Service name with error")
    field: str = Field(..., description="Field that has error")
    message: str = Field(..., description="Error message")
    severity: str = Field(
        default="error",
        description="Severity: 'error' or 'warning'"
    )

class ValidationResponse(BaseModel):
    """Response model for validation endpoint"""
    valid: bool = Field(..., description="Whether configuration is valid")
    errors: List[ValidationError] = Field(
        default_factory=list,
        description="List of validation errors"
    )
    warnings: List[ValidationError] = Field(
        default_factory=list,
        description="List of warnings"
    )