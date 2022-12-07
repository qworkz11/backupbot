from abc import ABC
from dataclasses import asdict, dataclass
from json import dumps
from typing import Dict

from pydantic import BaseModel


class AbstractStorageInfo(BaseModel):
    name: str
