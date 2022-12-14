"""Backupbot unit tests."""

from dataclasses import dataclass
from logging import ERROR
from pathlib import Path
from typing import Callable, Dict, List, Optional

import pytest
from docker import DockerClient
from pytest import LogCaptureFixture, MonkeyPatch

import backupbot.docker_compose.backup_tasks
from backupbot.abstract.backup_task import AbstractBackupTask
from backupbot.abstract.storage_info import AbstractStorageInfo
from backupbot.backupbot import BackupBot
from tests.utils.dummies import create_dummy_task


class DummyStorageInfo(AbstractStorageInfo):
    name: str
    unused_value: str


class RaisingBackupTask(AbstractBackupTask):
    target_dir_name: str = "raising"

    def __init__(self) -> None:
        pass

    def __call__(
        self, storage_info: Dict[str, AbstractStorageInfo], backup_tasks: Dict[str, List[AbstractBackupTask]]
    ) -> None:
        pass

    def __repr__(self) -> str:
        return "RaisingBackupTask"

    def __eq__(self, o: object) -> bool:
        pass


def raise_error(exception: Exception, msg: Optional[str] = None) -> None:
    raise exception(msg)


def test_init_raises_error_when_adapter_unknown() -> None:
    with pytest.raises(ValueError):
        BackupBot(root=Path("unimportant"), destination_directory=Path("unimportant"), adapter="unknown_adapter")


def test_create_service_backup_structure(tmp_path: Path) -> None:
    bub = BackupBot(root=Path("unimportant"), destination_directory=tmp_path, backup_config=Path("unimportant"))

    storage_info = {
        "service1": DummyStorageInfo(name="service1", unused_value="some_value"),
        "service2": DummyStorageInfo(name="service2", unused_value="some_value"),
    }
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
    bub = BackupBot(root=Path("unimportant"), destination_directory=tmp_path, backup_config=Path("unimportant"))

    storage_info = {
        "service1": DummyStorageInfo(name="service1", unused_value="some_value"),
        "service2": DummyStorageInfo(name="service2", unused_value="some_value"),
    }
    backup_tasks = {"service1": [create_dummy_task("dummy_task1")]}

    bub.create_service_backup_structure(storage_info=storage_info, backup_tasks=backup_tasks)

    assert len(list(tmp_path.iterdir())) == 1
    assert tmp_path.joinpath("service1").is_dir()


@pytest.mark.docker
def test_backupbot_backs_up_docker_compose_bind_mount(
    running_docker_compose_project: Callable,
    sample_docker_compose_project_dir: Path,
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    compose_file = sample_docker_compose_project_dir.joinpath("docker-compose.yaml")
    backup_config_file = sample_docker_compose_project_dir.joinpath("bind_mount_backup_scheme.json")

    bub = BackupBot(
        root=sample_docker_compose_project_dir,
        destination_directory=tmp_path,
        backup_config=backup_config_file,
        adapter="docker-compose",
    )

    monkeypatch.setattr(backupbot.docker_compose.backup_tasks, "timestamp", lambda *_: "TIMESTAMP")

    with running_docker_compose_project(compose_file) as _:
        bub.run_backup()

    assert len(list(tmp_path.iterdir())) == 1
    assert tmp_path.joinpath("bind_mount_service").is_dir()

    bind_mounts_task_dir = tmp_path.joinpath("bind_mount_service", "bind_mounts")
    assert len(list(bind_mounts_task_dir.iterdir())) == 1
    assert bind_mounts_task_dir.is_dir()

    bind_mount_dir = bind_mounts_task_dir.joinpath("bind_mount")
    assert len(list(bind_mount_dir.iterdir())) == 1
    assert bind_mount_dir.is_dir()

    file = bind_mount_dir.joinpath("TIMESTAMP-bind_mount.tar.gz")
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
        destination_directory=tmp_path,
        backup_config=backup_config_file,
        adapter="docker-compose",
    )

    with running_docker_compose_project(compose_file) as _:
        bub.run_backup()
        running_containers = [
            container.name for container in docker_client.containers.list(filters={"status": "running"})
        ]
        assert "bind_mount_service" in running_containers


def test_run_backup_tasks_logs_not_a_directory_error(caplog: LogCaptureFixture, monkeypatch: MonkeyPatch) -> None:
    bub = BackupBot(Path("unimportant"), destination_directory=Path("unimportant"), backup_config=Path("unimportant"))
    monkeypatch.setattr(
        RaisingBackupTask, "__call__", lambda *_, **__: raise_error(NotADirectoryError, "not a directory error")
    )

    backup_tasks: Dict[str, List[AbstractBackupTask]] = {"service_name": [RaisingBackupTask()]}

    bub._run_backup_tasks({"service_name": []}, backup_tasks)

    assert (
        "backupbot.logger",
        ERROR,
        "Failed to execute backup task 'RaisingBackupTask': 'not a directory error'.",
    ) in caplog.record_tuples


def test_run_backup_tasks_logs_runtime_error(caplog: LogCaptureFixture, monkeypatch: MonkeyPatch) -> None:
    bub = BackupBot(Path("unimportant"), destination_directory=Path("unimportant"), backup_config=Path("unimportant"))
    monkeypatch.setattr(RaisingBackupTask, "__call__", lambda *_, **__: raise_error(RuntimeError, "runtime error"))

    backup_tasks: Dict[str, List[AbstractBackupTask]] = {"service_name": [RaisingBackupTask()]}

    bub._run_backup_tasks({"service_name": []}, backup_tasks)

    assert (
        "backupbot.logger",
        ERROR,
        "Failed to execute backup task 'RaisingBackupTask': 'runtime error'.",
    ) in caplog.record_tuples


def test_generate_backup_config(tmp_path: Path, sample_docker_compose_project_dir: Path) -> None:
    bub = BackupBot(root=sample_docker_compose_project_dir, destination_directory=Path("unused"))

    bub.generate_backup_config(target_directory=tmp_path)

    assert tmp_path.joinpath("backup-config.json").is_file()
