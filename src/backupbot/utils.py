#!/usr/bin/env pyhon3

"""Backupbot utility functions."""

import subprocess
from pathlib import Path
from typing import Any, Dict, List, Tuple, Union

from yaml import Loader, load


def load_compose_file(file: Path) -> Dict:
    """Loads a docker-compose.yaml and returns it as a dictionary.

    Args:
        file (Path): Absolute path.

    Raises:
        FileNotFoundError: If the file does not exist.

    Returns:
        Dict: Components of the docker-compose.yaml.
    """
    if not file.exists():
        raise FileNotFoundError(f"Unable to load Dockerfile '{file}': File does not extist.")

    with open(file.absolute(), "r") as file:
        content = load(file, Loader=Loader)

    return content


def get_volume_path(volume_string: str) -> str:
    """Returns the relative path of the volume as it is specified in the compose file.

    Args:
        volume_string (str): Docker volume.

    Returns:
        str: Relative path of the volume.
    """
    return volume_string.split(":")[0]


def absolute_path(relative_bind_mounts: List[str], root: Path) -> List[Path]:
    """Retuns a list of absolute paths of the specified bind mounts.

    Args:
        relative_bind_mounts (List[str]): List of relative bind mount paths.
        root (Path): Root directory of all volumes.

    Returns:
        List[Path]: List of absolute paths.
    """
    return [root.joinpath(get_volume_path(relative_path)) for relative_path in relative_bind_mounts]


def tar_directory(directory: Path, tar_name: str, destination: Path) -> None:
    """Tar-compresses the specified directory.

    Args:
        directory (Path): The directory to tar-compress.
        tar_name (str): Target name of the tar file (will be combined with a timestamp).
        destination (Path): Target directory for the tar file.

    Raises:
        NotADirectoryError: If 'directory' is invalid.
        NotADirectoryError: If 'destination' is invalid.
        RuntimeError: In case tar returns an error.
    """
    if not directory.exists():
        raise NotADirectoryError(f"Directory to compress does not exist: '{directory}'.")
    if not destination.exists():
        raise NotADirectoryError(f"Target directory does not exist: '{destination}'.")

    tar_file_path = destination.joinpath(f"{tar_name}.tar.gz")
    cmd_args = ("tar", "-czf", tar_file_path.absolute(), directory.absolute())

    proc_return: subprocess.CompletedProcess = subprocess.run(cmd_args)

    if proc_return.returncode != 0:
        raise RuntimeError(f"tar exited with an error: '{proc_return.stderr}'.")
