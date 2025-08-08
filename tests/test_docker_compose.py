from pathlib import Path

import yaml


def test_docker_compose_services() -> None:
    """Test that docker-compose.yml contains the expected services."""
    # Get the path to docker-compose.yml relative to the project root
    docker_compose_path = Path(__file__).parent.parent / "docker-compose.yml"
    data = yaml.safe_load(open(docker_compose_path))
    services = data.get("services", {})
    assert set(["db", "search", "web"]).issubset(services)
