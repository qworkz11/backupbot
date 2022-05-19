from contextlib import contextmanager
from pathlib import Path
from typing import List, Callable

import backupbot.docker_compose.backup_tasks
import pytest
from backupbot.abstract.backup_task import AbstractBackupTask
from backupbot.data_structures import HostDirectory
from backupbot.docker_compose.backup_tasks import (
    DockerBindMountBackupTask,
    DockerMySQLBackupTask,
    DockerVolumeBackupTask,
)
from backupbot.docker_compose.storage_info import DockerComposeService
from backupbot.utils import path_to_string
from pytest import MonkeyPatch
from tests.utils.dummies import create_dummy_task
from backupbot.data_structures import Volume
from pytest import LogCaptureFixture
import logging


def test_docker_bind_mount_backup_has_accessible_target_dir_name() -> None:
    backup_task: AbstractBackupTask = create_dummy_task("dir_name")

    assert backup_task.get_dest_dir_name() == "dir_name"


def test_docker_bind_mount_backup_task_can_be_created_from_dict() -> None:
    config = {"bind_mounts": ["all"]}
    backup_task = DockerBindMountBackupTask(**config)

    assert backup_task.bind_mounts == ["all"]


def test_docker_bind_mount_backup_task_raises_error_when_unknown_attributes_are_used() -> None:
    config = {"bind_mounts": ["all"], "unknown_key": "value"}

    with pytest.raises(NotImplementedError):
        DockerBindMountBackupTask(**config)


def test_docker_bind_mount_backup_task_backs_up_all_bind_mounts(
    tmp_path: Path, dummy_bind_mount_dir: Path, monkeypatch: MonkeyPatch
) -> None:
    storage_info: List[DockerComposeService] = [
        DockerComposeService(
            name="service1",
            container_name="service1",
            image="some_image",
            hostname="service1",
            bind_mounts=[
                HostDirectory(dummy_bind_mount_dir.joinpath("bind_mount1"), Path("/mount1")),
                HostDirectory(dummy_bind_mount_dir.joinpath("bind_mount2"), Path("/mount2")),
            ],
            volumes=[],
        )
    ]

    monkeypatch.setattr(backupbot.docker_compose.backup_tasks, "timestamp", lambda *_: "TIMESTAMP")

    bind_mount_path = tmp_path.joinpath("service1", "bind_mounts")
    bind_mount_path.mkdir(parents=True)

    backup_task = DockerBindMountBackupTask(bind_mounts=["all"])

    tar_files = backup_task(storage_info=storage_info, backup_task_dir=bind_mount_path)

    tar_file1_dir = bind_mount_path.joinpath(path_to_string(dummy_bind_mount_dir.joinpath("bind_mount1"), num_steps=1))
    tar_file2_dir = bind_mount_path.joinpath(path_to_string(dummy_bind_mount_dir.joinpath("bind_mount2"), num_steps=1))

    assert tar_file1_dir.is_dir()
    assert tar_file2_dir.is_dir()

    tar_file1 = f"TIMESTAMP-{path_to_string(dummy_bind_mount_dir.joinpath('bind_mount1'), num_steps=1)}.tar.gz"
    tar_file2 = f"TIMESTAMP-{path_to_string(dummy_bind_mount_dir.joinpath('bind_mount2'), num_steps=1)}.tar.gz"

    tar_file1_file = tar_file1_dir.joinpath(tar_file1)
    tar_file2_file = tar_file2_dir.joinpath(tar_file2)

    assert tar_file1_file.is_file()
    assert tar_file2_file.is_file()

    assert tar_files == [tar_file1_file, tar_file2_file]


def test_docker_bind_mount_backup_task_backs_up_selected_bind_mounts(
    tmp_path: Path, dummy_bind_mount_dir: Path, monkeypatch: MonkeyPatch
) -> None:
    storage_info: List[DockerComposeService] = [
        DockerComposeService(
            name="service1",
            container_name="service1",
            image="some_image",
            hostname="service1",
            bind_mounts=[
                HostDirectory(dummy_bind_mount_dir.joinpath("bind_mount1"), Path("/mount1")),
                HostDirectory(dummy_bind_mount_dir.joinpath("bind_mount2"), Path("/mount2")),
            ],
            volumes=[],
        )
    ]

    monkeypatch.setattr(backupbot.docker_compose.backup_tasks, "timestamp", lambda *_: "TIMESTAMP")

    bind_mount_path = tmp_path.joinpath("service1", "bind_mounts")
    bind_mount_path.mkdir(parents=True)

    backup_task = DockerBindMountBackupTask(bind_mounts=["bind_mount2"])
    backup_task(storage_info=storage_info, backup_task_dir=bind_mount_path)

    tar_file_dir = bind_mount_path.joinpath(path_to_string(dummy_bind_mount_dir.joinpath("bind_mount2"), num_steps=1))

    assert tar_file_dir.is_dir()
    assert len(list(bind_mount_path.iterdir())) == 1

    tar_file = path_to_string(dummy_bind_mount_dir.joinpath("bind_mount2"), num_steps=1) + "-TIMESTAMP.tar.gz"
    tar_file = f"TIMESTAMP-{path_to_string(dummy_bind_mount_dir.joinpath('bind_mount2'), num_steps=1)}.tar.gz"

    assert tar_file_dir.joinpath(tar_file).is_file()


def test_docker_bind_mount_backup_task_equality() -> None:
    assert DockerBindMountBackupTask(["item1", "item2"]) == DockerBindMountBackupTask(["item2", "item1"])
    assert not DockerBindMountBackupTask(["item1"]) == DockerBindMountBackupTask(["item1", "item2"])

    assert not DockerBindMountBackupTask(["item1", "item2"]) != DockerBindMountBackupTask(["item2", "item1"])
    assert DockerBindMountBackupTask(["item1"]) != DockerBindMountBackupTask(["item1", "item2"])


def test_docker_volume_backup_task_equality() -> None:
    assert DockerVolumeBackupTask(["item1", "item2"]) == DockerVolumeBackupTask(["item2", "item1"])
    assert not DockerVolumeBackupTask(["item1"]) == DockerVolumeBackupTask(["item1", "item2"])

    assert not DockerVolumeBackupTask(["item1", "item2"]) != DockerVolumeBackupTask(["item2", "item1"])
    assert DockerVolumeBackupTask(["item1"]) != DockerVolumeBackupTask(["item1", "item2"])


def test_docker_volume_backup_task_equality() -> None:
    assert DockerMySQLBackupTask("value1", "value2", "value3") == DockerMySQLBackupTask("value1", "value2", "value3")
    assert not DockerMySQLBackupTask("value1", "value2", "value3") == DockerMySQLBackupTask(
        "value1", "value4", "value5"
    )


def test_docker_volume_backup_task_prepare_volume_backup(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(backupbot.docker_compose.backup_tasks, "timestamp", lambda *_: "TIMESTAMP")

    target_dir = tmp_path.joinpath("target_dir")
    temp_dir = tmp_path.joinpath("temp_dir")

    target_dir.mkdir()
    temp_dir.mkdir()

    volumes = [Volume("volume1", Path("mount1")), Volume("volume2", Path("mount2"))]

    backup_task = DockerVolumeBackupTask([volume.name for volume in volumes])

    container_tmp_mapping, tar_commands = backup_task._prepare_volume_backup(
        volumes, target_dir=target_dir, tmp_directory=temp_dir
    )

    assert container_tmp_mapping == {
        target_dir.joinpath("volume1", "TIMESTAMP-volume1.tar.gz"): temp_dir.joinpath("TIMESTAMP-volume1.tar.gz"),
        target_dir.joinpath("volume2", "TIMESTAMP-volume2.tar.gz"): temp_dir.joinpath("TIMESTAMP-volume2.tar.gz"),
    }

    assert target_dir.joinpath("volume1").is_dir()
    assert target_dir.joinpath("volume2").is_dir()
    assert len(list(target_dir.iterdir())) == 2

    assert (
        tar_commands
        == "tar -czf /backup/TIMESTAMP-volume1.tar.gz mount1 && tar -czf /backup/TIMESTAMP-volume2.tar.gz mount2"
    )


def test_docker_volume_backup_task_prepare_volume_backup_only_adds_volume_once(
    tmp_path: Path, caplog: LogCaptureFixture, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.setattr(backupbot.docker_compose.backup_tasks, "timestamp", lambda *_: "TIMESTAMP")

    target_dir = tmp_path.joinpath("target_dir")
    temp_dir = tmp_path.joinpath("temp_dir")

    target_dir.mkdir()
    temp_dir.mkdir()

    volumes = [Volume("volume1", Path("mount1")), Volume("volume1", Path("mount1"))]

    backup_task = DockerVolumeBackupTask([volume.name for volume in volumes])

    container_tmp_mapping, tar_commands = backup_task._prepare_volume_backup(
        volumes, target_dir=target_dir, tmp_directory=temp_dir
    )

    assert container_tmp_mapping == {
        target_dir.joinpath("volume1", "TIMESTAMP-volume1.tar.gz"): temp_dir.joinpath("TIMESTAMP-volume1.tar.gz")
    }
    assert len(list(target_dir.iterdir())) == 1

    assert tar_commands == "tar -czf /backup/TIMESTAMP-volume1.tar.gz mount1"

    assert (
        "backupbot.logger",
        logging.ERROR,
        (
            f"""Error while mapping temporary file '{temp_dir.joinpath('TIMESTAMP-volume1.tar.gz')}' to their final"""
            f""" target: A mapping for target '{target_dir.joinpath('volume1', 'TIMESTAMP-volume1.tar.gz')}' already"""
            """ exists."""
        ),
    ) in caplog.record_tuples


def test_docker_volume_backup_call_creates_tar_files_in_temporary_directory(
    tmp_path: Path,
    running_docker_compose_project: Callable,
    sample_docker_compose_project_dir: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    temporary_directory = tmp_path.joinpath("temporary")
    temporary_directory.mkdir()

    @contextmanager
    def dummy_TemporayDirectory():
        yield temporary_directory

    monkeypatch.setattr(backupbot.docker_compose.backup_tasks, "TemporaryDirectory", dummy_TemporayDirectory)
    monkeypatch.setattr(backupbot.docker_compose.backup_tasks, "timestamp", lambda *_: "TIMESTAMP")

    target_dir = tmp_path.joinpath("target")
    target_dir.mkdir()

    volumes = [Volume("test_volume", Path("tmp/volume"))]

    storage_info = [
        DockerComposeService(
            name="volume_service",
            container_name="volume_service",
            image="ubuntu:latest",
            hostname="volume_service",
            volumes=volumes,
            bind_mounts=[],
        )
    ]
    backup_task = DockerVolumeBackupTask([volume.name for volume in volumes])

    with running_docker_compose_project(sample_docker_compose_project_dir.joinpath("docker-compose.yaml")) as _:
        created_files = backup_task(storage_info, target_dir)

    assert temporary_directory.joinpath("TIMESTAMP-test_volume.tar.gz").is_file()
    assert len(list(temporary_directory.iterdir())) == 1

    # make sure that created files are returned as list (following a bug in early development):
    assert created_files == [target_dir.joinpath("test_volume", "TIMESTAMP-test_volume.tar.gz")]


def test_docker_volume_backup_call_with_failing_docker_container(
    tmp_path: Path,
    running_docker_compose_project: Callable,
    sample_docker_compose_project_dir: Path,
    monkeypatch: MonkeyPatch,
    caplog: LogCaptureFixture,
) -> None:
    failing_tar_command = "tar -czf file.tar.gz /non/existing/directory"
    monkeypatch.setattr(
        backupbot.docker_compose.backup_tasks.DockerVolumeBackupTask,
        "_prepare_volume_backup",
        lambda *_: (
            {},
            failing_tar_command,
        ),
    )

    volumes = [Volume("test_volume", Path("tmp/volume"))]

    storage_info = [
        DockerComposeService(
            name="volume_service",
            container_name="volume_service",
            image="ubuntu:latest",
            hostname="volume_service",
            volumes=volumes,
            bind_mounts=[],
        )
    ]
    backup_task = DockerVolumeBackupTask([volume.name for volume in volumes])

    with running_docker_compose_project(sample_docker_compose_project_dir.joinpath("docker-compose.yaml")) as _:
        backup_task(storage_info, tmp_path)

    log_msg = caplog.record_tuples[0][2]

    assert "Failed to backup volumes from container 'volume_service':" in log_msg
