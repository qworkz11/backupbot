#!/usr/bin/env python3

"""Testing fixtures."""

from pathlib import Path

import pytest


@pytest.fixture
def dummy_docker_compose_file() -> Path:
    """Returns the path to the dummy Dockerfile located in /tests/utils.

    Returns:
        Path: Path instance.
    """
    return Path(__file__).parent.joinpath("resources", "docker-compose.yaml")


@pytest.fixture
def dummy_backup_scheme_file() -> Path:
    """Returns the path to the dummy Dockerfile located in /tests/utils.

    Returns:
        Path: Path instance.
    """
    return Path(__file__).parent.joinpath("resources", "docker_backup_scheme.json")


@pytest.fixture
def dummy_bind_mount_dir() -> Path:
    """Returns the path to a dummy folder structure containing dummy text files.

    Returns:
        Path: _description_
    """
    return Path(__file__).parent.joinpath("resources", "sample_bind_mount_dir")
