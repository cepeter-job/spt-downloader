"""Approved Indonesian UI copy; developer XML is compiled for frozen builds."""

import sys
from types import MappingProxyType
from typing import Mapping

from .ui_text_schema import COUNT_PARAMETERS

if getattr(sys, 'frozen', False):
    # PyInstaller bundles generated Python constants, never an external XML file.
    from ._ui_copy_generated import STRINGS as _STRINGS
else:
    # Local source runs immediately reflect developer edits to the repository XML.
    from .ui_text_xml import load_strings
    _STRINGS = load_strings()

COPY: Mapping[str, str] = MappingProxyType(_STRINGS)
STAGE_LABELS = tuple(COPY[key] for key in (
    'stage.authentication', 'stage.inventory', 'stage.details', 'stage.results',
))
_COUNT_PARAMETERS = COUNT_PARAMETERS


def copy_text(key: str, **values: str | int) -> str:
    """Reject broken templates rather than rendering misleading counts."""
    template = COPY[key]
    expected = _COUNT_PARAMETERS.get(key, frozenset())
    if values.keys() != expected:
        raise ValueError('Copy parameters do not match the named template')
    for value in values.values():
        if type(value) is not int:
            raise TypeError('Copy counters must be integers, not booleans or text')
        if value < 0:
            raise ValueError('Copy counters cannot be negative')
    return template.format(**values)
