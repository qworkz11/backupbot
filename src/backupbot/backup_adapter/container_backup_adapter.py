"""This module defines an abstract adapter for container backup classes."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List


class ContainerBackupAdapter(ABC):
    @abstractmethod
    def collect_config_files(self, root: Path) -> List[Path]:
        ...

    @abstractmethod
    def parse_config(self, file: Path, root_directory: Path) -> Dict[str, Dict[str, List]]:
        ...

    @abstractmethod
    def backup_host_directory(self, directory: Path, destination: Path, container_name: str) -> None:
        ...

    # @abstractmethod
    # def stop_container(self, container_id: str) -> None:
    #     ...

    # @abstractmethod
    # def backup_volume(self, volume_name: str, container_id: str) -> None:
    #     ...

    # @abstractmethod
    # def restart_container_with_volumes(self, container_id: str, volumes: List[str]) -> None:
    #     ...
