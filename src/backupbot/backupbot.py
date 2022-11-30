#!/usr/bin/env python3

"""Main Backupbot class."""

from pathlib import Path
from typing import Dict, List

from backupbot.abstract.backup_adapter import BackupAdapter
from backupbot.abstract.backup_task import AbstractBackupTask
from backupbot.abstract.storage_info import AbstractStorageInfo
from backupbot.docker_compose.backup import DockerComposeBackupAdapter
from backupbot.errors import BackupNotExistingContainerError
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
            self.backup_adapter: BackupAdapter = DockerComposeBackupAdapter()
        else:
            raise ValueError(f"Unknown backup adapter: '{adapter}'.")

    def create_service_backup_structure(
        self, storage_info: Dict[str, AbstractStorageInfo], backup_tasks: Dict[str, List[AbstractBackupTask]]
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
        for service in storage_info.values():
            if service.name in backup_tasks:
                dir_names = [type(task).target_dir_name for task in backup_tasks[service.name]]
                dir_names_unique = set(dir_names)

                for name in dir_names_unique:
                    subdir_path = self.destination.joinpath(service.name, name)
                    if not subdir_path.is_dir():
                        subdir_path.mkdir(parents=True)

    def parse_storage_info(self) -> Dict[str, AbstractStorageInfo]:
        """Generates a storage info instance from storage info files found in self.root directory.

        Raises:
            RuntimeError: If storage files cannot be found in root or they cannot be parsed.
            RuntimeError: _description_

        Returns:
            Dict[str, AbstractStorageInfo]: System storage info.
        """
        try:
            storage_files = self.backup_adapter.discover_config_files(self.root)
            logger.info(f"Found {len(storage_files)} storage file(s).")
            logger.debug(f"Storage files: {storage_files}")
        except RuntimeError as error:
            logger.error(f"Failed to locate storage files in '{self.root}': '{error.message}'.")
            raise RuntimeError from error

        try:
            storage_info: Dict[str, AbstractStorageInfo] = self.backup_adapter.parse_storage_info(
                storage_files, self.root
            )
            logger.info(f"Parsed storage info: {[info.name for info in storage_info.values()]}")
        except RuntimeError as error:
            logger.error(f"Failed to parse config files '{storage_files}': '{error.message}'.")
            raise RuntimeError from error

        return storage_info

    def run(self) -> None:
        """Executes the backup pipeline provided through the provided backup adapter.

        Backup steps:
        1) Gather configuration files from the target platform. This can e.g. be a docker-compose.yaml file in case of a
            docker-compose system.
        2) Parse information from configuration files into an AbstractStorageInfo instance.
        3) Parse backup scheme (JSON format) into a Dictionary. Dictionary maps service names to AbstractBackupTask
            instance.
        4) Using the parsed information, the target backup folder structure is created (if necessary).
        5) Execution of all backup tasks.
        6) If parameter 'versioning' is set: Update version numbers of just created files and files from previous
            backups.

        Note that errors in steps 1)-4) are re-raised and lead to a failed execution of the backup. Errors in step 5)
        are logged but do not lead to a full failure. This is so that a partial error does not affect the backup of
        working parts.

        Args:
            versioning (bool, optional): Whether or not to add version numbers to newly created files and update old
                backup versions. Defaults to False.

        Raises:
            RuntimeError: If the target platform's config files cannot be loaded.
            RuntimeError: If the loaded config files cannot be parsed.
            RuntimeError: If the backup scheme cannot be parsed.
        """
        storage_info = self.parse_storage_info()

        try:
            backup_tasks: Dict[str, List[AbstractBackupTask]] = self.backup_adapter.parse_backup_scheme(
                self.backup_config
            )
        except RuntimeError as error:
            logger.error(f"Failed to parse backup scheme '{self.backup_config}': '{error.message}'.")
            raise RuntimeError from error

        self.create_service_backup_structure(storage_info, backup_tasks)

        with self.backup_adapter.stopped_system(storage_info) as _:
            stats = self._run_backup_tasks(storage_info, backup_tasks)

        stat_message = f"{stats['success']} successful, {stats['error']} errors"
        if stats["error"] == 0:
            logger.info(stat_message)
        else:
            logger.warning(stat_message)

    def update_file_versions(self, created_files: List[Path]) -> None:
        """Updates version numbers in all specified files' parent directories.

        Args:
            created_files (List[Path]): List of files which have been newly created during the backup process.
        """
        for directory in set([file.parent for file in created_files]):
            update_version_numbers(directory, "tar.gz", major=self.update_major)

    def _run_backup_tasks(
        self,
        storage_info: Dict[str, AbstractStorageInfo],
        backup_tasks: Dict[str, List[AbstractBackupTask]],
    ) -> Dict[str, int]:
        stats: Dict[str, int] = {"success": 0, "error": 0}
        for service_name, tasks in backup_tasks.items():
            logger.info(f"Running {len(tasks)} backup task(s) for service '{service_name}'...")
            for task in tasks:
                task_str = task.__class__.__qualname__
                try:
                    logger.info(f"Running '{task.__class__.__qualname__}' for service '{service_name}'...")
                    task_files = task(
                        storage_info[service_name], self.destination.joinpath(service_name, type(task).target_dir_name)
                    )
                    logger.info(f"Finished '{task_str}': {task_files}")
                    stats["success"] += 1
                except NotImplementedError as task_init_error:
                    logger.error(f"Failed to execute backup task '{task_str}': '{task_init_error}'.")
                    stats["error"] += 1
                except NotADirectoryError as dir_error:
                    logger.error(f"Failed to execute backup task '{task_str}': '{dir_error}'.")
                    stats["error"] += 1
                except RuntimeError as runtime_error:
                    logger.error(f"Failed to execute backup task '{task_str}': '{runtime_error}'.")
                    stats["error"] += 1
                except BackupNotExistingContainerError as container_error:
                    logger.error(f"Failed to execute backup task '{task_str}': '{container_error}'.")
                    stats["error"] += 1

            logger.info(f"Finished backup of service '{service_name}'.")
        return stats

    def generate_backup_config(self, storage_files: List[Path]) -> None:
        pass
