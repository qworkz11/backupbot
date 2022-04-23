from pathlib import Path
from typing import Callable, List
from unicodedata import bidirectional

import backupbot.docker_compose.backup
import pytest
from backupbot.data_structures import HostDirectory, Volume
from backupbot.docker_compose.backup import DockerBackupAdapter
from backupbot.docker_compose.backup_tasks import (
    DockerBindMountBackupTask,
    DockerMySQLBackupTask,
    DockerVolumeBackupTask,
)
from backupbot.docker_compose.storage_info import DockerComposeService
from docker import DockerClient
from pytest import MonkeyPatch


def test_docker_backup_adapter_discover_config_files(tmp_path: Path) -> None:
    tmp_path.joinpath("services", "data").mkdir(parents=True)
    tmp_path.joinpath("services", "other_data", "more_data").mkdir(parents=True)

    tmp_path.joinpath("services", "other_data", "more_data", "docker-compose.yaml").touch()

    dba = DockerBackupAdapter()

    files = dba.discover_config_files(tmp_path)

    assert not set(files).difference(
        [
            tmp_path.joinpath("services", "other_data", "more_data", "docker-compose.yaml"),
        ]
    )
    assert len(files) == len(set(files))


def test_docker_backup_adapter_discover_config_files_raises_error_when_more_or_less_than_one_config_file_found(
    tmp_path: Path,
) -> None:
    tmp_path.joinpath("zero_files", "data").mkdir(parents=True)
    tmp_path.joinpath("two_files", "data", "more_data").mkdir(parents=True)

    tmp_path.joinpath("two_files", "data", "docker-compose.yaml").touch()
    tmp_path.joinpath("two_files", "data", "more_data", "docker-compose.yaml").touch()

    dba = DockerBackupAdapter()

    with pytest.raises(RuntimeError):
        dba.discover_config_files(tmp_path.joinpath("zero_files"))

    with pytest.raises(RuntimeError):
        dba.discover_config_files(tmp_path.joinpath("two_files"))


def test_docker_backup_adapter__parse_compose_file_parses_docker_compose_file_correctly(
    tmp_path: Path, dummy_docker_compose_file: Path
) -> None:
    dba = DockerBackupAdapter()

    # plit these up to enable better debugging...
    parsed = dba._parse_compose_file(file=dummy_docker_compose_file, root_directory=tmp_path)
    compare = [
        DockerComposeService(
            name="first_service",
            container_name="service1",
            image="image1",
            hostname="hostname1",
            bind_mounts=[HostDirectory(tmp_path.joinpath("service1_bind_mount1"), Path("/service1/bind_mount1/path"))],
            volumes=[
                Volume("service1_volume1", Path("/service1/volume1/path")),
                Volume("service1_volume2", Path("/service1/volume2/path")),
            ],
        ),
        DockerComposeService(
            name="second_service",
            container_name="service2",
            image="source/image",
            hostname="hostname2",
            bind_mounts=[
                HostDirectory(tmp_path.joinpath("service2_bind_mount1"), Path("/service2/bind_mount1/path")),
                HostDirectory(tmp_path.joinpath("service2_bind_mount2"), Path("/service2/bind_mount2/path")),
            ],
            volumes=[
                Volume("service2_volume1", Path("/service2/volume1/path")),
                Volume("service2_volume2", Path("/service2/volume2/path")),
            ],
        ),
    ]

    assert parsed == compare


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

    monkeypatch.setattr(backupbot.docker_compose.backup, "load_yaml_file", lambda *_, **__: {})

    with pytest.raises(RuntimeError):
        dba._parse_compose_file(None, tmp_path)  # type: ignore


def test_docker_backup_parse_backup_scheme_raises_error_for_wrong_file_type(tmp_path: Path) -> None:
    dba = DockerBackupAdapter()

    file = tmp_path.joinpath("no_json.txt")
    file.touch()

    with pytest.raises(RuntimeError):
        dba.parse_backup_scheme(file)


def test_docker_backup_parse_storage_info_raises_error_when_multiple_files_are_speccified(tmp_path: Path) -> None:
    dba = DockerBackupAdapter()

    with pytest.raises(RuntimeError):
        dba.parse_storage_info([Path("/first/path"), Path("/second/path")], tmp_path)


def test_docker_backup_parse_storage_info_returns_list_of_docker_compose_services(
    tmp_path: Path, dummy_docker_compose_file: Path
) -> None:
    dba = DockerBackupAdapter()

    result = dba.parse_storage_info([dummy_docker_compose_file], tmp_path)

    assert isinstance(result, list)
    service_names = [service.name for service in result]
    assert "first_service" in service_names
    assert "second_service" in service_names


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


def test_docker_backup_stopped_system_stops_docker_compose_system(
    docker_client: DockerClient, running_docker_compose_project: Callable, sample_docker_compose_project_dir: Path
) -> None:
    compose_file = sample_docker_compose_project_dir.joinpath("docker-compose.yaml")
    storage_info = [
        DockerComposeService(
            name="bind_mount_service",
            container_name="bind_mount_service",
            image="ubuntu",
            hostname="bind_mount_service",
            volumes=[],
            bind_mounts=[],
        ),
        DockerComposeService(
            name="volume_service",
            container_name="volume_service",
            image="ubuntu",
            hostname="volume_service",
            volumes=[],
            bind_mounts=[],
        ),
        DockerComposeService(
            name="mysql_service",
            container_name="mysql_service",
            image="mysql",
            hostname="mysql_service",
            volumes=[],
            bind_mounts=[],
        ),
    ]

    with running_docker_compose_project(compose_file) as _:
        dba = DockerBackupAdapter()
        dba.config_files = [compose_file]

        with dba.stopped_system(storage_info) as __:
            containers = [container.name for container in docker_client.containers.list(filters={"status": "exited"})]
            assert "bind_mount_service" in containers
            assert "volume_service" in containers
            assert "mysql_service" in containers

        containers = [container.name for container in docker_client.containers.list(filters={"status": "running"})]
        assert "bind_mount_service" in containers
        assert "volume_service" in containers
        assert "mysql_service" in containers


def test_stopped_system_does_not_restart_system_when_it_has_not_been_running(
    sample_docker_compose_project_dir: Path, docker_client: DockerClient
) -> None:
    compose_file = sample_docker_compose_project_dir.joinpath("docker-compose.yaml")
    dba = DockerBackupAdapter()
    dba.config_files = [compose_file]
    storage_info = [
        DockerComposeService(
            name="bind_mount_service",
            container_name="bind_mount_service",
            image="ubuntu",
            hostname="bind_mount_service",
            volumes=[],
            bind_mounts=[],
        ),
        DockerComposeService(
            name="volume_service",
            container_name="volume_service",
            image="ubuntu",
            hostname="volume_service",
            volumes=[],
            bind_mounts=[],
        ),
        DockerComposeService(
            name="mysql_service",
            container_name="mysql_service",
            image="mysql",
            hostname="mysql_service",
            volumes=[],
            bind_mounts=[],
        ),
    ]

    with dba.stopped_system(storage_info) as _:
        containers = [container.name for container in docker_client.containers.list(filters={"status": "running"})]
        assert "bind_mount_service" not in containers
        assert "volume_service" not in containers
        assert "mysql_service" not in containers

    containers = [container.name for container in docker_client.containers.list(filters={"status": "running"})]
    assert "bind_mount_service" not in containers
    assert "volume_service" not in containers
    assert "mysql_service" not in containers
