"""Synthetic current-grid metadata contracts; execute on GitHub runners only."""

import html
import json

import pytest

from support_isolated_browser import browser
from test_json_inventory import (EXPECTED_META, SOURCE_URL, TAXPAYER, api_row,
                                 context, encode, envelope, synthetic_listing_browser)


FAMILIES = [
    ('VAT_VAT', 'VAT_VATR', 'PPN', 'SPT Masa PPN'),
    ('ICT_WIT', 'ICT_WITR', 'PPh Pasal 21/26', 'SPT Masa PPh Pasal 21/26'),
    ('ICT_WT', 'ICT_WTR', 'PPh Unifikasi', 'SPT Masa PPh Unifikasi'),
]
MONTHS = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni',
          'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember']


def sample(family=FAMILIES[0], month=12, literal=True, *, identifier='fixture-masa', model='Normal'):
    row = api_row(identifier, model)
    row.update(TaxTypeCode=family[0], ReturnSheetTypeCode=family[1],
               TaxPeriodCode=f'{month:02d}{month:02d}2024')
    meta = {**EXPECTED_META, 'Jenis Pajak': family[2],
            'Jenis Surat Pemberitahuan Pajak': family[3], 'Model SPT': model,
            'Masa Pajak': row['TaxPeriodCode'] if literal else MONTHS[month-1] + ' 2024'}
    return row, meta


def adapt_current_grid(browser, folder, rows, displays, *, control=False, span=False,
                       check_cancel=None):
    import coretax_browser as driver

    folder.mkdir(exist_ok=True)
    headers = ''.join('<th>' + html.escape(key) + '</th>' for key in EXPECTED_META)
    body = ''
    for meta in displays:
        cells = []
        for key in EXPECTED_META:
            suffix = ''
            if control and key == 'Masa Pajak':
                suffix = '<input value="fixture-business-value"><input type="checkbox" checked value="fixture-checked">'
            cells.append('<td' + (' colspan="2"' if span and key == 'Kanal' else '') + '>' +
                         html.escape(meta[key]) + suffix + '</td>')
        body += '<tr>' + ''.join(cells) + '</tr>'
    ctx = context()
    response = {'binding': ctx, 'body': encode(envelope(rows)), 'rows': rows,
                'sequence': 7, 'after_sequence': 6}
    with browser.new_context(timezone_id='Asia/Jakarta') as owned:
        page = owned.new_page()
        page.set_content('<table><thead><tr>' + headers + '</tr></thead><tbody>' + body + '</tbody></table>')
        return driver._inventory_metadata(page, page.locator('table'), response,
                                          {'url': SOURCE_URL, 'label': 'SPT Dilaporkan'},
                                          TAXPAYER, ctx['npwp'], 2024, 'period', 1,
                                          folder, 1, check_cancel)


@pytest.mark.parametrize('family', FAMILIES, ids=['ppn', 'pph21', 'unifikasi'])
@pytest.mark.parametrize('month', range(1, 13))
@pytest.mark.parametrize('literal', [True, False], ids=['code', 'caption'])
def test_all_months_bind_current_masa_captions_without_normalizing_source(browser, tmp_path, family, month, literal):
    row, meta = sample(family, month, literal)
    result = adapt_current_grid(browser, tmp_path, [row], [meta])
    assert result['eligible'] is True, result['reason']
    assert result['rows'][0]['meta'] == meta
    assert result['rows'][0]['source_fields']['TaxPeriodCode'] == row['TaxPeriodCode']
    assert result['rows'][0]['source_fields']['ReturnSheetModel'] == 'Normal'
    identity = result['rows'][0]['source_identity']
    assert identity['record_id'] == row['RecordId']
    assert (tmp_path / identity['body_file']).read_bytes() == encode(envelope([row]))


@pytest.mark.parametrize('literal', [True, False])
def test_corporate_annual_binding_accepts_literal_or_reviewed_caption(browser, tmp_path, literal):
    row, meta = api_row(), dict(EXPECTED_META)
    if literal:
        meta['Masa Pajak'] = row['TaxPeriodCode']
    result = adapt_current_grid(browser, tmp_path, [row], [meta])
    assert result['eligible'] is True
    assert result['rows'][0]['meta'] == meta


def mixed_rows():
    pairs = [sample(FAMILIES[0], 11, identifier='fixture-ppn'),
             sample(FAMILIES[1], 12, False, identifier='fixture-21'),
             (api_row('fixture-corporate'), {**EXPECTED_META, 'Masa Pajak': '01122024'}),
             sample(FAMILIES[2], 1, identifier='fixture-unifikasi'),
             sample(FAMILIES[1], 12, identifier='fixture-21-amend', model='Amendment 001')]
    return [p[0] for p in pairs], [p[1] for p in pairs]


@pytest.mark.parametrize('unsupported_middle', [False, True])
def test_mixed_list_pagination_retains_json_pages_and_literal_selection(browser, tmp_path, monkeypatch, unsupported_middle):
    import coretax_browser as driver

    rows, displays = mixed_rows()
    if unsupported_middle:
        rows[3]['ChannelCode'] = None
    with synthetic_listing_browser(browser, monkeypatch, listing_rows=rows,
                                   listing_displays=displays) as (page, metrics):
        result = driver.collect_inventory(page, context()['npwp'], 2024, 'period', tmp_path, max_pages=5)
        assert result['inventory_complete'] is True, result['errors']
        assert [r['record_id'] for r in result['records']] == [r['RecordId'] for r in rows]
        assert [r['meta'] for r in result['records']] == displays
        audit = result['audit'][0]
        assert audit['scanned'] == audit['total'] == audit['selected'] == 5
        assert [p['used_source'] for p in audit['metadata_pages']] == (
            ['json', 'dom-fallback', 'json'] if unsupported_middle else ['json'] * 3)
        assert metrics['submitted_full_grid_reads'] == (1 if unsupported_middle else 0)
        assert metrics['detail_actions'] == metrics['unregistered_requests'] == 0
        for index in ([0, 1, 4] if unsupported_middle else range(5)):
            assert result['records'][index]['source_fields']['TaxPeriodCode'] == rows[index]['TaxPeriodCode']


@pytest.mark.parametrize('defect', ['unknown', 'null-channel', 'range', 'bad-month', 'bad-year', 'locale', 'missing-type', 'span'])
def test_unsupported_metadata_still_refuses_the_whole_json_page(browser, tmp_path, defect):
    row, meta = sample()
    if defect == 'unknown':
        row['TaxTypeCode'] = 'SYNTHETIC_UNREVIEWED'
    elif defect == 'null-channel':
        row['ChannelCode'] = None
    elif defect == 'range':
        row['TaxPeriodCode'] = meta['Masa Pajak'] = '01122024'
    elif defect == 'bad-month':
        row['TaxPeriodCode'] = meta['Masa Pajak'] = '13132024'
    elif defect == 'bad-year':
        row['TaxPeriodCode'] = meta['Masa Pajak'] = '12120000'
    elif defect == 'locale':
        meta['Jenis Pajak'] = 'fixture-unknown-locale'
    elif defect == 'missing-type':
        del row['ReturnSheetTypeCode']
    result = adapt_current_grid(browser, tmp_path, [row], [meta], span=defect == 'span')
    assert result['eligible'] is False
    assert result['rows'] == []


@pytest.mark.parametrize('defect', ['period', 'year', 'model', 'pair', 'reordered'])
@pytest.mark.parametrize('unknown_first', [False, True])
def test_known_row_contradictions_remain_fatal_before_unsupported_fallback(browser, tmp_path, defect, unknown_first):
    from coretax_json import JsonSafetyError

    row, meta = sample()
    if defect == 'period':
        meta['Masa Pajak'] = 'November 2024'
    elif defect == 'year':
        meta['Masa Pajak'] = 'Desember 2023'
    elif defect == 'model':
        meta['Model SPT'] = 'Amendment 001'
    elif defect == 'pair':
        row['ReturnSheetTypeCode'] = 'ICT_WITR'
    elif defect == 'reordered':
        meta['Jenis Pajak'], meta['Jenis Surat Pemberitahuan Pajak'] = FAMILIES[1][2:]
    rows, displays = [row], [meta]
    if unknown_first:
        unknown, caption = sample(identifier='fixture-unknown')
        unknown['TaxTypeCode'] = 'SYNTHETIC_UNREVIEWED'
        rows.insert(0, unknown)
        displays.insert(0, caption)
    with pytest.raises(JsonSafetyError):
        adapt_current_grid(browser, tmp_path, rows, displays)


def test_reference_caption_reader_excludes_control_values_and_checked_state(browser, tmp_path):
    row, meta = sample()
    result = adapt_current_grid(browser, tmp_path, [row], [meta], control=True)
    assert result['eligible'] is True, result['reason']
    assert result['rows'][0]['meta'] == meta
    assert 'fixture-business-value' not in json.dumps(result)
    assert 'fixture-checked' not in json.dumps(result)


def test_stop_surrounds_supported_reference_binding(browser, tmp_path):
    from coretax_browser import CaptureCancelled

    row, meta = sample()
    def stop():
        raise CaptureCancelled('Synthetic Stop')
    with pytest.raises(CaptureCancelled):
        adapt_current_grid(browser, tmp_path, [row], [meta], check_cancel=stop)
    assert not (tmp_path / 'listing-responses').exists()
