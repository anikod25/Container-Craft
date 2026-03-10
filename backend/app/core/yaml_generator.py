from typing import List, Dict, Any
import yaml
# Handle imports for both module and script execution
try:
    # When imported as a module (normal case)
    from ..models import ServiceConfig, ComposeConfig, RestartPolicy, HealthCheck, BuildConfig
except ImportError:
    # When run as a script
    import sys
    from pathlib import Path
    backend_dir = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(backend_dir))
    from app.models import ServiceConfig, ComposeConfig
    from app.core.yaml_formatter import dump_compose

class YAMLGenerator:
    def __init__(self):
        self.compose_version = "3.8"
    
    def generate_yaml(self, compose_config: ComposeConfig) -> str:
        """
        Generate docker-compose YAML from ComposeConfig
        arguement:: compose_config: ComposeConfig object with services
        output format:: str: Formatted YAML string
        """
        compose_dict = {
            "version": compose_config.version,
            "services": {}
        }

        for service in compose_config.services:
            compose_dict["services"][service.name] = self._service_to_dict(service)
        
        networks = self._extract_networks(compose_config.services)
        if networks:
            compose_dict["networks"] = networks
        
        volumes = self._extract_volumes(compose_config.services)
        if volumes:
            compose_dict["volumes"] = volumes

        # keeping the previous yaml_output commented for refernce, using helper functions from yaml_formatter for better formatting and section breaks.

        #converting to yaml format with apt. formatting

        # yaml_output = yaml.dump(
        #     compose_dict,
        #     default_flow_style=False,
        #     sort_keys=False,
        #     indent=2,
        #     allow_unicode=True
        # )
        
        # return yaml_output

        return dump_compose(compose_dict)

    def _service_to_dict(self, service: ServiceConfig) -> Dict[str, Any]:
        """
        Convert ServiceConfig to dictionary for YAML
        arguement:: service: ServiceConfig object
        output format:: dict: Service configuration as dictionary
        """
        service_dict = {
            "image": service.image
        }
        
        # add ports if specified
        if service.ports:
            service_dict["ports"] = service.ports
        
        # add environment variables if specified
        if service.environment:
            service_dict["environment"] = service.environment
        
        # add volumes if specified
        if service.volumes:
            service_dict["volumes"] = service.volumes
        
        # add networks if specified
        if service.networks:
            service_dict["networks"] = service.networks
        
        # add depends_on if specified
        if service.depends_on:
            service_dict["depends_on"] = service.depends_on
        
        # add restart policy (convert enum to string)
        if service.restart:
            service_dict["restart"] = service.restart.value
        
        # add command if specified
        if service.command:
            service_dict["command"] = service.command

        # add healthcheck if specified
        if service.healthcheck:
            service_dict["healthcheck"] = {
                "test": service.healthcheck.test,
                "interval": service.healthcheck.interval,
                "timeout": service.healthcheck.timeout,
                "retries": service.healthcheck.retries,
                "start_period": service.healthcheck.start_period,
            }

        # add build config if specified
        if service.build:
            service_dict["build"] = {
                "context": service.build.context,
                "dockerfile": service.build.dockerfile,
            }
        
        return service_dict
    
    def _extract_networks(self, services: List[ServiceConfig]) -> Dict[str, Any]:
        """
        Extract unique networks from services and create network definitions
        arguements:: services: List of ServiceConfig objects   
        returns:: dict: Network definitions
        """
        # getting in all the unique network names.
        network_names = set()
        for service in services:
            network_names.update(service.networks)

            if service.depends_on and not service.networks:
                network_names.add("default")

        if not network_names:
            return {}
        
        # Create network definitions (using default driver)
        networks = {}
        for network_name in network_names:
            networks[network_name] = {
                "driver": "bridge"
            }
        
        return networks
    
    def _extract_volumes(self, services: List[ServiceConfig]) -> Dict[str, Any]:
        """
        Extract named volumes from services and create top-level volume definitions.
        Named volumes are those that don't start with '.' or '/' (not bind mounts).
        e.g. 'postgres_data:/var/lib/postgresql/data' -> named volume 'postgres_data'
             './data:/app' -> bind mount, skipped

        arguements:: services: List of ServiceConfig objects
        returns:: dict: Named volume definitions (empty dict = use Docker defaults)
        """
        named_volumes = set()

        for service in services:
            for volume_mapping in service.volumes:
                source = volume_mapping.split(":")[0]  # get left side of "source:target"
                # bind mounts start with . or / — skip them
                if not source.startswith((".", "/")):
                    named_volumes.add(source)

        if not named_volumes:
            return {}

        # None value means Docker uses default volume settings
        return {vol: {} for vol in sorted(named_volumes)}

# testing yamlgenerator with basic information.
def test_yaml_generator():
    """Test the YAML generator with sample data"""
    from app.models import ServiceConfig, ComposeConfig, RestartPolicy
    
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
    import sys
    from pathlib import Path
    
    # Add backend directory to Python path so absolute imports work
    backend_dir = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(backend_dir))
    
    # Import RestartPolicy for standalone execution
    from app.models import RestartPolicy, ComposeConfig, ServiceConfig
    
    # Run test when script is executed directly
    test_yaml_generator()