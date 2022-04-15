from pathlib import Path
from typing import Dict, List, Union

from backupbot.abstract.backup_task import AbstractBackupTask
from backupbot.data_structures import HostDirectory
from backupbot.utils import path_to_string, tar_file_or_directory


class DockerBindMountBackupTask(AbstractBackupTask):
    target_dir_name: str = "bind_mounts"

    def __init__(self, bind_mounts: Union[List[str], str]):
        self.bind_mounts = bind_mounts

    def __call__(self, storage_info: Dict, root: Path) -> None:
        # TODO container needs to be stopped
        for service_name in storage_info:
            service_root_dir = root.joinpath(service_name)

            if self.bind_mounts == ["all"]:
                backup_mounts: List[HostDirectory] = storage_info[service_name]["bind_mounts"]
            else:
                backup_mounts: List[HostDirectory] = [
                    host_dir
                    for host_dir in storage_info[service_name]["bind_mounts"]
                    if any([host_dir.path.match(bind_mount) for bind_mount in self.bind_mounts])
                ]
            for mount in backup_mounts:
                target = service_root_dir.joinpath(mount.path.name)
                if not target.is_dir():
                    target.mkdir(parents=True)
                tar_file_or_directory(mount.path, path_to_string(mount.path, num_steps=3), target)


class DockerVolumeBackupTask(AbstractBackupTask):
    target_dir_name: str = "volumes"

    def __call__(self, storage_info: Dict[str, Dict[str, List]], target_dir: Path) -> None:
        pass


class DockerMySQLBackupTask(AbstractBackupTask):
    target_dir_name: str = "mysql_databases"

    def __call__(self, storage_info: Dict[str, Dict[str, List]], target_dir: Path) -> None:
        pass
