from app.models import ServiceConfig, ComposeConfig, RestartPolicy, ValidationError, ValidationResponse

from pydantic import BaseModel, Field, validator
from typing import List, Dict, Optional
from enum import Enum

def service_config_test():
    """Test the ServiceConfig model with sample data"""
    nginx = ServiceConfig(
        name="nginx",
        image="nginx:latest",
        ports=["80:80", "443:443"],
        volumes=["./nginx.conf:/etc/nginx/nginx.conf:ro"],
        networks=["frontend"],
        restart=RestartPolicy.unless_stopped
    )
    
    assert nginx.name == "nginx"
    assert nginx.image == "nginx:latest"
    assert nginx.ports == ["80:80", "443:443"]
    assert nginx.volumes == ["./nginx.conf:/etc/nginx/nginx.conf:ro"]
    assert nginx.networks == ["frontend"]
    assert nginx.restart == RestartPolicy.unless_stopped
    print("ServiceConfig test passed!")

def compose_config_test():
    """Test the ComposeConfig model with sample data"""
    nginx = ServiceConfig(
        name="nginx",
        image="nginx:latest",
        ports=["80:80", "443:443"],
        volumes=["./nginx.conf:/etc/nginx/nginx.conf:ro"],
        networks=["frontend"],
        restart=RestartPolicy.unless_stopped
    )
    
    postgres = ServiceConfig(
        name="postgres",
        image="postgres:14",
        environment={
            "POSTGRES_PASSWORD": "secret",
            "POSTGRES_DB": "mydb",
            "POSTGRES_USER": "admin"
        },
        volumes=["postgres_data:/var/lib/postgresql/data"],
        networks=["backend"],
        restart=RestartPolicy.always
    )
    
    app = ServiceConfig(
        name="app",
        image="node:18",
        command="npm start",
        ports=["3000:3000"],
        environment={"NODE_ENV": "development"},
        networks=["frontend", "backend"],
        depends_on=["postgres"],
        restart=RestartPolicy.unless_stopped
    )
    
    compose = ComposeConfig(
        version="3.8",
        services=[nginx, postgres, app]
    )
    
    assert compose.version == "3.8"
    assert len(compose.services) == 3
    assert compose.services[0].name == "nginx"
    assert compose.services[1].name == "postgres"
    assert compose.services[2].name == "app"
    
    print("ComposeConfig test passed!")

def validation_test():
    """Test validation logic in the models"""
    try:
        invalid_service = ServiceConfig(
            name="invalid",
            image="",
            ports=["invalid_port"],
            volumes=["invalid_volume"],
            networks=["invalid_network"],
            restart="invalid_restart"
        )
    except ValidationError as e:
        print("Validation test passed with error:", e)
    else:
        print("Validation test failed - no error raised for invalid data")

if __name__ == "__main__":
    service_config_test()
    compose_config_test()
    validation_test()