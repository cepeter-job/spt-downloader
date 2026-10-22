"""Bind desktop checkpoint ordinals to the exact approved inventory subset."""
import hashlib
import json
from pathlib import Path
from uuid import uuid4

from coretax_browser import _atomic_checkpoint
from coretax_exporter import validate_scope
from coretax_json import validate_detail_source
from coretax_pdf import _directories
from spt_desktop.interaction import select_records
from spt_desktop.output_windows import DirectoryGuard, locked_file, move_no_replace


_IDENTITY_FIELDS = ('key', 'record_id', 'meta', 'list_url', 'list_page',
                    'list_page_size', 'row_position', 'source_status')
_MAX_BYTES = 128 * 1024 * 1024


def _read(path):
    with locked_file(path) as stream:
        raw = stream.read(_MAX_BYTES + 1)
    if len(raw) > _MAX_BYTES:
        raise ValueError('Resume inventory or selection exceeds the supported size')
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError('Invalid resume inventory or selection')
    return value, hashlib.sha256(raw).hexdigest()


def _scope(run):
    validate_scope(run.get('npwp'), run.get('year'))
    if run.get('year_basis') not in ('period', 'submission'):
        raise ValueError('Invalid resume scope basis')
    return {key: run[key] for key in ('npwp', 'year', 'year_basis')}


def _selected(inventory, saved, digest):
    if (set(saved) != {'schema', 'inventory_sha256', 'scope', 'inventory_count',
                       'selected_ids', 'detail_source'}
            or type(saved.get('schema')) is not int or saved['schema'] != 1
            or saved.get('inventory_sha256') != digest or saved.get('scope') != _scope(inventory)
            or type(saved.get('inventory_count')) is not int
            or not isinstance(inventory.get('records'), list)
            or saved['inventory_count'] != len(inventory['records'])):
        raise ValueError('Resume inventory changed or selection scope is invalid')
    try:
        validate_detail_source(saved['detail_source'])
        selected = select_records(inventory, saved['selected_ids'])
    except (ValueError, TypeError) as error:
        raise ValueError('Invalid saved selection or capture source mode') from error
    if selected['selection']['selected_ids'] != saved['selected_ids']:
        raise ValueError('Saved selection order differs from the source inventory')
    return selected


def persist_selection(run, folder, *, detail_source='dom'):
    """Write before detail 1; never replace an existing selection with a wider one."""
    validate_detail_source(detail_source)
    folder = Path(folder).absolute()
    with DirectoryGuard() as guard:
        guard.include(_directories(folder))
        inventory, digest = _read(folder / 'inventory.json')
        selection = run.get('selection')
        if (not isinstance(selection, dict)
                or set(selection) != {'inventory_count', 'selected_ids'}
                or _scope(run) != _scope(inventory)):
            raise ValueError('Desktop selection must belong to the saved inventory scope')
        saved = {'schema': 1, 'inventory_sha256': digest, 'scope': _scope(inventory),
                 **selection, 'detail_source': detail_source}
        expected = _selected(inventory, saved, digest)
        records = run.get('records')
        if (not isinstance(records, list) or len(records) != len(expected['records'])
                or any(any(actual.get(key) != original.get(key) for key in _IDENTITY_FIELDS)
                       for actual, original in zip(records, expected['records']))):
            raise ValueError('Selected record identities differ from the inventory')
        destination = folder / 'selection.json'
        if destination.exists() or destination.is_symlink():
            prior, _ = _read(destination)
            if prior != saved:
                raise ValueError('Existing selection scope or capture source cannot be replaced')
            return
        temporary = folder / f'.selection-{uuid4().hex}.tmp'
        _atomic_checkpoint(temporary, saved)
        owned = temporary.lstat()
        try:
            try:
                move_no_replace(temporary, destination)
            except FileExistsError as error:
                prior, _ = _read(destination)
                if prior != saved:
                    raise ValueError('Concurrent selection scope cannot be replaced') from error
        finally:
            if temporary.exists():
                current = temporary.lstat()
                if (current.st_dev, current.st_ino) == (owned.st_dev, owned.st_ino):
                    temporary.unlink()


def load_resume_inventory(folder, *, detail_source=None):
    """Return the original ordered subset and its checkpoint-compatible mode."""
    if detail_source is not None:
        validate_detail_source(detail_source)
    folder = Path(folder).absolute()
    with DirectoryGuard() as guard:
        guard.include(_directories(folder))
        inventory, digest = _read(folder / 'inventory.json')
        _scope(inventory)
        manifest = folder / 'selection.json'
        if manifest.exists() or manifest.is_symlink():
            saved, _ = _read(manifest)
            selected = _selected(inventory, saved, digest)
            if detail_source is not None and detail_source != saved['detail_source']:
                raise ValueError('Resume capture source mode must match the saved selection')
            return selected, saved['detail_source']
        aggregate = folder / 'run.json'
        legacy = _read(aggregate)[0] if aggregate.exists() or aggregate.is_symlink() else {}
        if 'selection' in legacy or any(folder.glob('.interaction-*.request.json')):
            raise ValueError('Legacy desktop selection has no manifest; rebuild offline or start a new job')
        return inventory, detail_source or 'dom'
