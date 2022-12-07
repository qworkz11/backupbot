import os
import sys
from pathlib import Path
from subprocess import CompletedProcess, run
from typing import Callable

import pytest


@pytest.mark.docker
def test_backupbot_backup(
    tmp_path: Path,
    running_docker_compose_project: Callable,
    sample_docker_compose_project_dir: Path,
) -> None:
    backup_config = sample_docker_compose_project_dir.joinpath("combined_backup_scheme.json")
    compose_file = sample_docker_compose_project_dir.joinpath("docker-compose.yaml")

    env = os.environ.copy()

    args = (
        "backupbot",
        "-r",
        sample_docker_compose_project_dir.absolute(),
        "docker-compose",
        tmp_path.absolute(),
        backup_config.absolute(),
    )

    with running_docker_compose_project(compose_file) as _:
        proc: CompletedProcess = run(args, capture_output=True, env=env)

    assert proc.returncode == 0
    assert "Exited with success." in str(proc.stdout)

    bind_mount_dir = tmp_path.joinpath("bind_mount_service", "bind_mounts", "bind_mount")
    assert bind_mount_dir.is_dir()
    assert len(list(bind_mount_dir.iterdir())) == 1  # one backup file

    volume_dir = tmp_path.joinpath("volume_service", "volumes", "test_volume")
    assert volume_dir.is_dir()
    assert len(list(volume_dir.iterdir())) == 1  # one backup file

    mysql_dir = tmp_path.joinpath("mysql_service", "mysql_databases", "test_database")
    assert mysql_dir.is_dir()
    assert len(list(mysql_dir.iterdir())) == 1


def test_bub_backup(
    tmp_path: Path,
    running_docker_compose_project: Callable,
    sample_docker_compose_project_dir: Path,
) -> None:
    backup_config = sample_docker_compose_project_dir.joinpath("combined_backup_scheme.json")
    compose_file = sample_docker_compose_project_dir.joinpath("docker-compose.yaml")

    env = os.environ.copy()

    args = (
        "bub",
        "-r",
        sample_docker_compose_project_dir.absolute(),
        "docker-compose",
        tmp_path.absolute(),
        backup_config.absolute(),
    )

    with running_docker_compose_project(compose_file) as _:
        proc: CompletedProcess = run(args, capture_output=True, env=env)

    assert proc.returncode == 0
    assert "Exited with success." in str(proc.stdout)


def test_backupbot_confgen(tmp_path: Path, sample_docker_compose_project_dir: Path) -> None:
    args = (
        "backupbot-confgen",
        "-r",
        sample_docker_compose_project_dir,
        "-o",
        "backup-conf.json",
        "-d",
        tmp_path,
        "docker-compose",
    )

    proc: CompletedProcess = run(args, capture_output=True, env=os.environ.copy())

    assert proc.returncode == 0
    assert "Exited with success." in str(proc.stdout)


def test_bub_confgen(tmp_path: Path, sample_docker_compose_project_dir: Path) -> None:
    args = (
        "bub-confgen",
        "-r",
        sample_docker_compose_project_dir,
        "-o",
        "backup-conf.json",
        "-d",
        tmp_path,
        "docker-compose",
    )

    proc: CompletedProcess = run(args, capture_output=True, env=os.environ.copy())

    assert proc.returncode == 0
    assert "Exited with success." in str(proc.stdout)
