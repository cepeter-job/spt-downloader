"""User-visible copy is an explicit contract, separate from Tk and worker code."""
import ast
from pathlib import Path

import pytest


@pytest.mark.parametrize(('key', 'expected'), [
    ('app.title', 'Coretax SPT downloader : kalau bisa ribet, kenapa dibikin gampang'),
    ('app.subtitle', 'Coretax → Excel · for personal use only'),
    ('app.credit', 'for personal use : punto ap'),
    ('settings.background.label', 'jalankan proses sedot di background'),
    ('results.location_hint', 'Hasil Sedot berada di folder Downloads Windows'),
    ('selection.confirm', 'Sedot SPT terpilih'),
])
def test_locked_owner_copy_is_literal(key, expected):
    from spt_desktop.ui_copy import copy_text
    assert copy_text(key) == expected


def test_main_copy_is_exact_and_selection_is_not_automatic():
    from spt_desktop.ui_copy import copy_text, STAGE_LABELS
    assert copy_text('action.start') == 'Mulai unduh'
    assert copy_text('form.help') == 'Setelah daftar muncul, pilih SPT yang ingin diunduh.'
    assert copy_text('selection.confirm') == 'Sedot SPT terpilih'
    assert STAGE_LABELS == ('Masuk ke Coretax', 'Daftar SPT',
                            'Mengambil rincian', 'Hasil unduhan')


def test_selection_summary_requires_named_integer_counts():
    from spt_desktop.ui_copy import copy_text
    assert copy_text('selection.summary', selected=2, visible=3, inventory=8) == (
        '2 SPT dipilih · 3 dari 8 SPT ditampilkan.')
    with pytest.raises(TypeError):
        copy_text('selection.summary', selected=True, visible=3, inventory=8)
    with pytest.raises(ValueError):
        copy_text('selection.summary', selected=2, visible=3)
    with pytest.raises(KeyError):
        copy_text('key.yang.tidak.ada')


@pytest.mark.parametrize(('values', 'error'), [
    ({'selected': 2, 'visible': 3, 'inventory': 8, 'extra': 1}, ValueError),
    ({'selected': -1, 'visible': 3, 'inventory': 8}, ValueError),
    ({'selected': '2', 'visible': 3, 'inventory': 8}, TypeError),
    ({'selected': 2, 'visible': False, 'inventory': 8}, TypeError),
    ({'selected': 2, 'visible': 3, 'inventory': 8.0}, TypeError),
])
def test_template_rejects_extra_or_negative_counts(values, error):
    from spt_desktop.ui_copy import copy_text
    with pytest.raises(error):
        copy_text('selection.summary', **values)


def test_detail_template_keeps_counts_separate_from_percentage():
    from spt_desktop.ui_copy import copy_text
    assert copy_text('download.details.body', processed=2, total=3, verified=1) == (
        '2 dari 3 SPT sudah diproses. Kelengkapan 1 SPT sudah diperiksa.')
    assert copy_text('selection.summary', selected=0, visible=0, inventory=0) == (
        '0 SPT dipilih · 0 dari 0 SPT ditampilkan.')
    with pytest.raises(ValueError):
        copy_text('action.start', percent=30)


def test_catalog_matches_all_approved_spec_entries():
    from spt_desktop.ui_copy import COPY
    spec = (Path(__file__).parents[1] / 'docs/superpowers/specs/'
            '2026-10-13-magicpath-b-tkinter-design.md').read_text(encoding='utf-8')
    section = spec.split('## 11. Teks final', 1)[1].split('## 12.', 1)[0]
    rows = [line.split('|') for line in section.splitlines() if line.startswith('| `')]
    expected = {row[1].strip(' `'): row[2].strip() for row in rows}
    assert len(expected) == 44
    assert all(COPY[key] == value for key, value in expected.items())


def test_copy_module_has_only_standard_library_imports():
    from spt_desktop import ui_copy
    tree = ast.parse(Path(ui_copy.__file__).read_text(encoding='utf-8'))
    modules = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name.split('.')[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0
            modules.append(node.module.split('.')[0])
    assert set(modules) <= {'typing', 'types', 'string', '__future__', 'collections'}
