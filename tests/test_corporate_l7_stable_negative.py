"""One synthetic raw-negative kernel regression; execution is CI-only."""
from copy import deepcopy

from coretax_corporate_projection import project_l7
from coretax_json import _corporate_json
from support_json_corpus import Number, wire
from test_corporate_l7_projection import BODY, ROOT, HEADERS, SPANS, raw_source


def test_l7_stable_negative_main_preserves_raw_profit_and_distinct_provenance():
    form = raw_source()
    form[BODY][0]['TaxYear'] = Number('2023')
    form[BODY][1].update(TaxYear=Number('2025'), FiscalNetProfitIncome=Number('-1234'))
    current = {'TaxType': 'ICT_RCIT', ROOT: form, 'MainFormData': {
        'NetIncomeBeforeTax': Number('-1234'), 'TaxYear': Number('2025'),
        'IsIncomeUnder': Number('0'), 'IsIncomeSolely': None, 'IsCarriedForward': Number('1')}}
    payload = _corporate_json(wire({
        'ReturnSheetStatusCode': 'SUBMITTED', 'ReturnSheetModel': 'NORMAL',
        'PeriodYear': Number('2025'), 'PreviousFormData': None,
        'LastSubmittedFormData': None, 'CurrentFormData': wire(current)}))
    current = _corporate_json(payload['CurrentFormData'])
    before = deepcopy((payload, current))

    # This pure seam assumes the caller's submitted/current-only lifecycle proof.
    # The payload represents that profile (outer carry absent), not native proof.
    # Three loaded pins and manifest-owned continuous L7 history are separate gates.
    # Expected source-only RED: unverified_corporate_l7_main_lifecycle, not an API error.
    result = project_l7(current[ROOT], main_form=current['MainFormData'],
        period_year=payload['PeriodYear'], headers=list(HEADERS),
        footer_spans=deepcopy(SPANS), tax_type=current['TaxType'], locale='id-ID')

    table = result['table']
    assert table['rows'][1] == ['2', '2025', '-1.234', '100', '200', '300', '400', '500', '600']
    assert table['footer'] == [['JUMLAH', '200', '400', '600', '800', '1.000', '1.200']]
    assert table['rows'][2:] == table['footer']
    assert (payload, current) == before

    evidence = result['provenance']
    main_entry, = [entry for entry in evidence
                   if entry['path'] == ['MainFormData', 'NetIncomeBeforeTax']]
    assert main_entry['type'] == 'number' and main_entry['value'] == '-1234'
    assert main_entry['rule'] == 'submitted-stable-negative-main/raw-profit-identity'
    profit_entry, = [entry for entry in evidence
                     if entry['path'] == [ROOT, BODY, 1, 'FiscalNetProfitIncome']]
    assert profit_entry['type'] == 'number' and profit_entry['value'] == '-1234'
    assert not any(entry['rule'] in ('submitted-nonnegative-main-invariant',
                                   'submitted-first-current-year-zero-to-main')
                   for entry in evidence)
