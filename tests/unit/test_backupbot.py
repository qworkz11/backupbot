"""Backupbot unit tests."""

from pathlib import Path

from backupbot.backupbot import BackupBot
from backupbot.data_structures import HostDirectory, Volume


def test_create_target_folder_creates_host_directory_folder_structure(tmp_path: Path) -> None:
    bub = BackupBot(Path("not existing"), tmp_path)

    bub.create_target_folders(
        {
            "service1": {
                "host_directories": [
                    HostDirectory(Path("/host/directory/1"), Path("unimportant")),
                    HostDirectory(Path("/host/directory/2"), Path("unimportant")),
                ]
            },
            "service2": {"host_directories": [HostDirectory(Path("/host-directory-3"), Path("unimportant"))]},
        }
    )

    assert tmp_path.joinpath("service1", "host_directories", "-host-directory-1").is_dir()
    assert tmp_path.joinpath("service1", "host_directories", "-host-directory-2").is_dir()
    assert tmp_path.joinpath("service2", "host_directories", "-host-directory-3").is_dir()
    assert len(list(tmp_path.iterdir())) == 2


def test_create_target_folder_creates_volume_folder_structure(tmp_path: Path) -> None:
    bub = BackupBot(Path("not existing"), tmp_path)

    bub.create_target_folders(
        {
            "service1": {
                "volumes": [
                    Volume("volume1", Path("unimportant")),
                    Volume("volume2", Path("unimportant")),
                ]
            },
            "service2": {"volumes": [Volume("volume3", Path("unimportant"))]},
        }
    )

    assert tmp_path.joinpath("service1", "volumes", "volume1").is_dir()
    assert tmp_path.joinpath("service1", "volumes", "volume2").is_dir()
    assert tmp_path.joinpath("service2", "volumes", "volume3").is_dir()
    assert len(list(tmp_path.iterdir())) == 2
