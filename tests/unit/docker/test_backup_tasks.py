from pathlib import Path

from backupbot.data_structures import HostDirectory
from backupbot.docker.backup_tasks import DockerBindMountBackupTask
from backupbot.utils import path_to_string


def test_docker_bind_mount_backup_task_backs_up_all_bind_mounts(tmp_path: Path, dummy_bind_mount_dir: Path) -> None:
    storage_info = {
        "service1": {
            "bind_mounts": [
                HostDirectory(dummy_bind_mount_dir.joinpath("bind_mount1"), Path("/mount1")),
                HostDirectory(dummy_bind_mount_dir.joinpath("bind_mount2"), Path("/mount2")),
            ]
        }
    }

    backup_task = DockerBindMountBackupTask(bind_mounts=["all"])
    backup_task(storage_info=storage_info, root=tmp_path)

    service_subdir = tmp_path.joinpath("service1")

    assert service_subdir.joinpath("bind_mount1").is_dir()
    assert service_subdir.joinpath("bind_mount2").is_dir()

    tar_file1 = path_to_string(dummy_bind_mount_dir.joinpath("bind_mount1"), num_steps=3) + ".tar.gz"
    tar_file2 = path_to_string(dummy_bind_mount_dir.joinpath("bind_mount2"), num_steps=3) + ".tar.gz"

    assert service_subdir.joinpath("bind_mount1", tar_file1).is_file()
    assert service_subdir.joinpath("bind_mount2", tar_file2).is_file()


def test_docker_bind_mount_backup_task_backs_up_selected_bind_mounts(
    tmp_path: Path, dummy_bind_mount_dir: Path
) -> None:
    storage_info = {
        "service1": {
            "bind_mounts": [
                HostDirectory(dummy_bind_mount_dir.joinpath("bind_mount1"), Path("/mount1")),
                HostDirectory(dummy_bind_mount_dir.joinpath("bind_mount2"), Path("/mount2")),
            ]
        }
    }

    backup_task = DockerBindMountBackupTask(bind_mounts=["bind_mount2"])
    backup_task(storage_info=storage_info, root=tmp_path)

    service_subdir = tmp_path.joinpath("service1")

    assert not service_subdir.joinpath("bind_mount1").exists()
    assert service_subdir.joinpath("bind_mount2").is_dir()

    tar_file = path_to_string(dummy_bind_mount_dir.joinpath("bind_mount2"), num_steps=3) + ".tar.gz"

    assert service_subdir.joinpath("bind_mount2", tar_file).is_file()
