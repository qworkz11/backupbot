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
    match_files,
    path_to_string,
    tar_file_or_directory,
    copy_files,
)


def test_match_files_finds_single_file(tmp_path: Path) -> None:
    tmp_path.joinpath("services", "data").mkdir(parents=True)
    tmp_path.joinpath("services", "other_data", "more_data").mkdir(parents=True)
    tmp_path.joinpath("services", "docker-compose.yaml").touch()

    result: List[Path] = []
    match_files(tmp_path, ".yaml", result)

    assert result == [tmp_path.joinpath("services", "docker-compose.yaml")]


def test_match_files_finds_multiple_files(tmp_path: Path) -> None:
    tmp_path.joinpath("services", "data").mkdir(parents=True)
    tmp_path.joinpath("services", "other_data", "more_data").mkdir(parents=True)

    tmp_path.joinpath("services", "docker-compose.yaml").touch()
    tmp_path.joinpath("services", "data", "docker-compose.yaml").touch()
    tmp_path.joinpath("services", "other_data", "more_data", "docker-compose.yaml").touch()

    result: List[Path] = []
    match_files(tmp_path, "*.yaml", result)

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


def test_match_files_returns_empty_list_when_no_files_match(tmp_path: Path) -> None:
    result: List[Path] = []
    match_files(tmp_path, "*.not_exising", result)

    assert len(result) == 0


def test_match_files_raises_error_for_invalid_directory() -> None:
    with pytest.raises(NotADirectoryError):
        match_files(Path("not_exitsting_path"), "unimportant_pattern", [])


def test_match_files_matches_files_with_containing_pattern(tmp_path: Path) -> None:
    tmp_path.joinpath("services", "data").mkdir(parents=True)
    tmp_path.joinpath("services", "other_data", "more_data").mkdir(parents=True)
    tmp_path.joinpath("services", "file.txt").touch()
    tmp_path.joinpath("services", "other_data", "fileXYZ.txt").touch()

    result: List[Path] = []
    match_files(tmp_path, "file", result)

    assert result == [
        tmp_path.joinpath("services", "file.txt"),
        tmp_path.joinpath("services", "other_data", "fileXYZ.txt"),
    ]


def test_load_yaml_file_parses_dockerfile_correctly(
    dummy_docker_compose_file: Path,
) -> None:
    parsed = load_yaml_file(dummy_docker_compose_file)
    assert parsed == {
        "version": "3",
        "services": {
            "first_service": {
                "container_name": "service1",
                "image": "image1",
                "hostname": "hostname1",
                "ports": ["80:80", "443:443"],
                "volumes": [
                    "./service1_bind_mount1:/service1/bind_mount1/path",
                    "service1_volume1:/service1/volume1/path",
                    "service1_volume2:/service1/volume2/path",
                ],
            },
            "second_service": {
                "image": "source/image",
                "container_name": "service2",
                "hostname": "hostname2",
                "volumes": [
                    "service2_volume1:/service2/volume1/path",
                    "service2_volume2:/service2/volume2/path",
                    "./service2_bind_mount1:/service2/bind_mount1/path",
                    "./service2_bind_mount2:/service2/bind_mount2/path",
                ],
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


def test_tar_file_or_directory_tar_compresses_directory(tmp_path: Path) -> None:
    tmp_path.joinpath("data").mkdir()
    tmp_path.joinpath("data", "file1").touch()
    tmp_path.joinpath("data", "file2").touch()

    tar = tar_file_or_directory(tmp_path.joinpath("data"), "data_tar", tmp_path)

    assert tar.is_file()


def test_tar_file_or_directory_raises_error_for_invalid_paths(tmp_path: Path) -> None:
    tmp_path.joinpath("data").mkdir()

    with pytest.raises(NotADirectoryError):
        tar_file_or_directory(tmp_path.joinpath("not_exitsing"), "some_name", tmp_path.joinpath("data"))

    with pytest.raises(NotADirectoryError):
        tar_file_or_directory(tmp_path.joinpath("data"), "some_name", tmp_path.joinpath("not_exitsing"))


def test_tar_file_or_directory_raises_error_if_subprocess_returns_error_exit_code(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.setattr(backupbot.utils.subprocess, "run", lambda *_, **__: subprocess.CompletedProcess((), 1))
    tmp_path.joinpath("data").mkdir()

    with pytest.raises(RuntimeError):
        tar_file_or_directory(tmp_path.joinpath("data"), "name", tmp_path)


def test_tar_file_or_directory_raises_error_if_tar_file_does_not_exist_after_tar_command(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.setattr(backupbot.utils.subprocess, "run", lambda *_, **__: subprocess.CompletedProcess((), 0))

    with pytest.raises(RuntimeError):
        tar_file_or_directory(tmp_path, "irrelevant_name", tmp_path)


def test_tar_file_or_directory_for_file(tmp_path: Path) -> None:
    file = tmp_path.joinpath("file.txt")
    file.touch()

    tar_file_or_directory(file, "file.txt", tmp_path)
    assert tmp_path.joinpath("file.txt.tar.gz").is_file()


def test_tar_file_or_directory_does_not_override_existing_files_when_override_not_set(tmp_path: Path) -> None:
    file = tmp_path.joinpath("file.txt")
    file.touch()

    tar_files = [tmp_path.joinpath("file.txt.tar.gz"), tmp_path.joinpath("file.txt(1).tar.gz")]
    for f in tar_files:
        f.touch()

    tar_file_or_directory(file, "file.txt", tmp_path, override=False)

    assert tmp_path.joinpath("file.txt.tar.gz").is_file()
    assert tmp_path.joinpath("file.txt(1).tar.gz").is_file()
    assert tmp_path.joinpath("file.txt(2).tar.gz").is_file()


def test_path_to_string() -> None:
    assert path_to_string(Path("/path/with/name/foo"), num_steps=1) == "foo"
    assert path_to_string(Path("path/with/name/foo"), num_steps=-1) == "path-with-name-foo"
    assert path_to_string(Path("/path/with/name/foo"), num_steps=3) == "with-name-foo"
    assert path_to_string(Path("path/with/name/foo"), num_steps=2, delim="#") == "name#foo"


def test_copy_files(tmp_path: Path) -> None:
    source = tmp_path.joinpath("source")
    target_file = tmp_path.joinpath("target_file")
    target_zip = tmp_path.joinpath("target_zip")

    source.mkdir()
    target_file.mkdir()
    target_zip.mkdir()

    file = source.joinpath("file.txt")
    zip_dir = source.joinpath("zip.zip")
    file.touch()
    zip_dir.touch()

    copy_files({target_file.joinpath("file.txt"): file, target_zip.joinpath("zip.zip"): zip_dir})

    assert target_file.joinpath("file.txt").is_file()
    assert target_zip.joinpath("zip.zip").is_file()
