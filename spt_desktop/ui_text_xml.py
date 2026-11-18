"""Development-only reader for reviewed UI text. Never read local overrides."""

from pathlib import Path
import re
from string import Formatter
import xml.etree.ElementTree as ET  # nosec B405 - bounded developer XML, DTD/entities blocked

from .ui_text_schema import COUNT_PARAMETERS


CATALOG_FILE = Path(__file__).resolve().parent.parent / 'resources' / 'ui' / 'id-ID.xml'
_MAX_BYTES = 65536
_MAX_ENTRIES = 256
_KEY_PATTERN = re.compile(r'[a-z][a-z0-9_.]*\Z')
_FIELD_PATTERN = re.compile(r'[a-z][a-z0-9_]*\Z')
_STAGE_KEYS = frozenset({
    'stage.authentication', 'stage.inventory', 'stage.details', 'stage.results',
})


def load_strings(path: Path | None = None) -> dict[str, str]:
    """Read an exact, bounded XML format and reject ambiguous templates."""
    source = CATALOG_FILE if path is None else Path(path)
    raw = source.read_bytes()
    if len(raw) > _MAX_BYTES or b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():
        raise ValueError('Invalid UI XML structure')
    try:
        root = ET.fromstring(raw)  # nosec B314 - 64 KiB cap; no DTD/entity declarations
    except ET.ParseError as exc:
        raise ValueError('Invalid UI XML syntax') from exc
    if root.tag != 'resources' or root.attrib != {'language': 'id-ID'}:
        raise ValueError('Invalid UI XML root')
    entries: dict[str, str] = {}
    for item in root:
        if (item.tag != 'string' or set(item.attrib) != {'id'}
                or len(item) or len(entries) >= _MAX_ENTRIES):
            raise ValueError('Invalid UI XML element')
        key = item.attrib['id']
        if not _KEY_PATTERN.fullmatch(key) or key in entries:
            raise ValueError('Invalid or duplicate UI text ID')
        value = item.text or ''
        if not value.strip() or len(value) > 4096:
            raise ValueError('Empty or oversized UI text')
        try:
            fields = set()
            for _, field, spec, conversion in Formatter().parse(value):
                if field is not None:
                    if (not _FIELD_PATTERN.fullmatch(field) or spec or conversion
                            or field in fields):
                        raise ValueError('Invalid UI text placeholder')
                    fields.add(field)
        except ValueError as exc:
            raise ValueError('Invalid UI text placeholder') from exc
        if fields != COUNT_PARAMETERS.get(key, frozenset()):
            raise ValueError('UI text placeholder contract mismatch')
        entries[key] = value
    if not entries or not _STAGE_KEYS.issubset(entries):
        raise ValueError('Missing required UI text IDs')
    return entries
