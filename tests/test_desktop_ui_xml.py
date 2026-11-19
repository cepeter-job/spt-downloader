"""XML is the editable source; the packaged runtime is generated Python only."""

from pathlib import Path

import pytest

from scripts.compile_ui_copy import generate
from spt_desktop.ui_copy import COPY, STAGE_LABELS, copy_text
from spt_desktop.ui_text_xml import CATALOG_FILE, load_strings


def test_xml_catalog_matches_active_source_view():
    assert load_strings() == dict(COPY)
    assert STAGE_LABELS == tuple(COPY[key] for key in (
        'stage.authentication', 'stage.inventory', 'stage.details', 'stage.results',
    ))


def test_compiler_generates_identical_python_constants(tmp_path):
    target = tmp_path / 'ui_generated.py'
    assert generate(target=target) == target
    namespace = {}
    exec(compile(target.read_text(encoding='utf-8'), str(target), 'exec'), namespace)
    assert namespace['STRINGS'] == dict(COPY)
    assert '_ui_copy_generated' not in target.name
    assert copy_text('selection.summary', selected=2, visible=3, inventory=4) == (
        '2 SPT dipilih · 3 dari 4 SPT ditampilkan.'
    )


def test_xml_is_not_exposed_as_an_external_packaging_resource(tmp_path):
    from build_desktop import build_command
    cmd = build_command(tmp_path, tmp_path / 'dist', tmp_path / 'uv.exe')
    assert not any('id-ID.xml' in argument for argument in cmd)
    assert 'from ._ui_copy_generated import STRINGS' in (
        Path(__file__).resolve().parent.parent / 'spt_desktop' / 'ui_copy.py'
    ).read_text(encoding='utf-8')


@pytest.mark.parametrize('mutation', [
    lambda value: value.replace('<resources language="id-ID">', '<resources language="en-US">'),
    lambda value: value.replace('</resources>', '<string id="app.title">Duplicate</string></resources>'),
    lambda value: value.replace('id="action.start"', 'id="not valid"'),
    lambda value: value.replace('id="action.start"', 'id="unknown.placeholder"').replace(
        '>Mulai Sedot</string>', '>{unreviewed}</string>'),
    lambda value: value.replace('{selected} SPT dipilih', '{selection} SPT dipilih'),
    lambda value: value.replace('<string id="stage.results">Hasil unduhan</string>', ''),
    lambda value: value.replace('>Mulai Sedot</string>', '><b>Mulai Sedot</b></string>'),
    lambda value: value.replace('>Mulai Sedot</string>', '></string>'),
    lambda value: value.replace('>Mulai Sedot</string>', '>&unexpected;</string>'),
    lambda value: value.replace('<resources language="id-ID">', '<!DOCTYPE foo><resources language="id-ID">'),
])
def test_xml_rejects_invalid_edit(tmp_path, mutation):
    source = CATALOG_FILE.read_text(encoding='utf-8')
    modified = mutation(source)
    assert modified != source
    path = tmp_path / 'invalid.xml'
    path.write_text(modified, encoding='utf-8')
    with pytest.raises(ValueError):
        load_strings(path)
    with pytest.raises(ValueError):
        generate(path, tmp_path / 'invalid_generated.py')
    assert not (tmp_path / 'invalid_generated.py').exists()


def test_developer_xml_change_is_compiled_without_python_edits(tmp_path):
    source = CATALOG_FILE.read_text(encoding='utf-8')
    changed = source.replace('>Mulai Sedot</string>', '>Mulai SPT</string>')
    assert changed != source
    edited = tmp_path / 'edited.xml'
    edited.write_text(changed, encoding='utf-8')
    assert load_strings(edited)['action.start'] == 'Mulai SPT'
    target = tmp_path / 'generated.py'
    generate(edited, target)
    namespace = {}
    exec(compile(target.read_text(encoding='utf-8'), str(target), 'exec'), namespace)
    assert namespace['STRINGS']['action.start'] == 'Mulai sedot'
