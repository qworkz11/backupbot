from typing import Optional


class BackupNotExistingContainerError(Exception):
    def __init__(self, msg: Optional[str] = None):
        super().__init__(msg)
