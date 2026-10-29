"""Read only the public, immutable identity embedded by the trusted build."""
import json
import os
from pathlib import Path
import re
import stat
import sys
from typing import Literal, TypeGuard, TypedDict


class BuildInfo(TypedDict):
    """Validated public build coordinates; runtime validation remains mandatory."""
    schema: Literal[1]
    commit: str
    run_id: str
    run_attempt: int


def resource_root() -> Path:
    return Path(getattr(sys, '_MEIPASS')) if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent.parent


def is_valid_build_info(value: object) -> TypeGuard[BuildInfo]:
    """Keep produced and consumed public build coordinates within one schema."""
    return (isinstance(value, dict) and set(value) == {'schema', 'commit', 'run_id', 'run_attempt'}
            and type(value['schema']) is int and value['schema'] == 1
            and isinstance(value['commit'], str)
            and re.fullmatch(r'[0-9a-f]{40}', value['commit']) is not None
            and isinstance(value['run_id'], str)
            and re.fullmatch(r'[1-9][0-9]{0,23}', value['run_id']) is not None
            and type(value['run_attempt']) is int and 1 <= value['run_attempt'] <= 1_000_000)


def read_build_info(root: str | os.PathLike[str] | None = None) -> BuildInfo | None:
    """Invalid/unavailable metadata is unknown, never environment-supplied."""
    try:
        path = (Path(root) if root is not None else resource_root()) / 'build-info.json'
        before = path.lstat()
        if (not stat.S_ISREG(before.st_mode) or stat.S_ISLNK(before.st_mode)
                or getattr(before, 'st_file_attributes', 0) & 1024 or before.st_size > 4096):
            return None
        with path.open('rb') as stream:
            opened = os.fstat(stream.fileno())
            if (opened.st_dev, opened.st_ino, opened.st_size) != (before.st_dev, before.st_ino, before.st_size):
                return None
            value: object = json.loads(stream.read(4097))
        if not is_valid_build_info(value):
            return None
        return value
    except (OSError, ValueError, TypeError, RecursionError):
        return None


def diagnostic_fields() -> dict[str, str | int]:
    identity = read_build_info()
    if identity is None:
        return {'build_commit': 'unknown'}
    return {'build_commit': identity['commit'], 'build_run_id': identity['run_id'],
            'build_run_attempt': identity['run_attempt']}
