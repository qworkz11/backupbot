"""This module defines an abstract adapter for container backup classes."""

from abc import ABC, abstractmethod
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Generator, List, Optional

from backupbot.abstract.backup_task import AbstractBackupTask
from backupbot.abstract.storage_info import AbstractStorageInfo
from pydantic import BaseModel


class BackupAdapter(ABC):
    @abstractmethod
    def discover_config_files(self, root: Path) -> List[Path]:
        ...

    @abstractmethod
    def parse_storage_info(self, files: List[Path], root_directory: Path) -> List[AbstractStorageInfo]:
        ...

    @abstractmethod
    def parse_backup_scheme(self, file: Path) -> Dict[str, List[AbstractBackupTask]]:
        ...

    @abstractmethod
    @contextmanager
    def stopped_system(self, storage_info: Optional[List[AbstractStorageInfo]] = None) -> Generator:
        ...

    # @abstractmethod
    # def backup_host_directory(self, directory: Path, destination: Path, container_name: str) -> None:
    #     ...

    # @abstractmethod
    # def stop_container(self, container_id: str) -> None:
    #     ...

    # @abstractmethod
    # def backup_volume(self, volume_name: str, container_id: str) -> None:
    #     ...

    # @abstractmethod
    # def restart_container_with_volumes(self, container_id: str, volumes: List[str]) -> None:
    #     ...
