"""Backupbot unit tests."""

from dataclasses import dataclass
from logging import ERROR
from pathlib import Path
from typing import Callable, Dict, List, Optional

import pytest
from backupbot.abstract.backup_task import AbstractBackupTask
from backupbot.abstract.storage_info import AbstractStorageInfo
from backupbot.backupbot import BackupBot
from docker import DockerClient
from pytest import LogCaptureFixture, MonkeyPatch
from tests.utils.dummies import create_dummy_task


@dataclass
class DummyStorageInfo(AbstractStorageInfo):
    name: str
    unused_value: str


class RaisingBackupTask(AbstractBackupTask):
    target_dir_name: str = "raising"

    def __init__(self) -> None:
        pass

    def __call__(
        self, storage_info: List[AbstractStorageInfo], backup_tasks: Dict[str, List[AbstractBackupTask]]
    ) -> None:
        pass

    def __repr__(self) -> str:
        return "RaisingBackupTask"

    def __eq__(self, o: object) -> bool:
        pass


def raise_error(exception: Exception, msg: Optional[str] = None) -> None:
    raise exception(msg)


def test_init_raises_error_when_cri_unknown() -> None:
    with pytest.raises(ValueError):
        BackupBot(Path("unimportant"), Path("unimportant"), Path("unimportant"), adapter="unknown_cri")


def test_create_service_backup_structure(tmp_path: Path) -> None:
    bub = BackupBot(root=Path("unimportant"), destination=tmp_path, backup_config=Path("unimportant"))

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


def test_create_service_backup_structure_creates_directories_only_when_specified_in_config_file(tmp_path: Path) -> None:
    bub = BackupBot(root=Path("unimportant"), destination=tmp_path, backup_config=Path("unimportant"))

    storage_info = [
        DummyStorageInfo("service1", "some_value"),
        DummyStorageInfo("service2", "some_value"),
    ]
    backup_tasks = {"service1": [create_dummy_task("dummy_task1")]}

    bub.create_service_backup_structure(storage_info=storage_info, backup_tasks=backup_tasks)

    assert len(list(tmp_path.iterdir())) == 1
    assert tmp_path.joinpath("service1").is_dir()


@pytest.mark.docker
def test_backupbot_backs_up_docker_compose_bind_mount(
    running_docker_compose_project: Callable, sample_docker_compose_project_dir: Path, tmp_path: Path
) -> None:
    compose_file = sample_docker_compose_project_dir.joinpath("docker-compose.yaml")
    backup_config_file = sample_docker_compose_project_dir.joinpath("bind_mount_backup_scheme.json")

    bub = BackupBot(
        root=sample_docker_compose_project_dir,
        destination=tmp_path,
        backup_config=backup_config_file,
        adapter="docker-compose",
    )

    with running_docker_compose_project(compose_file) as _:
        bub.run()

    assert len(list(tmp_path.iterdir())) == 1
    assert tmp_path.joinpath("bind_mount_service").is_dir()

    bind_mounts_task_dir = tmp_path.joinpath("bind_mount_service", "bind_mounts")
    assert len(list(bind_mounts_task_dir.iterdir())) == 1
    assert bind_mounts_task_dir.is_dir()

    bind_mount_dir = bind_mounts_task_dir.joinpath("resources-sample_docker_compose_service-bind_mount")
    assert len(list(bind_mount_dir.iterdir())) == 1
    assert bind_mount_dir.is_dir()

    file = bind_mount_dir.joinpath("resources-sample_docker_compose_service-bind_mount.tar.gz")
    assert len(list(bind_mount_dir.iterdir())) == 1
    assert file.is_file()


@pytest.mark.docker
def test_backupbot_restarts_containers_after_backup(
    running_docker_compose_project: Callable,
    sample_docker_compose_project_dir: Path,
    tmp_path: Path,
    docker_client: DockerClient,
) -> None:
    compose_file = sample_docker_compose_project_dir.joinpath("docker-compose.yaml")
    backup_config_file = sample_docker_compose_project_dir.joinpath("bind_mount_backup_scheme.json")

    bub = BackupBot(
        root=sample_docker_compose_project_dir,
        destination=tmp_path,
        backup_config=backup_config_file,
        adapter="docker-compose",
    )

    with running_docker_compose_project(compose_file) as _:
        bub.run()
        running_containers = [
            container.name for container in docker_client.containers.list(filters={"status": "running"})
        ]
        assert "bind_mount_service" in running_containers


def test_update_file_versions_minor(tmp_path: Path) -> None:
    backup_dirs = [tmp_path.joinpath("backup1"), tmp_path.joinpath("backup2")]
    files = [
        tmp_path.joinpath("backup1", "file.tar.gz"),
        tmp_path.joinpath("backup1", "file-0-0.tar.gz"),
        tmp_path.joinpath("backup2", "file.tar.gz"),
    ]

    for d in backup_dirs:
        d.mkdir()
    for file in files:
        file.touch()

    bub = BackupBot(
        Path("unimportant"),
        destination=tmp_path,
        backup_config=Path("unimportant"),
        adapter="docker-compose",
        update_major=False,
    )

    bub.update_file_versions(created_files=files)

    assert tmp_path.joinpath("backup1", "file-0-0.tar.gz").is_file()
    assert tmp_path.joinpath("backup1", "file-0-1.tar.gz").is_file()

    assert tmp_path.joinpath("backup2", "file-0-0.tar.gz").is_file()


def test_update_file_versions_major(tmp_path: Path) -> None:
    backup_dirs = [tmp_path.joinpath("backup1"), tmp_path.joinpath("backup2")]
    files = [
        tmp_path.joinpath("backup1", "file.tar.gz"),
        tmp_path.joinpath("backup1", "file-0-0.tar.gz"),
        tmp_path.joinpath("backup2", "file.tar.gz"),
    ]

    for d in backup_dirs:
        d.mkdir()
    for file in files:
        file.touch()

    bub = BackupBot(
        Path("unimportant"),
        destination=tmp_path,
        backup_config=Path("unimportant"),
        adapter="docker-compose",
        update_major=True,
    )

    bub.update_file_versions(created_files=files)

    assert tmp_path.joinpath("backup1", "file-0-0.tar.gz").is_file()
    assert tmp_path.joinpath("backup1", "file-1-0.tar.gz").is_file()

    assert tmp_path.joinpath("backup2", "file-0-0.tar.gz").is_file()


def test_run_backup_tasks_logs_not_implemented_error(caplog: LogCaptureFixture, monkeypatch: MonkeyPatch) -> None:
    bub = BackupBot(Path("unimportant"), destination=Path("unimportant"), backup_config=Path("unimportant"))
    monkeypatch.setattr(
        RaisingBackupTask, "__call__", lambda *_, **__: raise_error(NotImplementedError, "not implemented error")
    )

    backup_tasks: Dict[str, List[AbstractBackupTask]] = {"service_name": [RaisingBackupTask()]}

    bub._run_backup_tasks({"unimportant_service": []}, backup_tasks)

    assert (
        "backupbot.logger",
        ERROR,
        "Failed to execute backup task 'RaisingBackupTask': 'not implemented error'.",
    ) in caplog.record_tuples


def test_run_backup_tasks_logs_not_a_directory_error(caplog: LogCaptureFixture, monkeypatch: MonkeyPatch) -> None:
    bub = BackupBot(Path("unimportant"), destination=Path("unimportant"), backup_config=Path("unimportant"))
    monkeypatch.setattr(
        RaisingBackupTask, "__call__", lambda *_, **__: raise_error(NotADirectoryError, "not a directory error")
    )

    backup_tasks: Dict[str, List[AbstractBackupTask]] = {"service_name": [RaisingBackupTask()]}

    bub._run_backup_tasks({"unimportant_service": []}, backup_tasks)

    assert (
        "backupbot.logger",
        ERROR,
        "Failed to execute backup task 'RaisingBackupTask': 'not a directory error'.",
    ) in caplog.record_tuples


def test_run_backup_tasks_logs_runtime_error(caplog: LogCaptureFixture, monkeypatch: MonkeyPatch) -> None:
    bub = BackupBot(Path("unimportant"), destination=Path("unimportant"), backup_config=Path("unimportant"))
    monkeypatch.setattr(RaisingBackupTask, "__call__", lambda *_, **__: raise_error(RuntimeError, "runtime error"))

    backup_tasks: Dict[str, List[AbstractBackupTask]] = {"service_name": [RaisingBackupTask()]}

    bub._run_backup_tasks({"unimportant_service": []}, backup_tasks)

    assert (
        "backupbot.logger",
        ERROR,
        "Failed to execute backup task 'RaisingBackupTask': 'runtime error'.",
    ) in caplog.record_tuples
