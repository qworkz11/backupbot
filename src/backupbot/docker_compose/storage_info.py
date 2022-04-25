#!/usr/bin/env python3

from dataclasses import dataclass
from typing import List

from backupbot.abstract.storage_info import AbstractStorageInfo
from backupbot.data_structures import HostDirectory, Volume


@dataclass
class DockerComposeService(AbstractStorageInfo):
    name: str
    container_name: str
    image: str
    hostname: str
    volumes: List[Volume]
    bind_mounts: List[HostDirectory]
