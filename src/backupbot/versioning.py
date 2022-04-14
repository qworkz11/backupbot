"""File versioning module."""

import re
from pathlib import Path
from typing import List, Pattern, Tuple, Union

from backupbot.data_structures import FileVersion

VERSIONING_TO_PATTERN = {"d-d": re.compile("\d-\d\.")}


def update_version_numbers(
    directory: Path, file_ending: str, version_pattern: Pattern[str] = VERSIONING_TO_PATTERN["d-d"], major: bool = False
) -> List[Tuple[Path, Path]]:
    """Updates all files (versions) in the specifies directory matching the specified file ending.

    The renaming is done on the file system. If major is set to True, a version '0-1' is updated to '1-1'. If not, the
    minor version is updated: '0-2'.

    Note: When there is no new file, thus the versions do not have to be updated, the files are still renamed, using
    their old names. As this situation only occurs once (when a new file is added to the versioning system) this
    behavior is acceptable.

    Args:
        directory (Path): The files' parent directory.
        file_ending (str): File type.
        version_pattern (Pattern[str], optional): Version pattern. Defaults to VERSIONING_TO_PATTERN["d-d"].
        major (bool, optional): Whether to update the major or minor version. Defaults to False.

    Raises:
        NotADirectoryError: In case of an invalid directory path.

    Returns:
        List[Tuple[Path, Path]]: Pairs of old and new file paths. The old paths do not exist anymore afterwards.
    """
    if not directory.is_dir():
        raise NotADirectoryError(f"Error updating file versions in '{directory}': Folder does not exist.")

    files: List[Path] = [file for file in directory.iterdir() if file.is_file() and file.name.endswith(file_ending)]
    old_new_pairs: List[Tuple[Path, Path]] = create_target_names(files, file_ending, version_pattern, major)

    for old_file, new_file in old_new_pairs:
        old_file.rename(new_file)

    return old_new_pairs


def create_target_names(
    files: List[Path],
    file_ending: str,
    version_pattern: Pattern[str] = VERSIONING_TO_PATTERN["d-d"],
    major: bool = False,
) -> List[Tuple[Path, Path]]:
    """Creates a path with an updated version number if necessary for each file in the list.

    Each tuple in the returned list contains the old path and the new path on the 0th and 1st index, respectively. If no
    new file is detected (aka the versions do not need to be updated) the unchanged path is returned.
    The order of files is determined based on their creation time. This means that the oldest file gets the highest
    version number, the youngest gets the lowest.

    Note: The files are not renamed, this needs to be done separately.

    Args:
        files (List[Path]): List of files.
        file_ending (str): File type.
        version_pattern (Pattern[str], optional): Version regex pattern. Defaults to VERSIONING_TO_PATTERN["d-d"].
        major (bool, optional): Whether to update the major or minor version. Defaults to False.

    Returns:
        List[Tuple[Path, Path]]: Pairs of old and new paths.
    """
    num_files = len(files)
    if num_files == 0:
        return []

    files = sorted(files, key=lambda x: x.lstat().st_ctime)  # sort from oldest to newest
    version = get_max_version_number(files)

    if version is None:
        version = FileVersion(0, 0)
    else:
        if major:
            version.major = len(files) - 1
        else:
            version.minor = len(files) - 1

    old_new_pairs = []
    for i in range(num_files):
        file = files[i]

        if not re.search(version_pattern, file.name):
            # this must be a newly created file without version number
            updated_name = file.name.replace(f".{file_ending}", f"-{version.major}-{version.minor}.{file_ending}")
        else:
            updated_name = re.sub(version_pattern, f"{version.major}-{version.minor}.", file.name)

        old_new_pairs.append((file, file.parent.joinpath(updated_name)))

        if i < num_files - 1:
            if major:
                version.decrease_major()
            else:
                version.decrease_minor()

    return old_new_pairs


def get_max_version_number(
    files: List[Path], version_pattern: Pattern[str] = VERSIONING_TO_PATTERN["d-d"]
) -> Union[FileVersion, None]:
    """Returns the highest file version matching the specified pattern.

    Args:
        files (List[Path]): List of files.
        version_pattern (Pattern[str], optional): Version pattern to match. Defaults to VERSIONING_TO_PATTERN["d-d"].

    Returns:
        Union[FileVersion, None]: File version or None if none could be found.
    """
    max = None
    for file in files:
        version = get_file_version(file.name, version_pattern)

        if version is None:
            continue

        if max is None:
            max = version
            continue

        if version > max:
            max = version

    return max


def get_file_version(
    file_name: str, version_pattern: Pattern[str] = VERSIONING_TO_PATTERN["d-d"]
) -> Union[FileVersion, None]:
    """Returns the version of the file according to the specified pattern.

        >>> get_file_version('test-0-1.txt')
        FileVersion(major=0, minor=1)
        >>> get_file_version('test.txt') # None

    Args:
        file_name (str): Name of the file.
        version_pattern (Pattern[str], optional): Regex pattern to match. Defaults to VERSIONING_TO_PATTERN["d-d"].

    Raises:
        NotImplementedError: In case of an unknown version pattern.

    Returns:
        Union[FileVersion, None]: File version or None.
    """
    if version_pattern == VERSIONING_TO_PATTERN["d-d"]:
        matches = re.findall(version_pattern, file_name)
        if not matches:
            return None
        version_string: str = matches[::-1][0]  # last match
        major_minor = [character for character in version_string if character.isnumeric()]

        return FileVersion(int(major_minor[0]), int(major_minor[1]))

    raise NotImplementedError(f"Unknown version pattern: '{version_pattern}'.")
