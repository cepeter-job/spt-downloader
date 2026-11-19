"""Guard broad desktop text extraction without running the live GUI or worker."""

import ast
from pathlib import Path
from string import Formatter

import pytest

from scripts.compile_ui_copy import referenced_ui_keys, validate_referenced_ui_keys, generate
from spt_desktop.ui_copy import COPY, copy_text, format_text
from spt_desktop.ui_text_schema import COUNT_PARAMETERS, DISPLAY_PARAMETERS
from spt_desktop.ui_text_xml import CATALOG_FILE, load_strings

ROOT = Path(__file__).resolve().parent.parent
GUI_SOURCES = ('spt_desktop/app.py', 'spt_desktop/ui_views.py', 'spt_gui.py')


def test_desktop_ui_strings_cover_settings_and_cleanup():
    assert len(COPY) >= 200
    examples = {
        'settings.widget.simpan': 'Simpan',
        'settings.widget.bersihkan.cache.job': 'bersihkan cache job',
        'settings.widget.hapus.job.partial.gagal': 'hapus job PARTIAL/gagal',
        'settings.widget.cek.pembaruan': 'Cek pembaruan',
        'settings.widget.perbarui.penggunaan.storage': 'Perbarui penggunaan storage',
        'settings.widget.buka.folder.log': 'Buka folder log',
        'settings.widget.select.all': 'Select All',
        'settings.storage.label.protected.auto.clean': 'Protected (Auto Clean)',
        'settings.storage.checking': 'Memeriksa…',
        'settings.storage.unavailable': '—',
    }
    for key, expected in examples.items():
        assert copy_text(key) == expected


def test_cleanup_confirmation_preserves_consent_and_downloads_boundary():
    prune = format_text('settings.dialog.body.total.job.lama.memenuhi.syarat',
                        total=2, value2='1.5')
    assert prune.startswith('2 job lama memenuhi syarat. Perkiraan ruang: 1.5 MiB.\n\n')
    assert 'Capture mentah dan checkpoint job ini akan dihapus permanen' in prune
    assert 'file hasil Downloads, akun, dan profil browser tetap disimpan' in prune
    assert 'Pemeriksaan kepemilikan dan file akan diulang' in prune

    deleted = format_text('settings.dialog.body.value1.job.partial.gagal.dipilih',
                          value1=3, value2='2.1')
    assert deleted.startswith('3 job PARTIAL/gagal dipilih (≈ 2.1 MiB).\n\n')
    assert 'secara permanen' in deleted
    assert 'profil dan login tidak dihapus' in deleted
    assert 'Pemeriksaan keselamatan diulang' in deleted


def test_dynamic_copy_does_not_weakly_format_unknown_fields():
    key = 'settings.dialog.body.value1.job.partial.gagal.dipilih'
    with pytest.raises(ValueError):
        format_text(key, value1=2)
    with pytest.raises(ValueError):
        format_text(key, value1=2, value2='1.2', stray='extra')
    with pytest.raises(TypeError):
        format_text(key, value1=True, value2='1.2')
    with pytest.raises(TypeError):
        format_text(key, value1=1.0, value2='1.2')
    with pytest.raises(KeyError):
        format_text('action.start')
    with pytest.raises(ValueError):
        copy_text('selection.summary', selected=2, visible=2)
    assert format_text('settings.storage.size_display', prefix='≥ ', size='2.5') == '≥ 2.5 MiB'
    assert format_text('settings.storage.size_display',
                       prefix='{not_a_field}', size='1.0') == '{not_a_field}1.0 MiB'


def test_every_catalog_placeholder_is_declared_and_unformatted():
    for key, text in COPY.items():
        tokens = list(Formatter().parse(text))
        names = {field for _, field, _, _ in tokens if field is not None}
        assert names == COUNT_PARAMETERS.get(key, DISPLAY_PARAMETERS.get(key, frozenset()))
        assert all(not spec and not conversion for _, _, spec, conversion in tokens)
    assert not COUNT_PARAMETERS.keys() & DISPLAY_PARAMETERS.keys()


def test_all_static_ui_references_exist_and_removal_is_blocked(tmp_path):
    current = load_strings()
    keys = referenced_ui_keys(ROOT)
    assert len(keys) >= 170
    assert keys <= current.keys()
    validate_referenced_ui_keys(current, ROOT)

    deleted = dict(current)
    del deleted['settings.widget.simpan']
    with pytest.raises(ValueError, match='missing referenced IDs'):
        validate_referenced_ui_keys(deleted, ROOT)

    source = tmp_path / 'edited.xml'
    xml = CATALOG_FILE.read_text(encoding='utf-8')
    xml = xml.replace('<string id="settings.widget.simpan">Simpan</string>', '')
    assert xml != CATALOG_FILE.read_text(encoding='utf-8')
    source.write_text(xml, encoding='utf-8')
    output = tmp_path / 'compiled.py'
    with pytest.raises(ValueError, match='missing referenced IDs'):
        generate(source=source, target=output)
    assert not output.exists()


def test_tk_widgets_dialog_titles_and_prompts_have_no_static_literal_text():
    """Prevent subsequent UI features bypassing the developer-owned catalog."""
    visible_widgets = {
        'ttk.Label', 'ttk.Button', 'ttk.Checkbutton', 'ttk.LabelFrame',
        'ttk.Radiobutton', 'tk.Label', 'tk.Button', 'tk.Checkbutton',
    }
    for relative in GUI_SOURCES:
        source = (ROOT / relative).read_text(encoding='utf-8')
        tree = ast.parse(source, filename=relative)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = ast.unparse(node.func)
            if name.startswith('messagebox.'):
                for argument in node.args[:2]:
                    assert not isinstance(argument, (ast.Constant, ast.JoinedStr)), (
                        relative, node.lineno, name
                    )
            if name in visible_widgets:
                for argument in node.keywords:
                    if argument.arg == 'text':
                        assert not isinstance(argument.value, (ast.Constant, ast.JoinedStr)), (
                            relative, node.lineno, name
                        )
            if name.endswith('.title') and node.args:
                assert not isinstance(node.args[0], (ast.Constant, ast.JoinedStr)), (
                    relative, node.lineno, name
                )
            if name.endswith('.heading'):
                for argument in node.keywords:
                    if argument.arg == 'text':
                        assert not isinstance(argument.value, (ast.Constant, ast.JoinedStr)), (
                            relative, node.lineno, name
                        )
