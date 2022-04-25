from abc import ABC
from dataclasses import dataclass


@dataclass
class AbstractStorageInfo(ABC):
    name: str
