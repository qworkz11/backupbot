#!/usr/bin/env python3

"""Utility functions to integrate docker and docker-compose functionality."""

from contextlib import contextmanager
from pathlib import Path
from subprocess import CompletedProcess, run

from docker import DockerClient
from docker.errors import ContainerError
from typing import List, Dict, Union
from pathlib import Path
from dataclasses import dataclass
from backupbot.logger import logger


@dataclass
class BackupItem:
    command: str
    file_name: str
    final_path: Path


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


def shell_backup(
    docker_client: DockerClient,
    image: str,
    bind_mount_dir: Path,
    container_to_backup: str,
    backup_items: List[BackupItem],
) -> Dict[Path, Union[Path, None]]:
    """Runs the shell command specified in the BackupItem instance on the specified container. Returns a dictionary
    mapping the target file name of a backup to its temporary file in the bind_mount directory.

    BackupItem instances must specify:
        - command: Shell command to run
        - final_path: Target backup directory on host, excluding file name
        - file_name: File name after backup

    Args:
        docker_client (DockerClient): DockerClient instance.
        image (str): Docker image to use for the backup.
        bind_mount_dir (Path): Temporary directory used as a bind mount. Backups will be stored there.
        backup_items (List[BackupItem]): BackupItem instances specifying the command to run for the backup, the backup
            file name and the target directory for the backup on the host.
    """
    target_temp_mapping: Dict[Path, Path] = {}

    for backup_item in backup_items:
        try:
            docker_client.containers.run(
                image=image,
                remove=True,
                command=backup_item.command,
                volumes={str(bind_mount_dir): {"bind": str(Path("/backup"))}},
                volumes_from=[container_to_backup],
            )
            mapping = bind_mount_dir.joinpath(backup_item.file_name)
        except ContainerError as _:
            mapping = None

        if not backup_item.final_path in target_temp_mapping:
            target_temp_mapping[backup_item.final_path.joinpath(backup_item.file_name)] = mapping
        else:
            logger.error(
                f"""Error while mapping a temporary file '{mapping}' to final file '{backup_item.final_path}': A"""
                """ mapping already exists."""
            )

    return target_temp_mapping
