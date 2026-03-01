from pydantic import BaseModel, Field, validator
from typing import List, Dict, Optional
from enum import Enum

class RestartPolicy(str, Enum):
    """Restart policy options for Docker services"""
    no = "no"
    always = "always"
    on_failure = "on-failure"
    unless_stopped = "unless-stopped"

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

    # Validators
    @validator('ports')
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
    
    @validator('name')
    def validate_name(cls, v):
        """Ensure service name is valid"""
        if not v or not v.strip():
            raise ValueError("Service name cannot be empty")
        # Docker service names: lowercase, alphanumeric, hyphens, underscores
        import re
        if not re.match(r'^[a-z0-9_-]+$', v):
            raise ValueError("Service name must be lowercase alphanumeric with hyphens/underscores")
        return v
    
    @validator('image')
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
                "restart": "unless-stopped"
            }
        }


class ComposeConfig(BaseModel):

class ValidationError(BaseModel):

class ValidationResponse(BaseMOdel):

