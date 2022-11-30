#!/usr/bin/env python3

"""Module containing the backup adapter for docker-compose."""

import json
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Generator, List, Optional, Tuple

from docker import DockerClient, from_env

from backupbot.abstract.backup_adapter import BackupAdapter
from backupbot.abstract.backup_task import AbstractBackupTask
from backupbot.data_structures import HostDirectory, Volume
from backupbot.docker_compose.backup_tasks import (
    DockerBindMountBackupTask,
    DockerMySQLBackupTask,
    DockerVolumeBackupTask,
)
from backupbot.docker_compose.container_utils import (
    docker_compose_start,
    docker_compose_stop,
)
from backupbot.docker_compose.storage_info import DockerComposeService
from backupbot.logger import logger
from backupbot.utils import load_yaml_file, match_files


class DockerComposeBackupAdapter(BackupAdapter):
    def __init__(self):
        self.docker_client: DockerClient = from_env()
        self.config_files: List[Path] = []

    def discover_config_files(self, root: Path) -> List[Path]:
        match_files(root, "docker-compose.yaml", self.config_files)

        num_files = len(self.config_files)
        if num_files != 1:
            raise RuntimeError(f"There must only be one docker-compose file, found: '{num_files}'.")

        return self.config_files

    def parse_storage_info(self, files: List[Path], root_directory: Path) -> Dict[str, DockerComposeService]:
        num_files = len(files)
        if num_files != 1:
            raise RuntimeError(f"Only one docker-compose file allowed: Got '{num_files}'.")

        return self._parse_compose_file(files[0], root_directory)

    def parse_backup_scheme(self, file: Path) -> Dict[str, List[AbstractBackupTask]]:
        """Parses the specified backup config file into backup tasks.

        Args:
            file (Path): Backup configuration file (.json).

        Raises:
            RuntimeError: If the file does not exist or it is not a JSON file.

        Returns:
            Dict[str, List[AbstractBackupTask]]: List of backup tasks for each docker container.
        """
        if not file.is_file() or not file.suffix.lower() == ".json":
            raise RuntimeError(f"Backup configuration file has wrong suffix or does not exist: '{file}'.")

        with open(file.absolute(), "r") as f:
            parsed: Dict[str, List] = json.load(f)

        backup_scheme: Dict[str, List[AbstractBackupTask]] = {}

        for service_name in parsed.keys():
            backup_scheme[service_name] = []
            for scheme_definition in parsed[service_name]:
                try:
                    if scheme_definition["type"] == "bind_mount_backup":
                        backup_task = DockerBindMountBackupTask(**scheme_definition["config"])
                    elif scheme_definition["type"] == "volume_backup":
                        backup_task = DockerVolumeBackupTask(**scheme_definition["config"])
                    elif scheme_definition["type"] == "mysql_backup":
                        backup_task = DockerMySQLBackupTask(**scheme_definition["config"])
                    else:
                        logger.error(f"Unknown backup scheme type: '{scheme_definition['type']}'")
                except NotImplementedError as error:
                    logger.error(f"Failed to parse backup task of type '{scheme_definition['type']}': {error}.")
                    continue

                backup_scheme[service_name].append(backup_task)

        return backup_scheme

    def generate_backup_config(self, storage_info: Dict[str, DockerComposeService]) -> Optional[Path]:
        backup_config: Dict[str] = {}

    @contextmanager
    def stopped_system(self, storage_info: Dict[str, DockerComposeService] = None) -> Generator:
        """Context manager which stops and restarts the docker-compose system if it is running.

        Note: The system is considered running if any container is running.

        Args:
            storage_info (List[DockerComposeService], optional): Storage info. Defaults to None.

        Yields:
            Generator: Yields when the system is down.
        """
        running_containers = [
            container.name for container in self.docker_client.containers.list(filters={"status": "running"})
        ]
        system_running = any([name in running_containers for name in storage_info.keys()])

        docker_compose_stop(self.config_files[0])  # in case some of the containers were running

        yield None

        if system_running:
            docker_compose_start(self.config_files[0])

    def _parse_volume(self, volume: str) -> Tuple[str, str]:
        if not ":" in volume:
            raise ValueError(f"Unable to parse volume: Delimiter ':' missing in volume '{volume}'.")
        split = volume.split(":")
        return split[0], split[1]

    def _parse_compose_file(self, file: Path, root_directory: Path) -> Dict[str, DockerComposeService]:
        compose_content: Dict[str, Dict] = load_yaml_file(file)

        if not "services" in compose_content.keys():
            raise RuntimeError("Failed to parse docker-compose.yaml: File has no 'services' key.")

        services: Dict[str, DockerComposeService] = {}

        for service_name, service_attributes in compose_content["services"].items():
            container_name = service_attributes["container_name"]

            service = DockerComposeService(
                name=service_name,
                container_name=container_name,
                image=service_attributes["image"],
                hostname=service_attributes["hostname"],
                volumes=[],
                bind_mounts=[],
            )
            if "volumes" in service_attributes:
                for volume in service_attributes["volumes"]:
                    try:
                        name, mount_point = self._parse_volume(volume)
                    except ValueError as error:
                        logger.error(
                            f"""Failed to parse volume name due to an error in file '{self.config_files[0]}': """
                            f"""{error.message}"""
                        )
                        continue

                    if volume.startswith("."):
                        host_directory_path = root_directory.joinpath(name)
                        service.bind_mounts.append(
                            HostDirectory(path=host_directory_path, mount_point=Path(mount_point))
                        )
                    else:
                        service.volumes.append(Volume(name=name, mount_point=Path(mount_point)))

            services[container_name] = service

        return services

    def _make_backup_name(self, directory: Path, container_name: str) -> str:
        return f"{container_name}-{str(directory).split('/')[::-1][0]}"
