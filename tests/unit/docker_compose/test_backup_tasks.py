from pathlib import Path
from typing import List

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
from tests.utils.dummies import create_dummy_task


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


def test_docker_bind_mount_backup_task_backs_up_all_bind_mounts(tmp_path: Path, dummy_bind_mount_dir: Path) -> None:
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

    bind_mount_path = tmp_path.joinpath("service1", "bind_mounts")
    bind_mount_path.mkdir(parents=True)

    backup_task = DockerBindMountBackupTask(bind_mounts=["all"])

    tar_files = backup_task(storage_info=storage_info, backup_task_dir=bind_mount_path)

    tar_file1_dir = bind_mount_path.joinpath(path_to_string(dummy_bind_mount_dir.joinpath("bind_mount1"), num_steps=3))
    tar_file2_dir = bind_mount_path.joinpath(path_to_string(dummy_bind_mount_dir.joinpath("bind_mount2"), num_steps=3))

    assert tar_file1_dir.is_dir()
    assert tar_file2_dir.is_dir()

    tar_file1 = path_to_string(dummy_bind_mount_dir.joinpath("bind_mount1"), num_steps=3) + ".tar.gz"
    tar_file2 = path_to_string(dummy_bind_mount_dir.joinpath("bind_mount2"), num_steps=3) + ".tar.gz"

    tar_file1_file = tar_file1_dir.joinpath(tar_file1)
    tar_file2_file = tar_file2_dir.joinpath(tar_file2)

    assert tar_file1_file.is_file()
    assert tar_file2_file.is_file()

    assert tar_files == [tar_file1_file, tar_file2_file]


def test_docker_bind_mount_backup_task_backs_up_selected_bind_mounts(
    tmp_path: Path, dummy_bind_mount_dir: Path
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

    bind_mount_path = tmp_path.joinpath("service1", "bind_mounts")
    bind_mount_path.mkdir(parents=True)

    backup_task = DockerBindMountBackupTask(bind_mounts=["bind_mount2"])
    backup_task(storage_info=storage_info, backup_task_dir=bind_mount_path)

    tar_file_dir = bind_mount_path.joinpath(path_to_string(dummy_bind_mount_dir.joinpath("bind_mount2"), num_steps=3))

    assert tar_file_dir.is_dir()
    assert len(list(bind_mount_path.iterdir())) == 1

    tar_file = path_to_string(dummy_bind_mount_dir.joinpath("bind_mount2"), num_steps=3) + ".tar.gz"

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
