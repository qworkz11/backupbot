from pathlib import Path
from subprocess import CompletedProcess, run
from typing import Callable

import pytest


@pytest.mark.docker
def test_backupbot_backs_up_bind_mounts(
    tmp_path: Path,
    running_docker_compose_project: Callable,
    sample_docker_compose_project_dir: Path,
) -> None:
    backup_config = sample_docker_compose_project_dir.joinpath("bind_mount_backup_scheme.json")
    compose_file = sample_docker_compose_project_dir.joinpath("docker-compose.yaml")

    args = (
        "backupbot",
        "-r",
        sample_docker_compose_project_dir.absolute(),
        "docker-compose",
        tmp_path.absolute(),
        backup_config.absolute(),
    )

    with running_docker_compose_project(compose_file) as _:
        proc: CompletedProcess = run(args, capture_output=True)

    assert proc.returncode == 0
    assert "Exited with success." in str(proc.stdout)

    assert tmp_path.joinpath("bind_mount_service").is_dir()
    assert len(list(tmp_path.iterdir())) == 1
