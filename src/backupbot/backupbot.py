#!/usr/bin/env python3

"""Main Backupbot class."""

from pathlib import Path


class BackupBot:
    def __init__(self, root: Path) -> None:
        self.path = root
