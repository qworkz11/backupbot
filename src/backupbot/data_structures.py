#!/usr/bin/env python3

"""Module that provides data structures needed throughout the project."""

from dataclasses import dataclass
from functools import total_ordering
from pathlib import Path
from typing import Any


@dataclass
class Volume:
    name: str  # (global) volume name
    mount_point: Path  # mount point inside the container


@dataclass
class HostDirectory:
    path: Path  # path on host
    mount_point: Path  # mount point inside the container


@dataclass
@total_ordering
class FileVersion:
    major: int
    minor: int

    def increase_major(self) -> None:
        self.major += 1

    def increase_minor(self) -> None:
        self.minor += 1

    def decrease_major(self) -> None:
        if self.major == 0:
            raise NotImplementedError(f"Cannot decrease major version below 0: '{self.major}-{self.minor}'.")
        self.major -= 1

    def decrease_minor(self) -> None:
        if self.minor == 0:
            raise NotImplementedError(f"Cannot decrease minor version below 0: '{self.major}-{self.minor}'.")
        self.minor -= 1

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, FileVersion):
            return False

        return self.major == other.major and self.minor == other.minor

    def __lt__(self, other: Any) -> bool:
        if not isinstance(other, FileVersion):
            raise NotImplementedError(f"Unable to compare {type(self)} with objects of type '{type(other)}'.")

        if self.major < other.major:
            return True

        return self.minor < other.minor

    def __gt__(self, other: Any) -> bool:
        if not isinstance(other, FileVersion):
            raise NotImplementedError(f"Unable to compare {type(self)} with objects of type '{type(other)}'.")

        if self.major > other.major:
            return True

        return self.minor > other.minor
