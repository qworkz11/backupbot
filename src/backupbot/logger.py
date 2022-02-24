#!/usr/bin/env python3

"""Module which sets up logging for the BackupBot."""

import logging
import sys
from pathlib import Path
from typing import List

LOGGING_PATH = Path("/var/log/backupbot")
LOG_FORMAT = "[%(asctime)s][%(name)s][%(levelname)s] %(message)s"
DEFAULT_LOG_LEVEL = logging.DEBUG

if not LOGGING_PATH.exists():
    LOGGING_PATH.mkdir(parents=True)

file_handler = logging.FileHandler(LOGGING_PATH.absolute())
stdout_handler = logging.StreamHandler(stream=sys.stdout)
formatter = logging.Formatter(LOG_FORMAT)

file_handler.setFormatter(formatter)
stdout_handler.setFormatter(formatter)

handlers: List[logging.Handler] = [file_handler, stdout_handler]

logger = logging.getLogger(__name__)

for handler in handlers:
    handler.setLevel(DEFAULT_LOG_LEVEL)
    logger.addHandler(handler)
