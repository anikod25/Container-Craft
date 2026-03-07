from typing import List, Dict, Any
import yaml

from app.core.yaml_generator import YAMLGenerator
from app.models import ServiceConfig, ComposeConfig, RestartPolicy

def test_yaml_generator():
    """Test the YAML generator with sample data"""
    
    # Create sample services
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
    
    # Create compose config
    compose = ComposeConfig(
        version="3.8",
        services=[nginx, postgres, app]
    )
    
    # Generate YAML
    generator = YAMLGenerator()
    yaml_output = generator.generate_yaml(compose)
    
    print("Generated docker-compose.yml:")
    print("=" * 50)
    print(yaml_output)
    print("=" * 50)
    
    return yaml_output


if __name__ == "__main__":
    # Run test when script is executed directly
    test_yaml_generator()