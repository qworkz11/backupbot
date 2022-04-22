"""Backupbot unit tests."""

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import pytest
from backupbot.abstract.storage_info import AbstractStorageInfo
from backupbot.backupbot import BackupBot
from docker import DockerClient
from tests.utils.dummies import create_dummy_task


@dataclass
class DummyStorageInfo(AbstractStorageInfo):
    name: str
    unused_value: str


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
