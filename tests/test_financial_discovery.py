"""Synthetic visible attachment-label bindings, exercised on the Windows runner."""
from copy import deepcopy

import pytest

from support_financial_browser import browser, routed, attachments, downloaded, RECORD, DETAIL, PDF_URL


CURRENT_LABEL = 'a. 1. Laporan Keuangan/Laporan Keuangan yang Telah Diaudit*'


@pytest.mark.parametrize('label', [CURRENT_LABEL, 'Laporan Keuangan/Laporan Keuangan yang Telah Diaudit*'])
def test_current_financial_caption_on_an_ordinary_link_is_recognized(routed, tmp_path, label):
    page, requests = routed(f'<a href="{PDF_URL}">{label}</a>')
    result = attachments().download_financial_attachments(page, deepcopy(RECORD), tmp_path)
    item, _ = downloaded(result, tmp_path)
    assert item['label'] == label
    assert requests == [('GET', DETAIL), ('GET', PDF_URL)]


def file_table(link, caption=''):
    return f'''<table>{caption}<thead><tr><th>NO.</th><th>FILENAME</th><th>TINDAKAN</th></tr></thead>
    <tbody><tr><td>1</td><td>{link}</td><td></td></tr></tbody></table>'''


@pytest.mark.parametrize('binding', ['caption', 'labelledby', 'preceding_label'])
def test_filename_link_is_bound_to_its_visible_financial_table(routed, tmp_path, binding):
    link = f'<a href="{PDF_URL}">SYNTHETIC-PRIVATE-FILENAME.pdf</a>'
    if binding == 'caption':
        html = file_table(link, f'<caption>{CURRENT_LABEL}</caption>')
    elif binding == 'labelledby':
        html = f'<label id="financial-label">{CURRENT_LABEL}</label>' + file_table(link).replace(
            '<table>', '<table aria-labelledby="financial-label">')
    else:
        html = f'<section><label>{CURRENT_LABEL}</label><p-table>' + file_table(link) + '</p-table></section>'
    # A neighboring attachment must not inherit the financial label.
    html += '<section><label>a. 2. Laporan Keuangan Konsolidasian untuk Wajib Pajak Grup</label>' + file_table(
        '<a href="/synthetic-unrelated.pdf">SYNTHETIC-OTHER.pdf</a>') + '</section>'
    page, requests = routed(html)
    result = attachments().download_financial_attachments(page, deepcopy(RECORD), tmp_path)
    item, _ = downloaded(result, tmp_path)
    assert item['label'] == CURRENT_LABEL
    assert requests == [('GET', DETAIL), ('GET', PDF_URL)]


@pytest.mark.parametrize('case', ['hidden_label', 'ambiguous_labels', 'foreign_table', 'button', 'handler'])
def test_unbound_or_action_based_attachment_never_authorizes_a_pdf_request(routed, tmp_path, case):
    label = f'<label>{CURRENT_LABEL}</label>'
    link = f'<a href="{PDF_URL}">SYNTHETIC-PRIVATE-FILENAME.pdf</a>'
    if case == 'hidden_label':
        label = f'<label hidden>{CURRENT_LABEL}</label>'
    elif case == 'ambiguous_labels':
        label += '<label>Unrelated attachment</label>'
    elif case == 'foreign_table':
        label += file_table('SYNTHETIC OTHER ROW')
    elif case == 'button':
        link = '<button onclick="fetch(\'/generate\', {method:\'POST\'})">Download</button>'
    else:
        link = link.replace('<a ', '<a onclick="fetch(\'/generate\', {method:\'POST\'})" ')
    page, requests = routed('<section>' + label + file_table(link) + '</section>')
    result = attachments().download_financial_attachments(page, deepcopy(RECORD), tmp_path)
    assert result and all(item['status'] == 'PARTIAL' for item in result)
    assert requests == [('GET', DETAIL)] and not list(tmp_path.glob('*.pdf'))
