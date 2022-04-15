from abc import ABC, abstractmethod
from typing import Dict, List


class AbstractBackupTask(ABC):
    @classmethod
    @property
    @abstractmethod
    def target_dir_name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def __call__(self, storage_info: Dict[str, Dict[str, List]]) -> None:
        ...


# class AbstractHostDirectoryBackupTask(AbstractBackupTask, ABC):
#     target_dir_name = "host_directories"

#     @abstractmethod
#     def __call__(self, storage_info: Dict[str, Dict[str, List]]) -> None:
#         ...


# class AbstractVolumeBackupTask(AbstractBackupTask, ABC):
#     target_dir_name = "volumes"

#     @abstractmethod
#     def __call__(self, storage_info: Dict[str, Dict[str, List]]) -> None:
#         ...


# class AbstractMySQLBackupTask(AbstractBackupTask, ABC):
#     target_dir_name = "mysql_databases"

#     @abstractmethod
#     def __call__(self, storage_info: Dict[str, Dict[str, List]]) -> None:
#         ...