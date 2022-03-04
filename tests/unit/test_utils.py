"""Unit tests for module backupbot.utils."""

import subprocess
from pathlib import Path
from typing import List

import backupbot.utils
import pytest
from _pytest.monkeypatch import MonkeyPatch
from backupbot.utils import (
    absolute_path,
    get_volume_path,
    load_yaml_file,
    locate_files,
    tar_directory,
)


def test_locate_files_finds_single_file(tmp_path: Path) -> None:
    tmp_path.joinpath("services", "data").mkdir(parents=True)
    tmp_path.joinpath("services", "other_data", "more_data").mkdir(parents=True)
    tmp_path.joinpath("services", "docker-compose.yaml").touch()

    result: List[Path] = []
    locate_files(tmp_path, "docker-compose.yaml", result)

    assert result == [tmp_path.joinpath("services", "docker-compose.yaml")]


def test_locate_files_finds_multiple_files(tmp_path: Path) -> None:
    tmp_path.joinpath("services", "data").mkdir(parents=True)
    tmp_path.joinpath("services", "other_data", "more_data").mkdir(parents=True)

    tmp_path.joinpath("services", "docker-compose.yaml").touch()
    tmp_path.joinpath("services", "data", "docker-compose.yaml").touch()
    tmp_path.joinpath("services", "other_data", "more_data", "docker-compose.yaml").touch()

    result: List[Path] = []
    locate_files(tmp_path, "docker-compose.yaml", result)

    # order does not matter:
    assert not (
        set(result).difference(
            [
                tmp_path.joinpath("services", "docker-compose.yaml"),
                tmp_path.joinpath("services", "data", "docker-compose.yaml"),
                tmp_path.joinpath("services", "other_data", "more_data", "docker-compose.yaml"),
            ]
        )
    )
    assert len(result) == len(set(result))  # to make sure no doubles are found


def test_locate_files_returns_empty_list_if_no_file_is_found(tmp_path: Path) -> None:
    result: List[Path] = []
    locate_files(tmp_path, "docker-compose.yaml", result)

    assert len(result) == 0


def test_locate_files_raises_error_for_invalid_directory() -> None:
    with pytest.raises(NotADirectoryError):
        locate_files(Path("not_exitsting_path"), "docker-compose.yaml", [])


def test_load_yaml_file_parses_dockerfile_correctly(
    dummy_docker_compose_file: Path,
) -> None:
    assert load_yaml_file(dummy_docker_compose_file) == {
        "version": "3",
        "services": {
            "first_service": {
                "container_name": "service1",
                "ports": ["80:80", "443:443"],
                "volumes": ["./bind_mount1:/container1/path", "named_volume1:/another/container1/path"],
            },
            "second_service": {
                "image": "source/image",
                "volumes": ["named_volume2:/container2/path", "./bind_mount2:/another/container2/path"],
            },
        },
        "networks": ["a_random_network"],
    }


def test_load_yaml_file_raises_error_for_invalid_path() -> None:
    with pytest.raises(FileNotFoundError):
        load_yaml_file(Path("invalid_path"))


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
    tmp_path.joinpath("data", "file1").touch()
    tmp_path.joinpath("data", "file2").touch()

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
