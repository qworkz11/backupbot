#!/usr/bin/env python3

"""Main Backupbot class."""

import subprocess
import sys
from pathlib import Path
from typing import List, Optional

from backupbot.logger import logger
from backupbot.utils import absolute_paths, extract_volumes, load_dockerfile


class BackupBot:
    def __init__(
        self,
        root: Path,
        dockerfile: Path,
    ) -> None:
        self.root = root
        self.dockerfile = dockerfile

    def run(self) -> None:
        try:
            docker_content = load_dockerfile(self.dockerfile)
        except FileNotFoundError:
            logger.error(f"Unable to load Dockerfile '{self.dockerfile}'.")
            sys.exit(1)

        named_volumes, bind_mounts_names = extract_volumes(docker_content)

    def backup_bind_mounts(self, bind_mount_names: Optional[List[str]]) -> None:
        if bind_mount_names is None:
            logger.info(f"No bind mounts found, skipping...")
            return

        bind_mounts: List[Path] = absolute_paths(bind_mount_names, self.root)

        for bind_mount in bind_mounts:
            if not bind_mount.is_dir():
                logger.error(f"'{bind_mount}' cannot be found. Skipping...")
                continue

            cmd_args = ("tar",)

            subprocess.run()
