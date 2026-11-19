"""User-visible copy is an explicit contract, separate from Tk and worker code."""
import ast
from pathlib import Path

import pytest

from spt_desktop.ui_text_xml import load_strings


@pytest.mark.parametrize('key', [
    'app.title', 'app.subtitle', 'app.bugreport', 'settings.background.label',
    'results.location_hint', 'selection.confirm',
])
def test_owner_copy_uses_xml_value_without_frozen_literal(key):
    from spt_desktop.ui_copy import copy_text
    from spt_desktop.ui_text_xml import load_strings
    assert copy_text(key) == load_strings()[key]


def test_main_copy_is_exact_and_selection_is_not_automatic():
    from spt_desktop.ui_copy import copy_text, STAGE_LABELS
    from spt_desktop.ui_text_xml import load_strings
    source = load_strings()
    for key in ('action.start', 'form.help', 'selection.confirm'):
        assert copy_text(key) == source[key]
    assert STAGE_LABELS == tuple(source[key] for key in (
        'stage.authentication', 'stage.inventory', 'stage.details', 'stage.results'))


def test_selection_summary_requires_named_integer_counts():
    from spt_desktop.ui_copy import copy_text
    assert copy_text('selection.summary', selected=2, visible=3, inventory=8) == (
        load_strings()['selection.summary'].format(selected=2, visible=3, inventory=8))
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
        load_strings()['download.details.body'].format(processed=2, total=3, verified=1))
    assert copy_text('selection.summary', selected=0, visible=0, inventory=0) == (
        load_strings()['selection.summary'].format(selected=0, visible=0, inventory=0))
    with pytest.raises(ValueError):
        copy_text('action.start', percent=30)


def test_catalog_matches_developer_xml():
    from spt_desktop.ui_copy import COPY
    assert dict(COPY) == load_strings()
    assert 'app.credit' not in COPY


def test_copy_module_has_only_standard_library_imports():
    from spt_desktop import ui_copy
    tree = ast.parse(Path(ui_copy.__file__).read_text(encoding='utf-8'))
    modules = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name.split('.')[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level == 1:
                assert node.module in {'ui_text_schema', 'ui_text_xml', '_ui_copy_generated'}
            else:
                modules.append(node.module.split('.')[0])
    assert set(modules) <= {'typing', 'types', 'sys', 'string', '__future__', 'collections'}


@pytest.mark.parametrize('key', [
    'selection.help', 'selection.search.label', 'selection.empty',
    'selection.focused_id', 'selection.keyboard_hint',
])
def test_phase2_selection_copy_matches_catalog(key):
    from spt_desktop.ui_copy import copy_text
    assert copy_text(key) == load_strings()[key]


@pytest.mark.parametrize('key', [
    'overwrite.folder.label', 'overwrite.help', 'overwrite.keep_hint',
    'overwrite.context_missing',
])
def test_phase2_overwrite_copy_matches_catalog(key):
    from spt_desktop.ui_copy import copy_text
    assert copy_text(key) == load_strings()[key]


@pytest.mark.parametrize('count', [0, 2])
def test_overwrite_count_template_is_strict(count):
    from spt_desktop.ui_copy import copy_text
    assert copy_text('overwrite.files_count', count=count) == load_strings()['overwrite.files_count'].format(count=count)


@pytest.mark.parametrize('values,error', [
    ({'count': True}, TypeError), ({'count': False}, TypeError),
    ({'count': '2'}, TypeError), ({'count': 2.0}, TypeError),
    ({'count': -1}, ValueError), ({}, ValueError),
    ({'count': 1, 'extra': 0}, ValueError),
])
def test_overwrite_count_rejects_wrong_types_and_keys(values, error):
    from spt_desktop.ui_copy import copy_text
    with pytest.raises(error):
        copy_text('overwrite.files_count', **values)
