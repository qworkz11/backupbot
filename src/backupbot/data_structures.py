from dataclasses import dataclass
from pathlib import Path


@dataclass
class Volume:
    name: str
    mount_point: Path


@dataclass
class HostDirectory:
    path: Path
    mount_point: Path
