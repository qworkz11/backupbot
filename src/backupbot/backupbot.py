#!/usr/bin/env python3

"""Main Backupbot class."""

import datetime
import sys
from pathlib import Path
from typing import Dict, List, Union

from backupbot.backup_adapter.container_backup_adapter import ContainerBackupAdapter
from backupbot.data_structures import HostDirectory, Volume
from backupbot.logger import logger
from backupbot.utils import load_yaml_file, tar_directory


class BackupBot:
    """Class which coordinates all backup tasks."""

    def __init__(
        self,
        root: Path,
        destination: Path,
    ) -> None:
        """Constructor.

        Args:
            root (Path): Path to the directory which contains all Docker volumes and the docker-compose file.
            destination (Path): Target directory for backup files.
            dockerfile (Path): Path to the docker-compose.yaml.
        """
        self.root = root
        self.destination = destination
        self.backup_adapter: ContainerBackupAdapter = None

    def create_target_folders(self, parsed_config: Dict[str, Dict[str, List[Union[Volume, HostDirectory]]]]) -> None:
        for service, persistence_lists in parsed_config.items():
            if "host_directories" in persistence_lists:
                for host_directory in persistence_lists["host_directories"]:
                    path_tag = str(host_directory.path).replace("/", "-")
                    path = self.destination.joinpath(service, "host_directories", path_tag)
                    if not path.is_dir():
                        path.mkdir(parents=True)

            if "volumes" in persistence_lists:
                for volume in persistence_lists["volumes"]:
                    path = self.destination.joinpath(service, "volumes", volume.name)
                    if not path.is_dir():
                        path.mkdir(parents=True)

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
