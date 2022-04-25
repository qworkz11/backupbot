from abc import ABC, abstractmethod
from typing import Callable, Dict, List

from backupbot.abstract.storage_info import AbstractStorageInfo


class AbstractBackupTask(ABC):
    @classmethod
    @property
    @abstractmethod
    def target_dir_name(self) -> Callable[[], str]:
        raise NotImplementedError

    @abstractmethod
    def __call__(self, storage_info: List[AbstractStorageInfo]) -> None:
        ...

    @abstractmethod
    def __eq__(self, o: object) -> bool:
        ...

    @abstractmethod
    def __repr__(self) -> str:
        ...

    def get_dest_dir_name(self) -> str:
        return type(self).target_dir_name


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
