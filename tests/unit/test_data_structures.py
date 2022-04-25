import pytest
from backupbot.data_structures import FileVersion


def test_fileversion_equals() -> None:
    assert FileVersion(major=2, minor=1) == FileVersion(major=2, minor=1)
    assert FileVersion(major=2, minor=1) != FileVersion(major=1, minor=1)


def test_fileversion_inequalities() -> None:
    assert not FileVersion(major=2, minor=1) < FileVersion(major=2, minor=1)
    assert FileVersion(major=2, minor=1) <= FileVersion(major=2, minor=1)
    assert FileVersion(major=2, minor=0) > FileVersion(major=1, minor=1)


def test_fileversion_raises_error_for_comparisons_with_other_type() -> None:
    with pytest.raises(NotImplementedError):
        FileVersion(2, 1) > 2


def test_fileversion_increase_major() -> None:
    fversion = FileVersion(2, 1)
    fversion.increase_major()
    assert fversion == FileVersion(3, 1)


def test_fileversion_increase_minor() -> None:
    fversion = FileVersion(2, 1)
    fversion.increase_minor()
    assert fversion == FileVersion(2, 2)
