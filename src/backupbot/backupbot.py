#!/usr/bin/env python3

"""Main Backupbot class."""

from pathlib import Path
from typing import Dict, List

from backupbot.abstract.backup_task import AbstractBackupTask
from backupbot.abstract.container_backup_adapter import ContainerBackupAdapter
from backupbot.abstract.storage_info import AbstractStorageInfo
from backupbot.docker_compose.backup import DockerBackupAdapter
from backupbot.logger import logger
from backupbot.versioning import update_version_numbers


class BackupBot:
    """Class which coordinates all backup tasks."""

    def __init__(
        self,
        root: Path,
        destination: Path,
        backup_config: Path,
        adapter: str = "docker-compose",
        update_major: bool = False,
    ) -> None:
        """Constructor.

        Args:
            root (Path): Path to the directory which contains all Docker volumes and the docker-compose file.
            destination (Path): Target directory for backup files.
            dockerfile (Path): Path to the docker-compose.yaml.
            update_major (bool): Whether to update the major or minor versions of the tar-compressed files. Defaults to
                False.
        """
        self.root = root
        self.destination = destination
        self.backup_config: Path = backup_config
        self.cri = adapter
        self.update_major = update_major

        if adapter == "docker-compose":
            self.backup_adapter: ContainerBackupAdapter = DockerBackupAdapter()
        else:
            raise ValueError(f"Unknown CRI: '{adapter}'.")

    def create_service_backup_structure(
        self, storage_info: List[AbstractStorageInfo], backup_tasks: Dict[str, List[AbstractBackupTask]]
    ) -> None:
        """Creates the backup folder structure for all services and backup tasks specified if necessary.

        The resulting folder structure is like so:
        backup_dir
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
            if service.name in backup_tasks:
                dir_names = [type(task).target_dir_name for task in backup_tasks[service.name]]
                dir_names_unique = set(dir_names)

                for name in dir_names_unique:
                    subdir_path = self.destination.joinpath(service.name, name)
                    if not subdir_path.is_dir():
                        subdir_path.mkdir(parents=True)

    def run(self, versioning: bool = False) -> None:
        try:
            storage_files = self.backup_adapter.discover_config_files(self.root)
        except RuntimeError as error:
            logger.error(f"Failed to locate config files in '{self.root}': '{error.message}'.")
            raise RuntimeError from error

        try:
            storage_info: List[AbstractStorageInfo] = self.backup_adapter.parse_storage_info(storage_files, self.root)
        except RuntimeError as error:
            logger.error(f"Failed to parse config files '{storage_files}': '{error.message}'.")
            raise RuntimeError from error

        try:
            backup_tasks: Dict[str, List[AbstractBackupTask]] = self.backup_adapter.parse_backup_scheme(
                self.backup_config
            )
        except RuntimeError as error:
            logger.error(f"Failed to parse backup scheme '{self.backup_config}': '{error.message}'.")
            raise RuntimeError from error

        self.create_service_backup_structure(storage_info, backup_tasks)

        with self.backup_adapter.stopped_system(storage_info) as _:
            created_files = self._run_backup_tasks(storage_info, backup_tasks)

        if versioning:
            self.update_file_versions(created_files)

    def update_file_versions(self, created_files: List[Path]) -> None:
        """Updates version numbers in all specified files' parent directories.

        Args:
            created_files (List[Path]): List of files which have been newly created during the backup process.
        """
        for directory in set([file.parent for file in created_files]):
            update_version_numbers(directory, "tar.gz", major=self.update_major)

    def _run_backup_tasks(
        self,
        storage_info: Dict[str, List[AbstractStorageInfo]],
        backup_tasks: Dict[str, List[AbstractBackupTask]],
    ) -> List[Path]:
        created_files = []
        for service_name, tasks in backup_tasks.items():
            for task in tasks:
                try:
                    task_files = task(storage_info, self.destination.joinpath(service_name, type(task).target_dir_name))
                    created_files.extend(task_files)
                except NotImplementedError as task_init_error:
                    logger.error(f"Failed to execute backup task '{task}': '{task_init_error.message}'.")
                except NotADirectoryError as dir_error:
                    logger.error(f"Failed to backup task '{task}: '{dir_error.message}'.")
                except RuntimeError as runtime_error:
                    logger.error(f"Failed to backup task '{task}: '{runtime_error.message}'.")

            return created_files
