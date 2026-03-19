import tempfile, os, subprocess
from typing import Any

import docker
from docker.errors import DockerException

class DockerManagerError(Exception):
    """Raised for known Docker integration errors (daemon not running, bad compose, etc.)"""
    pass

def _get_client() -> docker.DockerClient:
    """
    Return a connected Docker client.
    Raises DockerManagerError with a friendly message if the daemon is unreachable.
    """
    try:
        client = docker.from_env()
        client.ping()  # quick connectivity check
        return client
    except DockerException as e:
        raise DockerManagerError(
            "Could not connect to the Docker daemon. "
            "Make sure Docker is installed and running on this machine. "
            f"(Detail: {e})"
        )


def deploy_compose(yaml_content: str, project_name: str) -> dict[str, Any]:
    """
    Write YAML to a temp file and run `docker compose up -d` for the given project.
 
    argument:: yaml_content:  Raw docker-compose YAML string to deploy
    argument:: project_name:  Logical project name (passed as --project-name to compose)
    returns::  dict with keys:
                 - success (bool)
                 - project_name (str)
                 - message (str)   — stdout/stderr summary from compose
    raises::   DockerManagerError on daemon connection failure or compose errors
    """
    # Verify daemon is reachable before doing anything else
    _get_client()
 
    # Write YAML to a named temp file that docker compose can read
    tmp_file = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".yml",
            prefix=f"containercraft_{project_name}_",
            delete=False,
        ) as f:
            f.write(yaml_content)
            tmp_file = f.name
 
        result = subprocess.run(
            [
                "docker", "compose",
                "--project-name", project_name,
                "--file", tmp_file,
                "up", "--detach", "--remove-orphans",
            ],
            capture_output=True,
            text=True,
        )
 
        # docker compose writes progress to stderr even on success
        output = (result.stdout + result.stderr).strip()
 
        if result.returncode != 0:
            raise DockerManagerError(
                f"docker compose up failed for project '{project_name}':\n{output}"
            )
 
        return {
            "success": True,
            "project_name": project_name,
            "message": output or "Deployment started successfully.",
        }
 
    except DockerManagerError:
        raise
    except FileNotFoundError:
        raise DockerManagerError(
            "'docker compose' command not found. "
            "Make sure Docker with the Compose plugin is installed and on PATH."
        )
    except Exception as e:
        raise DockerManagerError(f"Unexpected error during deployment: {e}")
    finally:
        # Always clean up the temp file
        if tmp_file and os.path.exists(tmp_file):
            os.unlink(tmp_file)
 
 
def get_project_status(project_name: str) -> dict[str, Any]:
    """
    Return the running status of all containers belonging to a compose project.
 
    argument:: project_name: The --project-name used when deploying
    returns::  dict with keys:
                 - project_name (str)
                 - containers (list[dict]) — one entry per container with:
                     name, image, status, state, ports
                 - overall (str) — 'running' | 'partial' | 'stopped' | 'not_found'
    raises::   DockerManagerError on daemon connection failure
    """
    client = _get_client()
 
    # Containers created by `docker compose --project-name X` are labelled with
    # com.docker.compose.project=X
    containers = client.containers.list(
        all=True,  # include stopped containers
        filters={"label": f"com.docker.compose.project={project_name}"},
    )
 
    if not containers:
        return {
            "project_name": project_name,
            "containers": [],
            "overall": "not_found",
        }
 
    container_info = []
    states = set()
 
    for c in containers:
        # Port bindings: {container_port/proto: [{HostIp, HostPort}]}
        ports = {
            port: [f"{b['HostIp']}:{b['HostPort']}" for b in bindings]
            for port, bindings in (c.ports or {}).items()
            if bindings
        }
        container_info.append({
            "name": c.name,
            "image": c.image.tags[0] if c.image.tags else c.image.short_id,
            "status": c.status,        # e.g. "running", "exited"
            "state": c.attrs.get("State", {}).get("Status", "unknown"),
            "ports": ports,
        })
        states.add(c.status)
 
    # Derive a simple overall health summary
    if states == {"running"}:
        overall = "running"
    elif "running" in states:
        overall = "partial"
    else:
        overall = "stopped"
 
    return {
        "project_name": project_name,
        "containers": container_info,
        "overall": overall,
    }
 