"""Unit tests for module backupbot.utils."""

import subprocess
from pathlib import Path
from typing import Dict

import backupbot.utils
import pytest
from _pytest.monkeypatch import MonkeyPatch
from backupbot.utils import (
    absolute_path,
    get_volume_path,
    load_compose_file,
    locate_compose_file,
    tar_directory,
)


def test_locate_compose_file_finds_correct_paths(tmp_path: Path) -> None:
    tmp_path.joinpath("services", "data").mkdir(parents=True)
    tmp_path.joinpath("services", "other_data", "more_data").mkdir(parents=True)
    tmp_path.joinpath("services", "docker-compose.yaml").touch()

    assert locate_compose_file(tmp_path) == tmp_path.joinpath("services", "docker-compose.yaml")
    assert locate_compose_file(tmp_path.joinpath("services", "data")) == None


def test_locate_compose_file_raises_error_for_invalid_directory() -> None:
    with pytest.raises(NotADirectoryError):
        locate_compose_file(Path("not_exitsting_path"))


def test_load_compose_file_parses_dockerfile_correctly(
    dummy_dockerfile_path: Path,
) -> None:
    assert load_compose_file(dummy_dockerfile_path) == {
        "version": "3",
        "services": {
            "first_service": {
                "container_name": "service1",
                "ports": ["80:80", "443:443"],
                "volumes": ["./bind_mount1:/container/path", "named_volume1:/another/container/path"],
            },
            "second_service": {
                "image": "source/image",
                "volumes": ["named_volume2:/container/path", "./bind_mount2:/another/container/path"],
            },
        },
        "networks": ["a_random_network"],
    }


def test_load_compose_file_raises_error_for_invalid_path() -> None:
    with pytest.raises(FileNotFoundError):
        load_compose_file(Path("invalid_path"))


def test_get_volume_path() -> None:
    assert get_volume_path("named_volume:/path/on/container") == "named_volume"
    assert get_volume_path("./bind_mount:/path/on/container") == "./bind_mount"


def test_absolute_paths_composes_paths_correctly() -> None:
    assert absolute_path(["./hello", "./world", "../different/directory"], root=Path("root")) == [
        Path("root/hello"),
        Path("root/world"),
        Path("root/../different/directory"),
    ]


def test_tar_directory_tar_compresses_directory(tmp_path: Path) -> None:
    tmp_path.joinpath("data").mkdir()
    tmp_path.joinpath("data").touch("file1")
    tmp_path.joinpath("data").touch("file2")

    tar = tar_directory(tmp_path.joinpath("data"), "data_tar", tmp_path)

    assert tar.is_file()


def test_tar_directory_raises_error_for_invalid_paths(tmp_path: Path) -> None:
    tmp_path.joinpath("data").mkdir()

    with pytest.raises(NotADirectoryError):
        tar_directory(tmp_path.joinpath("not_exitsing"), "some_name", tmp_path.joinpath("data"))

    with pytest.raises(NotADirectoryError):
        tar_directory(tmp_path.joinpath("data"), "some_name", tmp_path.joinpath("not_exitsing"))


def test_tar_directory_raises_error_if_subprocess_returns_error_exit_code(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.setattr(backupbot.utils.subprocess, "run", lambda *_, **__: subprocess.CompletedProcess((), 1))
    tmp_path.joinpath("data").mkdir()

    with pytest.raises(RuntimeError):
        tar_directory(tmp_path.joinpath("data"), "name", tmp_path)


def test_tar_directory_raises_error_if_tar_file_does_not_exist_after_tar_command(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.setattr(backupbot.utils.subprocess, "run", lambda *_, **__: subprocess.CompletedProcess((), 0))

    with pytest.raises(RuntimeError):
        tar_directory(tmp_path, "irrelevant_name", tmp_path)
