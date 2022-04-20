from typing import Dict, List

from backupbot.abstract.backup_task import AbstractBackupTask


def create_dummy_task(name: str) -> AbstractBackupTask:
    class DummyBackupTask(AbstractBackupTask):
        target_dir_name: str = name

        def __init__(self, **kwargs: Dict):
            pass

        def __eq__(self, o) -> bool:
            pass

        def __repr__(self) -> str:
            return ""

        def __call__(self, storage_info: Dict[str, Dict[str, List]]) -> None:
            pass

    return DummyBackupTask()
