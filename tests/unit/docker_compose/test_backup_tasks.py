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

from backupbot.docker_compose.container_utils import stop_and_restart_container

from backupbot.docker_compose.container_utils import BackupItem


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
    service = DockerComposeService(
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

    monkeypatch.setattr(backupbot.docker_compose.backup_tasks, "timestamp", lambda *_: "TIMESTAMP")

    bind_mount_path = tmp_path.joinpath("service1", "bind_mounts")
    bind_mount_path.mkdir(parents=True)

    backup_task = DockerBindMountBackupTask(bind_mounts=["all"])

    tar_files = backup_task(service=service, backup_task_dir=bind_mount_path)

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
    service = DockerComposeService(
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

    monkeypatch.setattr(backupbot.docker_compose.backup_tasks, "timestamp", lambda *_: "TIMESTAMP")

    bind_mount_path = tmp_path.joinpath("service1", "bind_mounts")
    bind_mount_path.mkdir(parents=True)

    backup_task = DockerBindMountBackupTask(bind_mounts=["bind_mount2"])
    backup_task(service=service, backup_task_dir=bind_mount_path)

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

    backup_items = backup_task._prepare_volume_backup(volumes, target_dir=target_dir)

    assert backup_items == [
        BackupItem(
            command="tar -czf /backup/TIMESTAMP-volume1.tar.gz mount1",
            file_name="TIMESTAMP-volume1.tar.gz",
            final_path=target_dir.joinpath("volume1"),
        ),
        BackupItem(
            command="tar -czf /backup/TIMESTAMP-volume2.tar.gz mount2",
            file_name="TIMESTAMP-volume2.tar.gz",
            final_path=target_dir.joinpath("volume2"),
        ),
    ]

    assert target_dir.joinpath("volume1").is_dir()
    assert target_dir.joinpath("volume2").is_dir()
    assert len(list(target_dir.iterdir())) == 2


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

    service = DockerComposeService(
        name="volume_service",
        container_name="volume_service",
        image="ubuntu:latest",
        hostname="volume_service",
        volumes=volumes,
        bind_mounts=[],
    )
    backup_task = DockerVolumeBackupTask([volume.name for volume in volumes])

    with running_docker_compose_project(sample_docker_compose_project_dir.joinpath("docker-compose.yaml")) as _:
        created_files = backup_task(service=service, target_dir=target_dir)

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
        lambda *_: [BackupItem(failing_tar_command, Path("test_volume.tar.gz"), Path("/"))],
    )

    volumes = [Volume("test_volume", Path("tmp/volume"))]

    service = DockerComposeService(
        name="volume_service",
        container_name="volume_service",
        image="ubuntu:latest",
        hostname="volume_service",
        volumes=volumes,
        bind_mounts=[],
    )

    backup_task = DockerVolumeBackupTask([volume.name for volume in volumes])

    with running_docker_compose_project(sample_docker_compose_project_dir.joinpath("docker-compose.yaml")) as _:
        backup_task(service=service, target_dir=tmp_path)

    log_msg = caplog.record_tuples[1][2]

    assert (
        """Backup command 'tar -czf file.tar.gz /non/existing/directory' failed on service 'volume_service'. Backup"""
        """ file '/test_volume.tar.gz' was not created as a result.""" in log_msg
    )


def test_docker_mysql_backup_task_backs_up_mysql_contents(
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

    service = DockerComposeService(
        name="mysql_service",
        container_name="mysql_service",
        image="ubuntu:latest",
        hostname="mysql_service",
        volumes=[],
        bind_mounts=[],
    )

    backup_task = DockerMySQLBackupTask(database="test_database", user="root", password="root_password_42")

    with running_docker_compose_project(sample_docker_compose_project_dir.joinpath("docker-compose.yaml")) as _:
        with stop_and_restart_container(client=backup_task._docker_client, container_name="mysql_service"):
            created_files = backup_task(service=service, target_dir=target_dir)

    dump_file = temporary_directory.joinpath("TIMESTAMP-test_database.sql")
    assert dump_file.is_file()

    file_content = dump_file.read_text("utf-8")

    assert target_dir.joinpath("test_database", "TIMESTAMP-test_database.sql") in created_files
    assert len(list(temporary_directory.iterdir())) == 1

    # table is created via scropt /mount/create.sh in mysql_service
    create_table_command = """CREATE TABLE `test` (
  `id` int NOT NULL AUTO_INCREMENT,
  `value` int DEFAULT NULL,
  PRIMARY KEY (`id`)
)"""

    insert_table_command = "INSERT INTO `test` VALUES (1,42);"

    assert create_table_command in file_content
    assert insert_table_command in file_content
