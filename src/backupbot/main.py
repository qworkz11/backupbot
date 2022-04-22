#!/usr/bin/env python3

"""A dummy main module."""

import sys
from argparse import ArgumentParser
from pathlib import Path
from typing import Optional, Tuple

from backupbot.backupbot import BackupBot
from backupbot.logger import logger


def parse_args() -> Tuple[str, Path, Path, Optional[Path]]:
    parser = ArgumentParser()

    parser.add_argument("adapter", choices=["docker-compose"], help="Specifies the backup adapter to use.")
    parser.add_argument("destination", help="Absolute path to backup destination root directory.")
    parser.add_argument("backup_config", help="Path to the backup scheme configuration file (.json).")
    parser.add_argument("-r", "--root", help="Path to directory to backup.")

    args = parser.parse_args()

    if args.root:
        args.root = Path(args.root)

    return args.adapter, Path(args.destination), Path(args.backup_config), args.root


def main() -> None:
    adapter, destination_path, backup_config_path, root_path = parse_args()

    if root_path is None:
        root_path = Path.cwd()

    bub = BackupBot(
        root=root_path,
        destination=destination_path,
        backup_config=backup_config_path,
        container_runtime_environment=adapter,
    )

    try:
        bub.run()
    except RuntimeError:
        logger.error("Exited with an error.")
        sys.exit(1)
    logger.info("Exited with success.")
    sys.exit(0)


if __name__ == "__main__":
    main()
