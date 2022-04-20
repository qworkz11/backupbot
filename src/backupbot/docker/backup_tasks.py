from pathlib import Path
from typing import Dict, List, Union

from backupbot.abstract.backup_task import AbstractBackupTask
from backupbot.data_structures import HostDirectory
from backupbot.utils import path_to_string, tar_file_or_directory


class DockerBindMountBackupTask(AbstractBackupTask):
    target_dir_name: str = "bind_mounts"

    def __init__(self, bind_mounts: List[str], **kwargs: Dict):
        self.bind_mounts = bind_mounts

        if kwargs:
            raise NotImplementedError(f"Received unknown parameters: {kwargs}")

    def __call__(self, storage_info: Dict, backup_task_dir: Path) -> None:
        """Executes the bind mount backup task for docker-compose environments.

        Note: expects the following folder structure:
            backup_root
                |-service_root
                |   |-bind_mounts

        Args:
            storage_info (Dict): _description_
            backup_task_dir (Path): _description_
        """
        for service_name in storage_info:
            if self.bind_mounts == ["all"]:
                backup_mounts: List[HostDirectory] = storage_info[service_name]["bind_mounts"]
            else:
                backup_mounts: List[HostDirectory] = [
                    host_dir
                    for host_dir in storage_info[service_name]["bind_mounts"]
                    if any([host_dir.path.match(bind_mount) for bind_mount in self.bind_mounts])
                ]
            for mount in backup_mounts:
                target = backup_task_dir.joinpath(path_to_string(mount.path, num_steps=3))
                if not target.is_dir():
                    target.mkdir(parents=False)

                tar_file_or_directory(mount.path, path_to_string(mount.path, num_steps=3), target)

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, type(self)):
            return False

        if len(self.bind_mounts) != len(o.bind_mounts):
            return False

        return len(set(self.bind_mounts).difference(o.bind_mounts)) == 0

    def __repr__(self) -> str:
        return self.__class__.__name__ + f": {self.bind_mounts}"


class DockerVolumeBackupTask(AbstractBackupTask):
    target_dir_name: str = "volumes"

    def __init__(self, volumes: List[str], **kwargs: Dict):
        self.volumes = volumes

        if kwargs:
            raise NotImplementedError(f"Received unknown parameters: {kwargs}")

    def __call__(self, storage_info: Dict[str, Dict[str, List]], target_dir: Path) -> None:
        pass

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, type(self)):
            return False

        if len(self.volumes) != len(o.volumes):
            return False

        return len(set(self.volumes).difference(set(o.volumes))) == 0

    def __repr__(self) -> str:
        return self.__class__.__qualname__ + f": {self.volumes}"


class DockerMySQLBackupTask(AbstractBackupTask):
    target_dir_name: str = "mysql_databases"

    def __init__(self, database: str, user: str, password: str, **kwargs: Dict):
        self.database = database
        self.user = user
        self.password = password

        if kwargs:
            raise NotImplementedError(f"Received unknown parameters: {kwargs}")

    def __call__(self, storage_info: Dict[str, Dict[str, List]], target_dir: Path) -> None:
        pass

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, type(self)):
            return False

        return self.database == o.database and self.user == o.user and self.password == o.password

    def __repr__(self) -> str:
        return self.__class__.__qualname__ + f": {self.database}, {self.user}, {self.password}"
