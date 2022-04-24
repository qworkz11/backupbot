#!/usr/bin/env python3

"""Backupbot utility functions."""

import subprocess
from pathlib import Path
from typing import Dict, List

from yaml import Loader, load


def match_files(root: Path, pattern: str, result: List[Path]) -> None:
    """Finds all files (recursively) that match the specified pattern.

    Args:
        root (Path): Directory to start search from.
        pattern (str): Pattern to match.
        result (List[Path]): List to store found paths in.

    Raises:
        NotADirectoryError: If root is no valid directory.
    """
    if not root.exists():
        raise NotADirectoryError(
            f"Unable to locate files matching pattern '{pattern}': Directory '{root}' does not exits."
        )
    # return list(root.glob(f"**/{pattern}"))
    for file in [f for f in root.iterdir() if f.is_file()]:
        if pattern in file.name:
            result.append(file)

    directories = [file for file in root.iterdir() if file.is_dir()]
    if len(directories) == 0:
        return

    for dir in directories:
        match_files(dir, pattern, result)


def load_yaml_file(path: Path) -> Dict:
    """Loads a docker-compose.yaml and returns it as a dictionary.

    Args:
        file (Path): Absolute path.

    Raises:
        FileNotFoundError: If the file does not exist.

    Returns:
        Dict: Components of the docker-compose.yaml.
    """
    if not path.exists():
        raise FileNotFoundError(f"Unable to load Dockerfile '{path}': File does not extist.")

    with open(path.absolute(), "r") as file:
        content = load(file, Loader=Loader)

    return content


def get_volume_path(volume_string: str) -> str:
    """Returns the relative path of the volume or bind mount as it is specified in the compose file.

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


def tar_file_or_directory(file_or_directory: Path, tar_name: str, destination: Path, override: bool = False) -> Path:
    """Tar-compresses the specified file or directory.

    Args:
        directory (Path): The file or directory to tar-compress.
        tar_name (str): Target name of the tar file.
        destination (Path): Target directory for the tar file.
        override (bool): Whether or not to override an existing file. If set to False, a number will be appended to the
            tar file's name. Defaults to False.

    Raises:
        NotADirectoryError: If 'directory' is invalid.
        NotADirectoryError: If 'destination' is invalid.
        RuntimeError: In case tar returns an error.
    """
    if not file_or_directory.exists():
        raise NotADirectoryError(f"Directory to compress does not exist: '{file_or_directory}'.")
    if not destination.exists():
        raise NotADirectoryError(f"Target directory does not exist: '{destination}'.")

    tar_file_path = destination.joinpath(f"{tar_name}.tar.gz")

    if tar_file_path.exists():
        if not override:
            bare_name = tar_file_path.name.replace(".tar.gz", "")
            if "(" in bare_name:
                bare_name = bare_name.split("(")[0]
            existing_files = []
            match_files(destination, bare_name, existing_files)
            tar_file_path = destination.joinpath(f"{tar_name}({len(existing_files) - 1}).tar.gz")

    cmd_args = ("tar", "-czf", tar_file_path.absolute(), file_or_directory.absolute())

    proc_return: subprocess.CompletedProcess = subprocess.run(cmd_args)

    if proc_return.returncode != 0:
        raise RuntimeError(f"'tar' exited with an error: '{proc_return.stderr}'.")

    if not tar_file_path.is_file():
        raise RuntimeError(f"'tar' command failed: File '{tar_file_path}' was not found.")

    return tar_file_path


def path_to_string(directory: Path, num_steps: int = -1, delim: str = "-") -> str:
    """Creates a string from the specied path. Path delimiters '/' are replaced by the specified delimiter.

    Args:
        directory (Path): Path instance.
        num_steps (int, optional): Specifies how many components of the path are considered, starting from the back.
            Choosing 1 returns only the last component of the path. Defaults to -1.
        delim (str, optional): Character to use as a delimiter in the created string. Defaults to "-".

    Returns:
        str: String version of the path.
    """
    path_components = str(directory).split("/")
    if path_components[0] == "":
        path_components = path_components[1:]

    if num_steps == -1:
        return delim.join(path_components)

    start = len(path_components) - num_steps
    return delim.join(path_components[start:])
