import yaml


def test_docker_compose_services() -> None:
    data = yaml.safe_load(open("docker-compose.yml"))
    services = data.get("services", {})
    assert set(["db", "search", "web"]).issubset(services)
