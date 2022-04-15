from copy import deepcopy
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple, Union

from backupbot.abstract.backup_task import AbstractBackupTask
from backupbot.abstract.container_backup_adapter import ContainerBackupAdapter
from backupbot.data_structures import HostDirectory, Volume
from backupbot.utils import load_yaml_file, locate_files, tar_file_or_directory


class DockerBackupAdapter(ContainerBackupAdapter):
    def __init__(self):
        pass

    def collect_storage_info(self, root: Path) -> List[Path]:
        compose_files: List[Path] = []
        locate_files(root, "docker-compose.yaml", compose_files)

        return compose_files

    def parse_storage_info(self, files: List[Path], root_directory: Path) -> Dict[str, Dict[str, List]]:
        num_files = len(files)
        if num_files != 1:
            raise RuntimeError(f"Only one docker-compose file allowed: Got '{num_files}'.")

        return self._parse_compose_file(files[0], root_directory)

    def parse_backup_scheme(self, file: Path) -> Dict[str, List[AbstractBackupTask]]:
        pass

    def _parse_volume(self, volume: str) -> Tuple[str, str]:
        if not ":" in volume:
            raise ValueError(f"Unable to parse volume: Delimiter ':' missing in '{volume}'.")
        split = volume.split(":")
        return split[0], split[1]

    def _parse_compose_file(self, file: Path, root_directory: Path) -> Dict[str, Dict[str, List]]:
        compose_content = load_yaml_file(file)

        if not "services" in compose_content.keys():
            raise RuntimeError("Failed to parse docker-compose.yaml: File has no 'services' key.")

        parsed: Dict[str, Dict[str, Union[List[Volume], List[HostDirectory]]]] = {}
        parsed = deepcopy(compose_content["services"])

        for service_name, service_attributes in compose_content["services"].items():
            if "volumes" in service_attributes:
                bind_mounts = []
                named_volumes = []

                for volume in service_attributes["volumes"]:
                    if volume.startswith("."):
                        host_directory, container_mount_point = self._parse_volume(volume)
                        host_directory_path = root_directory.joinpath(host_directory)

                        bind_mounts.append(HostDirectory(host_directory_path, Path(container_mount_point)))
                    else:
                        volume_name, container_mount_point = self._parse_volume(volume)
                        named_volumes.append(Volume(volume_name, Path(container_mount_point)))

                parsed[service_name]["bind_mounts"] = bind_mounts
                parsed[service_name]["volumes"] = named_volumes

        return parsed

    def _make_backup_name(self, directory: Path, container_name: str) -> str:
        return f"{container_name}-{str(directory).split('/')[::-1][0]}"
