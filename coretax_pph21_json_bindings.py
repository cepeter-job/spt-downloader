"""PPh21 source projections from the pinned article-2126 public component.

These functions establish presentation only, never source identity or coverage.
The caller must bind primary custody, submitted lifecycle, model and migration.
"""
from decimal import Decimal
import math

from coretax_json import _CorporateNumber, _UnsupportedMetadata
from coretax_masa_bindings import _decimal, _number, _source_scalar, render_grid_value

_AMOUNT_SUFFIXES = (
    'IncomeTaxWithheld', 'CarryForward', 'PaymentWithSP2D',
    'IncomeTaxUnderpaidOverpaid', 'IncomeTaxPaidOnAmended',
    'IncomeTaxUnderpaidOverpaidDueToAmendment', 'IncomeTaxBorneByGovernment',
)
AMOUNT_CONTROLS = tuple(article + suffix for article in ('A21', 'A26')
                        for suffix in _AMOUNT_SUFFIXES)


def _safe(value):
    if not math.isfinite(value):
        raise _UnsupportedMetadata('nonfinite_pph21_number')
    decimal = Decimal(str(value))
    if abs(decimal) > Decimal('9007199254740991') or Decimal(format(decimal, '.15g')) != decimal:
        raise _UnsupportedMetadata('unverified_pph21_numeric_precision')
    return value


def _numeric(form, path, evidence, *, missing_zero=False):
    value = _source_scalar(form, path, evidence)
    if evidence[-1]['type'] == 'missing' and not missing_zero:
        # Math.round(undefined) is NaN, whereas Math.round(null) is zero.
        raise _UnsupportedMetadata('missing_pph21_direct_amount')
    if value is None:
        return 0.0
    if type(value) is not _CorporateNumber:
        raise _UnsupportedMetadata('unsupported_pph21_amount_type')
    decimal = _decimal(value)
    number = float(decimal)
    if Decimal(str(number)) != decimal:
        raise _UnsupportedMetadata('unverified_pph21_browser_conversion')
    return _safe(number)


def _round(value):
    # JS Math.round ties go towards positive infinity, including negative ties.
    # Avoid adding 0.5 to a large float, which can itself round before flooring.
    value = _safe(value)
    floor = math.floor(value)
    return _safe(floor + (1 if value - floor >= 0.5 else 0))


def _contribution_sum(form, article, suffix, evidence):
    paths = ([('Form1A', 'GrossIncomeAnd' + suffix, 'IncomeTax'),
              ('Form1B', 'GrossIncomeAnd' + suffix, 'IncomeTax')]
             if article == 'A21' else [])
    paths.append(('Form3', 'Article' + article[1:] + 'GrossIncomeAnd' + suffix, 'IncomeTax'))
    total = 0.0
    for path in paths:
        total = _safe(total + _numeric(form, path, evidence, missing_zero=True))
    return _round(total)


def _balance(form, article, evidence):
    withheld = _contribution_sum(form, article, 'IncomeTaxWithheld', evidence)
    carry = _round(_numeric(form, (article + 'CarryForward',), evidence))
    payment = _round(_numeric(form, (article + 'PaymentWithSP2D',), evidence))
    return _safe(_safe(withheld - carry) - payment)


def project_pph21_amount(form, control, *, model, migrated):
    """Project raw FormData through service calculation AND later child writes."""
    if (not isinstance(form, dict) or type(model) is not str or model not in ('NORMAL', 'AMENDMENT')
            or type(migrated) is not bool or type(control) is not str or control not in AMOUNT_CONTROLS):
        raise _UnsupportedMetadata('unsupported_pph21_amount_binding')
    article, suffix = control[:3], control[3:]
    evidence = []
    if suffix == 'IncomeTaxWithheld':
        value = _contribution_sum(form, article, suffix, evidence)
        rule = 'service_sum_then_child_round'
    elif suffix == 'IncomeTaxBorneByGovernment':
        stored = _numeric(form, (control,), evidence, missing_zero=True)
        value = (_contribution_sum(form, article, suffix, evidence) if stored == 0 else _round(stored))
        rule = 'zero_null_service_sum_else_stored_then_child_round'
    elif migrated and article == 'A21' and suffix in (
            'IncomeTaxUnderpaidOverpaid', 'IncomeTaxUnderpaidOverpaidDueToAmendment'):
        value = _round(_numeric(form, (control,), evidence))
        rule = 'migrated_a21_raw_balance'
    elif suffix == 'IncomeTaxUnderpaidOverpaid':
        value = _balance(form, article, evidence)
        rule = 'child_rounded_controls_balance'
    elif suffix == 'IncomeTaxUnderpaidOverpaidDueToAmendment' and model == 'AMENDMENT':
        balance = _balance(form, article, evidence)
        paid = _round(_numeric(form, (article + 'IncomeTaxPaidOnAmended',), evidence))
        value = _safe(balance - paid)
        rule = 'child_amendment_balance_after_base_model'
    else:
        value = _round(_numeric(form, (control,), evidence))
        rule = 'child_round_stored_value'
    return {'value': _number(str(value), 0, locale='id-ID'), 'rule': rule, 'provenance': evidence}


_BORNE = 'JUMLAH PENGHASILAN BRUTO DAN PAJAK PENGHASILAN YANG DITANGGUNG OLEH PEMERINTAH'
_WITHHELD = 'JUMLAH PENGHASILAN BRUTO DAN PAJAK PENGHASILAN YANG DIPOTONG'
_TOTAL = 'JUMLAH TOTAL PENGHASILAN BRUTO DAN PAJAK PENGHASILAN YANG DITANGGUNG OLEH PEMERINTAH SERTA PAJAK PENGHASILAN YANG DIPOTONG'
_TOTAL_KEY = 'TotalGrossIncomeAndIncomeTaxBorneByGovernmentAndIncomeTaxWithheld'
_COMMON_TOTALS = (('GrossIncomeAndIncomeTaxBorneByGovernment', _BORNE),
                  ('GrossIncomeAndIncomeTaxWithheld', _WITHHELD), (_TOTAL_KEY, _TOTAL))
_FOOTERS = {
    'l1a': ('Form1A', (5, 3, 1, 1, 1, 5), _COMMON_TOTALS),
    'l1b-bpa2': ('Form1B', (5, 3, 1, 1, 5), _COMMON_TOTALS),
    'l2-bpa2': ('Form2', (5, 5, 1, 1, 4), ((None, 'TOTAL'),)),
    'l3-bp21': ('Form3', (4, 4, 1, 1, 4), (
        ('Article21GrossIncomeAndIncomeTaxBorneByGovernment',
         'JUMLAH PENGHASILAN BRUTO UNTUK PASAL 21 DAN PAJAK PENGHASILAN PASAL 21 YANG DITANGGUNG OLEH PEMERINTAH'),
        ('Article21GrossIncomeAndIncomeTaxWithheld',
         'JUMLAH UNTUK PASAL 21 DAN PENGHASILAN BRUTO PASAL 21 SERTA PAJAK PENGHASILAN YANG DIPOTONG'))),
    'l3-bp26': ('Form3', (5, 7, 1, 1, 4), (
        ('Article26GrossIncomeAndIncomeTaxBorneByGovernment',
         'JUMLAH PENGHASILAN BRUTO UNTUK PASAL 26 DAN PAJAK PENGHASILAN PASAL 26 YANG DITANGGUNG OLEH PEMERINTAH'),
        ('Article26GrossIncomeAndIncomeTaxWithheld',
         'JUMLAH UNTUK PASAL 26 DAN PENGHASILAN BRUTO PASAL 26 SERTA PAJAK PENGHASILAN YANG DIPOTONG'),
        (_TOTAL_KEY, _TOTAL))),
}


def project_pph21_footer(grid_name, form):
    """Keep reported totals and physical blank spacer separate from body rows."""
    if not isinstance(form, dict) or type(grid_name) is not str:
        raise _UnsupportedMetadata('unsupported_pph21_footer_source')
    if grid_name in ('l1b-bpa1', 'l2-bpa1'):
        return {'footer': [], 'footer_spans': [], 'provenance': []}
    spec = _FOOTERS.get(grid_name)
    if spec is None:
        raise _UnsupportedMetadata('unsupported_pph21_footer_grid')
    root, spans, totals = spec
    if not isinstance(form.get(root), dict):
        raise _UnsupportedMetadata('missing_pph21_appendix_source')
    rows, evidence = [[]], []
    for key, label in totals:
        fields = ('TotalGrossIncome', 'TotalIncomeTax') if key is None else ('GrossIncome', 'IncomeTax')
        displayed = []
        for field in fields:
            path = (root, field) if key is None else (root, key, field)
            value = _source_scalar(form, path, evidence)
            displayed.append(render_grid_value('0' if value is None else value, 'number', footer=True))
        gross, tax = displayed
        rows.append(['', label, gross, '', tax, ''] if grid_name == 'l1a'
                    else ['', label, gross, tax, ''])
    return {'footer': rows, 'footer_spans': [[]] + [list(spans) for _ in totals],
            'provenance': evidence}
