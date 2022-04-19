from pathlib import Path

import pytest
from backupbot.docker.container_utils import (
    docker_compose_down,
    docker_compose_start,
    docker_compose_stop,
    docker_compose_up,
    stop_and_restart_container,
)

from docker import DockerClient


def test_stop_and_restart_container(docker_client: DockerClient):
    container_name = "sleeping_ubuntu"
    docker_client.containers.run("ubuntu:latest", "sleep infinity", name=container_name, detach=True)
    docker_client.containers.get(container_name)

    with stop_and_restart_container(docker_client, container_name, timeout=5) as stopped_container:
        assert docker_client.containers.get(container_name).status == "exited"

    assert docker_client.containers.get(container_name).status == "running"

    docker_client.containers.get(container_name).stop()
    docker_client.containers.get(container_name).remove()


def test_stop_and_restart_container_raises_error_when_container_is_not_running(docker_client: DockerClient) -> None:
    container_name = "sleeping_ubuntu"
    docker_client.containers.run("ubuntu:latest", "sleep infinity", name=container_name, detach=True)
    docker_client.containers.get(container_name).stop()

    with pytest.raises(RuntimeError):
        with stop_and_restart_container(docker_client, container_name) as _:
            pass

    docker_client.containers.get(container_name).remove()


def test_docker_compose(sample_docker_compose_project_dir: Path, docker_client: DockerClient) -> None:
    compose_file = sample_docker_compose_project_dir.joinpath("docker-compose.yaml")

    docker_compose_up(compose_file)
    containers = [container.name for container in docker_client.containers.list()]

    assert "bind_mount_service" in containers
    assert "volume_service" in containers
    assert "mysql_service" in containers

    docker_compose_stop(compose_file)
    containers = [container.name for container in docker_client.containers.list(filters={"status": "exited"})]

    assert "bind_mount_service" in containers
    assert "volume_service" in containers
    assert "mysql_service" in containers

    docker_compose_start(compose_file)
    containers = [container.name for container in docker_client.containers.list()]

    assert "bind_mount_service" in containers
    assert "volume_service" in containers
    assert "mysql_service" in containers

    docker_compose_down(compose_file)
    containers = [container.name for container in docker_client.containers.list(all=True)]

    assert "bind_mount_service" not in containers
    assert "volume_service" not in containers
    assert "mysql_service" not in containers


def test_docker_compose_up_raises_error_for_invalid_compose_file() -> None:
    with pytest.raises(RuntimeError):
        docker_compose_up(Path("not/existing"))

    with pytest.raises(RuntimeError):
        docker_compose_up(Path("not/existing.yaml"))


def test_docker_compose_start_raises_error_for_invalid_compose_file() -> None:
    with pytest.raises(RuntimeError):
        docker_compose_start(Path("not/existing"))

    with pytest.raises(RuntimeError):
        docker_compose_start(Path("not/existing.yaml"))


def test_docker_compose_stop_raises_error_for_invalid_compose_file() -> None:
    with pytest.raises(RuntimeError):
        docker_compose_stop(Path("not/existing"))

    with pytest.raises(RuntimeError):
        docker_compose_stop(Path("not/existing.yaml"))


def test_docker_compose_down_raises_error_for_invalid_compose_file() -> None:
    with pytest.raises(RuntimeError):
        docker_compose_down(Path("not/existing"))

    with pytest.raises(RuntimeError):
        docker_compose_down(Path("not/existing.yaml"))
