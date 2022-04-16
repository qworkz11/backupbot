#!/usr/bin/env python3

"""Main Backupbot class."""

from pathlib import Path
from typing import Dict, List

from backupbot.abstract.backup_task import AbstractBackupTask
from backupbot.abstract.container_backup_adapter import ContainerBackupAdapter
from backupbot.abstract.storage_info import AbstractStorageInfo
from backupbot.logger import logger


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
        self, storage_info: List[AbstractStorageInfo], backup_tasks: Dict[str, List[AbstractBackupTask]]
    ) -> None:
        """Creates the backup folder structure for all services and backup tasks specified if necessary.

        The resulting folder structure is like so:
        root
          |-service1
               |-task1
               |-task2
          |-service2
               |-taskA
               |-taskB

        Args:
            storage_info (List[AbstractStorageInfo]): Storage info.
            backup_tasks (Dict[str, List[AbstractBackupTask]]): Backup tasks.
        """
        for service in storage_info:
            dir_names = [type(task).target_dir_name for task in backup_tasks[service.name]]
            dir_names_unique = set(dir_names)

            for name in dir_names_unique:
                subdir_path = self.destination.joinpath(service.name, name)
                if not subdir_path.is_dir():
                    subdir_path.mkdir(parents=True)

    def run(self) -> None:
        storage_files = self.backup_adapter.collect_storage_info(self.root)
        storage_info: Dict[str, Dict[str, List]] = self.backup_adapter.parse_storage_info(storage_files, self.root)

        backup_tasks: Dict[List[AbstractBackupTask]] = self.backup_adapter.parse_backup_scheme(self.backup_config)

        self.create_service_backup_structure(storage_info, backup_tasks)

        for service_name, tasks in backup_tasks.items():
            for task in tasks:
                task(storage_info, self.root.joinpath(service_name, type(task).target_dir_name))

        # self.update_file_versions()

    # def update_file_versions(self) -> None:
