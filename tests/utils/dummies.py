from typing import Callable, Dict, List

from backupbot.abstract.backup_task import AbstractBackupTask
from backupbot.abstract.storage_info import AbstractStorageInfo


def create_dummy_task(name: str) -> AbstractBackupTask:
    class DummyBackupTask(AbstractBackupTask):
        target_dir_name: str = name

        def __init__(self, **kwargs: Dict):
            pass

        def __eq__(self, o) -> bool:
            pass

        def __repr__(self) -> str:
            return "DummyBackupTask"

        def __call__(
            self, storage_info: List[AbstractStorageInfo], backup_tasks: Dict[str, List[AbstractBackupTask]]
        ) -> None:
            pass

    return DummyBackupTask()
