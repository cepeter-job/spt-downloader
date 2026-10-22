"""Read only the public, immutable identity embedded by the trusted build."""
import json
import os
from pathlib import Path
import re
import stat
import sys


def resource_root():
    return Path(sys._MEIPASS) if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent.parent


def read_build_info(root=None):
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
            value = json.loads(stream.read(4097))
        if (not isinstance(value, dict) or set(value) != {'schema', 'commit', 'run_id', 'run_attempt'}
                or type(value['schema']) is not int or value['schema'] != 1
                or not isinstance(value['commit'], str) or not re.fullmatch(r'[0-9a-f]{40}', value['commit'])
                or not isinstance(value['run_id'], str) or not re.fullmatch(r'[1-9][0-9]{0,23}', value['run_id'])
                or type(value['run_attempt']) is not int or not 1 <= value['run_attempt'] <= 1000000):
            return None
        return value
    except (OSError, ValueError, TypeError, RecursionError):
        return None


def diagnostic_fields():
    identity = read_build_info()
    if identity is None:
        return {'build_commit': 'unknown'}
    return {'build_commit': identity['commit'], 'build_run_id': identity['run_id'],
            'build_run_attempt': identity['run_attempt']}
