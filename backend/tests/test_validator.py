import pytest
from app.models import ServiceConfig, RestartPolicy
from app.core.validator import validate_compose_config


# Helpers 

def make_service(**kwargs) -> ServiceConfig:
    """Shortcut to build a ServiceConfig with sensible defaults."""
    defaults = {
        "name": "app",
        "image": "nginx:latest",
        "ports": [],
        "environment": {},
        "volumes": [],
        "networks": [],
        "depends_on": [],
        "restart": RestartPolicy.unless_stopped,
    }
    defaults.update(kwargs)
    return ServiceConfig(**defaults)


# Port conflict tests 

class TestPortConflicts:

    def test_no_conflict_passes(self):
        """Two services on different ports should be valid."""
        services = [
            make_service(name="web", ports=["80:80"]),
            make_service(name="api", ports=["3000:3000"]),
        ]
        result = validate_compose_config(services)
        assert result.valid is True
        assert len(result.errors) == 0

    def test_same_host_port_is_error(self):
        """Two services binding the same host port should produce an error."""
        services = [
            make_service(name="web", ports=["80:80"]),
            make_service(name="nginx", ports=["80:8080"]),  # host port 80 conflict
        ]
        result = validate_compose_config(services)
        assert result.valid is False
        assert any("80" in e.message for e in result.errors)

    def test_same_container_port_different_host_is_fine(self):
        """Same container port but different host ports should not conflict."""
        services = [
            make_service(name="web", ports=["8080:80"]),
            make_service(name="api", ports=["8081:80"]),
        ]
        result = validate_compose_config(services)
        assert result.valid is True


# Image name tests 

class TestImageNames:

    def test_valid_image_with_tag(self):
        services = [make_service(image="nginx:latest")]
        result = validate_compose_config(services)
        assert result.valid is True

    def test_valid_image_without_tag(self):
        services = [make_service(image="nginx")]
        result = validate_compose_config(services)
        assert result.valid is True

    def test_valid_image_with_registry(self):
        services = [make_service(image="myregistry.io/myimage:v1.0")]
        result = validate_compose_config(services)
        assert result.valid is True

    def test_invalid_image_with_spaces(self):
        services = [make_service(image="my image:latest")]
        result = validate_compose_config(services)
        assert result.valid is False
        assert any(e.field == "image" for e in result.errors)

    def test_invalid_image_special_chars(self):
        services = [make_service(image="nginx@#$")]
        result = validate_compose_config(services)
        assert result.valid is False


# Network consistency tests 

class TestNetworkConsistency:

    def test_dependent_services_share_network_no_warning(self):
        """app depends on db and they share 'backend' — no warning expected."""
        services = [
            make_service(name="db", networks=["backend"]),
            make_service(name="app", networks=["backend"], depends_on=["db"]),
        ]
        result = validate_compose_config(services)
        network_warnings = [w for w in result.warnings if w.field == "networks"]
        assert len(network_warnings) == 0

    def test_dependent_services_no_shared_network_warns(self):
        """app depends on db but they are on completely different networks."""
        services = [
            make_service(name="db", networks=["backend"]),
            make_service(name="app", networks=["frontend"], depends_on=["db"]),
        ]
        result = validate_compose_config(services)
        network_warnings = [w for w in result.warnings if w.field == "networks"]
        assert len(network_warnings) == 1
        assert "app" in network_warnings[0].message
        assert "db" in network_warnings[0].message

    def test_no_networks_defined_no_warning(self):
        """If neither service defines networks, Docker handles it — no warning."""
        services = [
            make_service(name="db"),
            make_service(name="app", depends_on=["db"]),
        ]
        result = validate_compose_config(services)
        network_warnings = [w for w in result.warnings if w.field == "networks"]
        assert len(network_warnings) == 0


# Environment variable tests 

class TestEnvironmentVariables:

    def test_clean_env_vars_no_warnings(self):
        """Normal non-sensitive env vars should produce no warnings."""
        services = [
            make_service(environment={"NODE_ENV": "production", "PORT": "3000"})
        ]
        result = validate_compose_config(services)
        env_warnings = [w for w in result.warnings if w.field == "environment"]
        assert len(env_warnings) == 0

    def test_sensitive_key_warns(self):
        """Keys like PASSWORD, SECRET, TOKEN should trigger a plaintext warning."""
        services = [
            make_service(environment={"POSTGRES_PASSWORD": "mysecret"})
        ]
        result = validate_compose_config(services)
        env_warnings = [w for w in result.warnings if w.field == "environment"]
        assert len(env_warnings) == 1
        assert "sensitive" in env_warnings[0].message.lower()

    def test_empty_value_warns(self):
        """An env var with an empty string value should warn."""
        services = [
            make_service(environment={"DATABASE_URL": ""})
        ]
        result = validate_compose_config(services)
        env_warnings = [w for w in result.warnings if w.field == "environment"]
        assert any("empty" in w.message.lower() for w in env_warnings)

    def test_invalid_key_name_warns(self):
        """Lowercase or special character key names should warn."""
        services = [
            make_service(environment={"my-var": "value"})
        ]
        result = validate_compose_config(services)
        env_warnings = [w for w in result.warnings if w.field == "environment"]
        assert any("invalid" in w.message.lower() for w in env_warnings)


#Full clean config test 

class TestCleanConfig:

    def test_fully_valid_config_passes(self):
        """A well-formed multi-service config should return valid with no errors."""
        services = [
            make_service(
                name="postgres",
                image="postgres:14",
                networks=["backend"],
                volumes=["postgres_data:/var/lib/postgresql/data"],
            ),
            make_service(
                name="app",
                image="node:18",
                ports=["3000:3000"],
                networks=["backend", "frontend"],
                depends_on=["postgres"],
                environment={"NODE_ENV": "production"},
            ),
        ]
        result = validate_compose_config(services)
        assert result.valid is True
        assert len(result.errors) == 0