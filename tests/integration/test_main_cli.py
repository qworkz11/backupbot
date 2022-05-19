from pathlib import Path
from subprocess import CompletedProcess, run
from typing import Callable

import pytest
import os


@pytest.mark.docker
def test_backupbot_backs_up_bind_mounts(
    tmp_path: Path,
    running_docker_compose_project: Callable,
    sample_docker_compose_project_dir: Path,
) -> None:
    backup_config = sample_docker_compose_project_dir.joinpath("bind_mount_backup_scheme.json")
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

    target_dir = tmp_path.joinpath("bind_mount_service", "bind_mounts", "bind_mount")

    assert target_dir.is_dir()
    assert len(list(target_dir.iterdir())) == 1  # one backup file


def test_backupbot_backs_up_mounted_volues(
    tmp_path: Path, running_docker_compose_project: Callable, sample_docker_compose_project_dir: Path
) -> None:
    backup_config = sample_docker_compose_project_dir.joinpath("volume_backup_scheme.json")
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

    target_dir = tmp_path.joinpath("volume_service", "volumes", "test_volume")

    assert target_dir.is_dir()
    assert len(list(target_dir.iterdir())) == 1  # one backup file
