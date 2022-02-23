#!/usr/bin/env python3

"""Testing fixtures."""

from pathlib import Path

import pytest


@pytest.fixture
def dummy_dockerfile_path() -> Path:
    """Returns the path to the dummy Dockerfile located in /tests/utils.

    Returns:
        Path: Path instance.
    """
    return Path(__file__).parent.joinpath("utils", "Dockerfile")
