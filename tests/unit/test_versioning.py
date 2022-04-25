import time
from pathlib import Path
from typing import List

import pytest
from backupbot.data_structures import FileVersion
from backupbot.versioning import (
    VERSIONING_TO_PATTERN,
    create_target_names,
    get_max_version_number,
    update_version_numbers,
)


def test_get_max_version_number(tmp_path: Path) -> None:
    tmp_path.joinpath("some_directory").mkdir()
    file1 = [tmp_path.joinpath("file1-1-0.txt"), tmp_path.joinpath("file1-1-1.txt"), tmp_path.joinpath("file1-2-0.txt")]
    file2 = [tmp_path.joinpath("file2-1-0.txt"), tmp_path.joinpath("other-2-1.zip")]

    for file in file1:
        file.touch()
    for file in file2:
        file.touch()

    assert get_max_version_number(file1, version_pattern=VERSIONING_TO_PATTERN["d-d"]) == FileVersion(major=2, minor=0)
    assert get_max_version_number(file2, version_pattern=VERSIONING_TO_PATTERN["d-d"]) == FileVersion(major=2, minor=1)
    assert get_max_version_number([], version_pattern=VERSIONING_TO_PATTERN["d-d"]) is None


def test_create_target_names_existing_versions(tmp_path: Path) -> None:
    tmp_path.joinpath("some_directory").mkdir()
    files = [
        tmp_path.joinpath("file-0-2.txt"),
        tmp_path.joinpath("file-0-1.txt"),
        tmp_path.joinpath("file-0-0.txt"),
        tmp_path.joinpath("file.txt"),
    ]

    for file in files:
        file.touch()

    assert create_target_names(files, file_ending="txt", major=False) == [
        (tmp_path.joinpath("file-0-2.txt"), tmp_path.joinpath("file-0-3.txt")),
        (tmp_path.joinpath("file-0-1.txt"), tmp_path.joinpath("file-0-2.txt")),
        (tmp_path.joinpath("file-0-0.txt"), tmp_path.joinpath("file-0-1.txt")),
        (tmp_path.joinpath("file.txt"), tmp_path.joinpath("file-0-0.txt")),
    ]


def test_create_target_names_first_version(tmp_path: Path) -> None:
    tmp_path.joinpath("some_directory").mkdir()
    tmp_path.joinpath("file.txt").touch()

    assert create_target_names([tmp_path.joinpath("file.txt")], "txt", major=False) == [
        (tmp_path.joinpath("file.txt"), tmp_path.joinpath("file-0-0.txt"))
    ]


def test_create_target_names_returns_empty_list_when_file_list_is_empty() -> None:
    assert create_target_names([], "txt") == []


def test_create_target_names_does_noting_when_list_contains_no_unversioned_file(tmp_path: Path) -> None:
    files: List[Path] = [
        tmp_path.joinpath("file-0-2.txt"),
        tmp_path.joinpath("file-0-1.txt"),
        tmp_path.joinpath("file-0-0.txt"),
    ]
    for file in files:
        file.touch()
        time.sleep(0.001)

    assert create_target_names(files, file_ending="txt") == [
        (tmp_path.joinpath("file-0-2.txt"), tmp_path.joinpath("file-0-2.txt")),
        (tmp_path.joinpath("file-0-1.txt"), tmp_path.joinpath("file-0-1.txt")),
        (tmp_path.joinpath("file-0-0.txt"), tmp_path.joinpath("file-0-0.txt")),
    ]


def test_update_version_numbers_raises_error_for_invalid_directory_path() -> None:
    with pytest.raises(NotADirectoryError):
        update_version_numbers(Path("invalid"), "txt")


def test_update_version_numbers(tmp_path: Path) -> None:
    files: List[Path] = [
        tmp_path.joinpath("file-0-2.txt"),
        tmp_path.joinpath("file-0-1.txt"),
        tmp_path.joinpath("file-0-0.txt"),
        tmp_path.joinpath("file.txt"),
    ]

    for file in files:
        file.touch()
        file.write_text(file.name)
        time.sleep(0.1)

    renamed = update_version_numbers(tmp_path, "txt", version_pattern=VERSIONING_TO_PATTERN["d-d"], major=False)

    assert tmp_path.joinpath("file-0-3.txt").is_file()
    assert tmp_path.joinpath("file-0-2.txt").is_file()
    assert tmp_path.joinpath("file-0-1.txt").is_file()
    assert tmp_path.joinpath("file-0-0.txt").is_file()

    assert tmp_path.joinpath("file-0-3.txt").read_text() == "file-0-2.txt"
    assert tmp_path.joinpath("file-0-2.txt").read_text() == "file-0-1.txt"
    assert tmp_path.joinpath("file-0-1.txt").read_text() == "file-0-0.txt"
    assert tmp_path.joinpath("file-0-0.txt").read_text() == "file.txt"

    assert len(renamed) == len(files)
