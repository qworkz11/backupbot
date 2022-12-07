#!/usr/bin/env python3

"""Main backupbot module, containing the main CLI entry point."""

import sys
from argparse import ArgumentParser
from pathlib import Path
from typing import Optional, Tuple

from backupbot.backupbot import BackupBot
from backupbot.logger import logger


def parse_args_backup() -> Tuple[str, Path, Path, Optional[Path]]:
    """Parses CLI parameters.

    Returns:
        Tuple[str, Path, Path, Optional[Path]]: Adapter type, destination path instance, backup scheme config file path,
            source root directory.
    """
    parser = ArgumentParser()

    parser.add_argument("adapter", choices=["docker-compose"], help="Specifies the backup adapter to use.")
    parser.add_argument("destination", help="Absolute path to backup destination root directory.")
    parser.add_argument("backup_config", help="Path to the backup scheme configuration file (.json).")
    parser.add_argument("-r", "--root", help="Path to service directory to backup.")

    args = parser.parse_args()

    if args.root:
        args.root = Path(args.root)

    return args.adapter, Path(args.destination), Path(args.backup_config), args.root


def parse_args_generate() -> Tuple[str, Path, Path, Optional[Path]]:
    parser = ArgumentParser()

    parser.add_argument("adapter", choices=["docker-compose"], help="Specifies the backup adapter to use.")
    parser.add_argument("-r", "--root", help="Path to service directory to backup.")
    parser.add_argument("-o", "--out-name", help="Backup configuration file name (must end with .json).")
    parser.add_argument("-d", "--out-directory", help="Target directory for the generated files.")

    args = parser.parse_args()

    if args.root:
        args.root = Path(args.root)

    if args.out_directory:
        args.out_directory = Path(args.out_directory)

    return args.adapter, args.root, args.out_name, args.out_directory


def main_backup() -> None:
    """Main backup CLI entry point."""
    adapter, destination_path, backup_config_path, root_path = parse_args_backup()

    if root_path is None:
        root_path = Path.cwd()

    bub = BackupBot(
        root=root_path,
        destination_directory=destination_path,
        backup_config=backup_config_path,
        adapter=adapter,
    )

    try:
        bub.run_backup()
    except RuntimeError as error:
        logger.error(f"Exited with an error: {error}.")
        sys.exit(1)
    logger.info("Exited with success.")
    sys.exit(0)


def main_generate_config() -> None:
    """Main CLI configuration template entry point."""
    adapter, root_path, filename, target_dir = parse_args_generate()

    if root_path is None:
        root_path = Path.cwd()

    bub = BackupBot(root=root_path, adapter=adapter, destination_directory=target_dir)

    try:
        bub.generate_backup_config(target_directory=target_dir, filename=filename)
    except RuntimeError as error:
        logger.error(f"Exited with an error: {error}.")
        sys.exit(1)
    logger.info("Exited with success.")
    sys.exit(0)
