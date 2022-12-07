"""This module defines an abstract adapter for container backup classes."""

from abc import ABC, abstractmethod
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Generator, List, Optional

from backupbot.abstract.backup_task import AbstractBackupTask
from backupbot.abstract.storage_info import AbstractStorageInfo


class BackupAdapter(ABC):
    @abstractmethod
    def discover_config_files(self, root: Path) -> List[Path]:
        ...

    @abstractmethod
    def parse_storage_info(self, files: List[Path], root_directory: Path) -> Dict[str, AbstractStorageInfo]:
        ...

    @abstractmethod
    def generate_backup_config(self, storage_info: Dict[str, AbstractStorageInfo]) -> Optional[Path]:
        ...

    @abstractmethod
    def parse_backup_scheme(self, file: Path) -> Dict[str, List[AbstractBackupTask]]:
        ...

    @abstractmethod
    @contextmanager
    def stopped_system(self, storage_info: Optional[List[AbstractStorageInfo]] = None) -> Generator:
        ...
