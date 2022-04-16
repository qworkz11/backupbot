#!/usr/bin/env python3

"""Main Backupbot class."""

import datetime
import sys
from pathlib import Path
from typing import Dict, List, Union

from backupbot.abstract.backup_task import AbstractBackupTask
from backupbot.abstract.container_backup_adapter import ContainerBackupAdapter
from backupbot.data_structures import HostDirectory, Volume
from backupbot.logger import logger
from backupbot.utils import load_yaml_file, tar_file_or_directory


class BackupBot:
    """Class which coordinates all backup tasks."""

    def __init__(
        self, root: Path, destination: Path, backup_config: Path, container_runtime_environment: str = "docker"
    ) -> None:
        """Constructor.

        Args:
            root (Path): Path to the directory which contains all Docker volumes and the docker-compose file.
            destination (Path): Target directory for backup files.
            dockerfile (Path): Path to the docker-compose.yaml.
        """
        self.root = root
        self.destination = destination
        self.backup_config: Path = backup_config
        self.backup_adapter: ContainerBackupAdapter = None
        self.cri = container_runtime_environment

    def create_service_backup_structure(
        self, storage_info: Dict[str, Dict[str, List]], backup_tasks: List[AbstractBackupTask]
    ) -> None:
        for service in storage_info.keys():

            dir_names = [type(task).target_dir_name for task in backup_tasks]
            dir_names_unique = set(dir_names)

            for name in dir_names_unique:
                subdir_path = self.root.joinpath(service, name)
                if not subdir_path.is_dir():
                    subdir_path.mkdir(parents=True)

    # def create_target_folders(self, storage_info: Dict[str, Dict[str, List[Union[Volume, HostDirectory]]]]) -> None:
    #     for service in storage_info.keys():

    #     for service, persistence_lists in parsed_config.items():
    #         if "host_directories" in persistence_lists:
    #             for host_directory in persistence_lists["host_directories"]:
    #                 path_tag = str(host_directory.path).replace("/", "-")
    #                 path = self.destination.joinpath(service, "host_directories", path_tag)
    #                 if not path.is_dir():
    #                     path.mkdir(parents=True)

    #         if "volumes" in persistence_lists:
    #             for volume in persistence_lists["volumes"]:
    #                 path = self.destination.joinpath(service, "volumes", volume.name)
    #                 if not path.is_dir():
    #                     path.mkdir(parents=True)

    def run(self) -> None:
        storage_files = self.backup_adapter.collect_storage_info(self.root)
        storage_info: Dict[str, Dict[str, List]] = self.backup_adapter.parse_storage_info(storage_files, self.root)

        backup_tasks: Dict[List[AbstractBackupTask]] = self.backup_adapter.parse_backup_scheme(self.backup_config)

        # this creates a folder structure as follows (here for a Docker backup):
        # root
        # |-service1
        # |     |-bind_mounts
        # |     |-volumes
        # |     |-mysql_databases
        # |-service2
        # |     |-mysql_databases
        self.create_service_backup_structure(storage_info, backup_tasks)

        for service_name, tasks in backup_tasks.items():
            for task in tasks:
                task(storage_info, self.root.joinpath(service_name, type(task).target_dir_name))

    # def update_file_versions(self) -> None:

    # def run(self) -> None:
    #     """Executes all backup tasks."""
    #     try:
    #         docker_content = load_yaml_file(self.dockerfile)
    #     except FileNotFoundError:
    #         logger.error(f"Unable to load Dockerfile '{self.dockerfile}'.")
    #         sys.exit(1)

    #     for service_name, service_attributes in docker_content["services"]:
    #         if "volumes" in service_attributes:
    #             for volume in service_attributes["volumes"]:
    #                 if volume.startswith("."):
    #                     self.backup_bind_mount(volume, service_name)
    #                 # else:
    #                 #     self.backup_named_volume(volume)

    # def backup_bind_mount(self, bind_mount_name: str, service_name: str) -> None:
    #     """Backs up the specifies bind mount.

    #     Args:
    #         bind_mount_name (str): Bind mount name as specified in the docker-compose file.
    #         service_name (str): Name of the Docker service the volume belongs to.
    #     """
    #     target = self.destination.joinpath(service_name, "bind_mounts")
    #     if not target.exists():
    #         target.mkdir(parents=True)

    #     bind_mount_path: Path = self.root.joinpath(bind_mount_name)

    #     tar_directory(bind_mount_path, f"{datetime.datetime.now()}-{bind_mount_name}", target)
