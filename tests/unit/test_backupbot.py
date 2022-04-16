"""Backupbot unit tests."""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

from backupbot.abstract.backup_task import AbstractBackupTask
from backupbot.abstract.storage_info import AbstractStorageInfo
from backupbot.backupbot import BackupBot


def test_create_service_backup_structure(tmp_path: Path) -> None:
    bub = BackupBot(root=Path("unimportant"), destination=tmp_path, backup_config=Path("unimportant"))

    @dataclass
    class DummyStorageInfo(AbstractStorageInfo):
        name: str
        unused_value: str

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

    storage_info = [
        DummyStorageInfo("service1", "some_value"),
        DummyStorageInfo("service2", "some_value"),
    ]
    backup_tasks = {
        "service1": [create_dummy_task("dummy_task1"), create_dummy_task("dummy_task2")],
        "service2": [create_dummy_task("dummy_task3")],
    }

    bub.create_service_backup_structure(storage_info=storage_info, backup_tasks=backup_tasks)

    assert tmp_path.joinpath("service1").is_dir()
    assert tmp_path.joinpath("service1", "dummy_task1").is_dir()
    assert tmp_path.joinpath("service1", "dummy_task2").is_dir()

    assert tmp_path.joinpath("service2").is_dir()
    assert tmp_path.joinpath("service2", "dummy_task3").is_dir()

    assert len(list(tmp_path.iterdir())) == 2

    assert len(list(tmp_path.joinpath("service1").iterdir())) == 2
    assert len(list(tmp_path.joinpath("service2").iterdir())) == 1
