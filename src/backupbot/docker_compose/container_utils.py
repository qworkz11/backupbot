#!/usr/bin/env python3

"""Utility functions to integrate docker and docker-compose functionality."""

from contextlib import contextmanager
from pathlib import Path
from subprocess import CompletedProcess, run

from docker import DockerClient


@contextmanager
def stop_and_restart_container(client: DockerClient, container_name: str, timeout: int = 20) -> None:
    container_status = client.containers.get(container_name).status

    if container_status == "running":
        client.containers.get(container_name).stop(timeout=timeout)
        yield None
        client.containers.get(container_name).restart(timeout=timeout)
    else:
        raise RuntimeError(
            f"Container '{container_name}' must be runnung to be stopped and restarted, but is: '{container_status}'."
        )


def docker_compose_up(compose_file: Path) -> None:
    if not compose_file.is_file() or not compose_file.name.lower().endswith(".yaml"):
        raise RuntimeError(f"Failed to call docker-compose up: Compose file must be of type .yaml: '{compose_file}'.")

    args = ("docker-compose", "-f", compose_file.absolute(), "up", "-d")

    result: CompletedProcess = run(args)

    if result.returncode != 0:
        raise RuntimeError(f"Failed to call docker-compose up: '{result.stdout}'.")


def docker_compose_start(compose_file: Path) -> None:
    if not compose_file.is_file() or not compose_file.name.lower().endswith(".yaml"):
        raise RuntimeError(
            f"Failed to call docker-compose restart: Compose file must be of type .yaml: '{compose_file}'."
        )

    args = ("docker-compose", "-f", compose_file.absolute(), "start")

    result: CompletedProcess = run(args)

    if result.returncode != 0:
        raise RuntimeError(f"Failed to call docker-compose start: '{result.stderr}'.")


def docker_compose_stop(compose_file: Path) -> None:
    if not compose_file.is_file() or not compose_file.name.lower().endswith(".yaml"):
        raise RuntimeError(f"Failed to call docker-compose stop: Compose file must be of type .yaml: '{compose_file}'.")

    args = ("docker-compose", "-f", compose_file.absolute(), "stop")

    result: CompletedProcess = run(args)

    if result.returncode != 0:
        raise RuntimeError(f"Failed to call docker-compose stop: '{result.stderr}'.")


def docker_compose_down(compose_file: Path) -> None:
    if not compose_file.is_file() or not compose_file.name.lower().endswith(".yaml"):
        raise RuntimeError(f"Failed to call docker-compose down: Compose file must be of type .yaml: '{compose_file}'.")

    args = ("docker-compose", "-f", compose_file.absolute(), "down")

    result: CompletedProcess = run(args)

    if result.returncode != 0:
        raise RuntimeError(f"Failed to call docker-compose down: '{result.stderr}'.")
