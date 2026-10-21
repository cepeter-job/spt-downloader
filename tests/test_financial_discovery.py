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


@pytest.mark.parametrize('case', ['duplicate_id', 'hidden_reference', 'multiple_references',
    'contradictory_reference', 'foreign_section', 'nested_table', 'sibling_panel', 'sibling_accordion'])
def test_table_label_binding_cannot_escape_explicit_ownership(routed, tmp_path, case):
    link = f'<a href="{PDF_URL}">SYNTHETIC-PRIVATE-FILENAME.pdf</a>'
    label = f'<label id="financial">{CURRENT_LABEL}</label>'
    table = file_table(link).replace('<table>', '<table aria-labelledby="financial">')
    if case == 'duplicate_id':
        label += '<label id="financial">Other attachment</label>'
    elif case == 'hidden_reference':
        label = label.replace('<label ', '<label hidden ')
    elif case == 'multiple_references':
        label += '<label id="other">Other attachment</label>'
        table = table.replace('aria-labelledby="financial"', 'aria-labelledby="financial other"')
    elif case == 'contradictory_reference':
        label += '<label id="other">Other attachment</label>'
        table = file_table(link, f'<caption>{CURRENT_LABEL}</caption>').replace(
            '<table>', '<table aria-labelledby="other">')
    elif case == 'foreign_section':
        label = '<section>' + label + '</section>'
        table = '<section>' + table + '</section>'
    elif case == 'nested_table':
        label = ''
        table = file_table(file_table(link), f'<caption>{CURRENT_LABEL}</caption>')
    else:
        panel, title = ('p-panel', 'p-panel-title') if case == 'sibling_panel' else (
            'p-accordion-tab', 'p-accordion-header-text')
        label = ''
        table = f'<div><div class="{panel}"><span class="{title}">{CURRENT_LABEL}</span></div>' + \
            f'<div class="{panel}">{file_table(link)}</div></div>'
    page, requests = routed(label + table)
    result = attachments().download_financial_attachments(page, deepcopy(RECORD), tmp_path)
    assert result and all(item['status'] == 'PARTIAL' for item in result)
    assert requests == [('GET', DETAIL)] and not list(tmp_path.glob('*.pdf'))


@pytest.mark.parametrize('header', ['', '<thead><tr><th>Other document</th></tr></thead>'])
def test_financial_text_does_not_bind_an_unrecognized_file_table(routed, tmp_path, header):
    html = f'<table><caption>{CURRENT_LABEL}</caption>{header}<tbody><tr><td>' + \
        f'<a href="{PDF_URL}">SYNTHETIC-PRIVATE-FILENAME.pdf</a></td></tr></tbody></table>'
    page, requests = routed(html)
    result = attachments().download_financial_attachments(page, deepcopy(RECORD), tmp_path)
    assert result and all(item['status'] == 'PARTIAL' for item in result)
    assert requests == [('GET', DETAIL)] and not list(tmp_path.glob('*.pdf'))


def test_financial_link_outside_the_detail_content_is_not_downloaded(routed, tmp_path):
    page, requests = routed('<p>No financial control in this Induk.</p>')
    page.evaluate('''url => {
        const aside = document.createElement('aside');
        aside.innerHTML = '<a href="'+url+'">Laporan Keuangan</a>';
        document.body.append(aside);
    }''', PDF_URL)
    result = attachments().download_financial_attachments(page, deepcopy(RECORD), tmp_path)
    assert result and all(item['status'] == 'PARTIAL' for item in result)
    assert requests == [('GET', DETAIL)] and not list(tmp_path.glob('*.pdf'))
