"""XML is the editable source; the packaged runtime is generated Python only."""

from pathlib import Path
import re

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
        load_strings()['selection.summary'].format(selected=2, visible=3, inventory=4)
    )


def test_xml_is_not_exposed_as_an_external_packaging_resource(tmp_path):
    from build_desktop import build_command
    cmd = build_command(tmp_path, tmp_path / 'dist', tmp_path / 'uv.exe')
    assert not any('id-ID.xml' in argument for argument in cmd)
    assert 'from ._ui_copy_generated import STRINGS' in (
        Path(__file__).resolve().parent.parent / 'spt_desktop' / 'ui_copy.py'
    ).read_text(encoding='utf-8')


def replace_entry(xml: str, key: str, value: str) -> str:
    """Mutate exactly one string value, independently of its current wording."""
    changed, count = re.subn(r'(<string id="' + re.escape(key) + r'">).*?(</string>)',
                             lambda match: match.group(1) + value + match.group(2),
                             xml, count=1, flags=re.DOTALL)
    assert count == 1
    return changed


@pytest.mark.parametrize('mutation', [
    lambda value: value.replace('<resources language="id-ID">', '<resources language="en-US">'),
    lambda value: value.replace('</resources>', '<string id="app.title">Duplicate</string></resources>'),
    lambda value: value.replace('id="action.start"', 'id="not valid"'),
    lambda value: replace_entry(value.replace('id="action.start"', 'id="unknown.placeholder"'),
                                'unknown.placeholder', '{unreviewed}'),
    lambda value: replace_entry(value, 'selection.summary', '{selection}'),
    lambda value: value.replace('id="stage.results"', 'id="stage.results.removed"'),
    lambda value: replace_entry(value, 'action.start', '<b>Nested UI</b>'),
    lambda value: replace_entry(value, 'action.start', ''),
    lambda value: replace_entry(value, 'action.start', '&unexpected;'),
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


@pytest.mark.parametrize(('key', 'value'), [
    ('app.title', 'SYNTHETIC TITLE'),
    ('action.start', 'SYNTHETIC START'),
    ('stage.results', 'SYNTHETIC RESULTS'),
    ('settings.field.label.jumlah.cache.job.0.nonaktif', 'SYNTHETIC SETTING'),
    ('main.status.value1.menghentikan.unduhan', '{value1} synthetic stopping'),
    ('download.details.body', '{total} total, {processed} processed, {verified} verified'),
    ('settings.dialog.body.total.job.lama.memenuhi.syarat', '{total} jobs, {value2} MiB'),
])
def test_developer_value_only_edits_compile_without_python_edits(tmp_path, key, value):
    """Normal text changes may be shipped without changing IDs, tests or Python."""
    source = CATALOG_FILE.read_text(encoding='utf-8')
    changed = replace_entry(source, key, value)
    assert changed != source
    edited = tmp_path / 'edited.xml'
    edited.write_text(changed, encoding='utf-8')
    assert load_strings(edited)[key] == value
    target = tmp_path / 'generated.py'
    generate(edited, target)
    namespace = {}
    exec(compile(target.read_text(encoding='utf-8'), str(target), 'exec'), namespace)
    assert namespace['STRINGS'][key] == value


@pytest.mark.parametrize(('key', 'report_path'), [
    ('app.title', ('ui_text', 'title')),
    ('settings.background.label', ('ui_text', 'background')),
    ('results.location_hint', ('ui_text', 'results')),
    ('app.subtitle', ('personal_use_labels',)),
    ('app.bugreport', ('bugreport_footer', 'text')),
    ('settings.widget.simpan', ('gui_controls',)),
    ('selection.table.type', ('selection_sorting_control', 'directions')),
])
def test_packaged_selftest_accepts_revised_valid_display_values(monkeypatch, key, report_path):
    """The release gate must match the approved catalog, not yesterday's text."""
    import build_desktop
    from support_build_reports import report

    current = build_desktop.copy_text
    new_text = 'SYNTHETIC CHANGED DISPLAY VALUE'
    monkeypatch.setattr(build_desktop, 'copy_text',
                        lambda name: new_text if name == key else current(name))
    data = report()
    if report_path[0] == 'personal_use_labels':
        data['personal_use_labels'] = [new_text]
    elif report_path[0] == 'gui_controls':
        data['gui_controls'] = [new_text if item == current(key) else item
                                for item in data['gui_controls']]
    elif report_path[-1] == 'directions':
        data['selection_sorting_control']['directions'] = [
            new_text + ' ▲', new_text + ' ▼']
    else:
        data[report_path[0]][report_path[1]] = new_text
    build_desktop.validate_report(data)
