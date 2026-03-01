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



class ComposeConfig(BaseModel):

class ValidationError(BaseModel):

class ValidationResponse(BaseMOdel):

