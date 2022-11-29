from abc import ABC, abstractmethod
from typing import Callable, List
from pathlib import Path

from backupbot.abstract.storage_info import AbstractStorageInfo


class AbstractBackupTask(ABC):
    @classmethod
    @property
    @abstractmethod
    def target_dir_name(self) -> Callable[[], str]:
        raise NotImplementedError

    @abstractmethod
    def __call__(self, storage_info: AbstractStorageInfo) -> List[Path]:
        ...

    @abstractmethod
    def __eq__(self, o: object) -> bool:
        ...

    @abstractmethod
    def __repr__(self) -> str:
        ...

    def get_dest_dir_name(self) -> str:
        return type(self).target_dir_name
