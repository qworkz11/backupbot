from pathlib import Path

import backupbot.backup_adapter.docker_backup
import pytest
from backupbot.backup_adapter.docker_backup import DockerBackupAdapter
from backupbot.data_structures import HostDirectory, Volume
from pytest import MonkeyPatch


def test_docker_backup_adapter__parse_compose_file_parses_docker_compose_file_correctly(
    tmp_path: Path, dummy_docker_compose_file: Path
) -> None:
    dba = DockerBackupAdapter()

    assert dba._parse_compose_file(file=dummy_docker_compose_file, root_directory=tmp_path) == {
        "first_service": {
            "host_directories": [HostDirectory(tmp_path.joinpath("bind_mount1"), Path("/container1/path"))],
            "volumes": [Volume("named_volume1", Path("/another/container1/path"))],
        },
        "second_service": {
            "host_directories": [HostDirectory(tmp_path.joinpath("bind_mount2"), Path("/another/container2/path"))],
            "volumes": [Volume("named_volume2", Path("/container2/path"))],
        },
    }


def test_docker_backup__parse_compose_file_raises_error_if_no_services_key_in_file(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    dba = DockerBackupAdapter()

    monkeypatch.setattr(backupbot.backup_adapter.docker_backup, "load_yaml_file", lambda *_, **__: {})

    with pytest.raises(RuntimeError):
        dba._parse_compose_file(None, tmp_path)


def test_docker_backup_parse_config_raises_error_when_multiple_files_are_speccified(tmp_path: Path) -> None:
    dba = DockerBackupAdapter()

    with pytest.raises(RuntimeError):
        dba.parse_config([Path("/first/path"), Path("/second/path")], tmp_path)


def test_docker_backup_parse_config_returns_dictionary(tmp_path: Path, dummy_docker_compose_file: Path) -> None:
    dba = DockerBackupAdapter()

    result = dba.parse_config([dummy_docker_compose_file], tmp_path)

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


def test_docker_backup_backup_host_directory_backs_up_data_in_extisting_target_directory(tmp_path: Path) -> None:
    dba = DockerBackupAdapter()

    tmp_path.joinpath("data").mkdir()
    tmp_path.joinpath("backup", "container", "bind_mounts").mkdir(parents=True)

    dba.backup_host_directory(tmp_path.joinpath("data"), tmp_path.joinpath("backup"), "container")

    assert tmp_path.joinpath("backup", "container", "bind_mounts", "container-data.tar.gz").is_file()


def test_docker_backup_backup_host_directory_creates_folder_structure_if_not_exitsing(tmp_path: Path) -> None:
    dba = DockerBackupAdapter()

    tmp_path.joinpath("data").mkdir()
    tmp_path.joinpath("backup").mkdir(parents=True)

    dba.backup_host_directory(tmp_path.joinpath("data"), tmp_path.joinpath("backup"), "container")

    assert tmp_path.joinpath("backup", "container", "bind_mounts", "container-data.tar.gz").is_file()
