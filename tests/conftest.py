#!/usr/bin/env python3

"""Testing fixtures."""

from contextlib import contextmanager
from email.generator import Generator
from pathlib import Path
from typing import Callable

import pytest
from docker import DockerClient, from_env
from docker.errors import NotFound

from backupbot.docker_compose.container_utils import (
    docker_compose_down,
    docker_compose_up,
    docker_exec,
)


@pytest.fixture
def resources_dir() -> Path:
    return Path(__file__).parent.joinpath("resources")


@pytest.fixture
def dummy_docker_compose_file() -> Path:
    """Returns the path to the dummy Dockerfile located in /tests/utils.

    Returns:
        Path: Path instance.
    """
    return Path(__file__).parent.joinpath("resources", "docker-compose.yaml")


@pytest.fixture
def dummy_backup_scheme_file() -> Path:
    """Returns the path to the dummy Dockerfile located in /tests/utils.

    Returns:
        Path: Path instance.
    """
    return Path(__file__).parent.joinpath("resources", "docker_backup_scheme.json")


@pytest.fixture
def dummy_bind_mount_dir() -> Path:
    """Returns the path to a dummy folder structure containing dummy text files.

    Returns:
        Path: _description_
    """
    return Path(__file__).parent.joinpath("resources", "sample_bind_mount_dir")


@pytest.fixture(scope="session")
def docker_client() -> DockerClient:
    """Returns the host's docker client.

    Returns:
        DockerClient: Docker client instance.
    """
    client = from_env()
    return client


@pytest.fixture
def sample_docker_compose_project_dir() -> Path:
    """Returns the path to the dummy (but working) docker-compose project.

    Returns:
        Path: Path instance.
    """
    return Path(__file__).parent.joinpath("resources", "sample_docker_compose_service")


@pytest.fixture
def running_docker_compose_project() -> Callable:
    """Returns a callable which can be used to start a docker-compose project.

    Returns:
        Callable: Callable function.
    """

    @contextmanager
    def func(compose_file: Path) -> Generator:
        """Provides a the specified docker compose context and shuts it down if necessary after the test.

        Args:
            compose_file (Path): Path to the docker-compose file.

        Yields:
            Generator: Yields None.
        """
        docker_compose_up(compose_file)
        docker_exec("mysql_service", "chmod +x /mount/create.sh && ./mount/create.sh")
        try:
            yield None
        finally:
            docker_compose_down(compose_file)

    return func


@pytest.fixture(scope="function")
@contextmanager
def running_sleeping_ubuntu() -> str:
    client = from_env()

    container_name = "sleeping_container"

    try:
        client.containers.get(container_name)
        if client.containers.get(container_name).status == "exited":
            # else container is running
            client.containers.get(container_name).restart()
    except NotFound:
        # if the container name does not exist start a new container
        client.containers.run("ubuntu:latest", "sleep_infinity", name=container_name, detach=True)

    # if client.containers.get(container_name).status == "running":
    yield container_name

    try:
        if client.containers.get(container_name).status == "running":
            client.containers.get(container_name).stop()
        client.containers.get(container_name).remove()
    except:
        # container does not exist anymore
        pass
