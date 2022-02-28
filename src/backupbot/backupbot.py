#!/usr/bin/env python3

"""Main Backupbot class."""

import datetime
import sys
from pathlib import Path
from typing import List, Optional

from backupbot.logger import logger
from backupbot.utils import load_compose_file, tar_directory


class BackupBot:
    """Class which coordinates all backup tasks."""

    def __init__(
        self,
        root: Path,
        destination: Path,
        dockerfile: Path,
    ) -> None:
        """Constructor.

        Args:
            root (Path): Path to the directory which contains all Docker volumes and the docker-compose file.
            destination (Path): Target directory for backup files.
            dockerfile (Path): Path to the docker-compose.yaml.
        """
        self.root = root
        self.destination = destination
        self.dockerfile = dockerfile

    def run(self) -> None:
        """Executes all backup tasks."""
        try:
            docker_content = load_compose_file(self.dockerfile)
        except FileNotFoundError:
            logger.error(f"Unable to load Dockerfile '{self.dockerfile}'.")
            sys.exit(1)

        for service_name, service_attributes in docker_content["services"]:
            if "volumes" in service_attributes:
                for volume in service_attributes["volumes"]:
                    if volume.startswith("."):
                        self.backup_bind_mount(volume, service_name)
                    else:
                        self.backup_named_volume(volume)

    def backup_bind_mount(self, bind_mount_name: str, service_name: str) -> None:
        """Backs up the specifies bind mount.

        Args:
            bind_mount_name (str): Bind mount name as specified in the docker-compose file.
            service_name (str): Name of the Docker service the volume belongs to.
        """
        target = self.destination.joinpath(service_name, "bind_mounts")
        if not target.exists():
            target.mkdir(parents=True)

        bind_mount_path: Path = self.root.joinpath(bind_mount_name)

        tar_directory(bind_mount_path, f"{datetime.datetime.now()}-{bind_mount_name}", target)
