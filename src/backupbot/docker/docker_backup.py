import json
from contextlib import contextmanager
from copy import deepcopy
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Dict, Generator, List, Tuple, Union

from backupbot.abstract.backup_task import AbstractBackupTask
from backupbot.abstract.container_backup_adapter import ContainerBackupAdapter
from backupbot.data_structures import HostDirectory, Volume
from backupbot.docker.backup_tasks import (
    DockerBindMountBackupTask,
    DockerMySQLBackupTask,
    DockerVolumeBackupTask,
)
from backupbot.docker.container_utils import docker_compose_start, docker_compose_stop
from backupbot.docker.storage_info import DockerComposeService
from backupbot.logger import logger
from backupbot.utils import load_yaml_file, locate_files

from docker import DockerClient, from_env


class DockerBackupAdapter(ContainerBackupAdapter):
    def __init__(self):
        self.docker_client: DockerClient = from_env()
        self.config_files: List[Path] = []

    def discover_config_files(self, root: Path) -> List[Path]:
        locate_files(root, "docker-compose.yaml", self.config_files)

        num_files = len(self.config_files)
        if num_files != 1:
            raise RuntimeError(f"There must only be one docker-compose file, found: '{num_files}'.")

        return self.config_files

    def parse_storage_info(self, files: List[Path], root_directory: Path) -> List[DockerComposeService]:
        num_files = len(files)
        if num_files != 1:
            raise RuntimeError(f"Only one docker-compose file allowed: Got '{num_files}'.")

        return self._parse_compose_file(files[0], root_directory)

    def parse_backup_scheme(self, file: Path) -> Dict[str, List[AbstractBackupTask]]:
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

    @contextmanager
    def stopped_system(self, storage_info: List[DockerComposeService] = None) -> Generator:
        docker_compose_stop(self.config_files[0])
        yield None
        docker_compose_start(self.config_files[0])

    def _parse_volume(self, volume: str) -> Tuple[str, str]:
        if not ":" in volume:
            raise ValueError(f"Unable to parse volume: Delimiter ':' missing in '{volume}'.")
        split = volume.split(":")
        return split[0], split[1]

    def _parse_compose_file(self, file: Path, root_directory: Path) -> List[DockerComposeService]:
        compose_content: Dict[str, Dict] = load_yaml_file(file)

        if not "services" in compose_content.keys():
            raise RuntimeError("Failed to parse docker-compose.yaml: File has no 'services' key.")

        services: List[DockerComposeService] = []

        for service_name, service_attributes in compose_content["services"].items():
            service = DockerComposeService(
                name=service_name,
                container_name=service_attributes["container_name"],
                image=service_attributes["image"],
                hostname=service_attributes["hostname"],
                volumes=[],
                bind_mounts=[],
            )
            if "volumes" in service_attributes:
                for volume in service_attributes["volumes"]:
                    if volume.startswith("."):
                        host_directory, container_mount_point = self._parse_volume(volume)
                        host_directory_path = root_directory.joinpath(host_directory)

                        service.bind_mounts.append(HostDirectory(host_directory_path, Path(container_mount_point)))
                    else:
                        volume_name, container_mount_point = self._parse_volume(volume)
                        service.volumes.append(Volume(volume_name, Path(container_mount_point)))

            services.append(service)

        return services

    def _make_backup_name(self, directory: Path, container_name: str) -> str:
        return f"{container_name}-{str(directory).split('/')[::-1][0]}"
