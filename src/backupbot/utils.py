#!/usr/bin/env pyhon3

"""Backupbot utility functions."""

from pathlib import Path
from typing import Any, Dict, List, Tuple, Union

from yaml import Loader, load


def load_dockerfile(file: Path) -> Dict:
    if not file.exists():
        raise FileNotFoundError(f"Unable to load Dockerfile '{file}': File does not extist.")

    with open(file.absolute(), "r") as file:
        content = load(file, Loader=Loader)

    return content


def extract_volumes(parsed_docker_file: Dict[str, Any]) -> Tuple[Union[List[str], None], Union[List[str], None]]:
    if not "services" in parsed_docker_file:
        return None, None

    named_volumes = []
    bind_mounts = []

    for _, service_attributes in parsed_docker_file["services"].items():
        if "volumes" in service_attributes:
            for volume in service_attributes["volumes"]:
                if volume.startswith("."):
                    bind_mounts.append(volume)
                else:
                    named_volumes.append(volume)

    return named_volumes, bind_mounts


def get_volume_path(volume_string: str) -> str:
    return volume_string.split(":")[0]


def absolute_paths(relative_bind_mounts: List[str], root: Path) -> List[Path]:
    return [root.joinpath(get_volume_path(relative_path)) for relative_path in relative_bind_mounts]
