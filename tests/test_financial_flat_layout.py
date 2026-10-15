"""Financial PDFs belong directly beside Excel; synthetic runner-only contracts."""
from copy import deepcopy
import hashlib
import json
from pathlib import PurePosixPath
import shutil

import pytest
from openpyxl import load_workbook

import coretax
from coretax_exporter import validate_export_run
from spt_desktop import output
from test_financial_attachments import (browser, routed, attachments, downloaded,
                                        RECORD, DETAIL, PDF_URL, LABEL)
from test_financial_publication import PDF, financial_run
from test_model_workbook_publication import physical_bytes
from test_split_output import fixture_run


def flat_run(folder, count=1):
    run = fixture_run()
    run['records'] = run['records'][:count]
    run['complete'] = False
    run['inventory_complete'] = False
    folder.mkdir(parents=True, exist_ok=True)
    declared = []
    for record in run['records']:
        scope = [run['npwp'], run['year'], run['year_basis']]
        record['scope'] = scope
        record_key = hashlib.sha256(record['record_id'].encode()).hexdigest()[:32]
        url = 'https://coretax.synthetic.invalid/pdf/' + record['record_id']
        name = 'LK_' + record_key + '_' + hashlib.sha256(url.encode()).hexdigest() + '.pdf'
        item = {'label': 'Laporan Keuangan', 'relative_path': name,
                'status': 'COMPLETE', 'bytes': len(PDF), 'hash': hashlib.sha256(PDF).hexdigest()}
        record['attachments'] = [item]
        (folder / name).write_bytes(PDF)
        declared.append({**item, 'record_id': record['record_id'], 'scope': scope})
    run['output_attachments'] = declared
    return run


@pytest.mark.parametrize('label', [LABEL, 'Laporan Keuangan yang Telah Diaudit*'])
def test_new_financial_download_is_directly_in_the_given_spt_folder(routed, tmp_path, label):
    page, requests = routed('<a href="/synthetic-existing/statement.pdf">' + label + '</a>')
    result = attachments().download_financial_attachments(page, deepcopy(RECORD), tmp_path)
    item, path = downloaded(result, tmp_path)
    assert path.parent == tmp_path
    assert PurePosixPath(item['relative_path']).parent == PurePosixPath('.')
    assert not (tmp_path / 'attachments').exists()
    assert requests == [('GET', DETAIL), ('GET', PDF_URL)]


@pytest.mark.parametrize('model', ['Normal', 'Pembetulan 001'])
def test_flat_record_bound_pdf_metadata_can_be_exported_and_verified(tmp_path, model):
    run = flat_run(tmp_path)
    run['records'][0]['meta']['Model SPT'] = model
    before = deepcopy(run['records'])
    coretax.save_output(run, tmp_path)
    coretax.verify_outputs(run, tmp_path)
    assert run['records'] == before
    saved = json.loads((tmp_path / 'run.json').read_text(encoding='utf-8'))
    assert saved['output_attachments'] == run['output_attachments']
    assert all((tmp_path / item['relative_path']).parent == tmp_path
               and (tmp_path / item['relative_path']).read_bytes() == PDF
               for item in saved['output_attachments'])
    assert not (tmp_path / 'attachments').exists()


@pytest.mark.parametrize('count', [1, 2])
def test_desktop_publishes_flat_pdfs_beside_each_model_excel_with_exact_links(tmp_path, count):
    source = tmp_path / 'private-job'
    run = flat_run(source, count)
    expected = {item['relative_path']: PDF for item in deepcopy(run['output_attachments'])}
    assert len(expected) == count
    unrelated = source / 'SYNTHETIC_UNDECLARED_PRIVATE.pdf'
    unrelated.write_bytes(b'SYNTHETIC UNDECLARED PRIVATE BYTES')
    coretax.save_output(run, source)
    final = output.publish_workbooks(run, source, tmp_path / 'Downloads', 'synthetic-flat')
    assert {path.name: path.read_bytes() for path in final.glob('*.pdf')} == expected
    assert not (final / 'attachments').exists()
    assert {path.relative_to(final).as_posix() for path in final.rglob('*.pdf')} == set(expected)
    assert not (final / unrelated.name).exists() and unrelated.read_bytes() == b'SYNTHETIC UNDECLARED PRIVATE BYTES'
    assert not list(final.rglob('*.json'))
    coretax.verify_outputs(run, final)
    for name in run['output_files']:
        workbook = load_workbook(final / name)
        try:
            if name == 'resume.xlsx':
                links = [cell.hyperlink.target for row in workbook['Audit'] for cell in row
                         if cell.hyperlink and cell.hyperlink.target.endswith('.pdf')]
                assert set(links) == set(expected) and len(links) == count
            else:
                proof = json.loads(workbook.properties.identifier)
                assert len(proof['records']) == 1
                links = [item['relative_path'] for record in proof['records']
                         for item in record['attachments'] if item['status'] == 'COMPLETE']
                assert len(links) == 1 and set(links) <= set(expected)
            assert all(PurePosixPath(link).parent == PurePosixPath('.') for link in links)
            assert all((final / link).is_file() for link in links)
        finally:
            workbook.close()


@pytest.mark.parametrize('mutation', ['foreign-record', 'parent-traversal', 'windows-case-alias'])
def test_flat_path_support_does_not_weaken_record_binding_or_safe_names(tmp_path, mutation):
    run = flat_run(tmp_path)
    # The valid positive boundary must work before testing an invalid path.
    validate_export_run(run)
    bad = deepcopy(run)
    item = bad['records'][0]['attachments'][0]
    if mutation == 'foreign-record':
        original_key = hashlib.sha256(bad['records'][0]['record_id'].encode()).hexdigest()[:32]
        foreign_key = hashlib.sha256(b'SYNTHETIC DIFFERENT RETURN').hexdigest()[:32]
        item['relative_path'] = item['relative_path'].replace(original_key, foreign_key)
    elif mutation == 'parent-traversal':
        item['relative_path'] = '../' + item['relative_path']
    else:
        item['relative_path'] = item['relative_path'].upper()
    with pytest.raises(ValueError, match='(?i)pdf|financial|path|record|return'):
        validate_export_run(bad)


def test_new_flat_export_uses_new_folder_without_changing_old_nested_pdf_proofs(tmp_path):
    old_source = tmp_path / 'old-private-job'
    old_run = financial_run(old_source, count=2)
    coretax.save_output(old_run, old_source)
    downloads = tmp_path / 'Downloads'
    old = output._parent(old_run, downloads) / '20250101-000000-000000-legacy'
    old.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(old_source, old)
    assert len(list((old / 'attachments').rglob('*.pdf'))) == 2
    old_bytes = physical_bytes(old)
    source = tmp_path / 'new-private-job'
    run = flat_run(source, count=2)
    coretax.save_output(run, source)
    assert output.existing_outputs(run, downloads) is None
    final = output.publish_workbooks(run, source, downloads, 'synthetic-flat-migration')
    assert final != old and len(list(final.glob('*.pdf'))) == 2
    assert not (final / 'attachments').exists()
    coretax.verify_outputs(run, final)
    assert physical_bytes(old) == old_bytes
