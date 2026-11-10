"""Portable Windows reserved-device name guards for desktop and CLI output.

Only synthetic names/paths are used. No Windows device is opened or written.
"""
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import coretax
from coretax_exporter import tax_type_filename
from spt_desktop import output
from spt_desktop.paths import reject_windows_device_component, safe_taxpayer_name


@pytest.mark.parametrize('component', [
    'CON', 'con', 'CoN.txt', 'con .xlsx', 'CON.', 'CON ',
    'PRN', 'aux', 'NUL', 'nul.json', 'NUL .tmp',
    'COM1', 'com9.txt', 'LPT1', 'lpt9.CSV',
    'COM¹', 'com².txt', 'Com³.xls', 'LPT¹', 'lpt².xlsx', 'LPT³',
    'CONIN$', 'CONOUT$', 'conin$.log', 'conout$.txt',
])
def test_reserved_windows_components_are_always_rejected(component):
    with pytest.raises(ValueError, match='reserved device'):
        reject_windows_device_component(component)


@pytest.mark.parametrize('component', [
    'COM0', 'COM0.csv', 'LPT0', 'LPT0.xlsx',
    'COM10', 'LPT10.xlsx', 'CONTAINER', 'AUXILIARY.xlsx',
    'nulled.csv', 'NUL file.xlsx', 'CON_2025.xlsx',
    'PT CON.xlsx', 'NÚL.xlsx', 'コン.xlsx',
    'SPT_NUL.xlsx', 'SPT_Badan_NUL_Normal.xlsx',
    '0000000000000001 - CON', 'SPT Masa PPN',
])
def test_nondevice_components_are_preserved(component):
    reject_windows_device_component(component)


@pytest.mark.parametrize('relative', [
    'CON', 'nul.xlsx', 'COM1.csv', 'COM².xlsx',
    'LPT³.txt', 'SPT Masa PPN/NUL.xlsx',
    'SPT Masa PPN/Con.pdf', 'CON/child.xlsx',
    'SPT Masa 21/COM1/result.xlsx',
])
def test_cli_rejects_reserved_component_before_filesystem_access(tmp_path, relative):
    before = list(tmp_path.iterdir())
    with pytest.raises(ValueError, match='reserved device'):
        coretax.output_path(tmp_path, relative)
    assert list(tmp_path.iterdir()) == before


@pytest.mark.parametrize('wanted', [
    'SPT Masa PPN/SPT_PPN_NUL_Normal.xlsx',
    'COM0.csv', 'LPT0.xlsx',
    'SPT Masa 21/COM0/result.xlsx',
])
def test_cli_accepts_nonreserved_output_paths(tmp_path, wanted):
    assert coretax.output_path(tmp_path, wanted) == tmp_path / wanted


@pytest.mark.parametrize('source,max_length,want', [
    ('CON', 100, 'CON'),
    ('NUL.txt', 100, 'NUL.txt'),
    ('COM¹', 100, 'COM¹'),
    ('CON!.xlsx', 3, 'CON'),
    ('PT CON', 100, 'PT CON'),
    ('PT 日本 NUL', 100, 'PT 日本 NUL'),
])
def test_desktop_checks_complete_npwp_prefixed_component_not_source_fragment(
        tmp_path, source, max_length, want):
    # A reserved *fragment* is not a reserved Windows path component once the
    # validated NPWP is prepended. Avoid changing source names needlessly.
    name = safe_taxpayer_name(source, max_length=max_length)
    assert name == want
    run = {'npwp': '0000000000000001', 'year': 2025,
           'taxpayer_name': name}
    parent = output._parent(run, tmp_path)
    assert parent == tmp_path / ('0000000000000001 - ' + name) / '2025'
    for component in parent.relative_to(tmp_path).parts:
        reject_windows_device_component(component)


@pytest.mark.parametrize('tax_type', [
    'CON', 'NUL', 'com1', 'LPT³', 'PRN.txt', 'PPh Badan',
])
def test_tax_type_filename_has_safe_prefix_and_preserves_source_scope(tax_type):
    filename = tax_type_filename(tax_type)
    assert filename.startswith('SPT_')
    reject_windows_device_component(filename)


@pytest.mark.parametrize('component', ['COM', 'COM¹', 'CON.', 'NUL '])
def test_truncation_never_makes_prefixed_taxpayer_output_a_device(tmp_path, component):
    part = safe_taxpayer_name(component, max_length=3)
    # The sanitized fragment might equal a device, but the final path must not.
    final = output._parent({'npwp': '0000000000000001', 'year': 2025,
                            'taxpayer_name': part}, tmp_path)
    assert final.parent.name.startswith('0000000000000001 - ')
    reject_windows_device_component(final.parent.name)
