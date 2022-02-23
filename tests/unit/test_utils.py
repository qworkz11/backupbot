"""Unit tests for module backupbot.utils."""

from pathlib import Path
from typing import Dict

import pytest
from backupbot.utils import (
    absolute_paths,
    extract_volumes,
    get_volume_path,
    load_dockerfile,
)


def test_load_dockerfile_parses_dockerfile_correctly(
    dummy_dockerfile_path: Path,
) -> None:
    assert load_dockerfile(dummy_dockerfile_path) == {
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


def test_load_dockerfile_raises_error_for_invalid_path() -> None:
    with pytest.raises(FileNotFoundError):
        load_dockerfile(Path("invalid_path"))


def test_extract_volumes() -> None:
    assert extract_volumes(
        {
            "version": "3",
            "services": {
                "service1": {"volumes": ["./bind_mount1:/container/path", "named_volume1:/another/container/path"]},
                "service2": {"volumes": ["./bind_mount2:/container/path", "named_volume2:/another/container/path"]},
            },
        }
    ) == (
        ["named_volume1:/another/container/path", "named_volume2:/another/container/path"],
        ["./bind_mount1:/container/path", "./bind_mount2:/container/path"],
    )


def test_extract_volumes_returns_empty_list_if_dockerfile_has_no_services_attribute() -> None:
    assert extract_volumes({"networks": {"nw": None}}) == (None, None)


def test_get_volume_path() -> None:
    assert get_volume_path("named_volume:/path/on/container") == "named_volume"
    assert get_volume_path("./bind_mount:/path/on/container") == "./bind_mount"


def test_absolute_paths_composes_paths_correctly() -> None:
    assert absolute_paths(["./hello", "./world", "../different/directory"], root=Path("root")) == [
        Path("root/hello"),
        Path("root/world"),
        Path("root/../different/directory"),
    ]
