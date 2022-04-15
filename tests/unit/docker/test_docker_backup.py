from pathlib import Path

import backupbot.docker.docker_backup
import pytest
from backupbot.data_structures import HostDirectory, Volume
from backupbot.docker.backup_tasks import (
    DockerBindMountBackupTask,
    DockerMySQLBackupTask,
    DockerVolumeBackupTask,
)
from backupbot.docker.docker_backup import DockerBackupAdapter
from pytest import MonkeyPatch


def test_docker_backup_adapter_collect_storage_info(tmp_path: Path) -> None:
    tmp_path.joinpath("services", "data").mkdir(parents=True)
    tmp_path.joinpath("services", "other_data", "more_data").mkdir(parents=True)

    tmp_path.joinpath("services", "docker-compose.yaml").touch()
    tmp_path.joinpath("services", "data", "docker-compose.yaml").touch()
    tmp_path.joinpath("services", "other_data", "more_data", "docker-compose.yaml").touch()

    dba = DockerBackupAdapter()

    files = dba.collect_storage_info(tmp_path)

    assert not set(files).difference(
        [
            tmp_path.joinpath("services", "docker-compose.yaml"),
            tmp_path.joinpath("services", "data", "docker-compose.yaml"),
            tmp_path.joinpath("services", "other_data", "more_data", "docker-compose.yaml"),
        ]
    )
    assert len(files) == len(set(files))


def test_docker_backup_adapter__parse_compose_file_parses_docker_compose_file_correctly(
    tmp_path: Path, dummy_docker_compose_file: Path
) -> None:
    dba = DockerBackupAdapter()

    assert dba._parse_compose_file(file=dummy_docker_compose_file, root_directory=tmp_path) == {
        "first_service": {
            "container_name": "service1",
            "ports": ["80:80", "443:443"],
            "bind_mounts": [
                HostDirectory(tmp_path.joinpath("service1_bind_mount1"), Path("/service1/bind_mount1/path"))
            ],
            "volumes": [
                Volume("service1_volume1", Path("/service1/volume1/path")),
                Volume("service1_volume2", Path("/service1/volume2/path")),
            ],
        },
        "second_service": {
            "image": "source/image",
            "container_name": "service2",
            "bind_mounts": [
                HostDirectory(tmp_path.joinpath("service2_bind_mount1"), Path("/service2/bind_mount1/path")),
                HostDirectory(tmp_path.joinpath("service2_bind_mount2"), Path("/service2/bind_mount2/path")),
            ],
            "volumes": [
                Volume("service2_volume1", Path("/service2/volume1/path")),
                Volume("service2_volume2", Path("/service2/volume2/path")),
            ],
        },
    }


def test_docker_backup_adapter_parse_backup_scheme(dummy_backup_scheme_file: Path) -> None:
    dba = DockerBackupAdapter()

    assert dba.parse_backup_scheme(dummy_backup_scheme_file) == {
        "service1": [
            DockerBindMountBackupTask(["all"]),
            DockerVolumeBackupTask(["service1_volume1", "service1_volume2"]),
            DockerMySQLBackupTask(database="test_database", user="test_user", password="test_password"),
        ],
        "service2": [DockerVolumeBackupTask(["service2_volume2"]), DockerBindMountBackupTask(["service2_mount3"])],
    }


def test_docker_backup__parse_compose_file_raises_error_if_no_services_key_in_file(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    dba = DockerBackupAdapter()

    monkeypatch.setattr(backupbot.docker.docker_backup, "load_yaml_file", lambda *_, **__: {})

    with pytest.raises(RuntimeError):
        dba._parse_compose_file(None, tmp_path)  # type: ignore


def test_docker_backup_parse_storage_info_raises_error_when_multiple_files_are_speccified(tmp_path: Path) -> None:
    dba = DockerBackupAdapter()

    with pytest.raises(RuntimeError):
        dba.parse_storage_info([Path("/first/path"), Path("/second/path")], tmp_path)


def test_docker_backup_parse_storage_info_returns_dictionary(tmp_path: Path, dummy_docker_compose_file: Path) -> None:
    dba = DockerBackupAdapter()

    result = dba.parse_storage_info([dummy_docker_compose_file], tmp_path)

    assert isinstance(result, dict)
    assert "first_service" in result.keys()
    assert "second_service" in result.keys()


def test_docker_backup__parse_volume_returns_correctly_parsed_volume_names_and_mount_points() -> None:
    dba = DockerBackupAdapter()

    assert dba._parse_volume("volume:/container/mount/point") == ("volume", "/container/mount/point")
    assert dba._parse_volume("./bind_mount:/container/mount/point") == ("./bind_mount", "/container/mount/point")


def test_docker_backup__parse_volume_raises_error_for_invalid_volume_statement() -> None:
    dba = DockerBackupAdapter()

    with pytest.raises(ValueError):
        dba._parse_volume("invalid_volume_string")


def test_docker_backup__make_backup_name_creates_correct_name() -> None:
    dba = DockerBackupAdapter()

    assert dba._make_backup_name(Path("/path/to/data"), "data_container") == "data_container-data"
    assert dba._make_backup_name(Path("directory"), "data_container") == "data_container-directory"
