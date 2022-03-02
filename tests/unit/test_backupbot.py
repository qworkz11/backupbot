"""Backupbot module unit tests."""

import datetime
from pathlib import Path
from typing import Any

import backupbot.backupbot
from _pytest.monkeypatch import MonkeyPatch
from backupbot.backupbot import BackupBot

FAKE_TIMESTAMP = datetime.datetime(2022, 2, 27, 10, 0, 0, 0)


class FakeDatetime:
    """Mock for datetime.datetime."""

    def now(self) -> datetime.datetime:
        """Mock for datetime.datetime.now().

        Returns:
            datetime.datetime: Fake timestamp.
        """
        return FAKE_TIMESTAMP


def test_backupbot_backup_bind_mount_with_existing_target(
    tmp_path: Path, dummy_dockerfile_path: Path, monkeypatch: MonkeyPatch
) -> None:
    data_dir = tmp_path.joinpath("data")
    data_dir.mkdir()
    data_dir.joinpath("file").touch()

    backup_dir = tmp_path.joinpath("backup")
    backup_dir.mkdir()

    service_dir = backup_dir.joinpath("service", "bind_mounts")
    service_dir.mkdir(parents=True)

    monkeypatch.setattr(backupbot.backupbot.datetime, "datetime", FakeDatetime)

    bub = BackupBot(tmp_path, backup_dir, dummy_dockerfile_path)
    bub.backup_bind_mount("data", "service")

    assert backup_dir.joinpath("service", "bind_mounts", f"{FAKE_TIMESTAMP}-data.tar.gz").is_file()


def test_backupbot_backup_bind_mount_creates_service_root_directory_if_it_does_not_exitst(
    tmp_path: Path, dummy_dockerfile_path: Path
) -> None:
    data_dir = tmp_path.joinpath("data")
    data_dir.mkdir()
    data_dir.joinpath("file").touch()

    backup_dir = tmp_path.joinpath("backup")
    backup_dir.mkdir()

    bub = BackupBot(tmp_path, backup_dir, dummy_dockerfile_path)
    bub.backup_bind_mount("data", "service")

    assert backup_dir.joinpath("service").is_dir()
    assert backup_dir.joinpath("service", "bind_mounts").is_dir()
