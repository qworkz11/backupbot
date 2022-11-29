#!/usr/bin/env python3

from pathlib import Path
from typing import Dict, List, Tuple, Union

from backupbot.abstract.backup_task import AbstractBackupTask
from backupbot.data_structures import HostDirectory, Volume
from backupbot.docker_compose.container_utils import BackupItem
from backupbot.docker_compose.storage_info import DockerComposeService
from backupbot.utils import path_to_string, tar_file_or_directory, timestamp
from tempfile import TemporaryDirectory
from backupbot.logger import logger
from docker import from_env, DockerClient
from shutil import copyfile
from backupbot.docker_compose.container_utils import shell_backup

from docker.errors import ContainerError


class DockerBindMountBackupTask(AbstractBackupTask):
    """Class which defines a DockerBackupTask."""

    target_dir_name: str = "bind_mounts"

    def __init__(self, bind_mounts: List[str], **kwargs: Dict):
        """Constuctor.

        Args:
            bind_mounts (List[str]): List of docker-compose bind mount instances.

        Raises:
            NotImplementedError: When the class has no shared target_dir_name attribute.
        """
        self.bind_mounts = bind_mounts

        if kwargs:
            raise NotImplementedError(f"{type(self)} received unknown parameters: {kwargs}")

    def __call__(self, service: DockerComposeService, backup_task_dir: Path) -> List[Path]:
        """Executes the bind mount backup task for docker-compose environments. Creates a sub-folder for each bind mount
        named after the bind mount (if necessary). The bind mount content is tar-compressed a single file.

        Folder structure after the backup:

                |-bind_mounts
                |   |-bind_mount_name
                |   |      |-TIMESTAMP-bind_mount_name.tar.gz

        Args:
            storage_info (List[DockerComposeService]): Docker-compose storage info.
            backup_task_dir (Path): Destination directory.

        Returns:
            List[Path]: Created files.
        """
        if self.bind_mounts == ["all"]:
            backup_mounts: List[HostDirectory] = service.bind_mounts
        else:
            backup_mounts: List[HostDirectory] = [
                host_dir
                for host_dir in service.bind_mounts
                if any([host_dir.path.match(bind_mount) for bind_mount in self.bind_mounts])
            ]

        created_files: List[Path] = []
        for mount in backup_mounts:
            string_path = path_to_string(mount.path, num_steps=1)
            target_dir = backup_task_dir.joinpath(string_path)
            tar_name = f"{timestamp()}-{string_path}"

            if not target_dir.is_dir():
                target_dir.mkdir(parents=False)

            tar_file = tar_file_or_directory(mount.path, tar_name, target_dir)
            created_files.append(tar_file)

        return created_files

    def __eq__(self, o: object) -> bool:
        """Equality function.

        Args:
            o (object): Other object.

        Returns:
            bool: True if objects are equal.
        """
        if not isinstance(o, type(self)):
            return False

        if len(self.bind_mounts) != len(o.bind_mounts):
            return False

        return len(set(self.bind_mounts).difference(o.bind_mounts)) == 0

    def __repr__(self) -> str:
        """Representation function.

        Returns:
            str: String representation.
        """
        return self.__class__.__name__ + f": {self.bind_mounts}"


class DockerVolumeBackupTask(AbstractBackupTask):
    """Class which represents a docker-compose volume backup task."""

    target_dir_name: str = "volumes"

    def __init__(self, volumes: List[str], **kwargs: Dict):
        """Constructor.

        Args:
            volumes (List[str]): Volume (names) to back up.

        Raises:
            NotImplementedError: When the class has no target_dir_name attribute.
        """
        self.volumes = volumes
        self._container_backup_bind_mount = Path("/backup")  # must be absolute!
        self._docker_client: DockerClient = from_env()

        if kwargs:
            raise NotImplementedError(f"{type(self)} received unknown parameters: {kwargs}")

    def __call__(self, service: DockerComposeService, target_dir: Path) -> List[Path]:
        """Executes the volume backup task for docker-compose environments.

        Steps:
        - for every container in storage_info:
            - create a tar command to backup all volume mount points to /backup
            - start a Ubuntu Docker container which mounts all volumes from the container as well as a temporary
                directory under '/backup' and executes tar command
        - created files in temporary directory are associated with their target file names
        - copy all temporary files to target backup directory

        Folder structure after the backup:

                |-volumes
                |   |-volume_name
                |   |   |-TIMESTAMP-volume_name.tar.gz

        Args:
            storage_info (Dict[str, Dict[str, List]]): DockerComposeService instances containing containers to back up.
            target_dir (Path): Final backup directory
        """
        backup_files: List[Path] = []

        with TemporaryDirectory() as tmp_dir_name:
            tmp_dir = Path(tmp_dir_name)

            volume_backup_items = self._prepare_volume_backup(service.volumes, target_dir)

            backup_mapping = shell_backup(
                self._docker_client,
                "ubuntu:latest",
                bind_mount_dir=tmp_dir,
                container_to_backup=service.name,
                backup_items=volume_backup_items,
            )

            for backup_item, tmp_source in backup_mapping.items():
                final_path = backup_item.final_path.joinpath(backup_item.file_name)

                if tmp_source is None:
                    logger.error(
                        f"""Backup command '{backup_item.command}' failed on service '{service.name}'. Backup"""
                        f""" file '{final_path}' was not created as a result."""
                    )
                    continue

                copyfile(tmp_source, final_path)
                backup_files.append(final_path)

        return backup_files

    def _prepare_volume_backup(self, volumes: List[Volume], target_dir: Path) -> List[BackupItem]:
        backup_items: List[BackupItem] = []

        for volume in volumes:
            volume_backup_dir = target_dir.joinpath(volume.name)
            tar_file_name = f"{timestamp()}-{volume.name}.tar.gz"

            if not volume_backup_dir.exists():
                volume_backup_dir.mkdir(parents=False)

            item = BackupItem(
                command=f"tar -czf {self._container_backup_bind_mount.joinpath(tar_file_name)} {volume.mount_point}",
                file_name=tar_file_name,
                final_path=volume_backup_dir,
            )

            backup_items.append(item)

        return backup_items

    def __eq__(self, o: object) -> bool:
        """Checks for equality.

        Args:
            o (object): Object to compare against.

        Returns:
            bool: Whether or not the object is equal to this instance
        """
        if not isinstance(o, type(self)):
            return False

        if len(self.volumes) != len(o.volumes):
            return False

        return len(set(self.volumes).difference(set(o.volumes))) == 0

    def __repr__(self) -> str:
        """String representation.

        Returns:
            str: String representation.
        """
        return self.__class__.__qualname__ + f": {self.volumes}"


class DockerMySQLBackupTask(AbstractBackupTask):
    target_dir_name: str = "mysql_databases"

    def __init__(self, database: str, user: str, password: str, **kwargs: Dict):
        self.database = database
        self.user = user
        self.password = password

        self._docker_client = from_env()
        self._container_backup_bind_mount = Path("/backup")  # must be absolute!

        if kwargs:
            raise NotImplementedError(f"{type(self)} received unknown parameters: {kwargs}")

    def __call__(self, service: DockerComposeService, target_dir: Path) -> List[Path]:
        """Executes a MySQL Backup Task for docker-compose environments.

        Steps for every container in storage info:
            - specify the mysql command to be called via 'docker exec'
            - start a mysql image which mounts the container's volumes and bind mounts + a temporary bind mount under
                /backup
            - dump the contents of the specified MySQL database to a file in /backup
            - copy the dumped file from the temporary directory to its target path

        The issued command to create the MySQL dump:
        Command: mysqldump --password=<root-pw> --user=root <database name> > /backup/<file>.sql

        Folder structure after backup:

            |-mysql_databases
            |   |-database_name
            |   |   |-TIMESTAMP-database_name.sql

        Args:
            storage_info (List[DockerComposeService]): Docker Compose storage info.
            target_dir (Path): Destination directory.

        Returns:
            List[Path]: List of created files.
        """
        backup_files: List[Path] = []

        with TemporaryDirectory() as tmp_dir_name:
            tmp_dir = Path(tmp_dir_name)

            mysql_backup_item = self._create_mysql_backup_item(target_dir)

            backup_mapping = shell_backup(
                self._docker_client,
                "mysql:latest",
                bind_mount_dir=tmp_dir,
                container_to_backup=service.name,
                backup_items=[mysql_backup_item],
            )

            for backup_item, tmp_source in backup_mapping.items():
                final_path = backup_item.final_path.joinpath(backup_item.file_name)

                if tmp_source is None:
                    logger.error(
                        f"""Backup command '{backup_item.command}' failed on service '{service.name}'. Backup"""
                        f""" file '{final_path}' was not created."""
                    )
                    continue

                copyfile(tmp_source, final_path)
                backup_files.append(final_path)

        return backup_files

    def _create_mysql_backup_item(self, target_dir: Path) -> BackupItem:
        mysql_backup_dir = target_dir.joinpath(self.database)
        filename = f"{timestamp()}-{self.database}.sql"

        if not mysql_backup_dir.is_dir():
            mysql_backup_dir.mkdir(parents=True)

        container_filepath = self._container_backup_bind_mount.joinpath(filename)
        return BackupItem(
            command=None,  # make sure that MySQL main command is not overrideen
            exec=f"mysqldump --password={self.password} --user={self.user} {self.database} > {container_filepath}",
            file_name=filename,
            final_path=mysql_backup_dir,
        )

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, type(self)):
            return False

        return self.database == o.database and self.user == o.user and self.password == o.password

    def __repr__(self) -> str:
        return self.__class__.__qualname__ + f": {self.database}, {self.user}, {self.password}"
