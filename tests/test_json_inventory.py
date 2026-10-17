"""Synthetic contracts for source-bound submitted-list JSON metadata.

Fixtures describe the observed API structure, never a live taxpayer response.
These tests run only on GitHub runners; no production helper is mocked.
"""

import hashlib
import importlib
import importlib.util
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ORIGIN = 'https://coretax.intranet.pajak.go.id'
TAXPAYER = 'fixture-taxpayer'
SOURCE_URL = ORIGIN + '/returnsheets/id-ID/submitted-returnsheets/' + TAXPAYER
API_URL = ORIGIN + '/returnsheet/api/returnsheetssubmitted'


def context():
    return {
        'npwp': '0000000000000001', 'year': 2024, 'year_basis': 'period',
        'taxpayer_id': TAXPAYER, 'source_url': SOURCE_URL,
        'source_status': 'SPT Dilaporkan', 'page': 1, 'sequence': 7,
        'after_sequence': 6, 'response_url': API_URL, 'http_status': 200,
        'method': 'POST', 'frame_url': SOURCE_URL,
        'request': {
            'TaxpayerAggregateIdentifier': TAXPAYER, 'First': 0, 'Rows': 50,
            'Filters': [], 'isArchieved': False, 'LanguageId': 1,
            'SortField': None, 'SortOrder': None,
        },
        'date_format': 'dd-MM-yyyy', 'timezone': 'Asia/Jakarta',
        'lookup_labels': {
            'TaxTypeCode': {'ICT_RCIT': 'PPh Badan'},
            'ReturnSheetTypeCode': {'ICT_RCITR': 'SPT PPh Badan Rupiah'},
            'TaxPeriodCode': {
                '01122023': 'Januari - Desember 2023',
                '01122024': 'Januari - Desember 2024',
                '01122026': 'Januari - Desember 2026',
            },
            'ReturnSheetStatusCode': {'SUBMITTED': 'Dilaporkan'},
            'ChannelCode': {
                'TAXPAYER_PORTAL': 'Portal Wajib Pajak',
                'PAPER_AT_COUNTER': 'Kertas di Loket',
                'PAPER_VIA_MAIL': 'Kertas melalui Pos',
            },
        },
    }


def api_row(record_id='fixture-normal', model='Normal'):
    # Extra fields mirror the envelope but are not guessed canonical aliases.
    return {
        'AggregateIdentifier': 'fixture-aggregate-' + record_id,
        'AggregateVersion': '1', 'AssessmentDate': None,
        'BookkeepingPeriod': '01122024', 'BpsNo': '000123',
        'BpsSource': 'not-the-displayed-receipt-number', 'CanRecreate': None,
        'ChannelCode': 'TAXPAYER_PORTAL',
        'CreationDate': '2024-12-31T23:30:00Z',
        'CreationDateEvent': '2020-01-01T00:00:00',
        'DateNoticeOfLateFilling': None, 'DateOfReceipt': '2024-06-01T00:00:00',
        'DocumentFormAggregateIdentifier': 'fixture-document',
        'DocumentFormNumber': 'fixture-document-number',
        'DocumentFormSignStatus': 'fixture-sign-status',
        'DocumentReceiptAggregateIdentifier': None, 'DocumentReceiptNumber': None,
        'EnteredDate': '2024-12-31T23:30:00Z',
        'ExpectedReturnDate': '2025-04-30T00:00:00',
        'IdentityUser': 'fixture-identity', 'IsLatest': True, 'IsMigrated': False,
        'LetterAppendix': None, 'NameCore': 'Fixture creator', 'NamePortal': None,
        'OfficerID': '00123', 'OfficerName': '  ',
        'PrefillEnd': '2024-01-01T00:00:00',
        'PrefillLastUpdated': '2024-01-01T00:00:00',
        'PrefillStart': '2024-01-01T00:00:00', 'PrefillStatus': 'fixture-prefill',
        'ProcessRequeststatus': None, 'ProofOfReceipt': None,
        'ReceiptDate': '2020-01-01T00:00:00', 'RecordId': record_id,
        'RejectionNo': None, 'RejectionNumber': None, 'RejectionReason': None,
        'ReturnDate': '2019-01-01T00:00:00', 'ReturnSheetModel': model,
        'ReturnSheetNumber': 'fixture-return-number',
        'ReturnSheetStatusCode': 'SUBMITTED', 'ReturnSheetTypeCode': 'ICT_RCITR',
        'ReturnSheetVersionCode': 'fixture-version', 'SignedBy': 'fixture-signer',
        'SubmitInProgressStatus': False, 'SubmitTimestamp': 0,
        'TaxObjectName': None, 'TaxObjectNumber': None,
        'TaxOfficeCode': 'fixture-office', 'TaxPeriodCode': '01122024',
        'TaxTypeCode': 'ICT_RCIT', 'TaxpayerAggregateIdentifier': TAXPAYER,
        'TotalDeclaredAmount': 0, 'UserNameCore': None, 'UserNamePortal': None,
    }


def envelope(rows=None, *, total=None, successful=True):
    if rows is None:
        rows = [api_row()]
    return {
        'IsSuccessful': successful,
        'Payload': {'Data': rows, 'TotalRecords': len(rows) if total is None else total},
    }


def encode(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode('utf-8')


def adapt(payload, ctx=None):
    # Missing feature is a test-body assertion, not a collection import error.
    assert importlib.util.find_spec('coretax_json') is not None, 'Verified JSON inventory adapter is not implemented'
    module = importlib.import_module('coretax_json')
    function = getattr(module, 'adapt_inventory_page', None)
    assert callable(function), 'Public adapt_inventory_page contract is not implemented'
    return function(payload if isinstance(payload, bytes) else encode(payload), context() if ctx is None else ctx)


EXPECTED_META = {
    'Jenis Pajak': 'PPh Badan',
    'Jenis Surat Pemberitahuan Pajak': 'SPT PPh Badan Rupiah',
    'Masa Pajak': 'Januari - Desember 2024',
    'NOP': '', 'Nama Objek Pajak': '', 'Model SPT': 'Normal',
    'Tanggal Jatuh Tempo': '30-04-2025', 'Tanggal Dibuat': '01-01-2025',
    'Status SPT': 'Dilaporkan', 'Kanal': 'Portal Wajib Pajak',
    'Tanggal Penerimaan': '01-01-2025', 'Nomor Bukti Penerimaan': '000123',
    'Tanggal Resi Pos': '', 'Tanggal Submit SPT': '01-01-2025',
    'Nama Pegawai': '', 'ID Petugas': '00123',
}


def _period_union_context():
    ctx = context()
    ctx['request']['Filters'] = [{
        'PropertyName': 'TaxPeriodCode',
        'Value': ['01122023', '01122024'],
        'MatchMode': 'any-equals-equals',
        'CaseSensitive': True,
        'AsString': False,
    }]
    return ctx


def test_period_union_filter_preserves_all_matching_records_and_source_values():
    rows = [api_row('fixture-prior'), api_row('fixture-current')]
    rows[0]['TaxPeriodCode'] = '01122023'
    result = adapt(envelope(rows), _period_union_context())
    assert result['eligible'] is True
    assert result['total'] == 2
    assert [r['record_id'] for r in result['rows']] == ['fixture-prior', 'fixture-current']
    assert [r['source_fields']['TaxPeriodCode'] for r in result['rows']] == ['01122023', '01122024']


def test_period_union_filter_rejects_outside_record_before_metadata_fallback():
    from coretax_json import JsonSafetyError
    row = api_row()
    row['TaxPeriodCode'] = '01122026'
    row.pop('ChannelCode')
    with pytest.raises(JsonSafetyError):
        adapt(envelope([row]), _period_union_context())


def test_period_union_filter_preserves_amendments_with_distinct_identifiers():
    rows = [api_row('fixture-normal'), api_row('fixture-amendment', 'Amendment 001')]
    result = adapt(envelope(rows), _period_union_context())
    assert result['eligible'] is True
    assert [r['meta']['Model SPT'] for r in result['rows']] == ['Normal', 'Amendment 001']
    assert [r['record_id'] for r in result['rows']] == ['fixture-normal', 'fixture-amendment']


def test_period_union_filter_accepts_verified_empty_response():
    result = adapt(envelope([], total=0), _period_union_context())
    assert result['eligible'] is True
    assert result['total'] == 0 and result['rows'] == []


@pytest.mark.parametrize('values', [None, '01122024', [], ['01122024'],
                                    ['01122023', '01122024', '01122026'],
                                    ['01122024', '01122024'], ['01122023', 1122024],
                                    ['01122023', ' 01122024']])
def test_period_union_filter_rejects_malformed_values_even_for_empty_pages(values):
    from coretax_json import JsonSafetyError
    ctx = _period_union_context()
    ctx['request']['Filters'][0]['Value'] = values
    with pytest.raises(JsonSafetyError):
        adapt(envelope([], total=0), ctx)


def test_period_union_filter_rejects_wrong_request_taxpayer():
    from coretax_json import JsonSafetyError
    ctx = _period_union_context()
    ctx['request']['TaxpayerAggregateIdentifier'] = 'fixture-other-taxpayer'
    with pytest.raises(JsonSafetyError):
        adapt(envelope(), ctx)


def test_period_union_filter_rejects_foreign_response_identity():
    from coretax_json import JsonSafetyError
    row = api_row()
    row['TaxpayerAggregateIdentifier'] = 'fixture-other-taxpayer'
    with pytest.raises(JsonSafetyError):
        adapt(envelope([row]), _period_union_context())


def test_period_union_filter_preserves_offset_validation():
    from coretax_json import JsonSafetyError
    ctx = _period_union_context()
    ctx['request']['First'] = 50
    with pytest.raises(JsonSafetyError):
        adapt(envelope(), ctx)


def test_adapter_produces_complete_canonical_metadata_from_verified_fields():
    result = adapt(envelope())
    assert result['eligible'] is True
    assert result['total'] == 1
    assert result['rows'][0]['record_id'] == 'fixture-normal'
    assert result['rows'][0]['meta'] == EXPECTED_META


def test_adapter_preserves_normal_and_distinct_amendment_identities():
    rows = [api_row(), api_row('fixture-amend-001', 'Amendment 001'), api_row('fixture-amend-002', 'Amendment 002')]
    result = adapt(envelope(rows))
    assert result['eligible'] is True
    assert [row['record_id'] for row in result['rows']] == ['fixture-normal', 'fixture-amend-001', 'fixture-amend-002']
    assert [row['meta']['Model SPT'] for row in result['rows']] == ['Normal', 'Amendment 001', 'Amendment 002']
    assert result['total'] == 3


def test_adapter_uses_verified_catalog_not_private_sample_year_or_labels():
    row = api_row()
    row['TaxPeriodCode'] = '01122026'
    ctx = context()
    ctx['year'] = 2026
    ctx['lookup_labels']['TaxTypeCode']['ICT_RCIT'] = 'Verified fixture tax caption'
    result = adapt(envelope([row]), ctx)
    assert result['eligible'] is True
    assert result['rows'][0]['meta']['Masa Pajak'] == 'Januari - Desember 2026'
    assert result['rows'][0]['meta']['Jenis Pajak'] == 'Verified fixture tax caption'


def test_rendered_blank_does_not_destroy_raw_source_whitespace_or_leading_zeros():
    result = adapt(envelope())
    row = result['rows'][0]
    assert row['meta']['Nama Pegawai'] == ''
    assert row['source_fields']['OfficerName'] == '  '
    assert row['source_fields']['BpsNo'] == '000123'
    assert row['source_fields']['TaxPeriodCode'] == '01122024'
    assert row['source_fields']['TaxObjectNumber'] is None


def test_source_evidence_preserves_record_aggregate_and_response_binding():
    body = encode(envelope())
    result = adapt(body)
    evidence = result['rows'][0]['source_identity']
    assert evidence['record_id'] == 'fixture-normal'
    assert evidence['aggregate_id'] == 'fixture-aggregate-fixture-normal'
    assert evidence['taxpayer_id'] == TAXPAYER
    assert evidence['source_url'] == SOURCE_URL
    assert evidence['page'] == 1 and evidence['sequence'] == 7
    assert evidence['body_sha256'] == hashlib.sha256(body).hexdigest()


def test_submit_and_receipt_dates_follow_entered_date_not_plausible_aliases():
    result = adapt(envelope())
    meta = result['rows'][0]['meta']
    assert meta['Tanggal Submit SPT'] == '01-01-2025'
    assert meta['Tanggal Penerimaan'] == '01-01-2025'
    assert meta['Nomor Bukti Penerimaan'] == '000123'


def test_year_basis_uses_rendered_period_or_submit_date_without_changing_source():
    from coretax_exporter import in_scope
    meta = adapt(envelope())['rows'][0]['meta']
    assert in_scope(meta, 2024, 'period') is True
    assert in_scope(meta, 2024, 'submission') is False
    assert in_scope(meta, 2025, 'submission') is True


@pytest.mark.parametrize('channel', ['PAPER_AT_COUNTER', 'PAPER_VIA_MAIL'])
def test_postal_receipt_date_is_rendered_only_for_verified_paper_channels(channel):
    row = api_row()
    row['ChannelCode'] = channel
    result = adapt(envelope([row]))
    assert result['rows'][0]['meta']['Tanggal Resi Pos'] == '01-06-2024'


@pytest.mark.parametrize('value', [None, '0001-01-01T00:00:00', '2024-03-04T00:00:00.000100Z'])
def test_missing_or_source_sentinel_date_matches_empty_ui_display(value):
    row = api_row()
    row['ExpectedReturnDate'] = value
    result = adapt(envelope([row]))
    assert result['rows'][0]['meta']['Tanggal Jatuh Tempo'] == ''
    assert result['rows'][0]['source_fields']['ExpectedReturnDate'] == value


def test_safe_unknown_metadata_schema_is_explicitly_ineligible_without_inventing_fields():
    row = api_row()
    del row['ReturnSheetModel']
    result = adapt(envelope([row]))
    assert result['eligible'] is False
    assert result['reason']
    assert not result.get('rows')


def test_unknown_reference_code_is_not_guessed_from_similar_field_names():
    row = api_row()
    row['TaxTypeCode'] = 'UNOBSERVED_FIXTURE_CODE'
    result = adapt(envelope([row]))
    assert result['eligible'] is False
    assert result['reason']
    assert not result.get('rows')


def test_safe_unsupported_row_makes_whole_page_ineligible_not_partly_mixed():
    rows = [api_row(), api_row('fixture-unknown', 'Normal')]
    rows[1]['TaxTypeCode'] = 'UNOBSERVED_FIXTURE_CODE'
    result = adapt(envelope(rows))
    assert result['eligible'] is False
    assert not result.get('rows')


@pytest.mark.parametrize('value', [[], {'not': 'scalar'}, 123, True])
def test_nontext_metadata_is_not_coerced_into_plausible_source_text(value):
    row = api_row()
    row['BpsNo'] = value
    result = adapt(envelope([row]))
    assert result['eligible'] is False
    assert not result.get('rows')


@pytest.mark.parametrize('bad_id', [None, '', 123, True])
def test_invalid_record_identity_fails_closed_instead_of_aggregate_substitution(bad_id):
    row = api_row()
    row['RecordId'] = bad_id
    with pytest.raises(RuntimeError, match='(?i)record|identity'):
        adapt(envelope([row]))


def test_missing_record_id_does_not_fall_back_to_existing_aggregate_identifier():
    row = api_row()
    del row['RecordId']
    with pytest.raises(RuntimeError, match='(?i)record|identity'):
        adapt(envelope([row]))


def test_repeated_record_id_is_unsafe_even_when_metadata_rows_are_identical():
    with pytest.raises(RuntimeError, match='(?i)duplicate|repeated|identity'):
        adapt(envelope([api_row(), api_row()]))


def test_other_taxpayer_row_fails_closed_before_unknown_schema_fallback():
    row = api_row()
    row['TaxpayerAggregateIdentifier'] = 'fixture-other-taxpayer'
    del row['ReturnSheetModel']
    with pytest.raises(RuntimeError, match='(?i)taxpayer|scope|identity'):
        adapt(envelope([row]))


def test_request_taxpayer_mismatch_fails_closed_even_for_empty_page():
    ctx = context()
    ctx['request']['TaxpayerAggregateIdentifier'] = 'fixture-other-taxpayer'
    payload = envelope([], total=0)
    payload['Payload']['Data'] = None
    with pytest.raises(RuntimeError, match='(?i)taxpayer|scope|identity'):
        adapt(payload, ctx)


@pytest.mark.parametrize('changes', [
    {'http_status': 401}, {'method': 'GET'},
    {'response_url': ORIGIN + '/returnsheet/api/returnsheetsrejected'},
    {'frame_url': SOURCE_URL.replace(TAXPAYER, 'fixture-other-taxpayer')},
    {'source_status': 'SPT Ditolak'}, {'sequence': 6},
])
def test_wrong_status_page_response_fails_closed(changes):
    ctx = context()
    ctx.update(changes)
    with pytest.raises(RuntimeError, match='(?i)status|source|frame|sequence|request|origin'):
        adapt(envelope(), ctx)


@pytest.mark.parametrize('url', [
    API_URL.replace('https:', 'http:'),
    API_URL.replace('coretax.intranet.pajak.go.id', 'untrusted.invalid'),
    API_URL.replace('https://', 'https://user@'),
    API_URL.replace('pajak.go.id/', 'pajak.go.id:444/'),
])
def test_foreign_or_credentialed_response_origin_is_never_safe_fallback(url):
    ctx = context()
    ctx['response_url'] = url
    with pytest.raises(RuntimeError, match='(?i)origin|source|request'):
        adapt(envelope(), ctx)


@pytest.mark.parametrize('successful', [False, 1, 'true', None])
def test_http_success_without_explicit_success_flag_fails_closed(successful):
    with pytest.raises(RuntimeError, match='(?i)success|status'):
        adapt(envelope(successful=successful))


@pytest.mark.parametrize('total', [True, -1, '1', 1.0])
def test_invalid_declared_count_is_not_coerced_or_silently_ignored(total):
    with pytest.raises(RuntimeError, match='(?i)count|total|records'):
        adapt(envelope(total=total))


def test_positive_total_with_null_data_cannot_be_certified_as_empty():
    payload = envelope([], total=1)
    payload['Payload']['Data'] = None
    with pytest.raises(RuntimeError, match='(?i)count|row|data|total'):
        adapt(payload)


def test_missing_rows_for_requested_page_fails_closed():
    with pytest.raises(RuntimeError, match='(?i)count|row|total'):
        adapt(envelope(total=3))


def test_bound_empty_page_preserves_null_observation_without_inventing_a_record():
    payload = envelope([], total=0)
    payload['Payload']['Data'] = None
    result = adapt(payload)
    assert result['eligible'] is True
    assert result['total'] == 0
    assert result['rows'] == []


def test_page_counts_do_not_turn_first_page_into_whole_list_completeness():
    ctx = context()
    ctx['request']['Rows'] = 2
    result = adapt(envelope([api_row(), api_row('fixture-amend', 'Amendment 001')], total=3), ctx)
    assert result['eligible'] is True
    assert result['total'] == 3
    assert len(result['rows']) == 2
    assert result.get('inventory_complete') is not True


def test_request_period_filter_contradiction_is_unsafe_not_unknown_schema():
    ctx = context()
    ctx['request']['Filters'] = [
        {'PropertyName': 'TaxPeriodCode', 'Value': '01122026', 'MatchMode': 'equals'}]
    with pytest.raises(RuntimeError, match='(?i)period|filter|scope'):
        adapt(envelope(), ctx)


@pytest.mark.parametrize('changes', [
    {'First': -1}, {'First': True}, {'Rows': 0}, {'Rows': True},
    {'isArchieved': True},
])
def test_unbound_or_invalid_page_request_is_not_safe_metadata_fallback(changes):
    ctx = context()
    ctx['request'].update(changes)
    with pytest.raises(RuntimeError, match='(?i)request|page|row|scope|archiv'):
        adapt(envelope(), ctx)


def test_submitted_endpoint_cannot_relabel_a_draft_record_as_submitted():
    row = api_row()
    row['ReturnSheetStatusCode'] = 'DRAFT'
    with pytest.raises(RuntimeError, match='(?i)status|source'):
        adapt(envelope([row]))


def test_more_rows_than_declared_total_fails_closed():
    rows = [api_row(), api_row('fixture-other', 'Amendment 001')]
    with pytest.raises(RuntimeError, match='(?i)count|row|total'):
        adapt(envelope(rows, total=1))


def synthetic_listing_browser(monkeypatch, *, unknown=False, unsafe=False, start=0,
                              changed_total=False, empty=False, stop_state=None):
    """Return only synthetic pages; abort every unregistered network target."""
    from contextlib import contextmanager
    from urllib.parse import urlsplit

    import coretax_browser as driver
    from playwright.sync_api import Locator, sync_playwright

    rows = [api_row(), api_row('fixture-amend-001', 'Amendment 001'), api_row('fixture-later-year', 'Normal')]
    rows[2]['TaxPeriodCode'] = '01122026'
    if unknown:
        for row in rows:
            del row['ReturnSheetModel']
    if unsafe:
        rows[0]['TaxpayerAggregateIdentifier'] = 'fixture-other-taxpayer'
    displays = [dict(EXPECTED_META), {**EXPECTED_META, 'Model SPT': 'Amendment 001'},
                {**EXPECTED_META, 'Masa Pajak': 'Januari - Desember 2026'}]
    if empty:
        rows = []
    labels = list(EXPECTED_META)
    metrics = {'submitted_full_grid_reads': 0, 'submitted_api_requests': 0,
               'unregistered_requests': 0, 'detail_actions': 0}
    original = Locator.evaluate

    def observed_evaluate(locator, expression, *args, **kwargs):
        if expression == driver.TABLE_JS and urlsplit(locator.page.url).path.startswith('/returnsheets/id-ID/submitted-returnsheets/'):
            metrics['submitted_full_grid_reads'] += 1
        return original(locator, expression, *args, **kwargs)

    monkeypatch.setattr(Locator, 'evaluate', observed_evaluate)

    search = '''<div class="main-content"><input id="ObjectPermitNumber"><table><tbody></tbody></table></div>
    <script>document.querySelector('input').onkeydown=e=>{
      if(e.key==='Enter'){
        const row=document.createElement('tr');row.innerHTML='<td>0000000000000001</td><td>Synthetic fixture</td><td><button>Pilih</button></td>';
        row.querySelector('button').onclick=()=>location.href='/returnsheets/id-ID/not-submitted-returnsheets/fixture-taxpayer';
        document.querySelector('tbody').appendChild(row);
      }
    };</script>'''

    def listing(submitted):
        import html
        headers = ''.join('<th>' + html.escape(label) + '</th>' for label in labels)
        config = json.dumps({'submitted': submitted, 'start': start if submitted else 0,
                             'headers': labels, 'displays': displays})
        endpoint = '/returnsheet/api/returnsheetssubmitted' if submitted else '/returnsheet/api/returnsheetsfixture'
        return '''<a href="/returnsheets/id-ID/submitted-returnsheets/fixture-taxpayer">SPT Dilaporkan</a>
        <div class="main-content"><p-table><table><thead><tr>''' + headers + '''</tr></thead><tbody></tbody></table>
        <div class="p-paginator"><button class="p-paginator-prev" onclick="first=0;load()">Previous</button>
        <button class="p-paginator-page p-highlight">1</button><button class="p-paginator-next" onclick="first+=2;load()">Next</button></div>
        </p-table></div><script>
        const config=''' + config + ''';let first=config.start;
        function load(){
          const request={TaxpayerAggregateIdentifier:'fixture-taxpayer',First:first,Rows:2,Filters:[],isArchieved:false,LanguageId:1,SortField:null,SortOrder:null};
          fetch(''' + json.dumps(endpoint) + ''',{method:'POST',body:JSON.stringify(request)}).then(r=>r.json()).then(body=>{
            const received=body.Payload.Data||[];const tbody=document.querySelector('tbody');tbody.replaceChildren();
            received.forEach((record,i)=>{
              const index=first+i;const row=document.createElement('tr');
              const view=document.createElement('button');view.id='ViewButton';view.textContent='View';
              view.onclick=()=>fetch('/fixture-disallowed-action');
              config.headers.forEach((label,column)=>{
                const td=document.createElement('td');td.textContent=config.displays[index][label];
                if(column===0)td.appendChild(view);
                row.appendChild(td);
              });tbody.appendChild(row);
            });
            document.querySelector('.p-highlight').textContent=String(first/2+1);
            document.querySelector('.p-paginator-prev').disabled=first===0;
            document.querySelector('.p-paginator-next').disabled=first+received.length>=body.Payload.TotalRecords;
          });
        }load();</script>'''

    @contextmanager
    def opened():
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel='msedge', headless=True)
            owned_context = browser.new_context(timezone_id='Asia/Jakarta')
            page = owned_context.new_page()
            page.set_default_timeout(5000)

            def handle(route):
                request = route.request
                url = urlsplit(request.url)
                if url.scheme != 'https' or url.netloc != 'coretax.intranet.pajak.go.id':
                    metrics['unregistered_requests'] += 1
                    route.abort()
                elif url.path == '/returnsheets/id-ID/taxpayer-search':
                    route.fulfill(body=search, content_type='text/html')
                elif url.path == '/returnsheets/id-ID/not-submitted-returnsheets/fixture-taxpayer':
                    route.fulfill(body=listing(False), content_type='text/html')
                elif url.path == '/returnsheets/id-ID/submitted-returnsheets/fixture-taxpayer':
                    route.fulfill(body=listing(True), content_type='text/html')
                elif url.path in ('/returnsheet/api/returnsheetsfixture', '/returnsheet/api/returnsheetssubmitted'):
                    data = request.post_data_json
                    assert request.method == 'POST'
                    assert data['TaxpayerAggregateIdentifier'] == TAXPAYER
                    assert data['Rows'] == 2 and type(data['First']) is int
                    submitted = url.path.endswith('/returnsheetssubmitted')
                    data_rows = rows[data['First']:data['First'] + 2] if submitted else []
                    if submitted:
                        metrics['submitted_api_requests'] += 1
                        if stop_state is not None:
                            stop_state['requested'] = True
                    total = len(rows) if submitted else 0
                    if submitted and changed_total and data['First'] > 0:
                        total += 1
                    route.fulfill(json=envelope(data_rows, total=total))
                else:
                    if url.path == '/fixture-disallowed-action':
                        metrics['detail_actions'] += 1
                    metrics['unregistered_requests'] += 1
                    route.abort()

            owned_context.route('**/*', handle)
            try:
                yield page, metrics
            finally:
                browser.close()

    return opened()


def test_supported_submitted_list_uses_json_metadata_not_dom_cells(tmp_path, monkeypatch):
    import coretax_browser as driver
    with synthetic_listing_browser(monkeypatch) as (page, metrics):
        result = driver.collect_inventory(page, '0000000000000001', 2024, 'period', tmp_path, max_pages=5)
        assert result['inventory_complete'] is True, result['errors']
        assert [row['record_id'] for row in result['records']] == ['fixture-normal', 'fixture-amend-001']
        assert result['records'][0]['meta'] == EXPECTED_META
        assert metrics['submitted_full_grid_reads'] == 0, 'Supported JSON metadata still read the full DOM grid'
        assert metrics['submitted_api_requests'] >= 2
        assert metrics['unregistered_requests'] == metrics['detail_actions'] == 0
        submitted = next(entry for entry in result['audit'] if entry['status'] == 'SPT Dilaporkan')
        assert submitted['requested_source'] == 'json-first'
        assert submitted['used_source'] == 'json'
        assert submitted['total'] == submitted['scanned'] == 3
        assert submitted['selected'] == 2


def test_unknown_metadata_schema_uses_audited_dom_page(tmp_path, monkeypatch):
    import coretax_browser as driver
    with synthetic_listing_browser(monkeypatch, unknown=True) as (page, metrics):
        result = driver.collect_inventory(page, '0000000000000001', 2024, 'period', tmp_path, max_pages=5)
        assert result['inventory_complete'] is True, result['errors']
        assert [row['record_id'] for row in result['records']] == ['fixture-normal', 'fixture-amend-001']
        assert result['records'][0]['meta'] == EXPECTED_META
        assert metrics['submitted_full_grid_reads'] >= 2
        assert metrics['unregistered_requests'] == metrics['detail_actions'] == 0
        submitted = next(entry for entry in result['audit'] if entry['status'] == 'SPT Dilaporkan')
        assert submitted['requested_source'] == 'json-first'
        assert submitted['used_source'] == 'dom-fallback'
        assert submitted['fallback_reason']


def test_unsafe_submitted_identity_does_not_start_dom_fallback(tmp_path, monkeypatch):
    import coretax_browser as driver
    with synthetic_listing_browser(monkeypatch, unsafe=True) as (page, metrics):
        result = driver.collect_inventory(page, '0000000000000001', 2024, 'period', tmp_path, max_pages=5)
        assert result['inventory_complete'] is False
        assert result['errors']
        assert result['records'] == []
        assert metrics['submitted_full_grid_reads'] == 0, 'Unsafe identity was hidden by a DOM fallback'
        assert metrics['unregistered_requests'] == metrics['detail_actions'] == 0


def test_json_inventory_resets_retained_pagination_and_preserves_amendments(tmp_path, monkeypatch):
    import coretax_browser as driver
    with synthetic_listing_browser(monkeypatch, start=2) as (page, metrics):
        result = driver.collect_inventory(page, '0000000000000001', 2024, 'period', tmp_path, max_pages=5)
        assert result['inventory_complete'] is True, result['errors']
        assert [row['record_id'] for row in result['records']] == ['fixture-normal', 'fixture-amend-001']
        assert metrics['submitted_full_grid_reads'] == 0
        submitted = next(entry for entry in result['audit'] if entry['status'] == 'SPT Dilaporkan')
        assert submitted['scanned'] == submitted['total'] == 3


def test_changed_total_between_pages_is_partial_not_certified(tmp_path, monkeypatch):
    import coretax_browser as driver
    with synthetic_listing_browser(monkeypatch, changed_total=True) as (page, metrics):
        result = driver.collect_inventory(page, '0000000000000001', 2024, 'period', tmp_path, max_pages=5)
        assert result['inventory_complete'] is False
        assert result['errors']
        submitted = next(entry for entry in result['audit'] if entry['status'] == 'SPT Dilaporkan')
        assert submitted['result'] == 'PARTIAL'
        assert metrics['detail_actions'] == metrics['unregistered_requests'] == 0


def test_json_inventory_page_limit_is_partial_not_first_page_complete(tmp_path, monkeypatch):
    import coretax_browser as driver
    with synthetic_listing_browser(monkeypatch) as (page, metrics):
        result = driver.collect_inventory(page, '0000000000000001', 2024, 'period', tmp_path, max_pages=1)
        assert result['inventory_complete'] is False
        assert result['errors']
        assert metrics['detail_actions'] == metrics['unregistered_requests'] == 0


def test_source_bound_empty_status_lists_are_reconciled_without_fake_records(tmp_path, monkeypatch):
    import coretax_browser as driver
    with synthetic_listing_browser(monkeypatch, empty=True) as (page, metrics):
        result = driver.collect_inventory(page, '0000000000000001', 2024, 'period', tmp_path, max_pages=5)
        assert result['inventory_complete'] is True, result['errors']
        assert result['records'] == []
        assert all(entry['total'] == entry['scanned'] == entry['selected'] == 0 for entry in result['audit'])
        assert metrics['detail_actions'] == metrics['unregistered_requests'] == 0


def test_stop_prevents_unknown_schema_dom_fallback(tmp_path, monkeypatch):
    import coretax_browser as driver

    class FixtureStop(RuntimeError):
        pass

    state = {'requested': False}
    def check_cancel():
        if state['requested']:
            raise FixtureStop('Synthetic cancellation requested')

    with synthetic_listing_browser(monkeypatch, unknown=True, stop_state=state) as (page, metrics):
        stopped = False
        result = None
        try:
            result = driver.collect_inventory(page, '0000000000000001', 2024, 'period', tmp_path,
                                              max_pages=5, check_cancel=check_cancel)
        except FixtureStop:
            stopped = True
        assert stopped or result['inventory_complete'] is False
        assert not result or result['records'] == []
        assert metrics['submitted_full_grid_reads'] == 0
        assert metrics['detail_actions'] == metrics['unregistered_requests'] == 0
