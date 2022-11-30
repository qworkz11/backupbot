#!/usr/bin/env python3

"""Utility functions to integrate docker and docker-compose functionality."""

import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from subprocess import CompletedProcess, run
from typing import Dict, List, Optional, Union

from docker import DockerClient
from docker.errors import ContainerError

from backupbot.logger import logger
from backupbot.utils import timestamp


@dataclass(unsafe_hash=True)
class BackupItem:
    # make sure this class is hashable so that it can be used as a dictionary key
    command: str = field(hash=False)
    file_name: str = field(hash=True)
    final_path: Path = field(hash=True)
    exec: Optional[str] = field(hash=False, default=None)


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


def docker_exec(container: str, command: str) -> None:
    """Runs a shell command on a docker container using a sub-process.

    Args:
        container (str): Container to run the command on (must be running).
        command (str): Shell command.

    Raises:
        RuntimeError: If the executop failed.
    """
    args = ("docker", "exec", container, "sh", "-c", command)

    result: CompletedProcess = run(args)

    if result.returncode != 0:
        raise RuntimeError(f"Failed to docker exec command '{command}': '{result.stdout}'.")


def docker_exec_loop(container: str, command: str, timeout_s: int) -> None:
    """Tries to execute a shell command on a running docker container until successful.

    Args:
        container (str): Container name to run the command on (must be running).
        command (str): Shell command.
        timeout_s (int): Timeout to raise an Exception if the execution was unsuccessful.

    Raises:
        TimeoutError: If the execution was not successful after the specified time.
    """
    start = time.time()
    while True:
        try:
            docker_exec(container, command)
            break
        except RuntimeError as error:
            if time.time() - start >= timeout_s:
                raise TimeoutError(f"Docker exec was not successful after {timeout_s}s.") from error


def shell_backup(
    docker_client: DockerClient,
    image: str,
    bind_mount_dir: Path,
    container_to_backup: str,
    backup_items: List[BackupItem],
    timeout_s: int = 5,
) -> Dict[BackupItem, Union[Path, None]]:
    """Runs commands in a freshly started container.

    The temporary container mounts 'bind_mount_dir'. Any files created by the command should be placed in
    'bind_mount_dir' where they can be used by the caller.
    When the backup item specifies a 'command' it is executed as the main command of the container. It therefore
    replaces the container's main command.
    When the backup item specifies an 'exec' command it is executed via 'docker exec' after the container has finished
    its startign process.

    The function returns a dictionary which maps the backup item to its created file in the mounted directory
    ('bind_mount_dir').

    BackupItem instances must specify:
        - command: Shell command to run
        - final_path: Target backup directory on host, excluding file name
        - file_name: File name after backup
        - exec: Shell command run by 'docker exec'

    Args:
        docker_client (DockerClient): DockerClient instance.
        image (str): Docker image to use for the backup.
        bind_mount_dir (Path): Temporary directory used as a bind mount. Backups will be stored there.
        backup_items (List[BackupItem]): BackupItem instances specifying the command to run for the backup, the backup
            file name and the target directory for the backup on the host.
        timeout_s (int): Time to wait for a successful 'docker exec' execution. Only used if BackupItem.exec is
            specified.

    Returns:
        Dict[BackupItem, Union[Path, None]]: Contains the created backup file (if one was created) for each BackupItem
            instance.
    """
    backup_temporary_file_mapping: Dict[BackupItem, Union[Path, None]] = {}  # key: backup item; value: temporary file

    for backup_item in backup_items:
        name = f"{timestamp()}-backup-container"
        try:
            container = docker_client.containers.run(
                image=image,
                name=name,
                detach=backup_item.exec is not None,  # we need the container alive after the function returns
                remove=True,
                command=backup_item.command,
                volumes={str(bind_mount_dir): {"bind": str(Path("/backup"))}},
                volumes_from=[container_to_backup],
            )

            if backup_item.exec is not None:
                # this means the container has not stopped yet
                docker_exec_loop(name, command=backup_item.exec, timeout_s=timeout_s)
                container.stop()

            mapping = bind_mount_dir.joinpath(backup_item.file_name)

            if not mapping.exists():
                logger.error(
                    f"Failed to backup item '{backup_item}': The backup container did not fail but no file was created."
                )
                mapping = None

        except ContainerError as error:
            logger.warning(f"Failed to run image '{image}': {error}")
            mapping = None
        finally:
            try:
                docker_client.containers.get(name).stop()
            except Exception:
                pass

        if not backup_item.final_path in backup_temporary_file_mapping:
            backup_temporary_file_mapping[backup_item] = mapping
        else:
            logger.error(
                f"""Error while mapping backup item '{backup_item}' to temporary file '{mapping}': A"""
                f""" mapping already exists for this backup item ('{backup_temporary_file_mapping[backup_item]}')."""
            )

    return backup_temporary_file_mapping


def container_exists(client: DockerClient, container_name: str) -> bool:
    """Checks if a docker container has a valid state, e.g 'running' or 'stopped'.

    Args:
        client (DockerClient): Docker client.
        container_name (str): Container name.

    Returns:
        bool: Whether or not the container exists.
    """
    containers = [container.name for container in client.containers.list(all=True)]
    return container_name in containers
