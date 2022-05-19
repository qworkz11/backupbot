#!/usr/bin/env python3

from pathlib import Path
from typing import Dict, List, Tuple

from backupbot.abstract.backup_task import AbstractBackupTask
from backupbot.data_structures import HostDirectory, Volume
from backupbot.docker_compose.storage_info import DockerComposeService
from backupbot.utils import path_to_string, tar_file_or_directory, timestamp
from tempfile import TemporaryDirectory
from backupbot.logger import logger
from docker import from_env, DockerClient
from shutil import copyfile

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

    def __call__(self, storage_info: List[DockerComposeService], backup_task_dir: Path) -> List[Path]:
        """Executes the bind mount backup task for docker-compose environments. Creates a sub-folder for each bind mount
        named after the bind mount (if necessary). The bind mount content is tar-compressed a single file.

        Folder structure after the backup:

                |-backup_task_dir
                |   |-bind_mounts
                |   |      |-bind_mount_name.tar.gz

        Args:
            storage_info (List[DockerComposeService]): Docker-compose storage info.
            backup_task_dir (Path): Destination directory.
        """
        created_files: List[Path] = []
        for service in storage_info:
            if self.bind_mounts == ["all"]:
                backup_mounts: List[HostDirectory] = service.bind_mounts
            else:
                backup_mounts: List[HostDirectory] = [
                    host_dir
                    for host_dir in service.bind_mounts
                    if any([host_dir.path.match(bind_mount) for bind_mount in self.bind_mounts])
                ]
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

    def __call__(self, storage_info: List[DockerComposeService], target_dir: Path) -> List[Path]:
        """Executes the volume backup task for docker-compose environments.

        Steps:
        - for every container in storage_info:
            - create a tar command to backup all volume mount points to /backup
            - start a Ubuntu Docker container which mounts all volumes from the container as well as a temporary
                directory under '/backup' and executes tar command
        - created files in temporary directory are associated with their target file names
        - copy all temporary files to target backup directory

        Folder structure after the backup:

                |-volume_backup
                |   |-volumes
                |   |   |-volume_name.tar.gz

        Args:
            storage_info (Dict[str, Dict[str, List]]): DockerComposeService instances containing containers to back up.
            target_dir (Path): Final backup directory
        """
        # map temporary tar files to their target directory in host backup structure:
        temp_target_mapping: Dict[Path, Path] = {}

        with TemporaryDirectory() as tmp_dir_name:
            tmp_dir = Path(tmp_dir_name)

            for container in storage_info:
                try:
                    self._backup_volumes_from(container, tmp_dir, target_dir, temp_target_mapping)
                except ContainerError as error:
                    logger.error(f"Failed to backup volumes from container '{container.name}': {error}")
                    continue

            for target, tmp_source in temp_target_mapping.items():
                copyfile(tmp_source, target)

        return [backup_file for backup_file, _ in temp_target_mapping.items()]

    def _backup_volumes_from(
        self, container: DockerComposeService, tmp_dir: Path, target_dir: Path, temp_target_mapping: Dict[Path, Path]
    ) -> None:
        container_tmp_target_mapping, tar_commands = self._prepare_volume_backup(
            container.volumes,
            target_dir,
            tmp_dir,
        )
        # bind mount the temporary path to '/backup' inside the container
        self._docker_client.containers.run(
            image="ubuntu:latest",
            remove=True,
            command=tar_commands,
            volumes={str(tmp_dir): {"bind": str(self._container_backup_bind_mount.absolute()), "mode": "rw"}},
            volumes_from=[container.name],
        )

        # when everything went alright
        temp_target_mapping.update(container_tmp_target_mapping)

    def _prepare_volume_backup(
        self, volumes: List[Volume], target_dir: Path, tmp_directory: Path
    ) -> Tuple[Dict[Path, Path], str]:
        temp_target_mapping: Dict[Path, Path] = {}
        tar_commands: List[str] = []

        for volume in volumes:
            volume_backup_dir = target_dir.joinpath(volume.name)
            tar_file_name = f"{timestamp()}-{volume.name}.tar.gz"
            tmp_tar_file = tmp_directory.joinpath(tar_file_name)
            target_tar_file = volume_backup_dir.joinpath(tar_file_name)

            if target_tar_file not in temp_target_mapping:
                temp_target_mapping[target_tar_file] = tmp_tar_file
            else:
                logger.error(
                    f"""Error while mapping temporary file '{tmp_tar_file}' to their final target: A mapping for"""
                    f""" target '{target_tar_file}' already exists."""
                )
                continue

            if not volume_backup_dir.exists():
                volume_backup_dir.mkdir(parents=False)

            tar_commands.append(
                f"tar -czf {self._container_backup_bind_mount.joinpath(tar_file_name)} {volume.mount_point}"
            )

        return temp_target_mapping, " && ".join(tar_commands)

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

        if kwargs:
            raise NotImplementedError(f"{type(self)} received unknown parameters: {kwargs}")

    def __call__(self, storage_info: Dict[str, Dict[str, List]], target_dir: Path) -> None:
        pass

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, type(self)):
            return False

        return self.database == o.database and self.user == o.user and self.password == o.password

    def __repr__(self) -> str:
        return self.__class__.__qualname__ + f": {self.database}, {self.user}, {self.password}"
