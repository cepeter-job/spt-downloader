"""Source-bound corporate presentation with separately proved form branches."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from decimal import Decimal, DecimalException
from fractions import Fraction
import re

from coretax_json import (ORIGIN, CORPORATE_COUNTRY_REFERENCE_URL, JsonSafetyError,
                          CORPORATE_L3_REFERENCE_URLS, CORPORATE_L3_GRID_URL, CORPORATE_L3_FOOTER_URL,
                          CORPORATE_L4_GRID_URL, CORPORATE_L4_FOOTER_URL,
                          CORPORATE_L11A_REFERENCE_URLS, CORPORATE_L11A_GRID_URLS,
                          CORPORATE_REFERENCE_REQUESTS, CORPORATE_L10_REFERENCE_URLS,
                          CORPORATE_L4_REFERENCE_URLS, CORPORATE_L2_REFERENCE_URLS,
                          CORPORATE_L9_REFERENCE_URLS, CORPORATE_INDUK_REFERENCE_URLS,
                          CORPORATE_L10A_GRID_URL,
                          _CorporateNumber, _UnsupportedMetadata, _corporate_json,
                          _corporate_request_key, _corporate_integer,
                          _select_reference_version, _reference_consumer_order, _reference_locale)
from coretax_masa_bindings import _decimal, _number, _evidence
from coretax_build_pins import load_build_pins

CIT_SOURCE = ORIGIN + '/returnsheets/id-ID/525.c5690c441d8dbc45.js'
MAIN_SOURCE = ORIGIN + '/returnsheets/id-ID/main.16a01374a2a1ece5.js'
VENDOR_SOURCE = ORIGIN + '/returnsheets/id-ID/vendor.c32c4ee39d966e30.js'

def _corporate_pins(urls):
    pins = load_build_pins()
    return {url: pins[url] for url in urls if url in pins}

BUILD_DIGESTS = _corporate_pins((CIT_SOURCE, MAIN_SOURCE))
L7_NEGATIVE_BUILD_DIGESTS = _corporate_pins((CIT_SOURCE, MAIN_SOURCE, VENDOR_SOURCE))
L7_OWNER_CHAIN = ['rshshr-corporate-income-tax-return', 'rshshr-citr-l7-form',
                  'rsh-citr-l7-grid1', 'p-table', 'table']
L11C_BUILD_DIGESTS = {**BUILD_DIGESTS, **_corporate_pins((VENDOR_SOURCE,))}
L10C_BUILD_DIGESTS = dict(L11C_BUILD_DIGESTS)
L1D_BUILD_DIGESTS = dict(L11C_BUILD_DIGESTS)
L3_BUILD_DIGESTS = dict(L11C_BUILD_DIGESTS)
L11A_BUILD_DIGESTS = dict(L11C_BUILD_DIGESTS)
L8_BUILD_DIGESTS = dict(L11C_BUILD_DIGESTS)
L11B_HYDRATED_BUILD_DIGESTS = _corporate_pins((CIT_SOURCE, MAIN_SOURCE, VENDOR_SOURCE))
L10B_BUILD_DIGESTS = dict(L11C_BUILD_DIGESTS)
L10B_KIND = 'corporate-l10b-nondisplay-v1'
L10B_ROOT = 'L10bFormData'
L10B_KEYS = tuple('Question' + suffix for suffix in
    ('1a', '1b', '1c', '1d', '2a', '2b', '2c', '3a', '3b', '3c', '3d', '3e', '4a', '4b', '4c'))
INDUK_ROOT = 'MainFormData'
# The reviewed identity slots, spelled exactly as
# coretax_badan_template._INDUK_IDENTITY declares them. A caption is never a
# binding: every slot below also names the payload control it is read from.
INDUK_IDENTITY_FIELDS = (
    ('HEADER', 'TaxYear', 'Tahun Pajak/Bagian Tahun Pajak'),
    ('HEADER', 'Status', 'Status'),
    ('HEADER', 'AccountingPeriodStart', 'Periode Pembukuan'),
    ('HEADER', 'AccountingPeriodEnd', 'Periode Pembukuan'),
    ('A. IDENTITAS WAJIB PAJAK', 'Tin', '1. NPWP'),
    ('A. IDENTITAS WAJIB PAJAK', 'Name', '2. Nama'),
    ('B. INFORMASI LAPORAN KEUANGAN', 'TinAccountant', '2.b. NPWP Kantor Akuntan Publik'),
    ('B. INFORMASI LAPORAN KEUANGAN', 'NameAccountant', '2.c. Nama Kantor Akuntan Publik'),
    ('A. IDENTITAS WAJIB PAJAK', 'EmailAddress', '3. Alamat Email'),
    ('A. IDENTITAS WAJIB PAJAK', 'PhoneNumber', '4. Nomor Telepon'),
)
INDUK_UNPROJECTED_REASON = 'unprojected_induk_captions'
L10A_ROOT = 'DeclarationTransactionRelatedParties'
L10A_GRID_ENDPOINT = CORPORATE_L10A_GRID_URL
L10A_GRID_NAME = 'L10-A/l10a-grid'
# The pinned L10-A panel owns no scalar body control: it remembers the declared
# root but only re-reads PeriodYear/CollectorTin from outer baseFormData.
# All worksheet body data belongs to the independent l10a-grid response.
# Columns and captions are read from that owner's initColumn()/ngOnChanges.
L10A_COLUMNS = ('Name', 'TIN', 'Country', 'RelationshipCode', 'BusinessActivity',
                'TypeOfTransaction', 'TransactionValue', 'PricingMethod', 'ReasonPricingMethod')
# Row 2 of the approved L10-A sheet, in the reviewed grid order.
L10A_HEADERS = ['Nama', 'NPWP/TIN', 'Negara', 'BENTUK HUBUNGAN', 'Kegiatan Usaha',
                'Jenis Transaksi', 'NILAI TRANSAKSI (Rupiah)',
                'METODE PENENTUAN HARGA TRANSFER YANG DIGUNAKAN', 'ALASAN PENGGUNAAN METODE']


L6_ROOT = 'FiscalYearIncomeTax'
# Approved Angsuran PPh 25 captions in template order (rows 2..8, column B).
L6_FIELDS = (
    ('IncomeAsTheBasisOfInstallment',
     '1. PENGHASILAN YANG MENJADI DASAR PENGHITUNGAN ANGSURAN'),
    ('FiscalLossCompensation',
     '2. KOMPENSASI KERUGIAN FISKAL (Diisi dari Formulir Lampiran-07 Jumlah Kompensasi '
     'Kerugian Fiskal Tahun Pajak Berjalan)'),
    ('TaxableIncome', '3. PENGHASILAN KENA PAJAK'),
    ('IncomeTaxPayable', '4. PPh YANG TERUTANG'),
    ('TaxCreditWitheld',
     '5. KREDIT PAJAK TAHUN PAJAK YANG LALU ATAS PENGHASILAN YANG TERMASUK DALAM '
     'ANGKA 1 YANG DIPOTONG/DIPUNGUT PIHAK LAIN'),
    ('IncomeTaxSelfpaid', '6. PPh YANG HARUS DIBAYAR SENDIRI'),
    ('FollowingFiscalYear', '7. ANGSURAN PPh PASAL 25'),
)
# Non-display edit markers the pinned L6 owner always submits next to the values.
L6_EDIT_FLAGS = ('IncomeAsTheBasisOfInstallmentEdited', 'IncomeTaxPayableEdited',
                 'TaxCreditWitheldEdited')

L9_ROOT = 'RecapitulationFiscalDepreciationAmortization'
# Approved L9 recap totals: template sheet rows 226..228 and 259..261 hold these
# six captions in column A and the amount in column H. Each one is the payload
# control the pinned owner's `getFormData()` emits for that slot.
L9_FIELDS = (
    ('TotalFiscalDepreciationTangible', 'JUMLAH PENYUSUTAN FISKAL'),
    ('TotalCommercialDepreciationTangible', 'JUMLAH PENYUSUTAN KOMERSIAL'),
    ('DiferencesDepreciationTangible', 'SELISIH PENYUSUTAN'),
    ('TotalFiscalAmortization', 'JUMLAH AMORTISASI FISKAL'),
    ('TotalCommercialAmortization', 'JUMLAH AMORTISASI KOMERSIAL'),
    ('DiferencesAmortization', 'SELISIH AMORTISASI'),
)
# The pinned owner's twelve per-group grid totals, in `TotalTable1..12` order:
# tables 1..7 are the tangible groups, 8..12 the intangible ones.
L9_TABLE_TOTALS = tuple('TotalTable' + str(index) for index in range(1, 13))
L9_KEYS = frozenset([name for name, _ in L9_FIELDS] + list(L9_TABLE_TOTALS))
# Only the two differences may be negative; every other control is a sum.
L9_SIGNED = frozenset(('DiferencesDepreciationTangible', 'DiferencesAmortization'))
L9_UNPROJECTED_REASON = 'unprojected_l9_grid_rows'
# The twelve grid requests the observer declares, in the order it appends them.
L9_GRIDS = tuple(
    ('L9/' + suffix + '/' + group, ORIGIN + '/returnsheet/api/loadcit/' + suffix)
    for suffix, groups in (
        ('l9-table-1-grid', ('Group 1', 'Group 2', 'Group 3', 'Group 4', 'Other Group')),
        ('l9-table-2-grid', ('Permanent', 'Non-permanent')),
        ('l9-table-3-grid', ('Group 1', 'Group 2', 'Group 3', 'Group 4', 'Other Group')))
    for group in groups)
L9_GRID_HEADERS = ['KODE HARTA', 'KELOMPOK/JENIS HARTA', 'BULAN/TAHUN PEROLEHAN',
    'BIAYA PEROLEHAN (Rp)', 'NILAI SISA BUKU FISKAL PADA AWAL TAHUN (Rp)',
    'METODE PENYUSUTAN/AMORTISASI / KOMERSIAL', 'METODE PENYUSUTAN/AMORTISASI / FISKAL',
    'PENYUSUTAN/AMORTISASI FISKAL TAHUN INI (Rp)', 'KETERANGAN']
L9_GRID_SPANS = [[], [7, 1, 1]]
L9_GRID_COLUMNS = ('GroupAssetType', 'GroupAssetType', 'MonthYearAcquisition',
    'AcquisitionPrice', 'RemainingBeginningValue', 'MethodCommercial', 'MethodFiscal',
    'FiscalYearValue', 'Notes')
L9_ROW_METADATA = frozenset(('GroupType', 'CodeOfAsset', 'RecordId', 'Index', 'Action'))
L9_REFERENCE_KINDS = ('TANGIBLE_ASSET', 'COMMERCIAL_METHOD', 'FISCAL_METHOD',
                      'GROUP_OF_BUILDINGS', 'INTANGIBLE_ASSET')
L9_DETAIL_BUILD_DIGESTS = _corporate_pins((CIT_SOURCE, MAIN_SOURCE, VENDOR_SOURCE))
INDUK_SUBMITTED_BUILD_DIGESTS = _corporate_pins((CIT_SOURCE, MAIN_SOURCE, VENDOR_SOURCE))
# Caption-only template slots bind the actual amount input, NOT the radio
# control whose question shares its label. See the pinned submitted proof.
INDUK_SUBMITTED_FIELDS = (
    ('D. PENGHITUNGAN PPh', 'NetIncomeBeforeTax', '4. Penghasilan Neto Fiskal sebelum Fasilitas Pajak'),
    ('D. PENGHITUNGAN PPh', 'IncomeTaxInAYear', '12. PPh Terutang'),
    ('E. PENGURANG PPh TERUTANG', 'TotalIncomeTaxOverseas', '13. Apakah terdapat kredit pajak yang dibayarkan di luar negeri dan/atau dipotong/pungut oleh pihak lain? / Tidak / Ya'),
    ('E. PENGURANG PPh TERUTANG', 'InstallmentOfIncome', '14. Angsuran PPh Pasal 25'),
    ('E. PENGURANG PPh TERUTANG', 'NoticeOfCollection', '15. Surat Tagihan Pajak PPh Pasal 25 (hanya pokok pajak)'),
    ('F. PPh KURANG/LEBIH BAYAR', 'UnderpaymentIncomeTax', '17.a. PPh yang Kurang/Lebih Bayar'),
    ('F. PPh KURANG/LEBIH BAYAR', 'TotalApprovalInstallment', '17.b. Apakah terdapat Surat Keputusan Persetujuan Pengangsuran atau Penundaan Pembayaran Pajak? / Tidak / Ya'),
    ('F. PPh KURANG/LEBIH BAYAR', 'IncomeTaxMustPaid', '17.c. PPh yang masih harus dibayar atau lebih dibayar'),
)
# Original fixed-point no-activity submitted profile. These three inputs
# are predicates, never aliases for the blank-name amount caption controls.
INDUK_INACTIVE_SELECTORS = ('IsIncomeSubject', 'IsIncomeExcluded', 'IsIncomeTaxDeduction')
INDUK_INACTIVE_FIELDS = (
    ('C. PENGHASILAN YANG DIKENAKAN PPh YANG BERSIFAT FINAL DAN YANG TIDAK TERMASUK OBJEK PAJAK',
     'TotalIncomeSubject',
     '2. Apakah Wajib Pajak menerima atau memperoleh penghasilan yang dikenakan PPh yang bersifat final? * / Tidak / Ya'),
    ('C. PENGHASILAN YANG DIKENAKAN PPh YANG BERSIFAT FINAL DAN YANG TIDAK TERMASUK OBJEK PAJAK',
     'TotalIncomeExcluded',
     '3. Apakah Wajib Pajak menerima atau memperoleh penghasilan yang tidak termasuk objek pajak? * / Tidak / Ya'),
    ('E. PENGURANG PPh TERUTANG', 'TotalIncomeTaxDeduction',
     '16. Apakah Wajib Pajak memperoleh Fasilitas Pengurangan PPh Badan? * / Tidak / Ya'),
    ('F. PPh KURANG/LEBIH BAYAR', 'UnderpaymentIncomeDueAmended',
     '18.b. PPh yang kurang atau lebih bayar karena pembetulan'),
)


def _induk_inactive_profile(main):
    """Exact original fixed point: three selectors and amounts are 0, last null."""
    if not isinstance(main, dict):
        return False
    for key in (*INDUK_INACTIVE_SELECTORS,
                *(name for _, name, _ in INDUK_INACTIVE_FIELDS[:3])):
        if key not in main or type(main[key]) is not _CorporateNumber or main[key] != '0':
            return False
    last = INDUK_INACTIVE_FIELDS[-1][1]
    return last in main and main[last] is None


L11C_ROOT, L11C_BODY = 'L11CFormData', 'ForeignPrivateDebtReports'
L11C_AMOUNTS = ('DebtPrincipalBeginningOfYear', 'AdditionOfDebtPrincipal',
    'SubstractionOfDebtPrincipal', 'DebtPrincipalEndOfYear', 'AmountOfInterest',
    'BorrowingCostOtherThanInterest')
L11C_TOTALS = ('TotalDebtPrincipalBeginningOfYear', 'TotalAdditionOfDebtPrincipal',
    'TotalSubstractionOfDebtPrincipal', 'TotalDebtPrincipalEndOfYear', 'TotalInterest',
    'TotalBorrowingCostOtherThanInterest')
L11C_COLUMNS = ('NameOfCreditor', 'AddressOfCreditor', 'CountryOfCreditor', 'Currency',
    'EndOfYearRate', *L11C_AMOUNTS[:4], 'LoanStartDate', 'LoanDueDate', 'InterestRate',
    *L11C_AMOUNTS[4:], 'LoanAllocation')
L11C_HEADERS = ['NO.', 'PEMBERI PINJAMAN / NAMA', 'PEMBERI PINJAMAN / ALAMAT',
    'PEMBERI PINJAMAN / NEGARA/YURISDIKSI', 'MATA UANG / KODE', 'MATA UANG / KURS AKHIR TAHUN',
    'POKOK UTANG (Rp) / AWAL TAHUN', 'POKOK UTANG (Rp) / MUTASI / PENAMBAHAN',
    'POKOK UTANG (Rp) / MUTASI / PENGURANGAN', 'POKOK UTANG (Rp) / AKHIR TAHUN',
    'JANGKA WAKTU PINJAMAN / Tanggal Mulai', 'JANGKA WAKTU PINJAMAN / Tanggal Jatuh Tempo',
    'BUNGA / TINGKAT (%)', 'BUNGA / JUMLAH (Rp)',
    'BIAYA TERKAIT PEROLEHAN PINJAMAN SELAIN BUNGA (Rp)', 'PERUNTUKAN PINJAMAN']
L11C_SPANS = [[1, 5, *([1] * 10)]]
L11B_ROOT = 'L11BFormData'
# Only the first four literal controls have a stable submitted/manual branch.
# EBITDA, its quarter and conditional Part II remain explicit omissions.
L11B_FIELDS = (
    ('CommercialNettIncome', '1. PENGHASILAN NETO KOMERSIAL'),
    ('DepreciationAndAmortizationExpenses', '2. BEBAN PENYUSUTAN DAN AMORTISASI'),
    ('IncomeTaxExpense', '3. BEBAN PAJAK PENGHASILAN'),
    ('BorrowingCostExpense', '4. BEBAN BIAYA PINJAMAN'),
)
L11B_COST_ROW = ('Name', 'AverageDebtBalances', 'BorrowingCostAmount',
                 'BorrowingCostThatCanBeDeducted', 'BorrowingCostThatAreNotDeductible')
L11B_COST_HEADERS = ['PEMBERI PINJAMAN', 'Saldo Rata-Rata Utang', 'Biaya Pinjaman (Bunga)',
    'Biaya Pinjaman Yang Dapat Diperhitungkan', 'Biaya Pinjaman Yang Tidak Dapat Diperhitungkan']
L11B_PART_II_GROUP = 'II. PERBANDINGAN ANTARA UTANG DAN MODAL (DEBT TO EQUITY RATIO)'
L11B_GROUPS = ('A. PENGHITUNGAN RATA-RATA SALDO UTANG',
              'B. PENGHITUNGAN SALDO RATA-RATA MODAL', 'III. PENGHITUNGAN BIAYA PINJAMAN')
L11B_MONTH_HEADERS = (
    ['PEMBERI PINJAMAN / ' + label for label in ('Nomor Identitas', 'Nama', 'Hubungan')]
    + ['SALDO UTANG TIAP AKHIR BULAN (Rp) / ' + label for label in
       [*[f'Bulan - {month}' for month in range(1, 13)], 'RATA-RATA']],
    ['RINCIAN MODAL'] + ['SALDO MODAL TIAP AKHIR BULAN (Rp) / ' + label for label in
       [*[f'Bulan - {month}' for month in range(1, 13)], 'RATA-RATA']],
)


def l11b_tables(part_ii):
    indices = (0, 1, 2) if part_ii else (2,)
    return [{'component': f'rsh-citr-l11b-form-grid{index + 1}',
             'headers': list((*L11B_MONTH_HEADERS, L11B_COST_HEADERS)[index]),
             'source_structure': {'form': 'L11-B', 'component': f'rsh-citr-l11b-form-grid{index + 1}',
                                  'groups': ([L11B_PART_II_GROUP] if index < 2 else []) + [L11B_GROUPS[index]]},
             'footer_spans': [[3, *([1] * 13)]] if index == 0 else [[1] * (14 if index == 1 else 5)]}
            for index in indices]
# getFormData reads n.TotalBorrowingCosts, which is not a FormGroup control:
# undefined is omitted by JSON. A present alias (even null) is unreviewed.
L11B_KEYS = frozenset({
    *(name for name, _ in L11B_FIELDS), 'Ebitda', 'Ebitda25',
    'DebtBalanceAverage', 'TotalDebtBalanceAverage', 'EquityBalanceAverage',
    'TotalEquityBalanceAverage', 'DebtToEquityRatio', 'BorrowingCosts',
    'TotalBorrowingCosts', 'IsDocumentListForm', 'IsEbitdaManuallyEdited'})
L7_ROOT = 'CalculationOfFiscalLossCompensation'
L7_BODY = 'FiscalNetProfitAndLossCompensation'
L7_SUFFIXES = ('YearMinus4', 'YearMinus3', 'YearMinus2', 'YearMinus1', 'YearCurrent', 'YearNext')
L2_ROOT, L2_AFFILIATES = 'ListOfOwnership', 'InvestmentList'
L2_SHAREHOLDERS = 'ListOfShareholders'
L2_TOTALS = ('TotalPaidInCapital', 'TotalPaidInCapitalPercentage', 'TotalDividend',
             'TotalDebt', 'TotalReceivable')
L2_UNPROJECTED_REASON = 'unprojected_l2_owner_rendering'
L2_BUILD_DIGESTS = _corporate_pins((CIT_SOURCE, MAIN_SOURCE, VENDOR_SOURCE))
L2_SHAREHOLDER_HEADERS = ['NO.', 'NAMA', 'ALAMAT', 'NEGARA', 'NPWP/NIK', 'Jabatan',
    'Modal Disetor / NILAI (Rp)', 'Modal Disetor / %', 'DIVIDEN/PEMBAGIAN LABA(Rp)']
L2_SHAREHOLDER_SPANS = [[1, 5, 1, 1, 1]]
L2_COMPONENTS = ('rsh-citr-l2-form-grid1', 'rsh-citr-l2-form-grid2')
L2_GROUPS = (
    'A. DAFTAR PEMEGANG SAHAM/PEMILIK MODAL DAN JUMLAH DIVIDEN/PEMBAGIAN LABA YANG DIBAGIKAN SERTA DAFTAR SUSUNAN PENGURUS DAN KOMISARIS',
    'B. DAFTAR PENYERTAAN MODAL, UTANG, DAN/ATAU PIUTANG PADA PERUSAHAAN AFILIASI')
# Block B's approved Rupiah template headers.
L2_AFFILIATE_HEADERS = ['NO.', 'NAMA', 'NEGARA', 'NPWP/NIK',
    'PENYERTAAN MODAL / NILAI (Rp)', 'PENYERTAAN MODAL / %',
    'UTANG / NILAI (Rp)', 'UTANG / TAHUN', 'UTANG / BUNGA UTANG/TAHUN',
    'PIUTANG / NILAI (Rp)', 'PIUTANG / TAHUN', 'PIUTANG / BUNGA UTANG/TAHUN']
L2_AFFILIATE_SPANS = [[1, 5, 1, 2, 1, 2]]
_MAX_INTEGER = 999999999999999


def _integer(value):
    if type(value) is not _CorporateNumber:
        raise _UnsupportedMetadata('unsupported_corporate_l7_numeric_type')
    try:
        number = _decimal(value)
        if abs(number) > _MAX_INTEGER or number != number.to_integral_value():
            raise _UnsupportedMetadata('unsupported_corporate_l7_numeric_precision')
        return int(number)
    except DecimalException:
        raise _UnsupportedMetadata('unsupported_corporate_l7_numeric_precision') from None


def _year(value):
    if (type(value) not in (str, _CorporateNumber) or len(value) > 32
            or not re.fullmatch(r'[0-9]+', value) or not 1900 <= int(value) <= 2100):
        raise _UnsupportedMetadata('unsupported_corporate_l7_year')
    return int(value)


def l7_headers(year):
    return ['NO.', 'LABA (RUGI) NETTO FISKAL / TAHUN/BAGIAN TAHUN PAJAK',
            'LABA (RUGI) NETTO FISKAL / NILAI (Rp)',
            *[f'KOMPENSASI KERUGIAN FISKAL / Y-{offset} / NILAI (Rp)' for offset in (4, 3, 2, 1)],
            f'KOMPENSASI KERUGIAN FISKAL / {year} / TAHUN PAJAK INI - NILAI (Rp)',
            'KOMPENSASI KERUGIAN FISKAL / Y+1 / TAHUN PAJAK BERJALAN - NILAI (Rp)']


def project_l7(form, *, main_form, period_year, headers, footer_spans, tax_type, locale):
    """Caller proves submitted initialization, current source, loaded pins and route.

    Nonnegative inputs retain the legacy initialization rule. Negative inputs
    require the closed current-main subset and raw first-profit identity below;
    callers independently prove Payload absence/null predicates and continuous
    capture-owned lifetime. This pure calculation grants no native admission.
    Preserve reported totals only after proving equality with the six ordered
    JS reductions. Exact integral operands and partial sums avoid float guesses.
    """
    year = _year(period_year)
    if (type(period_year) is not _CorporateNumber or str(year) != period_year
            or tax_type not in ('ICT_RCIT', 'ICT_ROGCIT') or locale != 'id-ID'
            or headers != l7_headers(year) or footer_spans != [[3, 1, 1, 1, 1, 1, 1]]):
        raise _UnsupportedMetadata('unverified_corporate_l7_structure')
    total_keys = ['TotalFiscalLossCompensation' + suffix for suffix in L7_SUFFIXES]
    row_keys = ['TaxYear', 'FiscalNetProfitIncome'] + ['FiscalLossCompensation' + suffix for suffix in L7_SUFFIXES]
    if (not isinstance(form, dict) or set(form) != {L7_BODY, *total_keys}
            or not isinstance(form[L7_BODY], list) or not form[L7_BODY]
            or any(not isinstance(row, dict) or set(row) != set(row_keys) for row in form[L7_BODY])
            or not isinstance(main_form, dict) or 'NetIncomeBeforeTax' not in main_form):
        raise _UnsupportedMetadata('unsupported_corporate_l7_source_shape')
    main_value = main_form['NetIncomeBeforeTax']
    main_number = _integer(main_value)
    negative = main_number < 0
    if negative and (tax_type != 'ICT_RCIT'
            or any(key not in main_form for key in ('IsIncomeUnder', 'IsIncomeSolely', 'IsCarriedForward', 'TaxYear'))
            or main_form['IsIncomeSolely'] is not None
            or _integer(main_form['IsIncomeUnder']) != 0
            or _integer(main_form['IsCarriedForward']) != 1
            or type(main_form['TaxYear']) is not _CorporateNumber
            or _year(main_form['TaxYear']) != year):
        raise _UnsupportedMetadata('unverified_corporate_l7_main_lifecycle')
    years = [_year(row['TaxYear']) for row in form[L7_BODY]]
    if year not in years:
        # Pinned child dereferences find(currentYear) when main first changes.
        raise _UnsupportedMetadata('unverified_corporate_l7_current_year_row')
    first_current = years.index(year)
    if negative and _integer(form[L7_BODY][first_current]['FiscalNetProfitIncome']) != main_number:
        raise _UnsupportedMetadata('unverified_corporate_l7_raw_profit_identity')
    totals, rows, provenance = [0] * 6, [], []
    for index, source in enumerate(form[L7_BODY]):
        values = [_integer(source[key]) for key in row_keys[1:]]
        for column, value in enumerate(values[1:]):
            totals[column] += value
            if abs(totals[column]) > _MAX_INTEGER:
                raise _UnsupportedMetadata('unsafe_corporate_l7_ordered_total')
        profit = main_value if index == first_current and values[0] == 0 else source['FiscalNetProfitIncome']
        rendered = [str(index + 1), str(source['TaxYear']),
                    _number(profit, 0, locale=locale),
                    *[_number(source[key], 0, locale=locale) for key in row_keys[2:]]]
        rows.append(rendered)
        for column, key in enumerate(row_keys, 1):
            entry = _evidence(source[key], [L7_ROOT, L7_BODY, index, key])
            entry.update(destination={'table': 'L7', 'row': index, 'column': column},
                         rule='literal-year' if key == 'TaxYear' else 'angular-number-1.0-0-id')
            if index == first_current and key == 'FiscalNetProfitIncome' and values[0] == 0:
                entry['rule'] = 'submitted-first-current-year-zero-to-main'
            provenance.append(entry)
    footer = ['JUMLAH']
    for column, key in enumerate(total_keys):
        if _integer(form[key]) != totals[column]:
            raise _UnsupportedMetadata('unreconciled_corporate_l7_reported_total')
        footer.append(_number(form[key], 0, locale=locale))
        entry = _evidence(form[key], [L7_ROOT, key])
        entry.update(destination={'table': 'L7', 'footer': 0, 'column': column + 3},
                     rule='reconciled-reported-total/angular-number-1.0-0-id')
        provenance.append(entry)
    main_entry = _evidence(main_value, ['MainFormData', 'NetIncomeBeforeTax'])
    main_entry.update(rule=('submitted-stable-negative-main/raw-profit-identity' if negative
                            else 'submitted-nonnegative-main-invariant'),
                      destination={'table': 'L7', 'row': first_current, 'column': 2})
    provenance.append(main_entry)
    count = len(rows)
    return {'table': {'name': 'L7', 'headers': list(headers), 'rows': rows + [footer],
                     'footer': [footer], 'footer_spans': [[3, 1, 1, 1, 1, 1, 1]],
                     'body_row_count': count, 'source_total': count, 'complete': True},
            'provenance': provenance}


L8_ROOT = 'CalculationFacilitiesIncomeTaxRateReduction'
L8_HEADERS = ['NO.', 'DESKRIPSI', 'AMOUNT (Rupiah)']
_L8_GROUP = ('PERHITUNGAN FASILITAS PENGURANGAN TARIF PPh BAGI WAJIB PAJAK BADAN DALAM NEGERI '
             'BERDASARKAN PASAL 31E AYAT (1) UNDANG-UNDANG PPh')
_L8_KEYS = (
    'GrossTurnOver',
    'TaxableIncomeShareOfGrossCirculationGrantedFacility',
    'TaxableIncomeShareOfGrossCirculationNotGrantedFacility',
    'IncomeTaxPayableFromTaxableIncomeShareOfGrossCirculationGrantedFacility',
    'IncomeTaxPayableFromTaxableIncomeShareOfGrossCirculationNotGrantedFacility',
    'TotalIncomeTax',
)
_L8_CAPTIONS = (
    'Jumlah Peredaran Bruto',
    'Penghasilan Kena Pajak',
    'Penghasilan Kena Pajak dari bagian peredaran bruto yang memperoleh fasilitas',
    'Penghasilan Kena Pajak dari bagian peredaran bruto yang tidak memperoleh fasilitas',
    'Pajak Terutang',
    'PPh Terutang atas Penghasilan Kena Pajak dari bagian peredararan bruto yang memperoleh fasilitas',
    'PPh Terutang atas Penghasilan Kena Pajak dari bagian peredararan bruto yang tidak memperoleh fasilitas',
)
_L8_SPANS = ((1, 2), (1, 1, 1), (1, 2), (1, 1, 1), (1, 1, 1), (1, 2), (1, 1, 1), (1, 1, 1))


def _l8_integer(value):
    if type(value) is not _CorporateNumber:
        raise _UnsupportedMetadata('unsupported_corporate_l8_numeric_type')
    try:
        number = _decimal(value)
    except DecimalException:
        raise _UnsupportedMetadata('unsupported_corporate_l8_numeric_precision') from None
    # Exact integral tokens only: no fractional truncation, no signed zero,
    # no overflow. Negative integers are legitimate (loss-making returns).
    if (abs(number) > _MAX_INTEGER or number != number.to_integral_value()
            or number.is_zero() and number.is_signed()):
        raise _UnsupportedMetadata('unsupported_corporate_l8_numeric_precision')
    return int(number)


def project_l8(form, *, main_form, period_year, headers, footer_spans, tax_type, locale):
    """Pure projection, never native admission or proof of stable main inputs.

    Caller proves loaded sources, current data, final original main operands and
    effective grid rate 1 throughout the relevant Rupiah lifecycle. The parent's
    optional captured exchange control cannot prove the grid rate. Preserve
    reported values only when initialization and recalculation agree; the
    reviewed integer bound makes the supported 11% multiplication exact.
    """
    if (tax_type != 'ICT_RCIT' or locale != 'id-ID' or headers != L8_HEADERS
            or footer_spans != [[1, 1, 1]]
            or any(type(span) is not int for span in footer_spans[0])):
        raise _UnsupportedMetadata('unverified_corporate_l8_structure')
    required = set(_L8_KEYS)
    if (not isinstance(form, dict) or set(form) not in (required, required | {'ExchangeRateValue'})
            or not isinstance(main_form, dict)
            or not {'TaxYear', 'TaxableIncome', 'TotalGrossIncomeResearch'} <= set(main_form)
            or ('ExchangeRateValue' in form and form['ExchangeRateValue'] is not None
                and type(form['ExchangeRateValue']) is not _CorporateNumber)):
        raise _UnsupportedMetadata('unsupported_corporate_l8_source_shape')
    if (type(period_year) is not _CorporateNumber or not re.fullmatch(r'[0-9]{4}', period_year)
            or not 2020 <= int(period_year) <= 2100
            or type(main_form['TaxYear']) is not _CorporateNumber or main_form['TaxYear'] != period_year):
        raise _UnsupportedMetadata('unverified_corporate_l8_rate_year')
    values = [_l8_integer(form[key]) for key in _L8_KEYS]
    taxable = _l8_integer(main_form['TaxableIncome'])
    research = _l8_integer(main_form['TotalGrossIncomeResearch'])
    if research != 0 or values[0] < 0:
        raise _UnsupportedMetadata('unverified_corporate_l8_branch')
    if taxable > 0:
        # 31E-eligible branch: reviewed turnover bound, thousand mask, 11%.
        if values[0] > 4800000000:
            raise _UnsupportedMetadata('unverified_corporate_l8_branch')
        masked = taxable - taxable % 1000
        tax = (masked // 100) * 11
    else:
        # No taxable base (loss or nil): the facility rows are inert zeros and
        # the captured turnover is reported exactly, never rounded.
        masked = tax = 0
    if values[1:5] != [masked, 0, tax, 0]:
        raise _UnsupportedMetadata('unreconciled_corporate_l8_reported_values')
    if values[5] != values[3] + values[4] or values[5] != tax:
        raise _UnsupportedMetadata('unreconciled_corporate_l8_reported_total')

    rendered = [_number(form[key], 0, locale=locale) for key in _L8_KEYS]
    body = [
        ['1.', _L8_CAPTIONS[0]], ['', _L8_CAPTIONS[0], rendered[0]],
        ['2.', _L8_CAPTIONS[1]], ['', _L8_CAPTIONS[2], rendered[1]], ['', _L8_CAPTIONS[3], rendered[2]],
        ['3.', _L8_CAPTIONS[4]], ['', _L8_CAPTIONS[5], rendered[3]], ['', _L8_CAPTIONS[6], rendered[4]],
    ]
    footer = ['', 'Jumlah PPh Terutang', rendered[5]]
    destinations = [{'table': 'L8', 'row': row, 'column': 2} for row in (1, 3, 4, 6, 7)]
    destinations.append({'table': 'L8', 'footer': 0, 'column': 2})
    provenance = []
    for index, key in enumerate(_L8_KEYS):
        entry = _evidence(form[key], [L8_ROOT, key])
        entry.update(source='current', destination=deepcopy(destinations[index]),
                     rule='reconciled-captured/input-number-integer-id')
        if index in (3, 4):
            entry['also_supports'] = [deepcopy(destinations[-1])]
        provenance.append(entry)
    for key in ('TaxableIncome', 'TotalGrossIncomeResearch'):
        entry = _evidence(main_form[key], ['MainFormData', key])
        entry.update(source='current', destinations=deepcopy(destinations[1:]),
                     rule='reconciled-original-main-input')
        provenance.append(entry)
    for value, path, source, control in (
            (main_form['TaxYear'], ['MainFormData', 'TaxYear'], 'current', 'rate-year'),
            (period_year, ['PeriodYear'], 'primary', 'header-year')):
        entry = _evidence(value, path)
        entry.update(source=source, destination={'table': 'L8', 'control': control},
                     rule='matched-original-rate-and-header-years')
        provenance.append(entry)
    if 'ExchangeRateValue' in form:
        entry = _evidence(form['ExchangeRateValue'], [L8_ROOT, 'ExchangeRateValue'])
        entry.update(source='current', destination={'table': 'L8', 'control': 'unused-rupiah-exchange-rate'},
                     rule='retained-unused-rupiah-source-control')
        provenance.append(entry)
    return {'table': {'name': 'L8', 'group': _L8_GROUP, 'headers': list(headers),
                     'rows': body + [footer], 'footer': [footer], 'footer_spans': [[1, 1, 1]],
                     'body_spans': [list(spans) for spans in _L8_SPANS],
                     'body_rowspans': [[1] * len(row) for row in body],
                     'source_structure': {'form': 'L8', 'component': 'rsh-citr-l8-form-grid1',
                                          'groups': [_L8_GROUP]},
                     'pages': 1, 'body_row_count': 8, 'source_total': 8, 'complete': True},
            'provenance': provenance}


L10C_ROOT = 'L10cFormData'
L10C_BODY = 'ListTaxHavenCountry'
L10C_HEADERS = ['NO.', 'NAMA MITRA TRANSAKSI', 'Jenis Transaksi', 'NEGARA',
                'NILAI TRANSAKSI (RUPIAH)']
_L10C_COLUMNS = ('NameOfTransactionPartner', 'TypeOfTransaction', 'CountryCode', 'TransactionValue')
L10C_UNPROJECTED_REASON = 'unprojected_l10c_controls'
_L10C_QUESTION = ('II. PENENTUAN HARGA TRANSAKSI DI ATAS, DITENTUKAN DENGAN MENGGUNAKAN '
                  'PRINSIP KEWAJARAN DAN KELAZIMAN USAHA')


def _l10c_number(value, locale):
    """Actual DecimalPipe defaults: 1.0-3 with half-up on Number.toString digits.

    The fifteen-digit subset must survive the JS Number shortest decimal
    representation unchanged before the reviewed formatter rounds it. Exact
    provider excerpts are exercised on the hosted runner, not copied/executed
    locally. Null interpolates blank, never the online formatter's zero.
    """
    if value is None:
        return ''
    if type(value) is not _CorporateNumber:
        raise _UnsupportedMetadata('unsupported_corporate_l10c_number_type')
    try:
        number = _decimal(value)
        normalized = number.normalize()
        if (abs(number) > _MAX_INTEGER or len(normalized.as_tuple().digits) > 15
                or number.is_zero() and number.is_signed()
                or Decimal(str(float(number))) != number):
            raise _UnsupportedMetadata('unsupported_corporate_l10c_number_precision')
        return _number(value, 3, locale=locale, trim=True)
    except DecimalException:
        raise _UnsupportedMetadata('unsupported_corporate_l10c_number_precision') from None


def project_l10c(form, *, headers, footer_spans, tax_type, locale, labels):
    """Pure populated candidate, NOT native admission or catalog custody.

    Caller-supplied labels are transformation inputs, never catalog evidence.
    The native dispatch independently requires original same-attempt catalogs,
    positive loaded provider pins and manifest-owned current child custody.
    The shared producer/joint-snapshot integration remains independently required.
    Preserve nondisplayed controls; never infer the radio selection or fabricate
    a total/footer from getFormData's unconditional zero.
    """
    if (headers != L10C_HEADERS or footer_spans != [] or tax_type != 'ICT_RCIT' or locale != 'id-ID'
            or not isinstance(labels, dict) or set(labels) != {'TRANSACTION_TYPE', 'COUNTRY_CODE'}
            or any(not isinstance(value, dict) for value in labels.values())):
        raise _UnsupportedMetadata('unverified_corporate_l10c_structure')
    if (not isinstance(form, dict) or set(form) - {L10C_BODY, 'TotalTransactionValue',
            'DeterminationOfTransactionQuestion'}
            or not {'TotalTransactionValue', 'DeterminationOfTransactionQuestion'} <= set(form)
            or type(form['TotalTransactionValue']) is not _CorporateNumber
            or type(form['DeterminationOfTransactionQuestion']) not in (bool, str, _CorporateNumber, type(None))):
        raise _UnsupportedMetadata('unsupported_corporate_l10c_source_shape')
    original_body = form.get(L10C_BODY)
    body = [] if original_body is None else original_body
    if (not isinstance(body, list) or len(body) > 10000
            or any(not isinstance(row, dict) or set(row) != set(_L10C_COLUMNS) for row in body)):
        raise _UnsupportedMetadata('unsupported_corporate_l10c_rows')
    rows, provenance = [], []
    for index, source in enumerate(body):
        rendered = [str(index + 1)]
        for column, key in enumerate(_L10C_COLUMNS, 1):
            value = source[key]
            entry = _evidence(value, [L10C_ROOT, L10C_BODY, index, key])
            if key == 'TransactionValue':
                text = _l10c_number(value, locale)
                rule = 'angular-number-default-1.0-3-id/number-to-string-round-half-up/null-blank'
            elif value is None or type(value) is str:
                text = '' if value is None else value
                rule = 'literal-string/null-blank'
                if key in ('TypeOfTransaction', 'CountryCode') and text:
                    kind = 'TRANSACTION_TYPE' if key == 'TypeOfTransaction' else 'COUNTRY_CODE'
                    choices = labels[kind]
                    if (value not in choices or type(choices[value]) is not str or not choices[value].strip()):
                        raise _UnsupportedMetadata('unbound_corporate_l10c_description')
                    text, rule = choices[value], 'caller-bound-reference-description/no-native-custody'
            else:
                raise _UnsupportedMetadata('unsupported_corporate_l10c_text_type')
            rendered.append(text)
            entry.update(destination={'table': 'L10-C', 'row': index, 'column': column}, rule=rule)
            provenance.append(entry)
        rows.append(rendered)
    if not body:
        provenance.append({'path': [L10C_ROOT, L10C_BODY],
            'type': 'null' if original_body is None else 'array',
            'value': None if original_body is None else '[]', 'rule': 'retained-original-empty-body'})
    total = _evidence(form['TotalTransactionValue'], [L10C_ROOT, 'TotalTransactionValue'])
    total['rule'] = 'retained-nondisplayed-total/no-footer/no-sum'
    question_value = form['DeterminationOfTransactionQuestion']
    # Boolean evidence is local to this candidate, never a widened Masa scalar
    # contract or a claim that boolean true selects the string-valued radio.
    question = ({'path': [L10C_ROOT, 'DeterminationOfTransactionQuestion'],
                 'type': 'boolean', 'value': question_value} if type(question_value) is bool else
                _evidence(question_value, [L10C_ROOT, 'DeterminationOfTransactionQuestion']))
    question['rule'] = 'retained-unresolved-radio/no-selection-inference'
    provenance.extend((total, question))
    return {'table': {'name': 'L10-C', 'headers': list(headers), 'rows': rows,
                     'footer': [], 'footer_spans': [], 'body_row_count': len(body),
                     'source_total': len(body), 'complete': True},
            'fields': [], 'projection_complete': False, 'projection_reason': L10C_UNPROJECTED_REASON,
            'projection_unresolved_fields': [
                {'group': 'HEADER', 'field': 'PeriodYear', 'label': 'Tahun Pajak'},
                {'group': 'HEADER', 'field': 'CollectorTin', 'label': 'Nomor Identitas WP'},
                {'group': '', 'field': 'Question', 'label': _L10C_QUESTION}],
            'provenance': provenance}


def _apply_l10c(binding, section, observed_forms, *, root, payload, record, event, reference_packets):
    """Consume shared original catalogs; caller labels can never be permission."""
    proof = binding['projection']
    keys = {'kind', 'builds', 'route', 'locale', 'timezone', 'tables', 'references', 'visibility_binding'}
    if (not isinstance(proof, dict) or set(proof) != keys
            or proof['kind'] != 'corporate-l10c-v1'
            or proof['builds'] != L10C_BUILD_DIGESTS
            or set(L10C_BUILD_DIGESTS) != {CIT_SOURCE, MAIN_SOURCE, VENDOR_SOURCE}
            or any(type(value) is not str or not re.fullmatch(r'[a-f0-9]{64}', value)
                   for value in L10C_BUILD_DIGESTS.values())
            or proof['locale'] != 'id-ID' or proof['timezone'] != 'Asia/Jakarta'
            or proof['visibility_binding'] != 'current-induk-enabled-v1'
            or proof['route'] != event['frame_url'] or binding.get('paths') != [[L10C_ROOT]]
            or any(binding.get(key) for key in ('grids', 'responses', 'dependencies'))
            or event.get('component_lifetime') is None or event.get('corporate_l10c_lifetime') is None):
        raise _UnsupportedMetadata('unverified_corporate_l10c_semantic_binding')
    fields = record.get('source_fields', {})
    route = ORIGIN + '/returnsheets/id-ID/corporate-income-tax-return/' + '/'.join(
        str(value) for value in (fields.get('TaxpayerAggregateIdentifier'), record['record_id'],
                                fields.get('TaxTypeCode'), fields.get('AggregateIdentifier'))) + '?view=true'
    main = root.get('MainFormData')
    literal = record.get('meta', {}).get('Model SPT')
    model = ('NORMAL' if literal == 'Normal' else 'AMENDMENT'
             if isinstance(literal, str) and re.fullmatch(r'Amendment [0-9]{3}', literal) else None)
    if (proof['route'] != route or fields.get('TaxTypeCode') != 'ICT_RCIT'
            or record.get('source_status') != 'SPT Dilaporkan'
            or model is None
            or fields.get('ReturnSheetModel') != literal
            or payload.get('ReturnSheetStatusCode') != 'SUBMITTED'
            or payload.get('ReturnSheetModel') != model
            or any(key not in payload or payload[key] is not None
                   for key in ('PreviousFormData', 'LastSubmittedFormData'))
            or 'Induk' not in [form['name'] for form in observed_forms[:observed_forms.index(binding)]]
            or not _current_induk_visibility(payload, main, 'IsTransactionWithRelated', proof)
            or type(payload.get('PeriodYear')) is not _CorporateNumber
            or type(payload.get('TIN')) is not str):
        raise _UnsupportedMetadata('unverified_corporate_l10c_submitted_lifecycle')
    tables = proof['tables']
    if (not isinstance(tables, list) or tables != [{'component': 'rsh-citr-l10c-grid1',
            'headers': L10C_HEADERS, 'footer_spans': []}]):
        raise _UnsupportedMetadata('unverified_corporate_l10c_grid_owner')
    references = proof['references']
    if not isinstance(references, list) or not 1 <= len(references) <= 4:
        raise _UnsupportedMetadata('missing_corporate_l10c_reference_bindings')
    catalogs, sources, contributors, urls = {}, {}, [], set()
    needed = {'COUNTRY_CODE', 'TRANSACTION_TYPE'}
    for ref in references:
        if (not isinstance(ref, dict) or set(ref) != {'endpoint', 'method', 'sequences'}
                or ref['method'] != 'GET' or ref['endpoint'] in urls):
            raise _UnsupportedMetadata('unsupported_corporate_l10c_reference_binding')
        kinds = CORPORATE_REFERENCE_REQUESTS.get(ref['endpoint'])
        if not kinds or not set(kinds) <= needed:
            raise _UnsupportedMetadata('unsupported_corporate_l10c_reference_binding')
        urls.add(ref['endpoint'])
        sequences = ref['sequences']
        if (not isinstance(sequences, list) or not sequences
                or any(type(number) is not int or number <= 0 for number in sequences)
                or sequences != sorted(set(sequences))):
            raise _UnsupportedMetadata('unsupported_corporate_l10c_reference_sequences')
        actual = sorted(number for number, packet in reference_packets.items()
                        if packet['event']['url'] == ref['endpoint'])
        if sequences != actual or any(not reference_packets[number]['successful'] for number in actual):
            raise _UnsupportedMetadata('missing_or_failed_corporate_l10c_catalog')
        for number in sequences:
            source = reference_packets[number]
            for kind in kinds:
                catalog = _project_corporate_catalog(source['payload'], kind=kind,
                    requested_types=kinds, clock_interval=source['event'].get('clock_interval'))
                contributors.append((kind, catalog, source['event']))
                if kind not in sources or number < sources[kind]['sequence']:
                    catalogs[kind], sources[kind] = catalog, source['event']
    actual_urls = {packet['event']['url'] for packet in reference_packets.values()
                   if set(CORPORATE_REFERENCE_REQUESTS.get(packet['event']['url'], ())) & needed}
    if urls != actual_urls or set(catalogs) != needed:
        raise _UnsupportedMetadata('unbound_corporate_l10c_catalog')
    result = project_l10c(root.get(L10C_ROOT), headers=tables[0]['headers'],
        footer_spans=tables[0]['footer_spans'], tax_type=fields['TaxTypeCode'], locale=proof['locale'],
        labels={kind: catalog['lookups'] for kind, catalog in catalogs.items()})
    section['tables'], section['fields'] = [result['table']], result['fields']
    for key in ('projection_complete', 'projection_reason', 'projection_unresolved_fields'):
        section[key] = deepcopy(result[key])
    for entry in tuple(result['provenance']):
        entry.update(response_sequence=event['sequence'], container=['Payload', 'CurrentFormData'])
        kind = {'TypeOfTransaction': 'TRANSACTION_TYPE', 'CountryCode': 'COUNTRY_CODE'}.get(entry['path'][-1])
        if kind is not None and entry['value'] in catalogs[kind]['selected']:
            entry['rule'] = 'bound-original-reference-description'
            result['provenance'].append({**deepcopy(catalogs[kind]['selected'][entry['value']]),
                'response_sequence': sources[kind]['sequence'], 'container': ['Payload'],
                'destination': deepcopy(entry['destination'])})
    for kind, catalog, source in contributors:
        result['provenance'].extend({**deepcopy(entry), 'response_sequence': source['sequence'],
            'container': ['Payload'], 'destination': {'table': 'L10-C', 'reference': kind}}
            for entry in catalog['provenance'])
    for key in ('PeriodYear', 'TIN', 'ReturnSheetStatusCode', 'ReturnSheetModel',
                'PreviousFormData', 'LastSubmittedFormData', 'IsTransactionWithRelated'):
        if key in payload:
            entry = _evidence(payload[key], [key])
            entry.update(response_sequence=event['sequence'], container=['Payload'],
                         rule='retained-original-l10c-base-header-or-lifecycle-control')
            result['provenance'].append(entry)
    entry = _evidence(main['IsTransactionWithRelated'], ['MainFormData', 'IsTransactionWithRelated'])
    entry.update(response_sequence=event['sequence'], container=['Payload', 'CurrentFormData'],
                 rule='current-induk-callback/owned-enabled-l10c')
    result['provenance'].append(entry)
    return {'form': 'L10-C', 'kind': proof['kind'], 'builds': dict(proof['builds']),
        'route': proof['route'], 'values': result['provenance'], 'presence_facts': [{
            'response_sequence': event['sequence'], 'container': ['Payload'],
            'path': ['IsTransactionWithRelated'], 'present': 'IsTransactionWithRelated' in payload,
            'rule': 'outer-selection-presence/current-induk-enabled'}]}


def _l11c_integer(value):
    if type(value) is not _CorporateNumber:
        raise _UnsupportedMetadata('unsupported_corporate_l11c_number_type')
    number = _decimal(value)
    if abs(number) > _MAX_INTEGER or number != number.to_integral_value():
        raise _UnsupportedMetadata('unsupported_corporate_l11c_number_precision')
    return int(number)


def _l11c_date(value):
    if value is None or value == '':
        return ''
    if type(value) is not str or not (
            re.fullmatch(
                r'[0-9]{4}-[0-9]{2}-[0-9]{2}(?:T(?:[01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]'
                r'(?:\.[0-9]{1,3})?Z)?', value)
            or re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}T00:00:00\+07:00', value)):
        raise _UnsupportedMetadata('unsupported_corporate_l11c_date')
    try:
        date = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if date.year == 1:
            return ''  # Validated normalized ISO year0001 is the source sentinel.
        if not 1970 <= date.year <= 2100:
            raise ValueError('Unreviewed date range')
        date = date.replace(tzinfo=timezone.utc) if date.tzinfo is None else date
        return date.astimezone(timezone(timedelta(hours=7))).strftime('%d-%m-%Y')
    except (ValueError, OverflowError):
        raise _UnsupportedMetadata('unsupported_corporate_l11c_date') from None


def project_countries(payload, *, clock_interval=None):
    """Exact naturally observed COUNTRY_CODE consumer; never read browser cache."""
    return _project_corporate_catalog(payload, kind='COUNTRY_CODE', clock_interval=clock_interval)


def _project_corporate_catalog(payload, *, kind, clock_interval=None, requested_types=None):
    """Reviewed singleton or exact ordered pair; preserve original array paths."""
    _reference_locale(payload)
    requested = (kind,) if requested_types is None else tuple(requested_types)
    if (kind not in {*CORPORATE_L3_REFERENCE_URLS, *CORPORATE_L11A_REFERENCE_URLS,
                    *CORPORATE_L10_REFERENCE_URLS, *CORPORATE_L4_REFERENCE_URLS,
                    *CORPORATE_L2_REFERENCE_URLS, *CORPORATE_L9_REFERENCE_URLS,
                    *CORPORATE_INDUK_REFERENCE_URLS}
            or requested not in ((kind,), ('DEDUCTION_METHOD', 'TYPE_OF_FULFILLMENT'))
            or kind not in requested or not isinstance(payload, list) or len(payload) != len(requested)
            or any(not isinstance(item, dict) or type(item.get('ReferenceDataType')) is not str
                   for item in payload)
            or {item['ReferenceDataType'] for item in payload} != set(requested)):
        raise _UnsupportedMetadata('unsupported_corporate_country_catalog')
    catalog_index = next(index for index, item in enumerate(payload) if item['ReferenceDataType'] == kind)
    catalog, groups, evidence = payload[catalog_index], {}, []
    if not isinstance(catalog.get('Details'), list):
        raise _UnsupportedMetadata('unsupported_corporate_country_catalog')
    if 'language' in catalog and catalog['language'] != 'id-ID':
        raise JsonSafetyError('Corporate country locale contradicts observed source')
    evidence.append(_evidence(kind, [catalog_index, 'ReferenceDataType']))
    descriptions = {}
    ordered, order_rule = _reference_consumer_order(catalog['Details'], kind)
    for index, row in enumerate(catalog['Details']):
        if (not isinstance(row, dict) or type(row.get('Code')) is not str or not row['Code']
                or type(row.get('CodeDescription')) is not str or not row['CodeDescription'].strip()):
            raise _UnsupportedMetadata('unsupported_corporate_country_description')
        if 'language' in row and row['language'] != 'id-ID':
            raise JsonSafetyError('Corporate country locale contradicts observed source')
        for key in ('ValidFrom', 'ValidTo'):
            if key in row and row[key] is not None and type(row[key]) is not str:
                raise _UnsupportedMetadata('unsupported_corporate_country_validity')
        for key in ('Code', 'CodeDescription', 'ValidFrom', 'ValidTo', 'ParameterData'):
            entry = (_evidence(row[key], [catalog_index, 'Details', index, key]) if key in row else
                     {'path': [catalog_index, 'Details', index, key], 'type': 'missing', 'value': None})
            evidence.append(entry)
            if key == 'CodeDescription':
                descriptions[index] = entry
    for index, row in ordered:
        groups.setdefault(row['Code'], []).append((index, row))
    lookups, selected = {}, {}
    for code, candidates in groups.items():
        # w1.getFullPosition uses ordered .find, NOT the active-version service.
        # L2 retains its separate duplicate refusal through requires_vendor.
        if kind == 'RELATED_PERSON_TYPE':
            index, row = candidates[0]
            rule = 'first-ordered-code-match'
        else:
            index, row, rule = _select_reference_version(candidates, clock_interval)
        lookups[code] = row['CodeDescription']
        entry = descriptions[index]
        entry['rule'] = ('reviewed-country-active-version:' if kind == 'COUNTRY_CODE'
                         else 'reviewed-related-person-' if kind == 'RELATED_PERSON_TYPE'
                         else 'reviewed-corporate-catalog-active-version:') + rule
        entry['catalog_order_rule'] = order_rule
        if clock_interval is not None and rule not in ('first-open-ended', 'only-version',
                                                       'first-ordered-code-match'):
            entry['clock_interval'] = dict(clock_interval)
        selected[code] = deepcopy(entry)
    return {'lookups': lookups, 'provenance': evidence, 'selected': selected,
            'raw_catalog': deepcopy(catalog), 'catalog_index': catalog_index,
            'requires_vendor': any(len(items) > 1 for items in groups.values())}


def bind_corporate_reference_catalogs(references, reference_packets, *, kinds, event, builds):
    """Bind existing packet custody before reusing the one ordinary catalog consumer.

    Only already reviewed singleton transports participate. Other observed
    catalogs remain fully checked custody, not implicit form dependencies.
    """
    from coretax_json import (_corporate_reference_builds, _capture_clock_interval,
                              _capture_corporate_reference_providers, _capture_component_lifetime)

    urls = {types[0]: url for url, types in CORPORATE_REFERENCE_REQUESTS.items() if len(types) == 1}
    if (not isinstance(kinds, (tuple, list)) or not kinds or len(set(kinds)) != len(kinds)
            or any(kind not in urls for kind in kinds)
            or not isinstance(references, list) or len(references) != len(kinds)
            or not _corporate_reference_builds(builds)):
        raise _UnsupportedMetadata('unverified_corporate_reference_binding')
    providers, lifetime, clock = (event.get(key) for key in
        ('corporate_reference_providers', 'component_lifetime', 'clock_interval'))
    if not isinstance(providers, dict) or not isinstance(lifetime, dict) or clock is None:
        raise _UnsupportedMetadata('missing_corporate_reference_custody')
    _capture_component_lifetime(lifetime, attempt=event.get('attempt'),
        record_id=event.get('record_id'), source_url=providers.get('source_url'),
        detail_url=event.get('frame_url'))
    _capture_corporate_reference_providers(providers, attempt=event.get('attempt'),
        record_id=event.get('record_id'), source_url=lifetime.get('source_url'),
        detail_url=event.get('frame_url'))
    _capture_clock_interval(clock, event.get('attempt'))
    if builds != providers['builds']:
        raise _UnsupportedMetadata('unverified_corporate_reference_builds')
    expected = {urls[kind]: kind for kind in kinds}
    catalogs, seen = {}, set()
    for ref in references:
        if (not isinstance(ref, dict) or set(ref) != {'endpoint', 'method', 'sequences'}
                or type(ref['endpoint']) is not str or ref['endpoint'] not in expected
                or ref['endpoint'] in seen or ref['method'] != 'GET'
                or not isinstance(ref['sequences'], list) or not ref['sequences']):
            raise _UnsupportedMetadata('unsupported_corporate_reference_binding')
        seen.add(ref['endpoint'])
        sequences = ref['sequences']
        if any(type(n) is not int or n <= 0 for n in sequences) or len(set(sequences)) != len(sequences):
            raise JsonSafetyError('Corporate reference sequence is invalid or repeated')
        actual = {n for n, packet in reference_packets.items() if packet['event']['url'] == ref['endpoint']}
        if actual != set(sequences) or any(reference_packets[n]['successful'] is not True for n in actual):
            raise _UnsupportedMetadata('missing_or_failed_corporate_reference_packet')
        hashes = set()
        for sequence in sequences:
            source = reference_packets[sequence]['event']
            if (source.get('sequence') != sequence or source.get('method') != 'GET'
                    or source.get('request_json') is not None
                    or any(source.get(key) != event.get(key) for key in
                        ('attempt', 'record_id', 'frame_url', 'clock_interval',
                         'component_lifetime', 'corporate_reference_providers'))):
                raise JsonSafetyError('Corporate reference packet custody contradicts primary')
            hashes.add(source['sha256'])
        if len(hashes) != 1:
            raise JsonSafetyError('Corporate reference full snapshot changed')
        first = reference_packets[min(sequences)]
        kind = expected[ref['endpoint']]
        catalog = _project_corporate_catalog(first['payload'], kind=kind,
            clock_interval=clock, requested_types=(kind,))
        catalogs[kind] = {**catalog, 'source': deepcopy(first['event']), 'sequences': sorted(sequences)}
    return catalogs


def project_l11c(form, *, headers, footer_spans, tax_type, locale, timezone_name, country_labels):
    """Caller proves loaded provider/consumer pins and submitted current lifecycle."""
    if (headers != L11C_HEADERS or footer_spans != L11C_SPANS or tax_type != 'ICT_RCIT'
            or locale != 'id-ID' or timezone_name != 'Asia/Jakarta' or not isinstance(country_labels, dict)):
        raise _UnsupportedMetadata('unverified_corporate_l11c_structure')
    if not isinstance(form, dict) or set(form) != {L11C_BODY, *L11C_TOTALS}:
        raise _UnsupportedMetadata('unsupported_corporate_l11c_source_shape')
    body = [] if form[L11C_BODY] is None else form[L11C_BODY]
    if (not isinstance(body, list) or len(body) > 10000
            or any(not isinstance(row, dict) or set(row) != set(L11C_COLUMNS) for row in body)):
        raise _UnsupportedMetadata('unsupported_corporate_l11c_source_shape')
    rows, evidence, sums = [], [], [0] * len(L11C_AMOUNTS)
    for index, source in enumerate(body):
        rendered = [str(index + 1)]
        for column, key in enumerate(L11C_COLUMNS, 1):
            value = source[key]
            entry = _evidence(value, [L11C_ROOT, L11C_BODY, index, key])
            entry['destination'] = {'table': 'L11-C', 'row': index, 'column': column}
            if key in L11C_AMOUNTS:
                number = 0 if value is None else _l11c_integer(value)
                position = L11C_AMOUNTS.index(key)
                sums[position] += number
                if abs(sums[position]) > _MAX_INTEGER:
                    raise _UnsupportedMetadata('unsafe_corporate_l11c_ordered_total')
                digits = 2 if key == 'DebtPrincipalEndOfYear' else 0
                text = _number(str(number), digits, locale=locale)
                entry['rule'] = 'nullish-zero/angular-number-id' if value is None else 'angular-number-id'
            elif key == 'InterestRate':
                # Live rates carry up to two fraction digits; the integer helper
                # only proved whole percentages.
                if value is None:
                    text = ''
                else:
                    number = _decimal(value)
                    if abs(number) > _MAX_INTEGER or number.as_tuple().exponent < -2:
                        raise _UnsupportedMetadata('unsupported_corporate_l11c_number_precision')
                    text = _number(str(number), 2, locale=locale)
                entry['rule'] = 'angular-number-1.2-2-id'
            elif key == 'EndOfYearRate' and type(value) in (int, float, _CorporateNumber):
                # The live build sends the year-end rate as a JSON number while
                # the reviewed fixture keeps the locale-formatted string.
                number = _decimal(value)
                if number != number.to_integral_value() or abs(number) > _MAX_INTEGER:
                    raise _UnsupportedMetadata('unsupported_corporate_l11c_number_precision')
                text = _number(str(int(number)), 2, locale=locale)
                entry['rule'] = 'angular-number-1.2-2-id'
            elif key in ('LoanStartDate', 'LoanDueDate'):
                text = _l11c_date(value)
                entry['rule'] = 'validated-date/normalized-sentinel/jakarta-dd-MM-yyyy'
            elif key == 'CountryOfCreditor':
                if value is None or value == '':
                    text = ''
                elif type(value) is str and value in country_labels and type(country_labels[value]) is str:
                    text = country_labels[value]
                else:
                    raise _UnsupportedMetadata('unbound_corporate_country_description')
                entry['rule'] = 'country-code-to-description'
            elif value is None or type(value) is str:
                text = '' if value is None else value
                entry['rule'] = 'literal-string'
            else:
                raise _UnsupportedMetadata('unsupported_corporate_l11c_text_type')
            rendered.append(text)
            evidence.append(entry)
        rows.append(rendered)
    amounts = []
    for index, key in enumerate(L11C_TOTALS):
        if _l11c_integer(form[key]) != sums[index]:
            raise _UnsupportedMetadata('unreconciled_corporate_l11c_reported_total')
        amounts.append(_number(form[key], 2 if index == 3 else 0, locale=locale))
        entry = _evidence(form[key], [L11C_ROOT, key])
        entry.update(destination={'table': 'L11-C', 'footer': 0, 'column': (6, 7, 8, 9, 13, 14)[index]},
                     rule='reconciled-reported-total/angular-number-id')
        evidence.append(entry)
    footer = ['', 'JUMLAH', *amounts[:4], '', '', '', *amounts[4:], '']
    return {'table': {'name': 'L11-C', 'headers': list(headers), 'rows': rows + [footer],
        'footer': [footer], 'footer_spans': deepcopy(L11C_SPANS), 'body_row_count': len(body),
        'source_total': len(body), 'complete': True}, 'provenance': evidence}


def _apply_l11c(binding, section, observed_forms, *, root, payload, record, event, country_packets):
    proof = binding['projection']
    if (not isinstance(proof, dict) or set(proof) != {'kind', 'builds', 'route', 'locale', 'timezone', 'tables', 'references'}
            or proof['kind'] != 'corporate-l11c-v1' or proof['builds'] != L11C_BUILD_DIGESTS
            or proof['route'] != event['frame_url'] or binding.get('paths') != [[L11C_ROOT]]
            or binding.get('grids', []) or binding.get('responses', []) or binding.get('dependencies', [])):
        raise _UnsupportedMetadata('unsupported_corporate_l11c_semantic_binding')
    fields = record.get('source_fields', {})
    route = ORIGIN + '/returnsheets/id-ID/corporate-income-tax-return/' + '/'.join(
        str(value) for value in (fields.get('TaxpayerAggregateIdentifier'), record['record_id'],
                                fields.get('TaxTypeCode'), fields.get('AggregateIdentifier')))
    literal = record.get('meta', {}).get('Model SPT')
    model = 'NORMAL' if literal == 'Normal' else 'AMENDMENT' if isinstance(literal, str) and re.fullmatch(r'Amendment [0-9]{3}', literal) else None
    if (proof['route'] not in (route, route + '?view=true') or record.get('source_status') != 'SPT Dilaporkan'
            or payload.get('ReturnSheetStatusCode') != 'SUBMITTED' or model is None
            or payload.get('ReturnSheetModel') != model or fields.get('ReturnSheetModel') != literal
            or 'Induk' not in [f['name'] for f in observed_forms[:observed_forms.index(binding)]]):
        raise _UnsupportedMetadata('unverified_corporate_l11c_submitted_lifecycle')
    if 'PreviousFormData' not in payload:
        raise _UnsupportedMetadata('missing_corporate_l11c_previous_encoding')
    previous = payload['PreviousFormData']
    if previous is not None:
        if type(previous) is not str:
            raise _UnsupportedMetadata('unsupported_corporate_l11c_previous_encoding')
        try:
            previous = _corporate_json(previous)
        except JsonSafetyError:
            raise _UnsupportedMetadata('unsupported_corporate_l11c_previous_encoding') from None
        if previous is not None and not isinstance(previous, dict):
            raise _UnsupportedMetadata('unsupported_corporate_l11c_previous_shape')
    if not isinstance(proof['tables'], list) or len(proof['tables']) != 1:
        raise _UnsupportedMetadata('unverified_corporate_l11c_table_catalog')
    table = proof['tables'][0]
    if (not isinstance(table, dict) or set(table) != {'component', 'headers', 'footer_spans'}
            or table['component'] != 'rshshr-citr-l11c-form-grid1'):
        raise _UnsupportedMetadata('unverified_corporate_l11c_grid_owner')
    references = proof['references']
    if not isinstance(references, list) or len(references) > 1:
        raise _UnsupportedMetadata('unsupported_corporate_country_binding')
    catalogs, catalog_source = {'lookups': {}, 'provenance': [], 'selected': {}}, None
    if references:
        ref = references[0]
        if (not isinstance(ref, dict) or set(ref) != {'endpoint', 'method', 'sequences'}
                or ref['endpoint'] != CORPORATE_COUNTRY_REFERENCE_URL or ref['method'] != 'GET'
                or not isinstance(ref['sequences'], list) or not ref['sequences']):
            raise _UnsupportedMetadata('unsupported_corporate_country_binding')
        sequences = ref['sequences']
        if any(type(n) is not int or n <= 0 for n in sequences) or len(set(sequences)) != len(sequences):
            raise JsonSafetyError('Corporate country sequence is invalid or repeated')
        if set(sequences) != set(country_packets) or any(not country_packets[n]['successful'] for n in sequences):
            raise _UnsupportedMetadata('missing_or_failed_corporate_country_packet')
        catalog_source = country_packets[sequences[0]]
        catalogs = project_countries(catalog_source['payload'], clock_interval=catalog_source['event'].get('clock_interval'))
    result = project_l11c(root.get(L11C_ROOT), headers=table['headers'], footer_spans=table['footer_spans'],
        tax_type=fields.get('TaxTypeCode'), locale=proof['locale'], timezone_name=proof['timezone'],
        country_labels=catalogs['lookups'])
    section['tables'] = [result['table']]
    for entry in result['provenance']:
        entry.update(response_sequence=event['sequence'], container=['Payload', 'CurrentFormData'])
    if catalog_source is not None:
        for entry in catalogs['provenance']:
            result['provenance'].append({**entry, 'response_sequence': catalog_source['event']['sequence'],
                'container': ['Payload'], 'destination': {'table': 'L11-C', 'reference': 'COUNTRY_CODE'}})
        for index, row in enumerate(root[L11C_ROOT][L11C_BODY] or []):
            if row['CountryOfCreditor'] in catalogs['selected']:
                result['provenance'].append({**deepcopy(catalogs['selected'][row['CountryOfCreditor']]),
                    'response_sequence': catalog_source['event']['sequence'], 'container': ['Payload'],
                    'destination': {'table': 'L11-C', 'row': index, 'column': 3}})
    return {'form': 'L11-C', 'kind': proof['kind'], 'builds': dict(proof['builds']),
            'route': proof['route'], 'values': result['provenance']}


def _l11b_amount(value):
    if type(value) is not _CorporateNumber:
        raise _UnsupportedMetadata('unsupported_corporate_l11b_amount_type')
    try:
        number = _decimal(value)
    except _UnsupportedMetadata:
        raise _UnsupportedMetadata('unsupported_corporate_l11b_amount_type') from None
    if number != number.to_integral_value() or abs(number) > _MAX_INTEGER:
        raise _UnsupportedMetadata('unsupported_corporate_l11b_amount_precision')
    return int(number)


def project_l11b(form, *, tax_type, locale, null_defaults=False):
    """Only stable literal controls and the unconditional Part III grid.

    Submitted disables user editing, but does not suppress every callback.
    Manual=true/number-one excludes the L1-derived first-two-control overwrite;
    the IncomeTaxExpense overwrite separately requires not-submitted. Null
    scalar defaults, EBITDA hydration and conditional Part II remain unproved.
    Editor-only month means are NOT View lifecycle evidence. Preserve them in
    custody, never round an average into a different Excel DER denominator.
    """
    if tax_type != 'ICT_RCIT' or locale != 'id-ID' or not isinstance(form, dict):
        raise _UnsupportedMetadata('unsupported_corporate_l11b_structure')
    l11b_optional = {'BorrowingCosts', 'DebtBalanceAverage', 'EquityBalanceAverage',
                     'TotalBorrowingCosts'}
    if (set(form) - L11B_KEYS or not L11B_KEYS - l11b_optional <= set(form)
            or type(form['IsDocumentListForm']) is not bool):
        raise _UnsupportedMetadata('unsupported_corporate_l11b_source_shape')
    # The live source serializes the borrowing-cost total as an explicit null
    # (or omits it); the projector footers the grid itself, so any non-null
    # alias value is unreviewed and refuses closed.
    if 'TotalBorrowingCosts' in form and form['TotalBorrowingCosts'] is not None:
        raise _UnsupportedMetadata('unsupported_corporate_l11b_source_shape')
    manual = form['IsEbitdaManuallyEdited']
    if not (manual is True or type(manual) is _CorporateNumber and manual == '1'):
        raise _UnsupportedMetadata('unverified_corporate_l11b_manual_lifecycle')
    evidence = []

    def cell(value, path, destination, rule):
        entry = _evidence(value, path)
        entry.update(rule=rule, destination=destination)
        evidence.append(entry)
        return _number(value, 0, locale=locale)

    fields = []
    for name, caption in L11B_FIELDS:
        value = form[name]
        # The separately proven hydrated View defaults only an explicit null
        # scalar to zero. Restricted v1 never gains this permission.
        defaulted = null_defaults and value is None
        if not defaulted:
            _l11b_amount(value)
        path = [L11B_ROOT, name]
        destination = {'form': 'L11-B', 'field': name}
        entry = _evidence(value, path)
        entry.update(rule=('submitted-null-default-zero' if defaulted
                           else 'stable-submitted-manual-control'),
                     destination=destination)
        evidence.append(entry)
        fields.append({'group': '', 'field': name, 'label': caption,
                       'value': '0' if defaulted else _number(value, 0, locale=locale)})
    manual_path = [L11B_ROOT, 'IsEbitdaManuallyEdited']
    manual_evidence = ({'path': manual_path, 'type': 'boolean', 'value': manual}
                       if manual is True else _evidence(manual, manual_path))
    evidence.append({**manual_evidence, 'rule': 'exclude-l1-auto-overwrite'})
    source = form.get('BorrowingCosts')
    if source is not None and (not isinstance(source, list) or len(source) > 10000):
        raise _UnsupportedMetadata('unsupported_corporate_l11b_cost_body')
    rows = [] if source is None else source
    sums = dict.fromkeys(L11B_COST_ROW[1:], 0)
    body = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or set(row) != set(L11B_COST_ROW):
            raise _UnsupportedMetadata('unsupported_corporate_l11b_cost_row')
        if type(row['Name']) is not str:
            raise _UnsupportedMetadata('unsupported_corporate_l11b_text')
        entry = _evidence(row['Name'], [L11B_ROOT, 'BorrowingCosts', index, 'Name'])
        entry.update(rule='literal-grid-value',
                     destination={'table': 'L11-B/costs', 'row': index, 'column': 1})
        evidence.append(entry)
        rendered = [row['Name']]
        for column, key in enumerate(L11B_COST_ROW[1:], 2):
            amount = _l11b_amount(row[key])
            if amount < 0:
                raise _UnsupportedMetadata('unsupported_corporate_l11b_negative_amount')
            sums[key] += amount
            if sums[key] > _MAX_INTEGER:
                raise _UnsupportedMetadata('unsafe_corporate_l11b_ordered_total')
            rendered.append(cell(row[key], [L11B_ROOT, 'BorrowingCosts', index, key],
                                 {'table': 'L11-B/costs', 'row': index, 'column': column},
                                 'literal-grid-value'))
        body.append(rendered)
    # The owner computes this footer from Grid3Data, not a submitted DTO total.
    footer = ['JUMLAH']
    for column, key in enumerate(L11B_COST_ROW[1:], 2):
        footer.append(_number(str(sums[key]), 0, locale=locale))
        destination = {'table': 'L11-B/costs', 'footer': 0, 'column': column}
        if not rows:
            empty_path = [L11B_ROOT, 'BorrowingCosts']
            empty_evidence = (_evidence(source, empty_path) if source is None else
                              {'path': empty_path, 'type': 'array', 'value': []})
            evidence.append({**empty_evidence,
                             'rule': 'empty-grid-total', 'destination': destination})
        for index, row in enumerate(rows):
            evidence.append({**_evidence(row[key], [L11B_ROOT, 'BorrowingCosts', index, key]),
                             'rule': 'checked-model-ordered-sum-operand',
                             'destination': destination})
    table = {'name': 'L11-B/costs', 'headers': list(L11B_COST_HEADERS),
             'rows': body + [footer], 'footer': [footer], 'footer_spans': [[1] * 5],
             'body_row_count': len(body), 'source_total': len(body), 'complete': True}
    return {'fields': fields, 'tables': [table], 'provenance': evidence}


def _l11b_exact(value):
    amount = _l11b_amount(value)
    if amount == 0 and value.startswith('-'):
        raise _UnsupportedMetadata('unsupported_corporate_l11b_signed_zero')
    return amount


def _l11b_quarter(value):
    """EBITDA (25%) is ebitda * 0.25 in binary64; a non-multiple-of-4 EBITDA
    leaves a .25/.5/.75 fraction. Admit exactly 2 decimals, reject more."""
    if type(value) is not _CorporateNumber:
        raise _UnsupportedMetadata('unsupported_corporate_l11b_amount_type')
    number = _decimal(value)
    if abs(number) > _MAX_INTEGER or number != number.quantize(Decimal('0.01')):
        raise _UnsupportedMetadata('unsupported_corporate_l11b_amount_precision')
    if number == 0 and number.is_signed():
        raise _UnsupportedMetadata('unsupported_corporate_l11b_signed_zero')
    return number


def _l11b_average(value):
    """Saved row Average is a computed mean, not a rupiah control.

    The ordinary submitted profile stores sum/12 as a fractional saved value.
    Admit only the reviewed binary64-exact subset (<=15 coefficient digits,
    finite round-trip, no signed zero); the raw Decimal stays the DER operand
    and the worksheet cell keeps the reviewed zero-digit display rounding.
    """
    if type(value) is not _CorporateNumber:
        raise _UnsupportedMetadata('unsupported_corporate_l11b_amount_type')
    try:
        number = _decimal(value)
    except _UnsupportedMetadata:
        raise _UnsupportedMetadata('unsupported_corporate_l11b_amount_type') from None
    normalized = number.normalize()
    if (abs(number) > _MAX_INTEGER or len(normalized.as_tuple().digits) > 15
            or number.is_zero() and number.is_signed()
            or Decimal(str(float(number))) != number):
        raise _UnsupportedMetadata('unsupported_corporate_l11b_average_precision')
    # Integral group means keep the exact integer operand shape; only a truly
    # fractional saved mean introduces a Decimal operand.
    return int(number) if number == number.to_integral_value() else number


def _l11b_add(total, amount):
    total = total + amount
    if abs(total) > _MAX_INTEGER:
        raise _UnsupportedMetadata('unsafe_corporate_l11b_ordered_total')
    return total


def project_l11b_hydrated(form, *, tax_type, locale, part_ii):
    """Fresh submitted eager-child hydration, never an edit-dialog mean.

    The caller proves the three loaded providers and fresh parent lifetime.
    Subscriptions precede the asynchronous primary hydration; submitted disable
    emits all three operands after patchValue. Manual excludes later L1 writes.
    Saved row Average is copied unchanged and summed, not recomputed from months.
    """
    result = project_l11b(form, tax_type=tax_type, locale=locale, null_defaults=True)
    numbers = [0 if form[name] is None else _l11b_exact(form[name])
               for name, _ in L11B_FIELDS]
    ebitda = _l11b_add(_l11b_add(numbers[0], numbers[1]), numbers[2])
    quarter = Decimal(ebitda) / 4  # binary64 multiplication by .25 is exact in this bound
    quarter_null = form['Ebitda25'] is None
    if (quarter != 0 if quarter_null else _l11b_quarter(form['Ebitda25']) != quarter):
        raise _UnsupportedMetadata('unverified_corporate_l11b_quarter_hydration')
    if type(part_ii) is not bool or part_ii != (numbers[3] > quarter or ebitda <= 0):
        raise _UnsupportedMetadata('unverified_corporate_l11b_conditional')
    evidence = result['provenance']
    for name, value, caption in (('Ebitda', ebitda, '5. EBITDA'),
                                 ('Ebitda25', quarter, '6. EBITDA (25%)')):
        result['fields'].append({'group': '', 'field': name, 'label': caption,
                                 'value': _number(str(value), 0, locale=locale)})
    evidence.extend({**_evidence(form[name], [L11B_ROOT, name]),
                     'rule': 'submitted-disable-ebitda-operand'} for name, _ in L11B_FIELDS[:3])
    for name in ('Ebitda', 'DebtToEquityRatio'):
        evidence.append({**_evidence(form[name], [L11B_ROOT, name]), 'rule': 'unused-saved-control'})
    evidence.append({**_evidence(form['Ebitda25'], [L11B_ROOT, 'Ebitda25']),
                     'rule': ('reconciled-quarter-null-default' if quarter_null
                              else 'reconciled-quarter-hydration')})
    evidence.append({**_evidence(form['BorrowingCostExpense'], [L11B_ROOT, 'BorrowingCostExpense']),
                     'rule': 'conditional-part-ii-operand'})
    monthly, averages = [], []
    for index, (key, prefix, text_keys) in enumerate((
            ('DebtBalanceAverage', 'Debt', ('IdentityNumber', 'Name', 'Relationship')),
            ('EquityBalanceAverage', 'Equity', ('TypeOfEquity',)))):
        source = form.get(key)
        if source is not None and (not isinstance(source, list) or len(source) > 10000):
            raise _UnsupportedMetadata('unsupported_corporate_l11b_month_body')
        rows = [] if source is None else source
        amount_keys = [*[f'{prefix}Month{month}' for month in range(1, 13)], 'Average']
        totals, body = [0] * 13, []
        table_name = 'L11-B/' + ('debt' if index == 0 else 'equity')
        for row_index, row in enumerate(rows):
            if not isinstance(row, dict) or set(row) != {*text_keys, *amount_keys}:
                raise _UnsupportedMetadata('unsupported_corporate_l11b_month_row')
            if any(type(row[name]) is not str for name in text_keys):
                raise _UnsupportedMetadata('unsupported_corporate_l11b_text')
            rendered = [row[name] for name in text_keys]
            for name in text_keys:
                evidence.append({**_evidence(row[name], [L11B_ROOT, key, row_index, name]),
                                 'rule': 'literal-view-model-text'})
            for column, name in enumerate(amount_keys):
                amount = (_l11b_average(row[name]) if name == 'Average'
                          else _l11b_exact(row[name]))
                totals[column] = _l11b_add(totals[column], amount)
                rendered.append(_number(row[name], 0, locale=locale))
                evidence.append({**_evidence(row[name], [L11B_ROOT, key, row_index, name]),
                    'rule': 'view-model-ordered-sum-operand',
                    'destination': {'table': table_name, 'row': row_index,
                                    'column': column + len(text_keys) + 1}})
            body.append(rendered)
        if not rows:
            empty = (_evidence(source, [L11B_ROOT, key]) if source is None else
                     {'path': [L11B_ROOT, key], 'type': 'array', 'value': []})
            evidence.extend({**empty, 'rule': 'empty-view-model-total',
                             'destination': {'table': table_name, 'footer': 0, 'column': column}}
                            for column in range(len(text_keys) + 1, len(text_keys) + 14))
        # Physical footer cells, not header-width padding: JUMLAH spans the
        # three creditor text columns in debt and one equity column.
        footer = ['JUMLAH', *[_number(str(total), 0, locale=locale) for total in totals]]
        metadata = l11b_tables(True)[index]
        monthly.append({'name': table_name, 'headers': metadata['headers'], 'rows': body + [footer],
                        'footer': [footer], 'footer_spans': metadata['footer_spans'],
                        'body_row_count': len(body), 'source_total': len(body), 'complete': True})
        averages.append(totals[-1])
    der_exact = False
    if part_ii:
        debt, equity = averages
        if equity == 0:
            if debt != 0:
                raise _UnsupportedMetadata('unsupported_corporate_l11b_der_precision')
            der_exact = True
        else:
            ratio = Fraction(debt) / Fraction(equity)
            # A fractional saved Average can make the DER a non-binary
            # fraction. Keep the exact raw operands in custody and report the
            # dependency as partial instead of manufacturing a rounded ratio.
            der_exact = (debt != 0 and ratio.denominator in (1, 2, 4)
                         and abs(ratio * 100) <= _MAX_INTEGER)
        result['tables'] = monthly + result['tables']
    else:
        for entry in evidence:
            if entry['path'][:2] in ([L11B_ROOT, 'DebtBalanceAverage'], [L11B_ROOT, 'EquityBalanceAverage']):
                entry['rule'] = 'unused-hidden-view-model'
                entry.pop('destination', None)
    result['der_operands'] = averages if part_ii else None
    result['der_exact'] = der_exact
    return result


def _apply_l11b(binding, section, observed_forms, *, root, payload, record, event):
    proof = binding['projection']
    builds = proof.get('builds') if isinstance(proof, dict) else None
    hydrated = isinstance(proof, dict) and proof.get('kind') == 'corporate-l11b-hydrated-v2'
    pins = L11B_HYDRATED_BUILD_DIGESTS if hydrated else BUILD_DIGESTS
    providers = {CIT_SOURCE, MAIN_SOURCE, VENDOR_SOURCE} if hydrated else {CIT_SOURCE, MAIN_SOURCE}
    if (not isinstance(proof, dict) or set(proof) != ({'kind', 'builds', 'route', 'tables', 'part_ii'}
                                                                  if hydrated else {'kind', 'builds', 'route'})
            or proof['kind'] not in ('corporate-l11b-v1', 'corporate-l11b-hydrated-v2')
            or not isinstance(builds, dict) or set(builds) != providers
            or set(pins) != providers
            or any(type(value) is not str or not re.fullmatch(r'[0-9a-f]{64}', value)
                   for value in [*builds.values(), *pins.values()])
            or builds != pins or proof['route'] != event['frame_url']
            or binding.get('paths') != [[L11B_ROOT]]
            or binding.get('grids') or binding.get('responses') or binding.get('dependencies')):
        raise _UnsupportedMetadata('unverified_corporate_l11b_binding')
    fields = record.get('source_fields', {})
    route = ORIGIN + '/returnsheets/id-ID/corporate-income-tax-return/' + '/'.join(
        str(value) for value in (fields.get('TaxpayerAggregateIdentifier'), record['record_id'],
                                fields.get('TaxTypeCode'), fields.get('AggregateIdentifier')))
    literal = record.get('meta', {}).get('Model SPT')
    model = ('NORMAL' if literal == 'Normal' else 'AMENDMENT'
             if type(literal) is str and re.fullmatch(r'Amendment [0-9]{3}', literal) else None)
    if (proof['route'] not in (route, route + '?view=true')
            or record.get('source_status') != 'SPT Dilaporkan'
            or payload.get('ReturnSheetStatusCode') != 'SUBMITTED' or model is None
            or payload.get('ReturnSheetModel') != model or fields.get('ReturnSheetModel') != literal
            or 'Induk' not in [form['name'] for form in observed_forms[:observed_forms.index(binding)]]
            or 'PreviousFormData' not in payload):
        raise _UnsupportedMetadata('unverified_corporate_l11b_submitted_lifecycle')
    previous = payload['PreviousFormData']
    if previous is not None:
        if type(previous) is not str:
            raise _UnsupportedMetadata('unverified_corporate_l11b_submitted_lifecycle')
        try:
            previous = _corporate_json(previous)
        except JsonSafetyError:
            raise _UnsupportedMetadata('unverified_corporate_l11b_submitted_lifecycle') from None
        if previous is not None and not isinstance(previous, dict):
            raise _UnsupportedMetadata('unverified_corporate_l11b_submitted_lifecycle')
    if hydrated:
        source_form = root.get(L11B_ROOT)
        null_profile = isinstance(source_form, dict) and any(
            source_form.get(name) is None for name in
            (*[key for key, _ in L11B_FIELDS], 'Ebitda25'))
        # Null hydration has its own non-migrated, original submitted parent
        # prerequisite; absence or an encoded previous form grants nothing.
        if null_profile and (payload.get('IsMigrated') is not False
                             or payload.get('LastSubmittedFormData', object()) is not None):
            raise _UnsupportedMetadata('unverified_corporate_l11b_hydrated_lifecycle')
        if (event.get('component_lifetime') is None or proof['route'] != route + '?view=true'
                or previous is not None
                or any(form.get('disabled') for form in observed_forms if form['name'] == 'Induk')
                or type(proof['part_ii']) is not bool or proof['tables'] != l11b_tables(proof['part_ii'])):
            raise _UnsupportedMetadata('unverified_corporate_l11b_hydrated_lifecycle')
        result = project_l11b_hydrated(root.get(L11B_ROOT), tax_type=fields.get('TaxTypeCode'),
                                        locale='id-ID', part_ii=proof['part_ii'])
        result['provenance'].extend({**_evidence(payload[key], [key]), 'container': ['Payload'],
                                    'rule': 'submitted-hydration-predicate'} for key in
                                   ('ReturnSheetStatusCode', 'ReturnSheetModel', 'PreviousFormData'))
        # Preserve the original typed non-migration predicate when supplied;
        # never invent it for the older hydrated non-null profile.
        if 'IsMigrated' in payload:
            if payload['IsMigrated'] is not False:
                raise _UnsupportedMetadata('unverified_corporate_l11b_hydrated_lifecycle')
            result['provenance'].append({**_evidence(payload['IsMigrated'], ['IsMigrated']),
                                         'container': ['Payload'],
                                         'rule': 'submitted-hydration-predicate'})
    else:
        result = project_l11b(root.get(L11B_ROOT), tax_type=fields.get('TaxTypeCode'), locale='id-ID')
    section['fields'] = result['fields']
    # Retain ALL original raw leaves, including omitted averages and metadata.
    section['tables'].extend(result['tables'])
    section['projection_complete'] = False
    section['projection_reason'] = ('unprojected_l11b_header_question' if hydrated
                                    else 'unprojected_l11b_lifecycle')
    for entry in result['provenance']:
        entry['response_sequence'] = event['sequence']
        entry.setdefault('container', ['Payload', 'CurrentFormData'])
    return {'form': 'L11-B', 'kind': proof['kind'], 'builds': dict(proof['builds']),
            'route': proof['route'], 'values': result['provenance'],
            # A fractional saved Average makes the DER a non-binary fraction.
            # The exact raw operands stay in custody; the ratio stays partial.
            'der_exact': result.get('der_exact', True)}


def _apply_l1d(binding, section, observed_forms, *, root, payload, record, event):
    proof = binding['projection']
    if (not isinstance(proof, dict)
            or set(proof) - {'visibility_binding', 'body_layout'} != {'kind', 'builds', 'route', 'locale', 'timezone', 'tables'}
            or 'visibility_binding' in proof and proof['visibility_binding'] != 'current-induk-enabled-v1'
            or 'body_layout' in proof and (proof['body_layout'] != L1D_OMISSION_LAYOUT
                or proof.get('visibility_binding') != 'current-induk-enabled-v1')
            or proof['kind'] != 'corporate-l1d-v1' or proof['builds'] != L1D_BUILD_DIGESTS
            or proof['route'] != event['frame_url'] or binding.get('paths') != [['L1dFormData']]
            or binding.get('grids', []) or binding.get('responses', []) or binding.get('dependencies', [])):
        raise _UnsupportedMetadata('unsupported_corporate_l1d_semantic_binding')
    # Packet decoding has already validated every present lifetime fact against
    # this attempt/record/source/frame. Absence never authorizes this branch.
    if event.get('component_lifetime') is None:
        raise _UnsupportedMetadata('missing_corporate_l1d_component_lifetime')
    fields = record.get('source_fields', {})
    route = ORIGIN + '/returnsheets/id-ID/corporate-income-tax-return/' + '/'.join(
        str(value) for value in (fields.get('TaxpayerAggregateIdentifier'), record['record_id'],
                                fields.get('TaxTypeCode'), fields.get('AggregateIdentifier'))) + '?view=true'
    literal = record.get('meta', {}).get('Model SPT')
    model = ('NORMAL' if literal == 'Normal' else 'AMENDMENT'
             if isinstance(literal, str) and re.fullmatch(r'Amendment [0-9]{3}', literal) else None)
    # The pinned parent initially reads the outer classification, then the
    # Induk callback selects Services from original current MainFormData.
    # Only an absent outer key may use that branch, with enabled-tab proof.
    main = root.get('MainFormData')
    current_present = isinstance(main, dict) and 'BusinessClassification' in main
    current_services = (current_present and type(main['BusinessClassification']) is str
                        and main['BusinessClassification'] == 'BC04')
    outer_present = 'BusinessClassification' in payload
    services = ((type(payload['BusinessClassification']) is str
                 and payload['BusinessClassification'] == 'BC04'
                 and (not current_present or current_services)) if outer_present else
                current_services and proof.get('visibility_binding') == 'current-induk-enabled-v1')
    if (proof['route'] != route or record.get('source_status') != 'SPT Dilaporkan'
            or payload.get('ReturnSheetStatusCode') != 'SUBMITTED' or model is None
            or payload.get('ReturnSheetModel') != model or fields.get('ReturnSheetModel') != literal
            or not services
            or type(payload.get('IsMigrated')) is not bool
            or 'Induk' not in [f['name'] for f in observed_forms[:observed_forms.index(binding)]]):
        raise _UnsupportedMetadata('unverified_corporate_l1d_submitted_lifecycle')
    if 'PreviousFormData' not in payload:
        raise _UnsupportedMetadata('missing_corporate_l1d_previous_encoding')
    previous = payload['PreviousFormData']
    if previous is not None:
        if type(previous) is not str:
            raise _UnsupportedMetadata('unsupported_corporate_l1d_previous_encoding')
        previous = _corporate_json(previous)
        if previous is not None and not isinstance(previous, dict):
            raise _UnsupportedMetadata('unsupported_corporate_l1d_previous_shape')
    tables = proof['tables']
    if not isinstance(tables, list) or len(tables) != 3:
        raise _UnsupportedMetadata('unverified_corporate_l1d_table_catalog')
    for index, table in enumerate(tables):
        structure = {'form': 'L1-D', 'component': f'rsh-citr-l1d-grid{index + 1}',
                     'groups': ['A. LAPORAN LABA RUGI' if index == 0 else 'B. LAPORAN POSISI KEUANGAN']}
        if (not isinstance(table, dict)
                or set(table) != {'component', 'headers', 'footer_spans', 'source_structure'}
                or table['component'] != structure['component'] or table['source_structure'] != structure):
            raise _UnsupportedMetadata('unverified_corporate_l1d_grid_owner')
    result = project_l1d(root.get('L1dFormData'), migrated=payload['IsMigrated'],
        headers=[t['headers'] for t in tables], footer_spans=[t['footer_spans'] for t in tables],
        tax_type=fields.get('TaxTypeCode'), locale=proof['locale'], timezone_name=proof['timezone'],
        body_layout=proof.get('body_layout'))
    section['tables'] = result['tables']
    if not outer_present:
        entry = _evidence(main['BusinessClassification'], ['MainFormData', 'BusinessClassification'])
        entry.update(destination={'form': 'L1-D', 'control': 'classification'},
                     rule='current-induk-services-enabled-v1')
        result['provenance'].append(entry)
    for entry in result['provenance']:
        entry.update(response_sequence=event['sequence'], container=['Payload', 'CurrentFormData'])
    return {'form': 'L1-D', 'kind': proof['kind'], 'builds': dict(proof['builds']),
            'route': proof['route'], 'values': result['provenance'],
            **({'body_layout': proof['body_layout'], 'omitted_account_codes': result['omitted_account_codes']}
               if 'body_layout' in proof else {}),
            **({'visibility_binding': proof['visibility_binding']} if 'visibility_binding' in proof else {})}


def _apply_l8(binding, section, observed_forms, *, root, payload, record, event):
    proof = binding['projection']
    if (not isinstance(proof, dict)
            or set(proof) != {'kind', 'builds', 'route', 'locale', 'timezone', 'tables'}
            or proof['kind'] != 'corporate-l8-v1' or proof['builds'] != L8_BUILD_DIGESTS
            or proof['route'] != event['frame_url'] or proof['locale'] != 'id-ID'
            or proof['timezone'] != 'Asia/Jakarta' or binding.get('paths') != [[L8_ROOT]]
            or binding.get('grids', []) or binding.get('responses', []) or binding.get('dependencies', [])
            or event.get('component_lifetime') is None or event.get('corporate_l8_lifetime') is None):
        raise _UnsupportedMetadata('unverified_corporate_l8_semantic_binding')
    fields = record.get('source_fields', {})
    route = ORIGIN + '/returnsheets/id-ID/corporate-income-tax-return/' + '/'.join(
        str(value) for value in (fields.get('TaxpayerAggregateIdentifier'), record['record_id'],
                                fields.get('TaxTypeCode'), fields.get('AggregateIdentifier'))) + '?view=true'
    literal = record.get('meta', {}).get('Model SPT')
    model = ('NORMAL' if literal == 'Normal' else 'AMENDMENT'
             if isinstance(literal, str) and re.fullmatch(r'Amendment [0-9]{3}', literal) else None)
    main = root.get('MainFormData')
    if (proof['route'] != route or record.get('source_status') != 'SPT Dilaporkan'
            or payload.get('ReturnSheetStatusCode') != 'SUBMITTED' or model is None
            or payload.get('ReturnSheetModel') != model or fields.get('ReturnSheetModel') != literal
            or 'Induk' not in [f['name'] for f in observed_forms[:observed_forms.index(binding)]]
            or not isinstance(main, dict) or main.get('TaxRate') != 'TX03'
            or ('TaxRate' in payload and payload['TaxRate'] != main.get('TaxRate'))
            or any(key not in payload or payload[key] is not None
                   for key in ('PreviousFormData', 'LastSubmittedFormData'))
            or any(root.get(key) is not None for key in ('CalculationOfFiscalLossCompensation',
                   'L13AListOfTaxFacilityInInvestment', 'L13BListOfAdditionalGrossIncomeDeduction'))):
        raise _UnsupportedMetadata('unverified_corporate_l8_fresh_submitted_lifecycle')
    flags = ('IsCarriedForward', 'IsNetIncomeReduction', 'IsInvestmentOtherIncome',
             'IsGrossIncomeVocational', 'IsGrossIncomeResearch')
    # Source contract: visibility flags live on MainFormData. The outer payload
    # copy is optional; when present it must agree with the main owner.
    if any(type(main.get(key)) is not _CorporateNumber or main[key] != '0' for key in flags):
        raise _UnsupportedMetadata('unverified_corporate_l8_visibility_flags')
    if any(key in payload and (type(payload[key]) is not _CorporateNumber
                               or payload[key] != main[key]) for key in flags):
        raise _UnsupportedMetadata('unverified_corporate_l8_visibility_flags')
    for source, start, end in ((main, 'AccountingPeriodStart', 'AccountingPeriodEnd'),
                                (payload, 'PeriodMonthStart', 'PeriodMonthEnd')):
        if (type(source.get(start)) is not _CorporateNumber or source[start] != '1'
                or type(source.get(end)) is not _CorporateNumber or source[end] != '12'):
            raise _UnsupportedMetadata('unverified_corporate_l8_original_annual_bounds')
    zeros = ('TotalNetIncomeReduction', 'TotalGrossIncomeVocational',
             'TotalCarriedForward', 'TotalGrossIncomeResearch')
    net = _l8_integer(main.get('NetIncomeBeforeTax'))
    # A loss-making return clamps the taxable base to zero: the 31E facility
    # branch is inert and fiscal net income keeps the reported loss. A
    # non-negative return keeps the reviewed thousand-mask fixed point.
    taxable = 0 if net < 0 else net - net % 1000
    if (any(_l8_integer(main.get(key)) != 0 for key in zeros)
            or _l8_integer(main.get('FiscalNetIncomeAfterTax')) != net
            or _l8_integer(main.get('TaxableIncome')) != taxable):
        raise _UnsupportedMetadata('unreconciled_corporate_l8_original_main_fixed_points')
    tables = proof['tables']
    structure = {'form': 'L8', 'component': 'rsh-citr-l8-form-grid1', 'groups': [_L8_GROUP]}
    if (not isinstance(tables, list) or len(tables) != 1 or not isinstance(tables[0], dict)
            or set(tables[0]) != {'component', 'headers', 'footer_spans', 'source_structure'}
            or tables[0]['component'] != structure['component'] or tables[0]['source_structure'] != structure):
        raise _UnsupportedMetadata('unverified_corporate_l8_grid_owner')
    result = project_l8(root.get(L8_ROOT), main_form=main, period_year=payload.get('PeriodYear'),
        headers=tables[0]['headers'], footer_spans=tables[0]['footer_spans'],
        tax_type=fields.get('TaxTypeCode'), locale=proof['locale'])
    # Keep every original fixed-point operand/control, including overwritten
    # outer/main annual and rate inputs. Never replace captured values by net.
    retained = {(entry['source'], tuple(entry['path'])) for entry in result['provenance']}
    for source, values, prefix, keys in (
            ('current', main, ['MainFormData'], ('NetIncomeBeforeTax', 'FiscalNetIncomeAfterTax',
                'TaxableIncome', *zeros, *flags, 'AccountingPeriodStart', 'AccountingPeriodEnd', 'TaxRate')),
            ('primary', payload, [], (*flags, 'PeriodMonthStart', 'PeriodMonthEnd', 'TaxRate',
                'PreviousFormData', 'LastSubmittedFormData'))):
        for key in keys:
            if key not in values:
                continue
            path = prefix + [key]
            if (source, tuple(path)) in retained:
                continue
            entry = _evidence(values[key], path)
            entry.update(source=source, destination={'table': 'L8', 'control': 'original-fixed-point'},
                         rule='retained-original-submitted-fixed-point')
            result['provenance'].append(entry)
    section['tables'] = [result['table']]
    for entry in result['provenance']:
        entry.update(response_sequence=event['sequence'],
                     container=['Payload'] if entry['source'] == 'primary' else ['Payload', 'CurrentFormData'])
    return {'form': 'L8', 'kind': proof['kind'], 'builds': dict(proof['builds']),
            'route': proof['route'], 'values': result['provenance']}


L4_ROOT = 'ListOfIncomeSubjectToFinalTaxAndNonTaxableObject'
L4_GRID_NAME = 'L4/l4-table-a-grid'
L4_FINAL_TABLE = 'L4/final-income'
L4_EXCLUDED_TABLE = 'L4/non-taxable-object'
# Approved block headers, spelled exactly as the template header rows 2 and 8.
L4_A_HEADERS = ['NPWP PEMOTONG/PEMUNGUT', 'NAMA PEMOTONG/PEMUNGUT', 'KODE OBJEK PAJAK',
    'OBJEK PAJAK', 'DASAR PENGENAAN PAJAK (Rupiah)', 'TINGKAT (%)',
    'PPH FINAL TERUTANG (Rupiah)']
L4_B_HEADERS = ['NO.', 'KODE', 'JENIS PENGHASILAN', 'SUMBER PENGHASILAN',
    'PENGHASILAN BRUTO(Rp)']
# Physical source footer cells, not template-expanded seven/five-cell rows.
# The pinned ui-grid has spacing disabled; the offline B row has a blank No.
# cell followed by the three-column JUMLAH label and its amount.
L4_A_SPANS = [[4, 1, 1, 1]]
L4_B_SPANS = [[1, 3, 1]]
L4_ROOT_FIELDS = frozenset(('TotalTaxBase', 'TotalFinalIncomeTaxPayable',
    'TotalFinalIncomeTaxPayableUsd', 'TotalGrossIncome', 'ListOfIncomeExcludedFromIncomeTax'))
L4_FOOTER_FIELDS = frozenset(('TaxBase', 'IncomeTax', 'TaxBaseUsd', 'IncomeTaxUsd'))


def l4_tables():
    return [{'component': 'rshshr-citr-l4-grid1', 'headers': list(L4_A_HEADERS),
             'footer_spans': deepcopy(L4_A_SPANS)},
            {'component': 'rsh-citr-l4-grid2', 'headers': list(L4_B_HEADERS),
             'footer_spans': deepcopy(L4_B_SPANS)}]


def _l4_zero(value):
    # No rounding, coercion, null->zero or binary-float calculations. This
    # subset emits only original numeric zero, so it needs no locale RPC.
    try:
        if type(value) is not _CorporateNumber:
            raise _UnsupportedMetadata('unsupported_corporate_l4_empty_total')
        number = _decimal(value)
        if number != 0 or number.is_signed():
            raise _UnsupportedMetadata('unsupported_corporate_l4_empty_total')
    except (DecimalException, _UnsupportedMetadata):
        raise _UnsupportedMetadata('unsupported_corporate_l4_empty_total') from None
    return '0'


def project_l4(form, *, footer, pages, tax_type, locale, labels=None):
    """Empty legacy branch or independently bound populated renderers.

    ``labels`` is pure input, never catalog acquisition/native permission.
    The caller must bind it to original same-attempt catalogs and loaded pins.
    """
    if labels is not None:
        return _project_l4_populated(form, footer=footer, pages=pages,
            tax_type=tax_type, locale=locale, labels=labels)
    if (tax_type != 'ICT_RCIT' or locale != 'id-ID' or not isinstance(form, dict)
            or set(form) not in (L4_ROOT_FIELDS, L4_ROOT_FIELDS | {'TotalTaxBaseUsd'})
            or not isinstance(footer, dict) or set(footer) != L4_FOOTER_FIELDS
            or not isinstance(pages, list) or len(pages) != 1):
        raise _UnsupportedMetadata('unsupported_corporate_l4_source_shape')
    excluded = form['ListOfIncomeExcludedFromIncomeTax']
    if excluded is not None and not isinstance(excluded, list):
        raise _UnsupportedMetadata('unsupported_corporate_l4_excluded_body')
    if excluded:
        raise _UnsupportedMetadata('unverified_corporate_l4_income_type_labels')
    page = pages[0]
    if (not isinstance(page, dict) or set(page) != {'offset', 'rows', 'total', 'data'}
            or any(type(page[key]) is not int for key in ('offset', 'rows', 'total'))
            or page['offset'] != 0 or page['rows'] not in (10, 25, 50, 100, 250, 500)
            or not isinstance(page['data'], list)):
        raise _UnsupportedMetadata('incomplete_corporate_l4_pages')
    if page['data']:
        raise _UnsupportedMetadata('unverified_corporate_l4_tax_object_labels')
    if page['total'] != 0:
        raise _UnsupportedMetadata('incomplete_corporate_l4_pages')
    provenance = []
    for key in sorted(set(form) - {'ListOfIncomeExcludedFromIncomeTax'}):
        _l4_zero(form[key])
        provenance.append({**_evidence(form[key], [L4_ROOT, key]), 'source': 'current',
                           'rule': 'original-empty-block-zero-total'})
    provenance.append({'path': [L4_ROOT, 'ListOfIncomeExcludedFromIncomeTax'],
        'type': 'null' if excluded is None else 'array', 'value': deepcopy(excluded),
        'source': 'current', 'rule': 'original-inert-empty-block-b'})
    for key in sorted(footer):
        _l4_zero(footer[key])
        provenance.append({**_evidence(footer[key], [key]), 'source': 'footer',
                           'rule': 'original-reconciled-empty-grid-footer'})
    afooter = [['TOTAL', _l4_zero(footer['TaxBase']), '', _l4_zero(footer['IncomeTax'])]]
    bfooter = [['', 'JUMLAH', _l4_zero(form['TotalGrossIncome'])]]
    return {'tables': [
        {'name': L4_FINAL_TABLE, 'headers': list(L4_A_HEADERS), 'rows': afooter,
         'footer': afooter, 'footer_spans': deepcopy(L4_A_SPANS),
         'body_row_count': 0, 'source_total': 0, 'complete': True},
        {'name': L4_EXCLUDED_TABLE, 'headers': list(L4_B_HEADERS), 'rows': bfooter,
         'footer': bfooter, 'footer_spans': deepcopy(L4_B_SPANS),
         'body_row_count': 0, 'source_total': 0, 'complete': True}],
        'fields': [], 'provenance': provenance}


L4_CATALOG_KINDS = ('TAX_OBJECT_CODE', 'INCOME_EXCLUDED_FROM_TAX_FOR_CIT')
L4_POPULATED_BUILD_DIGESTS = dict(L11C_BUILD_DIGESTS)
_L4_A_COLUMNS = ('TIN', 'Name', 'TaxObjectCode', 'TaxBase', 'TaxRate', 'IncomeTax')
_L4_A_METADATA = frozenset(('TaxObject', 'TaxBaseUsd', 'IncomeTaxUsd', 'Index',
                            'RecordId', 'IsManually', 'TableSource', 'Action'))
# Withholding-slip-sourced L4 A rows carry these extra read-only fields. They are
# not projected into any destination; they are evidenced as unused row metadata
# only, so their presence must not force a whole-record fallback.
_L4_A_EXTRA_METADATA = frozenset(('WithholdingDate', 'WithholdingSlipsAggregateIdentifier'))
_L4_B_COLUMNS = ('TaxObjectCode', 'TypeOfIncome', 'IncomeSource', 'GrossIncome')


def _l4_numeric(value, digits=0, *, nullable=False, exact_sum=False):
    # Direct DecimalPipe output, not the editor's Math.round(base*rate/100).
    # Number2 sums additionally require binary-exact operands/intermediates.
    if nullable and value is None:
        return None
    try:
        if type(value) is not _CorporateNumber:
            raise _UnsupportedMetadata('unsupported_corporate_l4_number')
        number = _decimal(value)
        if (number < 0 or number > _MAX_INTEGER or (number == 0 and number.is_signed())
                or number != number.quantize(Decimal(1).scaleb(-digits))
                or (exact_sum and number != Decimal.from_float(float(number)))):
            raise _UnsupportedMetadata('unsupported_corporate_l4_number_precision')
        return number
    except DecimalException:
        raise _UnsupportedMetadata('unsupported_corporate_l4_number_precision') from None


def _l4_text(value):
    if value is None:
        return ''
    if type(value) is not str:
        raise _UnsupportedMetadata('unsupported_corporate_l4_text')
    return value


# Non-displayed USD metadata (row TaxBaseUsd/IncomeTaxUsd, root
# TotalFinalIncomeTaxPayableUsd/TotalTaxBaseUsd, footer TaxBaseUsd/IncomeTaxUsd)
# carries finite, nonnegative exchange-rate precision up to eight decimal places.
# It is validated but never rendered or summed; the original lexeme is preserved.
_L4_USD_DECIMALS = 8


def _l4_usd(value):
    if type(value) is not _CorporateNumber:
        raise _UnsupportedMetadata('unsupported_corporate_l4_number')
    number = _decimal(value)
    if (number < 0 or number > _MAX_INTEGER or (number == 0 and number.is_signed())
            or number != number.quantize(Decimal(1).scaleb(-_L4_USD_DECIMALS))):
        raise _UnsupportedMetadata('unsupported_corporate_l4_number_precision')
    return number


def _l4_label(value, kind, labels):
    if type(value) is not str or not value or not isinstance(labels.get(kind), dict):
        raise _UnsupportedMetadata('unverified_corporate_l4_labels')
    text = labels[kind].get(value)
    if type(text) is not str or not text.strip():
        raise _UnsupportedMetadata('unverified_corporate_l4_labels')
    return text


def _l4_metadata(value, key, path):
    if key == 'IsManually':
        if type(value) is not bool:
            raise _UnsupportedMetadata('unsupported_corporate_l4_row_metadata')
        return {'path': path, 'type': 'boolean', 'value': value}
    if key in ('TaxBaseUsd', 'IncomeTaxUsd'):
        _l4_usd(value)
    elif key == 'Index':
        _l4_numeric(value, nullable=False)
    elif key == 'Action':
        if value is not None:
            raise _UnsupportedMetadata('unsupported_corporate_l4_row_metadata')
    else:
        _l4_text(value)
    return _evidence(value, path)


def _project_l4_populated(form, *, footer, pages, tax_type, locale, labels):
    """Bound Rupiah subset of IE/W1/pE, preserving both original blocks.

    A money is integral; A rates have at most two decimal places and no
    reconstruction. B Number2 accepts only binary-exact <=2-place operands,
    with every ordered JS-add intermediate exact. Unsupported precision keeps
    whole-record fallback. A null body cells are blank via checkIsString;
    B null Number2 cells are blank via DecimalPipe (never invented zero rows).
    """
    if (tax_type != 'ICT_RCIT' or locale != 'id-ID' or not isinstance(form, dict)
            or set(form) not in (L4_ROOT_FIELDS, L4_ROOT_FIELDS | {'TotalTaxBaseUsd'})
            or not isinstance(footer, dict) or set(footer) != L4_FOOTER_FIELDS
            or not isinstance(labels, dict) or not isinstance(pages, list) or not pages):
        raise _UnsupportedMetadata('unsupported_corporate_l4_source_shape')
    excluded = form['ListOfIncomeExcludedFromIncomeTax']
    if excluded is not None and (not isinstance(excluded, list) or len(excluded) > 10000):
        raise _UnsupportedMetadata('unsupported_corporate_l4_excluded_body')
    excluded = [] if excluded is None else excluded
    evidence, arows, brows, cursor, total = [], [], [], 0, None
    for page_index, page in enumerate(pages):
        if (not isinstance(page, dict) or set(page) != {'offset', 'rows', 'total', 'data'}
                or any(type(page[key]) is not int for key in ('offset', 'rows', 'total'))
                or page['offset'] != cursor or page['rows'] not in (10, 25, 50, 100, 250, 500)
                or not isinstance(page['data'], list) or not 0 <= page['total'] <= 10000
                or len(page['data']) != min(page['rows'], page['total'] - cursor)
                or (total is not None and page['total'] != total)):
            raise _UnsupportedMetadata('incomplete_corporate_l4_pages')
        total = page['total']
        for index, row in enumerate(page['data']):
            if (not isinstance(row, dict) or not set(_L4_A_COLUMNS) <= set(row)
                    or set(row) - {*_L4_A_COLUMNS, *_L4_A_METADATA, *_L4_A_EXTRA_METADATA}):
                raise _UnsupportedMetadata('unsupported_corporate_l4_row')
            rendered = [_l4_text(row['TIN']), _l4_text(row['Name']),
                        _l4_text(row['TaxObjectCode']),
                        _l4_label(row['TaxObjectCode'], L4_CATALOG_KINDS[0], labels)]
            for key, digits in (('TaxBase', 0), ('TaxRate', 2), ('IncomeTax', 0)):
                number = _l4_numeric(row[key], digits, nullable=True)
                if key == 'TaxRate' and number is not None and number > 100:
                    raise _UnsupportedMetadata('unsupported_corporate_l4_rate')
                rendered.append('' if number is None else _number(row[key], digits, locale=locale))
            arows.append(rendered)
            for key in row:
                path = ['Data', index, key]
                entry = (_l4_metadata(row[key], key, path) if key in _L4_A_METADATA
                         else _evidence(row[key], path))
                entry.update(source='grid', page_index=page_index,
                             rule='original-unused-row-metadata')
                if key in _L4_A_COLUMNS:
                    column = {'TIN': 0, 'Name': 1, 'TaxObjectCode': 2,
                              'TaxBase': 4, 'TaxRate': 5, 'IncomeTax': 6}[key]
                    entry.update(destination={'table': L4_FINAL_TABLE, 'row': cursor + index,
                                              'column': column},
                        rule=('literal-text' if column < 3 else
                              'submitted-number-null-blank' if row[key] is None else
                              'angular-number-1.2-2-id' if key == 'TaxRate' else
                              'angular-number-1.0-0-id'))
                evidence.append(entry)
                if key == 'TaxObjectCode':
                    evidence.append({**_evidence(row[key], path), 'source': 'grid',
                        'page_index': page_index, 'rule': 'bound-reference-label',
                        'reference_kind': L4_CATALOG_KINDS[0],
                        'destination': {'table': L4_FINAL_TABLE, 'row': cursor + index, 'column': 3}})
        cursor += len(page['data'])
    if cursor != total:
        raise _UnsupportedMetadata('incomplete_corporate_l4_pages')
    # JS reduce has no initializer: one null remains null, whereas a later +
    # coerces a null accumulator/operand to zero. getFormData serializes ??0.
    gross = None
    for index, row in enumerate(excluded):
        if not isinstance(row, dict) or set(row) != set(_L4_B_COLUMNS):
            raise _UnsupportedMetadata('unsupported_corporate_l4_excluded_row')
        amount = _l4_numeric(row['GrossIncome'], 2, nullable=True, exact_sum=True)
        gross = amount if index == 0 else (gross or 0) + (amount or 0)
        if gross is not None:
            _l4_numeric(_CorporateNumber(str(gross)), 2, exact_sum=True)
        brows.append([str(index + 1), _l4_text(row['TaxObjectCode']),
            _l4_label(row['TypeOfIncome'], L4_CATALOG_KINDS[1], labels),
            _l4_text(row['IncomeSource']),
            '' if amount is None else _number(row['GrossIncome'], 2, locale=locale)])
        for column, key in enumerate(_L4_B_COLUMNS, 1):
            entry = _evidence(row[key], [L4_ROOT, 'ListOfIncomeExcludedFromIncomeTax', index, key])
            entry.update(source='current', destination={'table': L4_EXCLUDED_TABLE,
                'row': index, 'column': column}, rule='literal-text')
            if key == 'TypeOfIncome':
                entry.update(rule='bound-reference-label', reference_kind=L4_CATALOG_KINDS[1])
            elif key == 'GrossIncome':
                entry['rule'] = 'angular-number-null-blank' if amount is None else 'angular-number-1.2-2-id'
            evidence.append(entry)
    for key in sorted(set(form) - {'ListOfIncomeExcludedFromIncomeTax'}):
        number = (_l4_usd(form[key]) if key in ('TotalFinalIncomeTaxPayableUsd', 'TotalTaxBaseUsd')
                  else _l4_numeric(form[key], 2 if key == 'TotalGrossIncome' else 0,
                                   exact_sum=key == 'TotalGrossIncome'))
        if key == 'TotalGrossIncome' and number != (gross or 0):
            raise _UnsupportedMetadata('unreconciled_corporate_l4_gross_total')
        entry = {**_evidence(form[key], [L4_ROOT, key]), 'source': 'current',
                 'rule': 'original-stored-total'}
        if key == 'TotalGrossIncome':
            entry.update(destination={'table': L4_EXCLUDED_TABLE, 'footer': 0, 'column': 4},
                rule=('null-singleton-stored-zero/display-blank' if excluded and gross is None else
                      'exact-ordered-reduce/angular-number-1.0-3-id'))
        evidence.append(entry)
    if 'TotalTaxBaseUsd' not in form:
        evidence.append({'path': [L4_ROOT, 'TotalTaxBaseUsd'], 'type': 'missing', 'value': None,
                         'source': 'current', 'rule': 'absent-unused-usd-root-total'})
    if not excluded:
        value = form['ListOfIncomeExcludedFromIncomeTax']
        evidence.append({'path': [L4_ROOT, 'ListOfIncomeExcludedFromIncomeTax'],
            'type': 'null' if value is None else 'array', 'value': deepcopy(value),
            'source': 'current', 'rule': 'original-inert-empty-block-b'})
    for key in sorted(footer):
        number = _l4_usd(footer[key]) if key in ('TaxBaseUsd', 'IncomeTaxUsd') else _l4_numeric(footer[key])
        stored_key = {'TaxBase': 'TotalTaxBase', 'IncomeTax': 'TotalFinalIncomeTaxPayable',
                      'TaxBaseUsd': 'TotalTaxBaseUsd', 'IncomeTaxUsd': 'TotalFinalIncomeTaxPayableUsd'}[key]
        if stored_key in form:
            # USD footer carries full precision; the root USD total is stored at
            # two decimals. Reconcile at the root's proven two-decimal precision
            # while preserving each original lexeme in provenance.
            stored = _l4_usd(form[stored_key]) if key in ('TaxBaseUsd', 'IncomeTaxUsd') else _l4_numeric(form[stored_key])
            quantum = Decimal(1).scaleb(-2)
            if number.quantize(quantum) != stored.quantize(quantum):
                raise _UnsupportedMetadata('unreconciled_corporate_l4_footer_total')
        entry = {**_evidence(footer[key], [key]), 'source': 'footer',
                 'rule': 'original-reconciled-grid-footer'}
        if key in ('TaxBase', 'IncomeTax'):
            entry['destination'] = {'table': L4_FINAL_TABLE, 'footer': 0,
                                    'column': 4 if key == 'TaxBase' else 6}
        evidence.append(entry)
    afooter = [['TOTAL', _number(footer['TaxBase'], 0, locale=locale), '',
                _number(footer['IncomeTax'], 0, locale=locale)]]
    bfooter = [['', 'JUMLAH', '' if excluded and gross is None else
                _number(str(gross or 0), 3, locale=locale, trim=True)]]
    return {'tables': [
        {'name': L4_FINAL_TABLE, 'headers': list(L4_A_HEADERS), 'rows': arows + afooter,
         'footer': afooter, 'footer_spans': deepcopy(L4_A_SPANS),
         'body_row_count': len(arows), 'source_total': len(arows), 'complete': True},
        {'name': L4_EXCLUDED_TABLE, 'headers': list(L4_B_HEADERS), 'rows': brows + bfooter,
         'footer': bfooter, 'footer_spans': deepcopy(L4_B_SPANS),
         'body_row_count': len(brows), 'source_total': len(brows), 'complete': True}],
        'fields': [], 'provenance': evidence}


def _l7_negative_profile(binding, *, root, payload, record, event, route, table):
    """Only a distinct capability plus final capture-owned facts admit negatives."""
    proof = binding.get('raw_negative_projection')
    fields = record.get('source_fields', {})
    pins = L7_NEGATIVE_BUILD_DIGESTS
    urls = {CIT_SOURCE, MAIN_SOURCE, VENDOR_SOURCE}
    literal = record.get('meta', {}).get('Model SPT')
    model = ('NORMAL' if literal == 'Normal' else 'AMENDMENT'
             if isinstance(literal, str) and re.fullmatch(r'Amendment [0-9]{3}', literal) else None)
    if (not isinstance(proof, dict) or proof.get('kind') != 'corporate-l7-stable-negative-v1'
            or set(pins) != urls or set(proof.get('builds', {})) != urls
            or any(type(value) is not str or not re.fullmatch(r'[a-f0-9]{64}', value)
                   for mapping in (pins, proof['builds']) for value in mapping.values())
            or proof['builds'] != pins or proof['route'] != route + '?view=true'
            or proof['route'] != event['frame_url'] or proof['locale'] != 'id-ID'
            or proof['timezone'] != 'Asia/Jakarta'
            or proof['visibility_binding'] != 'current-induk-enabled-v1'
            or proof['tables'] != [{**table, 'owner_chain': L7_OWNER_CHAIN}]
            or event.get('component_lifetime') is None or event.get('corporate_l7_lifetime') is None
            or fields.get('TaxTypeCode') != 'ICT_RCIT' or fields.get('ReturnSheetTypeCode') != 'ICT_RCITR'
            or model is None or fields.get('ReturnSheetModel') != literal
            or payload.get('ReturnSheetModel') != model
            or root.get('TaxType') != 'ICT_RCIT'
            or any(key not in payload or payload[key] is not None
                   for key in ('PreviousFormData', 'LastSubmittedFormData'))
            or 'IsCarriedForward' in payload):
        raise _UnsupportedMetadata('unverified_corporate_l7_raw_negative_lifecycle')
    return proof


def project_induk(main, *, tax_type):
    """Project the reviewed Induk identity slots; caller must prove the binding.

    Only slots whose payload control is present and scalar are emitted. A
    caption without a proven payload key is never guessed: the reviewed
    template decorations (``_INDUK_INCOME``/``_INDUK_CALCULATIONS``) stay
    unprojected, so the caller must report the section as partial.
    """
    if tax_type != 'ICT_RCIT' or not isinstance(main, dict):
        raise _UnsupportedMetadata('unsupported_corporate_induk_structure')
    fields, provenance = [], []
    for group, name, caption in INDUK_IDENTITY_FIELDS:
        if name not in main:
            continue
        value = main[name]
        # Only reviewed scalar controls: a JSON string or a number token. The
        # _CorporateNumber subclass marks number tokens; bool/list/dict/null
        # are never coerced into an identity value.
        if value is None:
            continue
        if not isinstance(value, str):
            raise _UnsupportedMetadata('unsupported_corporate_induk_identity_type')
        entry = _evidence(value, [INDUK_ROOT, name])
        text = entry['value']
        if not text or not str(text).strip():
            continue
        fields.append({'group': group, 'field': name, 'label': caption, 'value': text})
        entry.update(rule='literal-identity-control',
                     destination={'form': 'Induk', 'field': name})
        provenance.append(entry)
    return {'fields': fields, 'provenance': provenance}


def _induk_submitted(binding, *, main, root, payload, record, event):
    """Only stable submitted controls; editing arithmetic is NOT executed here."""
    proof = binding['projection']
    pins = INDUK_SUBMITTED_BUILD_DIGESTS
    urls = {CIT_SOURCE, MAIN_SOURCE, VENDOR_SOURCE}
    fields = record.get('source_fields', {})
    route = ORIGIN + '/returnsheets/id-ID/corporate-income-tax-return/' + '/'.join(
        str(value) for value in (fields.get('TaxpayerAggregateIdentifier'), record['record_id'],
                                fields.get('TaxTypeCode'), fields.get('AggregateIdentifier'))) + '?view=true'
    # Disabled controls also describe a read-only submitted record, so v3 evidence
    # alone never selects the inactive projection: the original fixed point decides.
    claimed_v3 = proof.get('kind') == 'corporate-induk-submitted-v3'
    inactive = claimed_v3 and _induk_inactive_profile(main)
    expected_controls = [name for _, name, _ in INDUK_SUBMITTED_FIELDS]
    if claimed_v3:
        expected_controls.extend(name for _, name, _ in INDUK_INACTIVE_FIELDS)
    if (set(proof) != {'kind', 'builds', 'route', 'locale', 'timezone', 'controls'}
            or proof.get('kind') not in ('corporate-induk-submitted-v2',
                                         'corporate-induk-submitted-v3')
            or not isinstance(proof.get('builds'), dict) or set(pins) != urls
            or set(proof['builds']) != urls
            or any(type(value) is not str or not re.fullmatch(r'[a-f0-9]{64}', value)
                   for mapping in (pins, proof['builds']) for value in mapping.values())
            or proof['builds'] != pins or proof['route'] != route
            or proof['route'] != event['frame_url'] or proof['locale'] != 'id-ID'
            or proof['timezone'] != 'Asia/Jakarta'
            or proof['controls'] != expected_controls
            or binding.get('paths') != [[INDUK_ROOT]] or 'primary' not in binding
            or any(binding.get(key) for key in ('grids', 'responses', 'dependencies'))):
        raise _UnsupportedMetadata('unverified_corporate_induk_submitted_binding')
    literal = record.get('meta', {}).get('Model SPT')
    model = ('NORMAL' if literal == 'Normal' else 'AMENDMENT'
             if isinstance(literal, str) and re.fullmatch(r'Amendment [0-9]{3}', literal) else None)
    if (event.get('component_lifetime') is None or fields.get('TaxTypeCode') != 'ICT_RCIT'
            or fields.get('ReturnSheetTypeCode') != 'ICT_RCITR'
            or model is None or fields.get('ReturnSheetModel') != literal
            or record.get('source_status') != 'SPT Dilaporkan'
            or payload.get('ReturnSheetModel') != model
            or payload.get('ReturnSheetStatusCode') != 'SUBMITTED'
            or payload.get('IsMigrated') is not False or root.get('TaxType') != 'ICT_RCIT'
            or any(key not in payload or payload[key] is not None
                   for key in ('PreviousFormData', 'LastSubmittedFormData'))
            or not isinstance(main, dict)):
        raise _UnsupportedMetadata('unverified_corporate_induk_submitted_lifecycle')
    # getDataFromBaseForm overwrites these eight identities after setFormData.
    # Admit only identical original typed values, preserving both owners.
    identity = (('PeriodYear', 'TaxYear'), ('PeriodMonthStart', 'AccountingPeriodStart'),
        ('PeriodMonthEnd', 'AccountingPeriodEnd'), ('ReturnSheetModel', 'Status'),
        ('TIN', 'Tin'), ('Name', 'Name'), ('Email', 'EmailAddress'), ('PhoneNumber', 'PhoneNumber'))
    if any(outer not in payload or inner not in main or payload[outer] is None
           or type(payload[outer]) is not type(main[inner]) or payload[outer] != main[inner]
           for outer, inner in identity):
        raise _UnsupportedMetadata('unsupported_corporate_induk_submitted_identity')
    result = project_induk(main, tax_type=fields['TaxTypeCode'])
    for group, name, caption in INDUK_SUBMITTED_FIELDS:
        if name not in main:
            raise _UnsupportedMetadata('unsupported_corporate_induk_submitted_presence')
        value = main[name]
        defaulted = value is None and name in (
            'InstallmentOfIncome', 'NoticeOfCollection', 'TotalApprovalInstallment')
        if value is None and name != 'NetIncomeBeforeTax':
            rendered = '0' if defaulted else ''
        else:
            try:
                number = _integer(value)
                if number == 0 and _decimal(value).is_signed():
                    raise _UnsupportedMetadata('unsupported_corporate_induk_submitted_number')
                if name == 'NetIncomeBeforeTax' and number < 0:
                    # The only submitted writer that could clear a negative
                    # main is the synchronous solely==1 reset. Both original
                    # patches exclude that trigger in this closed profile.
                    if (type(main.get('IsIncomeUnder')) is not _CorporateNumber
                            or main['IsIncomeUnder'] != '0'
                            or main.get('IsIncomeSolely') is not None):
                        raise _UnsupportedMetadata('unsupported_corporate_induk_submitted_number')
                    for key in ('IsIncomeUnder', 'IsIncomeSolely'):
                        predicate = _evidence(main.get(key), [INDUK_ROOT, key])
                        predicate.update(rule='submitted-negative-main/no-solely-reset',
                            destination={'form': 'Induk', 'control': 'negative-main-stability'})
                        result['provenance'].append(predicate)
                rendered = _number(value, 0, locale='id-ID')
            except (_UnsupportedMetadata, DecimalException):
                raise _UnsupportedMetadata('unsupported_corporate_induk_submitted_number') from None
        result['fields'].append({'group': group, 'field': '', 'label': caption, 'value': rendered})
        entry = _evidence(value, [INDUK_ROOT, name])
        entry.update(rule=('submitted-nullish-zero/input-number-id-0' if defaulted
                           else 'submitted-control/input-number-id-0'),
                     destination={'form': 'Induk', 'field': '', 'label': caption})
        result['provenance'].append(entry)
    if inactive:
        # _induk_inactive_profile already proved the exact original fixed point:
        # the three selectors and three amounts are original zero number tokens
        # and the amendment difference is an explicit null. Emit only; never
        # re-derive or coerce the values here.
        for key in INDUK_INACTIVE_SELECTORS:
            entry = _evidence(main[key], [INDUK_ROOT, key])
            entry.update(rule='submitted-original-inactive-selector',
                         destination={'form': 'Induk', 'control': 'inactive-profile'})
            result['provenance'].append(entry)
        last = INDUK_INACTIVE_FIELDS[-1][1]
        for group, name, caption in INDUK_INACTIVE_FIELDS:
            value = main[name]
            result['fields'].append({'group': group, 'field': '', 'label': caption,
                                     'value': '' if name == last else '0'})
            entry = _evidence(value, [INDUK_ROOT, name])
            entry.update(rule=('submitted-original-normal-null' if name == last
                               else 'submitted-original-inactive-zero'),
                         destination={'form': 'Induk', 'field': '', 'label': caption})
            result['provenance'].append(entry)
    result['inactive_profile'] = inactive
    for name in dict.fromkeys([outer for outer, _ in identity] +
            ['IsMigrated', 'ReturnSheetStatusCode', 'PreviousFormData', 'LastSubmittedFormData']):
        entry = ({'path': [name], 'type': 'boolean', 'value': False} if name == 'IsMigrated'
                 else _evidence(payload[name], [name]))
        entry.update(rule='retained-original-submitted-predicate', source='primary',
                     destination={'form': 'Induk', 'control': 'submitted-profile'})
        result['provenance'].append(entry)
    entry = _evidence(root['TaxType'], ['TaxType'])
    entry.update(rule='retained-original-submitted-predicate',
                 destination={'form': 'Induk', 'control': 'submitted-profile'})
    result['provenance'].append(entry)
    return result


def _apply_induk(binding, section, observed_forms, *, root, payload, record, event):
    proof = binding['projection']
    if isinstance(proof, dict) and proof.get('kind') in ('corporate-induk-submitted-v2', 'corporate-induk-submitted-v3'):
        result = _induk_submitted(binding, main=root.get(INDUK_ROOT), root=root,
            payload=payload, record=record, event=event)
    else:
        builds = proof.get('builds') if isinstance(proof, dict) else None
        # Legacy identity-only proof; no new numeric/environment requirement.
        if (not isinstance(proof, dict) or set(proof) != {'kind', 'builds', 'route'}
                or proof['kind'] != 'corporate-induk-v1'
                or not isinstance(builds, dict) or set(builds) != {CIT_SOURCE}
                or type(builds[CIT_SOURCE]) is not str or len(builds[CIT_SOURCE]) != 64
                or any(character not in '0123456789abcdef' for character in builds[CIT_SOURCE])
                or proof['route'] != event['frame_url']
                or binding.get('paths') != [[INDUK_ROOT]] or 'primary' not in binding):
            raise _UnsupportedMetadata('unverified_corporate_induk_binding')
        literal = record.get('meta', {}).get('Model SPT')
        model = ('NORMAL' if literal == 'Normal' else 'AMENDMENT'
                 if isinstance(literal, str) and re.fullmatch(r'Amendment [0-9]{3}', literal) else None)
        if (record.get('source_status') != 'SPT Dilaporkan'
                or payload.get('ReturnSheetStatusCode') != 'SUBMITTED' or model is None
                or payload.get('ReturnSheetModel') != model):
            raise _UnsupportedMetadata('unverified_corporate_induk_submitted_lifecycle')
        result = project_induk(root.get(INDUK_ROOT), tax_type=record.get('source_fields', {}).get('TaxTypeCode'))
    section['fields'] = result['fields']
    # Eight more amounts are proven; nine declarations are still unresolved.
    section['projection_complete'] = False
    section['projection_reason'] = INDUK_UNPROJECTED_REASON
    for entry in result['provenance']:
        entry.update(response_sequence=event['sequence'], container=(['Payload']
            if entry.get('source') == 'primary' else ['Payload', 'CurrentFormData']))
    return {'form': 'Induk', 'kind': proof['kind'], 'builds': dict(proof['builds']),
            'route': proof['route'], 'inactive_profile': result.get('inactive_profile', False),
            'values': result['provenance'],
            **({key: deepcopy(proof[key]) for key in ('locale', 'timezone', 'controls')}
               if proof['kind'] in ('corporate-induk-submitted-v2', 'corporate-induk-submitted-v3') else {})}


def _apply_l4(binding, section, observed_forms, *, root, payload, record, event,
              auxiliary_packets, reference_packets=None):
    proof = binding['projection']
    strong = isinstance(proof, dict) and proof.get('kind') == 'corporate-l4-populated-v2'
    builds = proof.get('builds') if isinstance(proof, dict) else None
    urls = {CIT_SOURCE, MAIN_SOURCE, VENDOR_SOURCE} if strong else {CIT_SOURCE}
    approved = L4_POPULATED_BUILD_DIGESTS if strong else {CIT_SOURCE: BUILD_DIGESTS.get(CIT_SOURCE)}
    keys = {'kind', 'builds', 'route', 'tables'} | ({'locale', 'timezone', 'references',
        'visibility_binding'} if strong else set())
    if (not isinstance(proof, dict) or set(proof) != keys
            or proof['kind'] not in ('corporate-l4-v1', 'corporate-l4-populated-v2')
            or not isinstance(builds, dict) or set(builds) != urls or set(approved) != urls
            or any(type(value) is not str or not re.fullmatch(r'[a-f0-9]{64}', value)
                   for mapping in (approved, builds) for value in mapping.values())
            or builds != approved or proof['tables'] != l4_tables()
            or any(type(span) is not int for table in proof['tables']
                   for row in table['footer_spans'] for span in row)
            or proof['route'] != event['frame_url']
            or binding.get('paths') != [[L4_ROOT]] or binding.get('responses')):
        raise _UnsupportedMetadata('unverified_corporate_l4_binding')
    literal = record.get('meta', {}).get('Model SPT')
    model = ('NORMAL' if literal == 'Normal' else 'AMENDMENT'
             if isinstance(literal, str) and re.fullmatch(r'Amendment [0-9]{3}', literal) else None)
    fields = record.get('source_fields', {})
    period = fields.get('TaxPeriodCode')
    if (record.get('source_status') != 'SPT Dilaporkan'
            or payload.get('ReturnSheetStatusCode') != 'SUBMITTED' or model is None
            or payload.get('ReturnSheetModel') != model
            or fields.get('TaxTypeCode') != 'ICT_RCIT'
            or type(period) is not str or not re.fullmatch(r'0112[0-9]{4}', period)):
        raise _UnsupportedMetadata('unverified_corporate_l4_submitted_lifecycle')
    catalogs, sources, labels = {}, {}, None
    if strong:
        route = ORIGIN + '/returnsheets/id-ID/corporate-income-tax-return/' + '/'.join(
            str(value) for value in (fields.get('TaxpayerAggregateIdentifier'), record['record_id'],
                                    fields.get('TaxTypeCode'), fields.get('AggregateIdentifier'))) + '?view=true'
        if (proof['route'] != route or proof['locale'] != 'id-ID' or proof['timezone'] != 'Asia/Jakarta'
                or event.get('component_lifetime') is None or literal != 'Normal'
                or fields.get('ReturnSheetTypeCode') != 'ICT_RCITR'
                or fields.get('ReturnSheetModel') != literal
                or 'Induk' not in [f['name'] for f in observed_forms[:observed_forms.index(binding)]]
                or any(key not in payload or payload[key] is not None
                       for key in ('PreviousFormData', 'LastSubmittedFormData'))):
            raise _UnsupportedMetadata('unverified_corporate_l4_populated_lifecycle')
        catalogs = bind_corporate_reference_catalogs(proof['references'], reference_packets or {},
            kinds=L4_CATALOG_KINDS, event=event, builds=builds)
        sources = {kind: catalog['source'] for kind, catalog in catalogs.items()}
        labels = {kind: catalog['lookups'] for kind, catalog in catalogs.items()}
    grids = binding.get('grids')
    if (not isinstance(grids, list) or len(grids) != 1 or not isinstance(grids[0], dict)
            or set(grids[0]) != {'name', 'endpoint', 'pages'}
            or grids[0]['name'] != L4_GRID_NAME or grids[0]['endpoint'] != CORPORATE_L4_GRID_URL
            or not isinstance(grids[0]['pages'], list)
            or not 1 <= len(grids[0]['pages']) <= (1000 if strong else 1)):
        raise _UnsupportedMetadata('unverified_corporate_l4_grid_binding')
    requests = []
    for declaration in grids[0]['pages']:
        if not isinstance(declaration, dict) or set(declaration) != {'request_json', 'offset'}:
            raise _UnsupportedMetadata('unverified_corporate_l4_grid_binding')
        request = declaration['request_json']
        if (not isinstance(request, dict)
                or set(request) != {'ReturnSheetRecordId', 'LanguageId', 'First', 'Rows',
                                    'SortField', 'SortOrder', 'Filters', 'PeriodYear'}
                or request['ReturnSheetRecordId'] != record['record_id']
                or request['LanguageId'] != 'id-ID' or type(request['First']) is not int
                or request['First'] < 0 or (not strong and request['First'] != 0)
                or type(declaration['offset']) is not int or declaration['offset'] != request['First']
                or type(request['Rows']) is not int or request['Rows'] not in (10, 25, 50, 100, 250, 500)
                or request['SortField'] != '' or type(request['SortOrder']) is not int
                or request['SortOrder'] != 1 or request['Filters'] != [] or request['PeriodYear'] != period[-4:]):
            raise _UnsupportedMetadata('unsupported_corporate_l4_page_request')
        requests.append(request)
    requests.sort(key=lambda value: value['First'])
    dependencies = binding.get('dependencies')
    if (not isinstance(dependencies, list) or not 1 <= len(dependencies) <= 2
            or any(not isinstance(item, dict) or set(item) != {'endpoint', 'request_json'}
                   or item['endpoint'] != CORPORATE_L4_FOOTER_URL
                   or item['request_json'] not in ({'ReturnSheetRecordId': record['record_id']},
                       {'ReturnSheetRecordId': record['record_id'], 'PeriodYear': period[-4:]})
                   for item in dependencies)):
        raise _UnsupportedMetadata('unverified_corporate_l4_footer_binding')
    grid_keys = [(CORPORATE_L4_GRID_URL, _corporate_request_key(request)) for request in requests]
    footer_keys = [(CORPORATE_L4_FOOTER_URL, _corporate_request_key(item['request_json']))
                   for item in dependencies]
    if (len(set(grid_keys)) != len(grid_keys) or len(set(footer_keys)) != len(footer_keys)
            or {*grid_keys, *footer_keys} != {key for key in auxiliary_packets
                if key[0] in (CORPORATE_L4_GRID_URL, CORPORATE_L4_FOOTER_URL)}):
        raise _UnsupportedMetadata('incomplete_corporate_l4_auxiliary_packets')
    pages, page_sources, values = [], [], []
    for request, key in zip(requests, grid_keys):
        grid = auxiliary_packets[key]
        source = grid['payload']
        if (not isinstance(source, dict) or set(source) != {'TotalRecords', 'Data', 'Index'}
                or source['Index'] is not None or not isinstance(source['Data'], list)):
            raise _UnsupportedMetadata('unsupported_corporate_l4_page_payload')
        pages.append({'offset': request['First'], 'rows': request['Rows'],
                      'total': _corporate_integer(source['TotalRecords']), 'data': source['Data']})
        page_sources.append(grid['event'])
        for field in ('TotalRecords', 'Index'):
            values.append({**_evidence(source[field], [field]), 'source': 'grid',
                'response_sequence': grid['event']['sequence'], 'container': ['Payload'],
                'rule': 'original-grid-envelope'})
        if not source['Data']:
            values.append({'path': ['Data'], 'type': 'array', 'value': [], 'source': 'grid',
                'response_sequence': grid['event']['sequence'], 'container': ['Payload'],
                'rule': 'original-empty-grid-body'})
    for key in footer_keys:
        footer = auxiliary_packets[key]
        result = project_l4(root.get(L4_ROOT), footer=footer['payload'], pages=pages,
                            tax_type=fields['TaxTypeCode'], locale='id-ID', labels=labels)
        for entry in result['provenance']:
            source = (event if entry['source'] == 'current' else
                      page_sources[entry['page_index']] if entry['source'] == 'grid' else footer['event'])
            entry.update(response_sequence=source['sequence'],
                         container=['Payload', 'CurrentFormData'] if source is event else ['Payload'])
            if key == footer_keys[0] or entry['source'] == 'footer':
                values.append(entry)
            kind = entry.get('reference_kind')
            if kind is not None and key == footer_keys[0]:
                values.append({**deepcopy(catalogs[kind]['selected'][entry['value']]),
                    'response_sequence': sources[kind]['sequence'], 'container': ['Payload'],
                    'destination': deepcopy(entry['destination'])})
    for kind, catalog in catalogs.items():
        values.extend({**entry, 'response_sequence': sources[kind]['sequence'],
            'container': ['Payload'], 'destination': {'form': 'L4', 'reference': kind}}
            for entry in catalog['provenance'])
    # All validation precedes replacement, including every declared footer.
    section['tables'], section['fields'] = result['tables'], result['fields']
    return {'form': 'L4', 'kind': proof['kind'], 'builds': dict(builds),
            'route': proof['route'], 'scope': ('source-bound-populated-both-blocks' if strong else
                                              'empty-both-blocks-only'), 'values': values}

def project_l10a(rows, *, headers, tax_type, locale):
    """Only empty rows are proved without original active catalog descriptions.

    The ordinary grid reference branch does NOT display raw codes. Its number
    branch uses DecimalPipe 1.0-0, not two-decimal trimming. No populated,
    including null-code/null-amount, branch is admitted by this capability.
    """
    if (tax_type != 'ICT_RCIT' or locale != 'id-ID' or headers != L10A_HEADERS
            or not isinstance(rows, list)):
        raise _UnsupportedMetadata('unverified_corporate_l10a_structure')
    if rows:
        raise _UnsupportedMetadata('unsupported_corporate_l10a_populated')
    return {'rows': [], 'provenance': []}


L10A_LABELS = {'Country': 'COUNTRY_CODE',
               'TypeOfTransaction': 'TRANSACTION_TYPE', 'PricingMethod': 'PRICING_METHOD'}
# The relationship code is not exposed as a live reference request; the portal
# resolves it from its own reviewed enum. Pinned from the portal's
# RELATIONSHIP_TYPE catalog (Pasal 18 ayat (4) huruf a-c, Pasal 9 ayat (1)).
L10A_RELATIONSHIP_LABELS = {
    'CIT_RT_01': 'Hubungan istimewa karena kepemilikan saham/ penyertaan sebagaimana '
                 'diatur oleh Pasal 18 ayat (4) huruf a UU Pajak Penghasilan',
    'CIT_RT_02': 'Hubungan istimewa karena penguasaan sebagaimana diatur oleh '
                 'Pasal 18 ayat (4) huruf b UU Pajak Penghasilan',
    'CIT_RT_03': 'Hubungan istimewa karena hubungan keluarga sebagaimana diatur oleh '
                 'Pasal 18 ayat (4) huruf c UU Pajak Penghasilan',
    'CIT_RT_04': 'Hubungan istimewa karena pengendalian sebagaimana diatur oleh '
                 'Pasal 9 ayat (1) Perjanjian Penghindaran Pajak Berganda (tax treaty) '
                 'antara Indonesia dengan negara domisili pihak yang mempunyai '
                 'hubungan istimewa dengan wajib pajak',
}
L10A_BUILD_DIGESTS = dict(L11C_BUILD_DIGESTS)


def _l10a_number(value):
    # The active checkIsString predicate includes null; null never reaches the
    # number pipe even though that pipe internally coalesces null to zero.
    if value is None or type(value) is str:
        if type(value) is str and re.match(r'^(0[0-9]|1[0-9]|2[0-3]):[0-5][0-9]', value):
            raise _UnsupportedMetadata('unsupported_corporate_l10a_time_string')
        return '' if value is None else value, 'grid-checkIsString/literal-null-or-string'
    if type(value) is not _CorporateNumber:
        raise _UnsupportedMetadata('unsupported_corporate_l10a_number_type')
    try:
        _decimal(value)  # Preserve the original strict finite/token budget gate.
        if not re.fullmatch(r'-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?', value):
            raise _UnsupportedMetadata('unsupported_corporate_l10a_number_precision')
        # JSON.parse has already converted the original decimal token to a
        # binary64 Number before Ka/DecimalPipe sees it. Keep the wire token in
        # provenance, but render that Number, including rounded decimal inputs
        # and real Number underflow. Do not apply Decimal math to the raw token.
        browser_number = float(value)
        number = Decimal.from_float(browser_number)
        if not number.is_finite() or abs(number) > _MAX_INTEGER:
            raise _UnsupportedMetadata('unsupported_corporate_l10a_number_precision')
        # In this bounded range every integer and half-integer is exactly
        # representable. A round-trip decimal spelling of the same binary64
        # cannot cross one of those thresholds. Thus Python's spelling and the
        # pinned Angular Number.toString path have identical zero-digit rounding;
        # the independent exact-source Edge inventory exercises those boundaries.
        text = _number(str(browser_number), 0, locale='id-ID')
        if abs(_decimal(text.replace('.', ''))) > _MAX_INTEGER:
            raise _UnsupportedMetadata('unsupported_corporate_l10a_number_precision')
        return text, 'angular-decimal-1.0-0-id/json-number-binary64'
    except (_UnsupportedMetadata, DecimalException, ValueError, OverflowError):
        raise _UnsupportedMetadata('unsupported_corporate_l10a_number_precision') from None


def project_l10a_populated(rows, *, headers, tax_type, locale, labels):
    """Pure active-grid consumer; caller proves original catalog and SPA custody.

    This is additive to empty-v1, never a raw-code fallback. Complete catalog
    inventories prove even null/missing-code blank descriptions. Preserve every
    original page-local leaf, duplicate occurrence and numeric lexeme.
    """
    if (tax_type != 'ICT_RCIT' or locale != 'id-ID' or headers != L10A_HEADERS
            or not isinstance(rows, list) or not 1 <= len(rows) <= 10000):
        raise _UnsupportedMetadata('unverified_corporate_l10a_structure')
    if (not isinstance(labels, dict) or set(labels) != set(L10A_LABELS.values())
            or any(not isinstance(catalog, dict) or any(type(code) is not str or not code
                or type(label) is not str or not label.strip() for code, label in catalog.items())
                for catalog in labels.values())):
        raise _UnsupportedMetadata('unverified_corporate_l10a_catalogs')
    rendered, evidence = [], []
    for index, source in enumerate(rows):
        if (not isinstance(source, dict) or not set(L10A_COLUMNS) <= set(source)
                or set(source) - set(L10A_COLUMNS) - {'RecordId'}
                or 'RecordId' in source and (type(source['RecordId']) is not str
                    or not re.fullmatch(r'[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}', source['RecordId']))):
            raise _UnsupportedMetadata('unsupported_corporate_l10a_row')
        output = []
        for column, key in enumerate(L10A_COLUMNS):
            value = source[key]
            entry = _evidence(value, ['Data', index, key])
            entry['destination'] = {'table': L10A_GRID_NAME, 'row': index, 'column': column}
            if key in L10A_LABELS:
                if value is not None and type(value) is not str:
                    raise _UnsupportedMetadata('unsupported_corporate_l10a_reference_type')
                text = labels[L10A_LABELS[key]].get(value, '')
                entry['rule'] = 'bound-reference-description'
            elif key == 'RelationshipCode':
                # Reviewed portal enum, not a captured reference request.
                if value is not None and type(value) is not str:
                    raise _UnsupportedMetadata('unsupported_corporate_l10a_reference_type')
                text = '' if value is None else L10A_RELATIONSHIP_LABELS.get(value, '')
                entry['rule'] = 'reviewed-relationship-enum'
            elif key == 'TransactionValue':
                text, entry['rule'] = _l10a_number(value)
            elif value is None or type(value) is str:
                text, entry['rule'] = '' if value is None else value, 'literal-string'
            else:
                raise _UnsupportedMetadata('unsupported_corporate_l10a_text_type')
            output.append(text)
            evidence.append(entry)
        if 'RecordId' in source:
            entry = _evidence(source['RecordId'], ['Data', index, 'RecordId'])
            entry.update(rule='retained-original-unused-row-id',
                         destination={'table': L10A_GRID_NAME, 'row': index, 'control': 'RecordId'})
            evidence.append(entry)
        rendered.append(output)
    return {'rows': rendered, 'provenance': evidence}


def _l10a_grid_binding(binding, record_id):
    """The empty branch needs exactly the reviewed first ten-row request."""
    grids = binding.get('grids')
    if (not isinstance(grids, list) or len(grids) != 1 or not isinstance(grids[0], dict)
            or set(grids[0]) != {'name', 'endpoint', 'pages'}
            or grids[0]['name'] != L10A_GRID_NAME or grids[0]['endpoint'] != L10A_GRID_ENDPOINT
            or not isinstance(grids[0]['pages'], list) or len(grids[0]['pages']) != 1
            or binding.get('responses') or binding.get('dependencies')):
        raise _UnsupportedMetadata('unverified_corporate_l10a_grid_binding')
    page = grids[0]['pages'][0]
    expected = {'ReturnSheetRecordId': record_id, 'First': 0, 'Rows': 10,
                'SortField': '', 'SortOrder': 1, 'Filters': [], 'LanguageId': 'id-ID'}
    if (not isinstance(page, dict) or set(page) != {'request_json', 'offset'}
            or type(page['offset']) is not int or page['offset'] != 0
            or _corporate_request_key(page['request_json']) != _corporate_request_key(expected)):
        raise _UnsupportedMetadata('unverified_corporate_l10a_grid_page')
    return expected


def _l10a_page_source(packets, request):
    """Choose earliest successful original exact-query packet, not iterator-first."""
    matches = []
    for packet in packets.values():
        event = packet['event']
        if (packet['successful'] is True and event.get('url') == L10A_GRID_ENDPOINT
                and event.get('method') == 'POST'
                and type(event.get('status')) is int and 200 <= event['status'] < 300
                and type(event.get('sequence')) is int and event['sequence'] > 0
                and _corporate_request_key(event.get('request_json')) == _corporate_request_key(request)):
            matches.append(packet)
    if not matches:
        raise _UnsupportedMetadata('missing_corporate_l10a_grid_response')
    return min(matches, key=lambda packet: packet['event']['sequence'])


def _apply_l10a_populated(binding, section, observed_forms, *, root, payload, record, event,
                          grid_packets, reference_packets):
    proof = binding['projection']
    pins = L10A_BUILD_DIGESTS
    if (not isinstance(proof, dict)
            or set(proof) != {'kind', 'builds', 'route', 'locale', 'timezone', 'tables',
                              'references', 'visibility_binding'}
            or proof['kind'] != 'corporate-l10a-populated-v1'
            or proof['visibility_binding'] != 'current-induk-enabled-v1'
            or set(pins) != {CIT_SOURCE, MAIN_SOURCE, VENDOR_SOURCE}
            or any(type(digest) is not str or not re.fullmatch(r'[0-9a-f]{64}', digest)
                   for digest in pins.values())
            or proof['builds'] != pins or proof['route'] != event['frame_url']
            or proof['locale'] != 'id-ID' or proof['timezone'] != 'Asia/Jakarta'
            or binding.get('paths') != [[L10A_ROOT]]):
        raise _UnsupportedMetadata('unverified_corporate_l10a_binding')
    fields = record.get('source_fields', {})
    route = ORIGIN + '/returnsheets/id-ID/corporate-income-tax-return/' + '/'.join(
        str(value) for value in (fields.get('TaxpayerAggregateIdentifier'), record['record_id'],
                                fields.get('TaxTypeCode'), fields.get('AggregateIdentifier'))) + '?view=true'
    literal = record.get('meta', {}).get('Model SPT')
    model = ('NORMAL' if literal == 'Normal' else 'AMENDMENT'
             if isinstance(literal, str) and re.fullmatch(r'Amendment [0-9]{3}', literal) else None)
    main = root.get('MainFormData')
    tables = proof['tables']
    structure = {'form': 'L10-A', 'owner_chain': [
        'rshshr-citr-l10a-form', 'rshshr-citr-l10a-form-grid1', 'ui-grid', 'p-table', 'table'],
        'header_controls': ['PeriodYear', 'CollectorTin']}
    if (not isinstance(tables, list) or len(tables) != 1 or not isinstance(tables[0], dict)
            or tables[0] != {'component': 'rshshr-citr-l10a-form-grid1',
                'headers': L10A_HEADERS, 'footer_spans': [], 'source_structure': structure}):
        raise _UnsupportedMetadata('unverified_corporate_l10a_grid_owner')
    present, value = L10A_ROOT in root, root.get(L10A_ROOT)
    if present and value is not None and not (type(value) in (list, dict) and not value):
        raise _UnsupportedMetadata('unsupported_corporate_l10a_source_root')
    grids = binding.get('grids')
    if (not isinstance(grids, list) or len(grids) != 1 or not isinstance(grids[0], dict)
            or set(grids[0]) != {'name', 'endpoint', 'pages'}
            or grids[0]['name'] != L10A_GRID_NAME or grids[0]['endpoint'] != L10A_GRID_ENDPOINT
            or not isinstance(grids[0]['pages'], list) or not 1 <= len(grids[0]['pages']) <= 1000
            or binding.get('responses') or binding.get('dependencies')):
        raise _UnsupportedMetadata('unverified_corporate_l10a_grid_binding')
    pages, offsets = [], set()
    for page in grids[0]['pages']:
        if (not isinstance(page, dict) or set(page) != {'request_json', 'offset'}
                or type(page['offset']) is not int or page['offset'] < 0 or page['offset'] in offsets):
            raise _UnsupportedMetadata('unverified_corporate_l10a_grid_page')
        query = {'ReturnSheetRecordId': record['record_id'], 'First': page['offset'], 'Rows': 10,
                 'SortField': '', 'SortOrder': 1, 'Filters': [], 'LanguageId': 'id-ID'}
        if _corporate_request_key(page['request_json']) != _corporate_request_key(query):
            raise _UnsupportedMetadata('unverified_corporate_l10a_grid_page')
        offsets.add(page['offset'])
        pages.append((_l10a_page_source(grid_packets, query), query))
    if (len(grids[0]['pages']) == 1 and
            _corporate_integer(pages[0][0]['payload']['TotalRecords']) == 0):
        # A valid stronger offer cannot disable the independently valid legacy
        # empty path. No catalog label or populated-only flag is consumed here.
        empty = {**binding, 'projection': {'kind': 'corporate-l10a-empty-v1',
            'builds': {CIT_SOURCE: proof['builds'][CIT_SOURCE]}, 'route': proof['route']}}
        empty_forms = [empty if form is binding else form for form in observed_forms]
        report = _apply_l10a(empty, section, empty_forms, root=root, payload=payload,
            record=record, event=event, grid_packets=grid_packets)
        report['offered_kind'] = proof['kind']
        return report
    if (proof['route'] != route or event.get('component_lifetime') is None
            or fields.get('TaxTypeCode') != 'ICT_RCIT' or fields.get('ReturnSheetTypeCode') != 'ICT_RCITR'
            or fields.get('ReturnSheetStatusCode') != 'SUBMITTED'
            or record.get('source_status') != 'SPT Dilaporkan'
            or payload.get('ReturnSheetStatusCode') != 'SUBMITTED' or model is None
            or payload.get('ReturnSheetModel') != model or fields.get('ReturnSheetModel') != literal
            or not isinstance(main, dict)
            or not _current_induk_visibility(payload, main, 'IsTransactionWithRelated', proof)
            or 'Induk' not in [f['name'] for f in observed_forms[:observed_forms.index(binding)]]):
        raise _UnsupportedMetadata('unverified_corporate_l10a_submitted_lifecycle')
    if 'PreviousFormData' not in payload:
        raise _UnsupportedMetadata('missing_corporate_l10a_previous_encoding')
    previous = payload['PreviousFormData']
    if previous is not None:
        if type(previous) is not str:
            raise _UnsupportedMetadata('unsupported_corporate_l10a_previous_encoding')
        try:
            decoded_previous = _corporate_json(previous)
        except JsonSafetyError:
            raise _UnsupportedMetadata('unsupported_corporate_l10a_previous_encoding') from None
        if decoded_previous is not None and not isinstance(decoded_previous, dict):
            raise _UnsupportedMetadata('unsupported_corporate_l10a_previous_shape')
    if (type(payload.get('PeriodYear')) is not _CorporateNumber
            or not re.fullmatch(r'[0-9]{4}', payload['PeriodYear'])
            or type(payload.get('TIN')) is not str):
        raise _UnsupportedMetadata('unverified_corporate_l10a_header_sources')
    catalogs = bind_corporate_reference_catalogs(proof['references'], reference_packets,
        kinds=tuple(L10A_LABELS.values()), event=event, builds=proof['builds'])
    rows, values, queries, total = [], [], [], None
    for source, query in sorted(pages, key=lambda item: item[1]['First']):
        page, source_event = source['payload'], source['event']
        count = _corporate_integer(page['TotalRecords'])
        data = page['Data']
        if (query['First'] != len(rows) or not isinstance(data, list) or not data
                or len(data) > 10 or total is not None and total != count):
            raise _UnsupportedMetadata('unverified_corporate_l10a_complete_pages')
        total = count
        result = project_l10a_populated(data, headers=proof['tables'][0]['headers'],
            tax_type=fields['TaxTypeCode'], locale=proof['locale'],
            labels={kind: catalog['lookups'] for kind, catalog in catalogs.items()})
        for entry in result['provenance']:
            entry['destination']['row'] += len(rows)
            entry.update(response_sequence=source_event['sequence'], container=['Payload'])
            values.append(entry)
            kind = L10A_LABELS.get(entry['path'][-1])
            if kind is not None and entry['value'] in catalogs[kind]['selected']:
                values.append({**deepcopy(catalogs[kind]['selected'][entry['value']]),
                    'response_sequence': catalogs[kind]['source']['sequence'], 'container': ['Payload'],
                    'destination': deepcopy(entry['destination'])})
        for key in ('TotalRecords', 'Index'):
            entry = _evidence(page[key], [key])
            entry.update(response_sequence=source_event['sequence'], container=['Payload'],
                         rule='captured-original-grid-control')
            values.append(entry)
        rows.extend(result['rows'])
        queries.append(deepcopy(query))
    if len(rows) != total:
        raise _UnsupportedMetadata('unverified_corporate_l10a_complete_pages')
    for kind, catalog in catalogs.items():
        values.extend({**entry, 'response_sequence': catalog['source']['sequence'], 'container': ['Payload'],
            'destination': {'table': L10A_GRID_NAME, 'reference': kind}} for entry in catalog['provenance'])
    for owner, source, prefix, keys in ((payload, 'primary', [], ('ReturnSheetStatusCode',
            'ReturnSheetModel', 'PreviousFormData', 'IsTransactionWithRelated')),
            (main, 'current', ['MainFormData'], ('IsTransactionWithRelated',))):
        for key in keys:
            if key not in owner:
                # The live amendment omits the outer transaction flag; the
                # current-Induk visibility binding proves it instead.
                continue
            entry = _evidence(owner[key], prefix + [key])
            entry.update(response_sequence=event['sequence'],
                container=['Payload'] if source == 'primary' else ['Payload', 'CurrentFormData'],
                rule='retained-original-submitted-grid-predicate')
            values.append(entry)
    source_root = {'present': present, 'path': [L10A_ROOT], 'response_sequence': event['sequence'],
                   'container': ['Payload', 'CurrentFormData']}
    if present:
        source_root.update(type='null' if value is None else 'array' if type(value) is list else 'object',
                           value=deepcopy(value))
    section['fields'] = [
        {'group': 'HEADER', 'field': 'PeriodYear', 'label': 'Tahun Pajak', 'value': str(payload['PeriodYear'])},
        {'group': 'HEADER', 'field': 'CollectorTin', 'label': 'Nomor Identitas WP', 'value': payload['TIN']}]
    for control, key in (('PeriodYear', 'PeriodYear'), ('CollectorTin', 'TIN')):
        entry = _evidence(payload[key], [key])
        entry.update(response_sequence=event['sequence'], container=['Payload'],
            rule='outer-baseFormData/input-text', destination={'form': 'L10-A', 'field': control})
        values.append(entry)
    # The approved clean template intentionally omits these two real header
    # controls. Preserve them and their unresolved counts; never hide them to
    # manufacture a COMPLETE nine-column worksheet.
    section['projection_complete'] = False
    section['projection_reason'] = 'l10a_header_slots_omitted'
    section['tables'] = [{'name': L10A_GRID_NAME, 'headers': list(L10A_HEADERS), 'rows': rows,
        'footer': [], 'footer_spans': [], 'body_row_count': len(rows), 'source_total': total, 'complete': True}]
    return {'form': 'L10-A', 'kind': proof['kind'], 'builds': dict(proof['builds']),
            'route': proof['route'], 'source_root': source_root, 'grid_requests': queries, 'values': values}


def _apply_l10a(binding, section, observed_forms, *, root, payload, record, event, grid_packets,
                 reference_packets=None):
    proof = binding['projection']
    if isinstance(proof, dict) and proof.get('kind') == 'corporate-l10a-populated-v1':
        return _apply_l10a_populated(binding, section, observed_forms, root=root, payload=payload,
            record=record, event=event, grid_packets=grid_packets, reference_packets=reference_packets or {})
    approved = BUILD_DIGESTS.get(CIT_SOURCE)
    if (not isinstance(proof, dict) or set(proof) != {'kind', 'builds', 'route'}
            or proof['kind'] != 'corporate-l10a-empty-v1'
            or type(approved) is not str or not re.fullmatch(r'[0-9a-f]{64}', approved)
            or proof['builds'] != {CIT_SOURCE: approved}
            or proof['route'] != event['frame_url'] or binding.get('paths') != [[L10A_ROOT]]):
        raise _UnsupportedMetadata('unverified_corporate_l10a_binding')
    fields = record.get('source_fields', {})
    route = ORIGIN + '/returnsheets/id-ID/corporate-income-tax-return/' + '/'.join(
        str(value) for value in (fields.get('TaxpayerAggregateIdentifier'), record['record_id'],
                                fields.get('TaxTypeCode'), fields.get('AggregateIdentifier'))) + '?view=true'
    literal = record.get('meta', {}).get('Model SPT')
    model = ('NORMAL' if literal == 'Normal' else 'AMENDMENT'
             if isinstance(literal, str) and re.fullmatch(r'Amendment [0-9]{3}', literal) else None)
    if (proof['route'] != route or event.get('component_lifetime') is None
            or fields.get('TaxTypeCode') != 'ICT_RCIT' or fields.get('ReturnSheetTypeCode') != 'ICT_RCITR'
            or record.get('source_status') != 'SPT Dilaporkan'
            or payload.get('ReturnSheetStatusCode') != 'SUBMITTED' or model is None
            or payload.get('ReturnSheetModel') != model or fields.get('ReturnSheetModel') != literal
            or 'Induk' not in [f['name'] for f in observed_forms[:observed_forms.index(binding)]]):
        raise _UnsupportedMetadata('unverified_corporate_l10a_submitted_lifecycle')
    request = _l10a_grid_binding(binding, record['record_id'])
    present, value = L10A_ROOT in root, root.get(L10A_ROOT)
    if present and value is not None and not (type(value) in (list, dict) and not value):
        # Flattened [{}] / {'Body': []} each has one empty leaf but is NOT an
        # inert root. Inspect the decoded original before replacing any table.
        raise _UnsupportedMetadata('unsupported_corporate_l10a_source_root')
    source = _l10a_page_source(grid_packets, request)
    page, source_event = source['payload'], source['event']
    # Packet shape, exact totals, contiguity and snapshots already passed in
    # the adapter. Preserve their original typed controls rather than rebuild
    # them from the generic presentation leaves or synthesize zero/null.
    if _corporate_integer(page['TotalRecords']) != 0 or page['Data']:
        raise _UnsupportedMetadata('unsupported_corporate_l10a_populated')
    result = project_l10a([] if page['Data'] is None else page['Data'],
                          headers=list(L10A_HEADERS), tax_type=fields.get('TaxTypeCode'), locale='id-ID')
    source_root = {'present': present, 'path': [L10A_ROOT],
                   'response_sequence': event['sequence'], 'container': ['Payload', 'CurrentFormData']}
    if present:
        source_root.update(type='null' if value is None else 'array' if type(value) is list else 'object',
                           value=deepcopy(value))
    values = [{'path': ['Data'], 'type': 'null' if page['Data'] is None else 'array',
               'value': deepcopy(page['Data'])},
              _evidence(page['TotalRecords'], ['TotalRecords']), _evidence(page['Index'], ['Index'])]
    for entry in values:
        entry.update(response_sequence=source_event['sequence'], container=['Payload'],
                     rule='captured-empty-grid-control')
    section['fields'] = []
    section['tables'] = [{'name': L10A_GRID_NAME, 'headers': list(L10A_HEADERS),
                          'rows': result['rows'], 'footer': [], 'footer_spans': [],
                          'body_row_count': 0, 'source_total': 0, 'complete': True}]
    return {'form': 'L10-A', 'kind': proof['kind'], 'builds': dict(proof['builds']),
            'route': proof['route'], 'source_root': source_root,
            'grid_request': deepcopy(request), 'values': values}


def project_l6(form, *, tax_type, locale):
    """Project the approved Angsuran PPh 25 worksheet; caller must prove binding.

    Every displayed amount is a literal payload control the pinned owner binds
    to the sheet, and the two subtractions the owner performs are re-checked
    exactly. Nothing is invented for an absent control.
    """
    if tax_type != 'ICT_RCIT' or locale != 'id-ID' or not isinstance(form, dict):
        raise _UnsupportedMetadata('unsupported_corporate_l6_structure')
    expected = {name for name, _ in L6_FIELDS} | set(L6_EDIT_FLAGS)
    if set(form) - expected or not expected - {'FiscalLossCompensation'} <= set(form):
        raise _UnsupportedMetadata('unsupported_corporate_l6_source_shape')
    if any(type(form[name]) is not bool for name in L6_EDIT_FLAGS):
        raise _UnsupportedMetadata('unsupported_corporate_l6_edit_flag')
    amounts = {}
    for name, _ in L6_FIELDS:
        value = form.get(name)
        if name == 'FiscalLossCompensation' and value is None:
            amounts[name] = Decimal(0)
            continue
        if type(value) is not _CorporateNumber:
            raise _UnsupportedMetadata('unsupported_corporate_l6_amount_type')
        number = _decimal(value)
        if number < 0:
            raise _UnsupportedMetadata('unsupported_corporate_l6_negative_amount')
        # The reviewed ICT_RCIT control displays whole rupiah. Do not round
        # fractional/unsafe source values into a different captured amount.
        if number != number.to_integral_value() or number > _MAX_INTEGER:
            raise _UnsupportedMetadata('unsupported_corporate_l6_amount_precision')
        amounts[name] = number
    if amounts['TaxableIncome'] != max(
            Decimal(0), amounts['IncomeAsTheBasisOfInstallment'] - amounts['FiscalLossCompensation']):
        raise _UnsupportedMetadata('unreconciled_corporate_l6_taxable_income')
    if amounts['IncomeTaxSelfpaid'] != max(
            Decimal(0), amounts['IncomeTaxPayable'] - amounts['TaxCreditWitheld']):
        raise _UnsupportedMetadata('unreconciled_corporate_l6_self_paid_tax')
    fields, provenance = [], []
    for name, caption in L6_FIELDS:
        value = form.get(name)
        fields.append({'group': '', 'field': name, 'label': caption,
                       'value': '0' if value is None else _number(value, 0, locale=locale)})
        entry = _evidence(value, [L6_ROOT, name])
        entry.update(rule='literal-installment-control',
                     destination={'form': 'L6', 'field': name})
        provenance.append(entry)
    for name in L6_EDIT_FLAGS:
        provenance.append({'path': [L6_ROOT, name], 'type': 'boolean',
                           'value': form[name], 'rule': 'retained-edit-flag',
                           'destination': {'form': 'L6', 'hidden_control': name}})
    return {'fields': fields, 'provenance': provenance}


def _apply_l6(binding, section, observed_forms, *, root, payload, record, event):
    proof = binding['projection']
    builds = proof.get('builds') if isinstance(proof, dict) else None
    if (not isinstance(proof, dict) or set(proof) != {'kind', 'builds', 'route'}
            or proof['kind'] != 'corporate-l6-v1'
            or not isinstance(builds, dict) or set(builds) != {CIT_SOURCE}
            or type(builds[CIT_SOURCE]) is not str or len(builds[CIT_SOURCE]) != 64
            or any(character not in '0123456789abcdef' for character in builds[CIT_SOURCE])
            or builds[CIT_SOURCE] != BUILD_DIGESTS.get(CIT_SOURCE)
            or proof['route'] != event['frame_url']
            or binding.get('paths') != [[L6_ROOT]]
            or binding.get('grids') or binding.get('responses') or binding.get('dependencies')):
        raise _UnsupportedMetadata('unverified_corporate_l6_binding')
    literal = record.get('meta', {}).get('Model SPT')
    model = ('NORMAL' if literal == 'Normal' else 'AMENDMENT'
             if isinstance(literal, str) and re.fullmatch(r'Amendment [0-9]{3}', literal) else None)
    if (record.get('source_status') != 'SPT Dilaporkan'
            or payload.get('ReturnSheetStatusCode') != 'SUBMITTED' or model is None
            or payload.get('ReturnSheetModel') != model):
        raise _UnsupportedMetadata('unverified_corporate_l6_submitted_lifecycle')
    fields = record.get('source_fields', {})
    result = project_l6(root.get(L6_ROOT), tax_type=fields.get('TaxTypeCode'), locale='id-ID')
    section['fields'] = result['fields']
    section['tables'] = []
    for entry in result['provenance']:
        entry.update(response_sequence=event['sequence'], container=['Payload', 'CurrentFormData'])
    return {'form': 'L6', 'kind': proof['kind'], 'builds': dict(proof['builds']),
            'route': proof['route'], 'values': result['provenance']}


def _l2_exact(value, digits):
    """No coercion/rounding subset of JSON.parse Number and DecimalPipe."""
    if value is None:
        return None
    if (type(value) is not _CorporateNumber or len(value) > 64
            or not re.fullmatch(r'-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?', value)
            or len(value.partition('.')[2].rstrip('0')) > digits
            or len(value.lstrip('-').replace('.', '').lstrip('0').rstrip('0')) > 15):
        raise _UnsupportedMetadata('unsupported_corporate_l2_number')
    exact = Fraction(str(value))
    if abs(exact) > _MAX_INTEGER or exact == 0 and value.startswith('-'):
        raise _UnsupportedMetadata('unsafe_corporate_l2_number')
    number = float(value)
    # The browser parses the token to a double and DecimalPipe renders that
    # double's shortest round-trip repr. Require the repr to equal the source
    # decimal exactly; binary-exactness is unnecessary and would refuse real
    # fractional rates such as 2.9.
    if Decimal(repr(number)) != Decimal(value):
        raise _UnsupportedMetadata('inexact_corporate_l2_browser_number')
    return number


def _l2_format(number, *, percentage=False):
    if number is None:
        return ''
    return _number(str(number), 4 if percentage else 3, locale='id-ID', trim=not percentage)


def _l2_reduce(values):
    # fa uses reduce WITHOUT an initial value. A singleton null stays null;
    # null participates as numeric zero only when a '+' operation occurs.
    if not values:
        return 0.0
    total = values[0]
    for value in values[1:]:
        left, right = 0.0 if total is None else total, 0.0 if value is None else value
        exact = Fraction.from_float(left) + Fraction.from_float(right)
        total = left + right
        if abs(exact) > _MAX_INTEGER or Fraction.from_float(total) != exact:
            raise _UnsupportedMetadata('unsafe_corporate_l2_ordered_total')
        _l2_exact(_CorporateNumber(format(total, '.4f')), 4)
    return total


def project_l2_owner(form, *, tax_type, locale, country_labels, position_labels):
    """Whole approved A/B bodies, not a native/callback/catalog authority.

    Caller independently owns the submitted restoration, loaded providers,
    exact offline structure and same-attempt original reference descriptions.
    Position's unique-Code labels implement w1's first find, not a second
    SubPosition lookup. Keep old v1 quarantine separate and unchanged.
    """
    if (tax_type != 'ICT_RCIT' or locale != 'id-ID' or not isinstance(form, dict)
            or not isinstance(country_labels, dict) or not isinstance(position_labels, dict)):
        raise _UnsupportedMetadata('unsupported_corporate_l2_owner_structure')
    if (set(form) - {L2_SHAREHOLDERS, L2_AFFILIATES, *L2_TOTALS}
            or not {L2_SHAREHOLDERS, *L2_TOTALS} <= set(form)):
        raise _UnsupportedMetadata('unsupported_corporate_l2_owner_shape')
    columns = (
        ('Name', 'Address', 'CountryCode', 'TIN', 'Position', 'PaidInCapital',
         'PaidInCapitalPercentage', 'Dividend'),
        ('Name', 'CountryCode', 'TIN', 'Investment', 'InvestmentPercentage', 'Debt',
         'DebtYear', 'DebtInterest', 'Receivable', 'ReceivableYear', 'ReceivableInterest'))
    sums, tables, provenance = {}, [], []
    for block, (body_key, headers, spans) in enumerate((
            (L2_SHAREHOLDERS, L2_SHAREHOLDER_HEADERS, L2_SHAREHOLDER_SPANS),
            (L2_AFFILIATES, L2_AFFILIATE_HEADERS, L2_AFFILIATE_SPANS))):
        value = form.get(body_key)
        body = [] if value is None else value
        if not isinstance(body, list) or len(body) > 10000:
            raise _UnsupportedMetadata('unsupported_corporate_l2_owner_body')
        rows, operands = [], {}
        # SubPosition is copied-but-unused row metadata (see the L2 quarantine
        # spec); the live portal omits it from shareholder rows, so it is
        # optional, never a required shape key.
        required = set(columns[block])
        optional = {'SubPosition', 'ValidFrom', 'ValidTo'} if block == 0 else {'IsEditable'}
        money = ({'PaidInCapital', 'Dividend'} if block == 0 else
                 {'Investment', 'Debt', 'DebtInterest', 'Receivable', 'ReceivableInterest'})
        percentages = {'PaidInCapitalPercentage', 'InvestmentPercentage'}
        for index, source in enumerate(body):
            if (not isinstance(source, dict) or not required <= set(source)
                    or set(source) - required - optional):
                raise _UnsupportedMetadata('unsupported_corporate_l2_owner_row')
            row = [str(index + 1)]
            for column, key in enumerate(columns[block], 1):
                value = source[key]
                entry = _evidence(value, [L2_ROOT, body_key, index, key])
                entry['destination'] = {'table': 'L2/' + ('shareholder' if block == 0 else 'affiliate'),
                                        'row': index, 'column': column}
                if key in money or key in percentages:
                    number = _l2_exact(value, 4 if key in percentages else 3)
                    if block == 0 and number is None:
                        number = 0.0
                    operands.setdefault(key, []).append(number)
                    text = _l2_format(number, percentage=key in percentages)
                    entry['rule'] = ('nullish-zero/' if block == 0 and value is None else '') + (
                        'offline-Number4-1.4-4-id' if key in percentages else 'offline-Number-1.0-3-id')
                elif key in ('CountryCode', 'Position'):
                    labels = country_labels if key == 'CountryCode' else position_labels
                    if value is None or value == '':
                        text = ''
                    elif type(value) is str and value in labels and type(labels[value]) is str:
                        text = labels[value]
                    else:
                        raise _UnsupportedMetadata('unbound_corporate_l2_reference_description')
                    entry['rule'] = 'country-active-description' if key == 'CountryCode' else 'position-first-description'
                elif key in ('DebtYear', 'ReceivableYear') and type(value) is _CorporateNumber:
                    text = str(int(_l2_exact(value, 0)))
                    entry['rule'] = 'integral-year/JS-String'
                elif value is None or type(value) is str:
                    text = '' if value is None else value
                    entry['rule'] = 'literal-string/nullish-blank'
                else:
                    raise _UnsupportedMetadata('unsupported_corporate_l2_literal_type')
                row.append(text)
                provenance.append(entry)
            for key in source:
                if key in columns[block]:
                    continue
                value = source[key]
                if key == 'IsEditable' and type(value) is bool:
                    entry = {'path': [L2_ROOT, body_key, index, key], 'type': 'boolean', 'value': value}
                else:
                    if value is not None and type(value) is not str:
                        raise _UnsupportedMetadata('unsupported_corporate_l2_row_metadata')
                    entry = _evidence(value, [L2_ROOT, body_key, index, key])
                entry['rule'] = 'unused-subposition' if key == 'SubPosition' else 'unused-row-metadata'
                provenance.append(entry)
            rows.append(row)
        for key in (('PaidInCapital', 'PaidInCapitalPercentage', 'Dividend') if block == 0 else ('Debt', 'Receivable')):
            sums[key] = _l2_reduce(operands.get(key, []))
        if block == 0:
            # The getter string -> parseFloat -> toFixed(4) path has no grouping.
            percentage = format(sums['PaidInCapitalPercentage'], '.4f').replace('.', ',')
            footer = ['', 'JUMLAH', _l2_format(sums['PaidInCapital']), percentage, _l2_format(sums['Dividend'])]
        else:
            footer = ['', 'JUMLAH', _l2_format(sums['Debt']), '', _l2_format(sums['Receivable']), '']
        tables.append({'name': 'L2/' + ('shareholder' if block == 0 else 'affiliate'),
            'headers': list(headers), 'rows': rows + [footer], 'footer': [footer],
            'footer_spans': deepcopy(spans), 'body_row_count': len(body),
            'source_total': len(body), 'complete': True})
    for key in L2_TOTALS:
        _l2_exact(form[key], 4 if key == 'TotalPaidInCapitalPercentage' else 3)
        provenance.append({**_evidence(form[key], [L2_ROOT, key]),
            'rule': ('saved-percentage-alias-not-rendered' if key == 'TotalPaidInCapitalPercentage'
                     else 'overwritten-saved-total/ordered-model-getter')})
    return {'tables': tables, 'provenance': provenance}


def project_l2(form, *, tax_type, locale):
    """Bounded empty-owner projection, not permission for native L2 capture.

    Populated A needs owned FullPosition/country descriptions. Populated B
    needs owned country descriptions and the Number/Number4 renderer contract.
    Never replace either body with a partial affiliate-only worksheet. Even the
    empty subset retains the entire audit dump and whole-record DOM fallback.
    """
    if tax_type != 'ICT_RCIT' or locale != 'id-ID' or not isinstance(form, dict):
        raise _UnsupportedMetadata('unsupported_corporate_l2_structure')
    if set(form) != {L2_SHAREHOLDERS, L2_AFFILIATES, *L2_TOTALS}:
        raise _UnsupportedMetadata('unsupported_corporate_l2_source_shape')
    for key in (L2_SHAREHOLDERS, L2_AFFILIATES):
        value = form[key]
        if value is not None and not isinstance(value, list):
            raise _UnsupportedMetadata('unsupported_corporate_l2_body')
    if form[L2_SHAREHOLDERS]:
        raise _UnsupportedMetadata('unprojected_corporate_l2_shareholder_body')
    if form[L2_AFFILIATES]:
        raise _UnsupportedMetadata('unverified_corporate_l2_affiliate_rendering')
    provenance = []
    for field in L2_TOTALS:
        value = form[field]
        # A closed zero grammar avoids JS fractional sums, signed zero, decimal
        # exceptions, null coercion and unsafe precision. Preserve source lexemes.
        if type(value) is not _CorporateNumber or not re.fullmatch(r'0(?:\.0+)?', value):
            raise _UnsupportedMetadata('unsupported_corporate_l2_empty_total')
        provenance.append({**_evidence(value, [L2_ROOT, field]),
            'rule': 'validated-empty-owner-zero'})
    # These two empty reductions are numeric zero in fa/setGridValue. Number,
    # not Number2, renders the Rupiah footer: no fabricated two-decimal format.
    footer = [['', 'JUMLAH', '0', '', '0', '']]
    tables = [{'name': 'L2/affiliate', 'headers': list(L2_AFFILIATE_HEADERS),
               'rows': deepcopy(footer), 'footer': footer,
               'footer_spans': deepcopy(L2_AFFILIATE_SPANS),
               'body_row_count': 0, 'source_total': 0, 'complete': True}]
    return {'tables': tables, 'provenance': provenance}


def _apply_l2_owner(binding, section, observed_forms, *, root, payload, record, event, reference_packets):
    proof = binding['projection']
    if (set(proof) != {'kind', 'builds', 'route', 'locale', 'timezone', 'tables', 'references'}
            or not isinstance(proof['builds'], dict)
            or set(proof['builds']) != {CIT_SOURCE, MAIN_SOURCE, VENDOR_SOURCE}
            or proof['builds'] != L2_BUILD_DIGESTS
            or any(type(value) is not str or not re.fullmatch(r'[0-9a-f]{64}', value)
                   for value in (*proof['builds'].values(), *L2_BUILD_DIGESTS.values()))
            or proof['route'] != event['frame_url'] or proof['locale'] != 'id-ID'
            or proof['timezone'] != 'Asia/Jakarta' or event.get('component_lifetime') is None
            or binding.get('paths') != [[L2_ROOT]] or binding.get('grids')
            or binding.get('responses') or binding.get('dependencies')):
        raise _UnsupportedMetadata('unverified_corporate_l2_owner_binding')
    proof = binding['projection']
    fields = record.get('source_fields', {})
    route = ORIGIN + '/returnsheets/id-ID/corporate-income-tax-return/' + '/'.join(
        str(value) for value in (fields.get('TaxpayerAggregateIdentifier'), record['record_id'],
                                fields.get('TaxTypeCode'), fields.get('AggregateIdentifier'))) + '?view=true'
    literal = record.get('meta', {}).get('Model SPT')
    model = ('NORMAL' if literal == 'Normal' else 'AMENDMENT'
             if type(literal) is str and re.fullmatch(r'Amendment [0-9]{3}', literal) else None)
    if (proof['route'] != route or record.get('source_status') != 'SPT Dilaporkan'
            or payload.get('ReturnSheetStatusCode') != 'SUBMITTED' or model is None
            or payload.get('ReturnSheetModel') != model or fields.get('ReturnSheetModel') != literal
            or 'Induk' not in [f['name'] for f in observed_forms[:observed_forms.index(binding)]]
            or 'PreviousFormData' not in payload):
        raise _UnsupportedMetadata('unverified_corporate_l2_owner_lifecycle')
    previous = payload['PreviousFormData']
    if previous is not None:
        if type(previous) is not str:
            raise _UnsupportedMetadata('unverified_corporate_l2_owner_previous')
        previous = _corporate_json(previous)
        if previous is not None and not isinstance(previous, dict):
            raise _UnsupportedMetadata('unverified_corporate_l2_owner_previous')
    tables = proof['tables']
    if not isinstance(tables, list) or len(tables) != 2:
        raise _UnsupportedMetadata('unverified_corporate_l2_owner_tables')
    for index, (headers, spans) in enumerate(((L2_SHAREHOLDER_HEADERS, L2_SHAREHOLDER_SPANS),
                                             (L2_AFFILIATE_HEADERS, L2_AFFILIATE_SPANS))):
        expected = {'component': L2_COMPONENTS[index], 'source_structure': {
            'form': 'L2', 'component': L2_COMPONENTS[index], 'groups': [L2_GROUPS[index]]},
            'headers': headers, 'footer_spans': spans}
        if (tables[index] != expected
                or any(type(span) is not int for line in tables[index]['footer_spans'] for span in line)):
            raise _UnsupportedMetadata('unverified_corporate_l2_owner_tables')
    references = proof['references']
    if not isinstance(references, list):
        raise _UnsupportedMetadata('unverified_corporate_l2_owner_references')
    catalogs, sources, seen = {}, {}, set()
    for ref in references:
        if (not isinstance(ref, dict) or set(ref) != {'endpoint', 'method', 'sequences'}
                or type(ref['endpoint']) is not str or ref['method'] != 'GET' or ref['endpoint'] in seen):
            raise _UnsupportedMetadata('unverified_corporate_l2_owner_references')
        kinds = CORPORATE_REFERENCE_REQUESTS.get(ref['endpoint'])
        if not kinds or set(kinds) - {'COUNTRY_CODE', 'RELATED_PERSON_TYPE'}:
            raise _UnsupportedMetadata('unverified_corporate_l2_owner_references')
        seen.add(ref['endpoint'])
        sequences = ref['sequences']
        if (not isinstance(sequences, list) or not sequences
                or any(type(n) is not int or n <= 0 for n in sequences)
                or len(set(sequences)) != len(sequences)):
            raise JsonSafetyError('Corporate L2 reference sequence is invalid or repeated')
        actual = {n for n, packet in reference_packets.items() if packet['event']['url'] == ref['endpoint']}
        if set(sequences) != actual or any(not reference_packets[n]['successful'] for n in actual):
            raise _UnsupportedMetadata('missing_or_failed_corporate_l2_catalog')
        source = reference_packets[min(sequences)]
        for kind in kinds:
            catalog = _project_corporate_catalog(source['payload'], kind=kind, requested_types=kinds,
                clock_interval=source['event'].get('clock_interval'))
            if kind == 'RELATED_PERSON_TYPE' and catalog['requires_vendor']:
                # w1 uses first Code==Position, NOT getActiveReferenceDataValue.
                raise _UnsupportedMetadata('unsupported_corporate_l2_position_versions')
            if kind in catalogs and catalog['provenance'] != catalogs[kind]['provenance']:
                raise JsonSafetyError('Corporate L2 catalog snapshots changed')
            if kind not in sources or source['event']['sequence'] < sources[kind]['sequence']:
                catalogs[kind], sources[kind] = catalog, source['event']
    result = project_l2_owner(root.get(L2_ROOT), tax_type=fields.get('TaxTypeCode'), locale=proof['locale'],
        country_labels=catalogs.get('COUNTRY_CODE', {}).get('lookups', {}),
        position_labels=catalogs.get('RELATED_PERSON_TYPE', {}).get('lookups', {}))
    for index, table in enumerate(result['tables']):
        table['source_structure'] = deepcopy(tables[index]['source_structure'])
    for entry in tuple(result['provenance']):
        entry.update(response_sequence=event['sequence'], container=['Payload', 'CurrentFormData'])
        kind = {'country-active-description': 'COUNTRY_CODE',
                'position-first-description': 'RELATED_PERSON_TYPE'}.get(entry['rule'])
        if kind in catalogs and entry['value'] in catalogs[kind]['selected']:
            result['provenance'].append({**deepcopy(catalogs[kind]['selected'][entry['value']]),
                'response_sequence': sources[kind]['sequence'], 'container': ['Payload'],
                'destination': deepcopy(entry['destination'])})
    for kind, catalog in catalogs.items():
        result['provenance'].extend({**entry, 'response_sequence': sources[kind]['sequence'],
            'container': ['Payload'], 'destination': {'form': 'L2', 'reference': kind}}
            for entry in catalog['provenance'])
    # Real header controls, not a dummy nonempty-fields dump exemption. The
    # approved workbook has no slots for them: preserve their mapping shortfall.
    if (type(payload.get('TIN')) is not str or type(payload.get('PeriodYear')) is not _CorporateNumber
            or not re.fullmatch(r'[0-9]{4}', payload['PeriodYear'])):
        raise _UnsupportedMetadata('unsupported_corporate_l2_header_controls')
    section['fields'] = []
    for key, field, caption in (('PeriodYear', 'TaxPeriodYear', 'Tahun Pajak/Bagian Tahun Pajak'),
                                ('TIN', 'CollectorTin', 'Nomor Identitas WP')):
        section['fields'].append({'group': 'HEADER', 'field': field, 'label': caption, 'value': str(payload[key])})
        result['provenance'].append({**_evidence(payload[key], [key]), 'container': ['Payload'],
            'response_sequence': event['sequence'], 'destination': {'form': 'L2', 'field': field},
            'rule': 'outer-primary-header-control'})
    section['tables'] = result['tables']
    section['projection_complete'] = False
    section['projection_reason'] = 'unmapped_l2_header_controls'
    return {'form': 'L2', 'kind': proof['kind'], 'builds': dict(proof['builds']),
            'route': proof['route'], 'values': result['provenance']}


def _apply_l2(binding, section, observed_forms, *, root, payload, record, event, reference_packets=None):
    proof = binding['projection']
    if isinstance(proof, dict) and proof.get('kind') == 'corporate-l2-owner-v2':
        return _apply_l2_owner(binding, section, observed_forms, root=root, payload=payload,
            record=record, event=event, reference_packets=reference_packets or {})
    builds = proof.get('builds') if isinstance(proof, dict) else None
    approved = BUILD_DIGESTS.get(CIT_SOURCE)
    if (not isinstance(proof, dict) or set(proof) != {'kind', 'builds', 'route'}
            or proof['kind'] != 'corporate-l2-v1'
            or not isinstance(builds, dict) or set(builds) != {CIT_SOURCE}
            or type(builds[CIT_SOURCE]) is not str or len(builds[CIT_SOURCE]) != 64
            or any(character not in '0123456789abcdef' for character in builds[CIT_SOURCE])
            or type(approved) is not str or not re.fullmatch(r'[0-9a-f]{64}', approved)
            or builds[CIT_SOURCE] != approved
            or proof['route'] != event['frame_url']
            or binding.get('paths') != [[L2_ROOT]]
            or binding.get('grids') or binding.get('responses') or binding.get('dependencies')):
        raise _UnsupportedMetadata('unverified_corporate_l2_binding')
    literal = record.get('meta', {}).get('Model SPT')
    model = ('NORMAL' if literal == 'Normal' else 'AMENDMENT'
             if isinstance(literal, str) and re.fullmatch(r'Amendment [0-9]{3}', literal) else None)
    if (record.get('source_status') != 'SPT Dilaporkan'
            or payload.get('ReturnSheetStatusCode') != 'SUBMITTED' or model is None
            or payload.get('ReturnSheetModel') != model):
        raise _UnsupportedMetadata('unverified_corporate_l2_submitted_lifecycle')
    fields = record.get('source_fields', {})
    result = project_l2(root.get(L2_ROOT), tax_type=fields.get('TaxTypeCode'), locale='id-ID')
    # Keep every original leaf, including empty/null bodies and all totals.
    # No fields marker may let this partial projection bypass the dump gate.
    section['tables'] = [*result['tables'], *section.get('tables', [])]
    section['fields'] = []
    section['projection_complete'] = False
    section['projection_reason'] = L2_UNPROJECTED_REASON
    for entry in result['provenance']:
        entry.update(response_sequence=event['sequence'], container=['Payload', 'CurrentFormData'])
    return {'form': 'L2', 'kind': proof['kind'], 'builds': dict(proof['builds']),
            'route': proof['route'], 'values': result['provenance']}


def l9_grid_structure(index):
    """Reviewed owner/group coordinates, not a source-order inference."""
    if type(index) is not int or not 0 <= index < 12:
        raise _UnsupportedMetadata('unsupported_corporate_l9_grid_role')
    if 5 <= index < 7:
        return {'form': 'L9', 'component': 'rshshr-citr-l9-form-grid2',
                'groups': ['BANGUNAN', 'PERMANEN' if index == 5 else 'TIDAK PERMANEN']}
    position = index if index < 5 else index - 7
    inner = 'KELOMPOK ' + str(position + 1) if position < 4 else 'KELOMPOK LAINNYA'
    return {'form': 'L9', 'component': 'rshshr-citr-l9-form-grid' + ('1' if index < 5 else '3'),
            'groups': ['HARTA BERWUJUD' if index < 5 else 'HARTA TIDAK BERWUJUD', inner]}


def _l9_grid_number(value):
    # The pinned numeric body uses DecimalPipe 1.0-0, not edit validators.
    # Bound decimal coefficients and require the parsed browser number's short
    # decimal to be identical before applying the reviewed half-up renderer.
    if type(value) is not _CorporateNumber:
        raise _UnsupportedMetadata('unsupported_corporate_l9_grid_number_type')
    try:
        number = _decimal(value)
        if (number < 0 or abs(number) > _MAX_INTEGER or len(number.as_tuple().digits) > 15
                or number.is_signed() and number.is_zero()
                or number != _decimal(str(float(number)))):
            raise _UnsupportedMetadata('unsupported_corporate_l9_grid_number_precision')
        text = _number(value, 0, locale='id-ID')
        if len(text.replace('.', '')) > 15:
            raise _UnsupportedMetadata('unsupported_corporate_l9_grid_number_precision')
        return text
    except (DecimalException, ValueError, OverflowError, _UnsupportedMetadata):
        raise _UnsupportedMetadata('unsupported_corporate_l9_grid_number_precision') from None


def _l9_month(value):
    if value is None:
        return ''
    if type(value) is not str:
        raise _UnsupportedMetadata('unsupported_corporate_l9_month')
    if not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}(?:T00:00:00(?:[.]000)?(?:Z|[+]07:00)?)?', value):
        raise _UnsupportedMetadata('unsupported_corporate_l9_month')
    try:
        date = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if date.year == 1 and date.month == date.day == 1:
            return ''  # Exact normalized sentinel, not an arbitrary substring.
        if not 1970 <= date.year <= 2100:
            raise ValueError
        return f'{date.month:02d}-{date.year:04d}'
    except ValueError:
        raise _UnsupportedMetadata('unsupported_corporate_l9_month') from None


def project_l9_grid(*, index, pages, total, headers, footer_spans, tax_type,
                    locale, timezone_name, labels):
    """Project one original, complete grid; callers own catalogs and lifecycle."""
    structure = l9_grid_structure(index)
    if (headers != L9_GRID_HEADERS or footer_spans != L9_GRID_SPANS or tax_type != 'ICT_RCIT'
            or locale != 'id-ID' or timezone_name != 'Asia/Jakarta' or not isinstance(labels, dict)):
        raise _UnsupportedMetadata('unverified_corporate_l9_grid_structure')
    if not isinstance(pages, list) or not 1 <= len(pages) <= 1000:
        raise _UnsupportedMetadata('unsupported_corporate_l9_grid_pages')
    rows, provenance, cursor, source_total = [], [], 0, None
    group = L9_GRIDS[index][0].rsplit('/', 1)[1]
    label_columns = {1: 'TANGIBLE_ASSET' if index < 5 else
                        'GROUP_OF_BUILDINGS' if index < 7 else 'INTANGIBLE_ASSET',
                     5: 'COMMERCIAL_METHOD', 6: 'FISCAL_METHOD'}
    required = set(L9_GRID_COLUMNS)
    for page_index, page in enumerate(pages):
        if page_index and cursor == source_total:
            raise _UnsupportedMetadata('unsupported_corporate_l9_repeated_terminal_page')
        if (not isinstance(page, dict) or set(page) != {'offset', 'rows', 'payload'}
                or type(page['offset']) is not int or page['offset'] != cursor
                or type(page['rows']) is not int or page['rows'] != 10):
            raise _UnsupportedMetadata('unsupported_corporate_l9_grid_pages')
        payload = page['payload']
        if (not isinstance(payload, dict) or set(payload) != {'Data', 'TotalRecords', 'Index'}
                or payload['Index'] is not None):
            raise _UnsupportedMetadata('unsupported_corporate_l9_grid_payload')
        count = _corporate_integer(payload['TotalRecords'])
        if source_total is not None and source_total != count:
            raise JsonSafetyError('Corporate L9 page totals changed')
        source_total = count
        data = [] if payload['Data'] is None and count == 0 else payload['Data']
        if (not isinstance(data, list) or len(data) > page['rows'] or count > 10000
                or cursor + len(data) > count or (not data and count != 0)):
            raise _UnsupportedMetadata('unsupported_corporate_l9_grid_rows')
        for name in ('TotalRecords', 'Index'):
            provenance.append({**_evidence(payload[name], [name]), 'source': 'grid',
                'page_index': page_index, 'rule': 'retained-original-grid-envelope',
                'destination': {'table': L9_GRIDS[index][0], 'control': name}})
        if not data:
            provenance.append({'path': ['Data'], 'type': 'null' if payload['Data'] is None else 'array',
                'value': None if payload['Data'] is None else '[]', 'source': 'grid',
                'page_index': page_index, 'rule': 'retained-original-empty-grid-container',
                'destination': {'table': L9_GRIDS[index][0], 'control': 'Data'}})
        for local_index, row in enumerate(data):
            if not isinstance(row, dict) or set(row) not in (required, required | L9_ROW_METADATA):
                raise _UnsupportedMetadata('unsupported_corporate_l9_grid_row_shape')
            if set(row) != required:
                if (row['GroupType'] != group or type(row['GroupType']) is not str
                        or row['CodeOfAsset'] is not None or row['Action'] is not None
                        or type(row['RecordId']) is not str or not row['RecordId']
                        or type(row['Index']) is not _CorporateNumber
                        or not re.fullmatch(r'0|[1-9][0-9]*', row['Index'])
                        or len(row['Index']) > 15):
                    raise _UnsupportedMetadata('unsupported_corporate_l9_grid_metadata')
                for key in row:
                    if key in L9_ROW_METADATA:
                        provenance.append({**_evidence(row[key], ['Data', local_index, key]),
                            'source': 'grid', 'page_index': page_index, 'source_row': cursor + local_index,
                            'rule': 'retained-original-grid-metadata',
                            'destination': {'table': L9_GRIDS[index][0], 'control': key}})
            rendered = []
            for column, key in enumerate(L9_GRID_COLUMNS):
                value = row[key]
                entry = {**_evidence(value, ['Data', local_index, key]), 'source': 'grid',
                    'page_index': page_index, 'source_row': cursor + local_index,
                    'destination': {'table': L9_GRIDS[index][0], 'row': cursor + local_index, 'column': column}}
                if column in label_columns:
                    kind = label_columns[column]
                    if (type(value) is not str or not value or not isinstance(labels.get(kind), dict)
                            or type(labels[kind].get(value)) is not str or not labels[kind][value].strip()):
                        raise _UnsupportedMetadata('missing_corporate_l9_grid_reference_label')
                    text, entry['rule'], entry['reference'] = labels[kind][value], 'bound-reference-label', kind
                elif column in (3, 4, 7):
                    text, entry['rule'] = _l9_grid_number(value), 'angular-decimal-1.0-0-id'
                elif column == 2:
                    text, entry['rule'] = _l9_month(value), 'dayjs-MM-YYYY-jakarta'
                else:
                    if value is not None and type(value) is not str:
                        raise _UnsupportedMetadata('unsupported_corporate_l9_grid_text')
                    text, entry['rule'] = '' if value is None else value, 'literal-grid-text'
                rendered.append(text)
                provenance.append(entry)
            rows.append(rendered)
        cursor += len(data)
        if cursor < count and len(data) != page['rows']:
            raise _UnsupportedMetadata('incomplete_corporate_l9_grid_pages')
    if cursor != source_total:
        raise _UnsupportedMetadata('incomplete_corporate_l9_grid_pages')
    footer_text = _l9_grid_number(total)
    if _decimal(total) != _decimal(total).to_integral_value():
        raise _UnsupportedMetadata('unsupported_corporate_l9_stored_footer')
    # Initial submitted read renders the stored customFooter. Do not sum body
    # display cells, and never acquire edit/refresh footer endpoints here.
    footer = [[], ['TOTAL', footer_text, '']]
    provenance.append({**_evidence(total, [L9_ROOT, L9_TABLE_TOTALS[index]]), 'source': 'current',
        'rule': 'initial-nonmigrated-stored-custom-footer/angular-decimal-1.0-0-id',
        'destination': {'table': L9_GRIDS[index][0], 'footer': 1, 'column': 1}})
    return {'table': {'name': L9_GRIDS[index][0], 'headers': list(headers), 'rows': rows + footer,
        'footer': footer, 'footer_spans': deepcopy(footer_spans), 'body_row_count': cursor,
        'source_total': source_total, 'complete': True, 'source_structure': structure},
        'provenance': provenance}


def project_l9(form, *, tax_type, locale, migrated):
    """Six recap controls only, never permission to discard twelve detail grids.

    Non-migrated setFormData calls all twelve patchFooterGrid callbacks. Require
    that the captured values already equal that initialization's fixed point.
    Migrated initialization patches only the tangible difference, not both stored
    differences, so that unproved branch stays unsupported. Integral operands
    avoid Math.round/fraction/IEEE-754 guesses; null is not silently zero-filled.
    """
    if (tax_type != 'ICT_RCIT' or locale != 'id-ID' or migrated is not False
            or not isinstance(form, dict)):
        raise _UnsupportedMetadata('unsupported_corporate_l9_structure')
    if set(form) != L9_KEYS:
        raise _UnsupportedMetadata('unsupported_corporate_l9_source_shape')
    amounts = {}
    for name in (*L9_TABLE_TOTALS, *(field for field, _ in L9_FIELDS)):
        value = form[name]
        if type(value) is not _CorporateNumber:
            raise _UnsupportedMetadata('unsupported_corporate_l9_amount_type')
        try:
            number = _decimal(value)
        except (DecimalException, _UnsupportedMetadata):
            raise _UnsupportedMetadata('unsupported_corporate_l9_amount_precision') from None
        # Signed-zero display has not been proved; never canonicalize it to 0.
        if (abs(number) > _MAX_INTEGER or number != number.to_integral_value()
                or number.is_zero() and number.is_signed()):
            raise _UnsupportedMetadata('unsupported_corporate_l9_amount_precision')
        if name not in L9_SIGNED and number < 0:
            raise _UnsupportedMetadata('unsupported_corporate_l9_negative_amount')
        amounts[name] = int(number)
    # Nonnegative summands and a reconciled <=15-digit total also bound every
    # ordered partial sum. All JS additions/subtractions are exact in this subset.
    if amounts['TotalFiscalDepreciationTangible'] != sum(amounts[name] for name in L9_TABLE_TOTALS[:7]):
        raise _UnsupportedMetadata('unreconciled_corporate_l9_fiscal_depreciation')
    if amounts['TotalFiscalAmortization'] != sum(amounts[name] for name in L9_TABLE_TOTALS[7:]):
        raise _UnsupportedMetadata('unreconciled_corporate_l9_fiscal_amortization')
    if amounts['DiferencesDepreciationTangible'] != (
            amounts['TotalFiscalDepreciationTangible'] - amounts['TotalCommercialDepreciationTangible']):
        raise _UnsupportedMetadata('unreconciled_corporate_l9_depreciation_difference')
    if amounts['DiferencesAmortization'] != (
            amounts['TotalFiscalAmortization'] - amounts['TotalCommercialAmortization']):
        raise _UnsupportedMetadata('unreconciled_corporate_l9_amortization_difference')
    fields, provenance = [], []
    for name, caption in L9_FIELDS:
        fields.append({'group': '', 'field': name, 'label': caption,
                       'value': _number(form[name], 0, locale=locale)})
        entry = _evidence(form[name], [L9_ROOT, name])
        entry.update(rule='nonmigrated-reconciled-recap/angular-integer-id',
                     destination={'form': 'L9', 'field': name})
        provenance.append(entry)
    for name in L9_TABLE_TOTALS:
        entry = _evidence(form[name], [L9_ROOT, name])
        entry.update(rule='retained-original-recap-reduction-operand',
                     destination={'form': 'L9', 'control': name})
        provenance.append(entry)
    return {'fields': fields, 'provenance': provenance}


def _apply_l9(binding, section, observed_forms, *, root, payload, record, event,
              reference_packets, auxiliary_packets):
    proof = binding['projection']
    builds = proof.get('builds') if isinstance(proof, dict) else None
    grids = binding.get('grids')
    details = isinstance(proof, dict) and proof.get('kind') == 'corporate-l9-details-v1'
    approved = L9_DETAIL_BUILD_DIGESTS if details else {CIT_SOURCE: BUILD_DIGESTS.get(CIT_SOURCE)}
    urls = {CIT_SOURCE, MAIN_SOURCE, VENDOR_SOURCE} if details else {CIT_SOURCE}
    keys = {'kind', 'builds', 'route', 'locale'} | ({'timezone', 'tables', 'references'} if details else set())
    if (not isinstance(proof, dict) or set(proof) != keys
            or proof['kind'] not in ('corporate-l9-v1', 'corporate-l9-details-v1')
            or not isinstance(builds, dict) or set(builds) != urls or set(approved) != urls
            or any(type(value) is not str or not re.fullmatch(r'[a-f0-9]{64}', value)
                   for mapping in (approved, builds) for value in mapping.values())
            or builds != approved or proof['locale'] != 'id-ID'
            or proof['route'] != event['frame_url']
            or binding.get('paths') != [[L9_ROOT]]
            or binding.get('responses') or binding.get('dependencies')
            or not isinstance(grids, list) or len(grids) != len(L9_GRIDS)
            or [(grid.get('name'), grid.get('endpoint')) if isinstance(grid, dict) else None
                for grid in grids] != list(L9_GRIDS)
            or any(not isinstance(grid.get('pages'), list) or not grid['pages'] for grid in grids)):
        raise _UnsupportedMetadata('unverified_corporate_l9_binding')
    fields = record.get('source_fields', {})
    route = ORIGIN + '/returnsheets/id-ID/corporate-income-tax-return/' + '/'.join(
        str(value) for value in (fields.get('TaxpayerAggregateIdentifier'), record['record_id'],
                                fields.get('TaxTypeCode'), fields.get('AggregateIdentifier'))) + '?view=true'
    literal = record.get('meta', {}).get('Model SPT')
    model = ('NORMAL' if literal == 'Normal' else 'AMENDMENT'
             if isinstance(literal, str) and re.fullmatch(r'Amendment [0-9]{3}', literal) else None)
    if (proof['route'] != route or event.get('component_lifetime') is None
            or record.get('source_status') != 'SPT Dilaporkan'
            or model is None
            or fields.get('ReturnSheetModel') != literal
            or fields.get('ReturnSheetTypeCode') != 'ICT_RCITR' or root.get('TaxType') != 'ICT_RCIT'
            or payload.get('ReturnSheetStatusCode') != 'SUBMITTED'
            or payload.get('ReturnSheetModel') != model
            or any(key not in payload or payload[key] is not None
                   for key in ('PreviousFormData', 'LastSubmittedFormData'))
            or 'Induk' not in [f['name'] for f in observed_forms[:observed_forms.index(binding)]]):
        raise _UnsupportedMetadata('unverified_corporate_l9_submitted_lifecycle')
    main = root.get('MainFormData')
    flag = main.get('IsMigrated') if isinstance(main, dict) else None
    flag_path = ['MainFormData', 'IsMigrated']
    if flag is None:
        # The source contract places the authoritative migrated flag on the
        # outer payload; an absent main copy is inert when the outer flag is
        # explicitly non-migrated.
        flag = payload.get('IsMigrated')
        flag_path = ['IsMigrated']
    if not (flag is False or (type(flag) is _CorporateNumber and _decimal(flag) == 0)):
        raise _UnsupportedMetadata('unsupported_corporate_l9_migrated_flag')
    result = project_l9(root.get(L9_ROOT), tax_type=fields.get('TaxTypeCode'),
                        locale=proof['locale'], migrated=False)
    result['provenance'].append({'path': flag_path,
        'type': 'boolean' if flag is False else 'number', 'value': False if flag is False else str(flag),
        'rule': 'retained-original-nonmigrated-initialization',
        'destination': {'form': 'L9', 'control': 'IsMigrated'}})
    section['fields'] = result['fields']
    # Preserve all original root/grid leaves. Six fields cannot launder twelve
    # unprojected inventories: the capture gate still requires whole-record DOM.
    section['unprojected_grids'] = [name for name, _ in L9_GRIDS]
    section['projection_complete'] = False
    section['projection_reason'] = L9_UNPROJECTED_REASON
    for entry in result['provenance']:
        entry.update(response_sequence=event['sequence'], container=['Payload', 'CurrentFormData'])
    if details:
        _apply_l9_details(binding, section, result['provenance'], root=root, record=record, event=event,
            reference_packets=reference_packets, auxiliary_packets=auxiliary_packets)
    return {'form': 'L9', 'kind': proof['kind'], 'builds': dict(proof['builds']),
            'route': proof['route'], 'values': result['provenance']}


def _apply_l9_details(binding, section, evidence, *, root, record, event,
                       reference_packets, auxiliary_packets):
    """Consume only shared-admitted original catalogs and exact original grids."""
    proof, tables, references = binding['projection'], binding['projection']['tables'], binding['projection']['references']
    if (proof['timezone'] != 'Asia/Jakarta' or event.get('clock_interval') is None
            or not isinstance(tables, list) or len(tables) != 12
            or not isinstance(references, list) or len(references) != len(L9_REFERENCE_KINDS)):
        raise _UnsupportedMetadata('unverified_corporate_l9_details_binding')
    for index, table in enumerate(tables):
        expected = l9_grid_structure(index)
        alternatives = [expected]
        if index in (4, 11):
            alternatives.append({**expected, 'groups': [expected['groups'][0], 'LAINNYA']})
        if (not isinstance(table, dict)
                or set(table) != {'component', 'source_structure', 'headers', 'footer_spans'}
                or table['component'] != expected['component'] or table['source_structure'] not in alternatives
                or table['headers'] != L9_GRID_HEADERS or table['footer_spans'] != L9_GRID_SPANS):
            raise _UnsupportedMetadata('unverified_corporate_l9_details_table')
    catalogs, sources, labels = {}, {}, {}
    for reference in references:
        if (not isinstance(reference, dict) or set(reference) != {'endpoint', 'method', 'sequences'}
                or reference['method'] != 'GET' or not isinstance(reference['sequences'], list)
                or not reference['sequences']):
            raise _UnsupportedMetadata('unverified_corporate_l9_reference_binding')
        # The separately owned passive registry is the only transport authority.
        # This consumer neither synthesizes an endpoint nor adds registrations.
        requested = CORPORATE_REFERENCE_REQUESTS.get(reference['endpoint'])
        if (not isinstance(requested, tuple) or len(requested) != 1
                or requested[0] not in L9_REFERENCE_KINDS or requested[0] in catalogs):
            raise _UnsupportedMetadata('unverified_corporate_l9_reference_binding')
        kind, sequences = requested[0], reference['sequences']
        if (any(type(number) is not int or number <= 0 for number in sequences)
                or len(set(sequences)) != len(sequences)):
            raise JsonSafetyError('Corporate L9 reference sequences are invalid or repeated')
        actual = {number for number, packet in reference_packets.items()
                  if packet['event']['url'] == reference['endpoint']}
        if set(sequences) != actual or any(not reference_packets[number]['successful'] for number in actual):
            raise _UnsupportedMetadata('missing_or_failed_corporate_l9_catalog')
        source = reference_packets[min(sequences)]
        if source['event'].get('clock_interval') != event['clock_interval']:
            raise _UnsupportedMetadata('unverified_corporate_l9_reference_clock')
        catalogs[kind] = _project_corporate_catalog(source['payload'], kind=kind,
            requested_types=requested, clock_interval=source['event']['clock_interval'])
        sources[kind], labels[kind] = source['event'], catalogs[kind]['lookups']
    if set(catalogs) != set(L9_REFERENCE_KINDS):
        raise _UnsupportedMetadata('missing_corporate_l9_catalog_types')
    requests, pages, page_sources, expected_keys = [], [], [], set()
    for declaration in binding['grids']:
        group = declaration['name'].rsplit('/', 1)[1]
        grid_pages, grid_sources = [], []
        for page in declaration['pages']:
            request = page.get('request_json') if isinstance(page, dict) else None
            if (not isinstance(request, dict) or set(request) != {'ReturnSheetRecordId', 'GroupType',
                    'First', 'Rows', 'SortField', 'SortOrder', 'Filters', 'LanguageId'}
                    or request['ReturnSheetRecordId'] != record['record_id'] or request['GroupType'] != group
                    or type(request['First']) is not int or request['First'] < 0
                    or type(request['Rows']) is not int or request['Rows'] != 10
                    or request['SortField'] != '' or type(request['SortOrder']) is not int or request['SortOrder'] != 1
                    or request['Filters'] != [] or request['LanguageId'] != 'id-ID'
                    or page.get('offset') != request['First']):
                raise _UnsupportedMetadata('unsupported_corporate_l9_details_request')
            key = (declaration['endpoint'], _corporate_request_key(request))
            if key in expected_keys:
                raise _UnsupportedMetadata('repeated_corporate_l9_details_request')
            expected_keys.add(key)
            packet = auxiliary_packets.get(key)
            if packet is None:
                raise _UnsupportedMetadata('missing_corporate_l9_original_grid')
            grid_pages.append({'offset': request['First'], 'rows': request['Rows'], 'payload': packet['payload']})
            grid_sources.append(packet['event'])
        requests.append(declaration['name'])
        pages.append(grid_pages)
        page_sources.append(grid_sources)
    if expected_keys != {key for key in auxiliary_packets if key[0] in {url for _, url in L9_GRIDS}}:
        raise _UnsupportedMetadata('unbound_corporate_l9_original_grid')
    original = deepcopy(section['tables'])
    if len(original) != 13 or [t['name'] for t in original[1:]] != requests:
        raise _UnsupportedMetadata('unverified_corporate_l9_original_inventory')
    semantic, unresolved, reasons = [], [], {}
    for index, (name, _) in enumerate(L9_GRIDS):
        try:
            result = project_l9_grid(index=index, pages=pages[index], total=root[L9_ROOT][L9_TABLE_TOTALS[index]],
                headers=tables[index]['headers'], footer_spans=tables[index]['footer_spans'],
                tax_type=record['source_fields'].get('TaxTypeCode'), locale=proof['locale'],
                timezone_name=proof['timezone'], labels=labels)
        except _UnsupportedMetadata as error:
            # Each refused grid remains visible to the whole-record native gate;
            # the other eleven may be projected but cannot launder its source.
            unresolved.append(name)
            reasons[name] = str(error)
            semantic.append(deepcopy(original[index + 1]))
            continue
        result['table']['source_structure'] = deepcopy(tables[index]['source_structure'])
        semantic.append(result['table'])
        for entry in result['provenance']:
            source = page_sources[index][entry['page_index']] if entry['source'] == 'grid' else event
            entry.update(response_sequence=source['sequence'], response_sha256=source['sha256'],
                attempt=source['attempt'], container=['Payload'] if entry['source'] == 'grid'
                else ['Payload', 'CurrentFormData'])
            evidence.append(entry)
            kind = entry.get('reference')
            if kind is not None:
                selected = deepcopy(catalogs[kind]['selected'][entry['value']])
                selected.update(response_sequence=sources[kind]['sequence'],
                    response_sha256=sources[kind]['sha256'], attempt=sources[kind]['attempt'],
                    container=['Payload'], destination=deepcopy(entry['destination']))
                evidence.append(selected)
    for kind, catalog in catalogs.items():
        evidence.extend({**deepcopy(entry), 'response_sequence': sources[kind]['sequence'],
            'response_sha256': sources[kind]['sha256'], 'attempt': sources[kind]['attempt'],
            'container': ['Payload'], 'destination': {'form': 'L9', 'reference': kind}}
            for entry in catalog['provenance'])
    # Custody is an explicit independent section member, not a fake semantic
    # table or a dropped raw source. Generic template matching sees only grids.
    section.update(tables=semantic, custody_tables=original, unprojected_grids=unresolved,
        unprojected_grid_reasons=reasons, projection_complete=not unresolved)
    if not unresolved:
        section.pop('projection_reason', None)
    else:
        section['projection_reason'] = 'unprojected_l9_detail_grids'
def _l10b_pins(builds):
    urls = {CIT_SOURCE, MAIN_SOURCE, VENDOR_SOURCE}
    configured = load_build_pins()
    expected = {url: configured.get(url) for url in urls}
    return (isinstance(builds, dict) and set(builds) == urls
            and all(type(value) is str and re.fullmatch(r'[a-f0-9]{64}', value)
                    for mapping in (expected, builds) for value in mapping.values())
            and builds == expected)


def _apply_l10b(binding, section, observed_forms, *, root, payload, record, event):
    """Validate custody, not a worksheet projection; never remove the raw dump."""
    proof = binding['projection']
    fields = record.get('source_fields', {})
    route = ORIGIN + '/returnsheets/id-ID/corporate-income-tax-return/' + '/'.join(
        str(value) for value in (fields.get('TaxpayerAggregateIdentifier'), record['record_id'],
                                fields.get('TaxTypeCode'), fields.get('AggregateIdentifier'))) + '?view=true'
    literal = record.get('meta', {}).get('Model SPT')
    model = ('NORMAL' if literal == 'Normal' else 'AMENDMENT'
             if type(literal) is str and re.fullmatch(r'Amendment [0-9]{3}', literal) else None)
    if (not isinstance(proof, dict)
        or set(proof) - {'kind', 'builds', 'route', 'visibility_binding'}
        or 'visibility_binding' in proof and proof['visibility_binding'] != 'current-induk-enabled-v1'
        or proof.get('kind') != L10B_KIND or not _l10b_pins(proof['builds'])
            or proof['route'] != route or proof['route'] != event['frame_url']
            or binding.get('paths') != [[L10B_ROOT]]
            or any(binding.get(key) for key in ('grids', 'responses', 'dependencies', 'primary'))
            or event.get('component_lifetime') is None or event.get('corporate_l10b_lifetime') is None):
        raise _UnsupportedMetadata('unverified_corporate_l10b_nondisplay_custody')
    main, form = root.get('MainFormData'), root.get(L10B_ROOT)
    if (record.get('source_status') != 'SPT Dilaporkan'
            or model is None
            or fields.get('ReturnSheetModel') != literal
            or fields.get('TaxTypeCode') != 'ICT_RCIT' or fields.get('ReturnSheetTypeCode') != 'ICT_RCITR'
            or payload.get('ReturnSheetStatusCode') != 'SUBMITTED' or payload.get('ReturnSheetModel') != model
            or any(key not in payload or payload[key] is not None
                   for key in ('PreviousFormData', 'LastSubmittedFormData'))
            or 'Induk' not in [f['name'] for f in observed_forms[:observed_forms.index(binding)]]
            or not isinstance(main, dict)
            or 'IsTransactionWithRelated' not in payload
            or not _current_induk_visibility(payload, main, 'IsTransactionWithRelated', proof)
            or type(payload.get('TIN')) is not str or payload['TIN'] != event['scope'][0]
            or type(main.get('Tin')) is not str or main['Tin'] != payload['TIN']
            or type(payload.get('PeriodYear')) is not _CorporateNumber
            or type(main.get('TaxYear')) is not _CorporateNumber
            or payload['PeriodYear'] != main['TaxYear']
            or not re.fullmatch(r'(?:19|20)[0-9]{2}|2100', payload['PeriodYear'])
            or type(root.get('TaxType')) is not str or root['TaxType'] != 'ICT_RCIT'
            or type(root.get('TaxPeriodCode')) is not str
            or root['TaxPeriodCode'] != '0112' + payload['PeriodYear']
            or fields.get('TaxPeriodCode') != root['TaxPeriodCode']
            or type(root.get('ReturnSheetRecordIdentifier')) is not str
            or root['ReturnSheetRecordIdentifier'] != record['record_id']
            or type(root.get('ReturnSheetAggregateIdentifier')) is not str
            or root['ReturnSheetAggregateIdentifier'] != fields.get('AggregateIdentifier')):
        raise _UnsupportedMetadata('unverified_corporate_l10b_submitted_lifecycle')
    if (not isinstance(form, dict) or set(form) != set(L10B_KEYS)
            or any(type(value) is not bool for value in form.values())):
        raise _UnsupportedMetadata('unsupported_corporate_l10b_source_shape')
    values, presence = [], []
    for owner, prefix, container, keys in (
            (form, [L10B_ROOT], ['Payload', 'CurrentFormData'], tuple(form)),
            (main, ['MainFormData'], ['Payload', 'CurrentFormData'],
             ('Tin', 'TaxYear', 'IsTransactionWithRelated')),
            (root, [], ['Payload', 'CurrentFormData'], ('TaxType', 'TaxPeriodCode',
             'ReturnSheetRecordIdentifier', 'ReturnSheetAggregateIdentifier')),
            (payload, [], ['Payload'], ('TIN', 'PeriodYear', 'ReturnSheetStatusCode',
             'ReturnSheetModel', 'PreviousFormData', 'LastSubmittedFormData', 'IsTransactionWithRelated'))):
        for key in keys:
            value = owner[key]
            entry = ({'path': prefix + [key], 'type': 'boolean', 'value': value}
                     if type(value) is bool else _evidence(value, prefix + [key]))
            entry.update(container=list(container), response_sequence=event['sequence'],
                         attempt=event['attempt'], rule='retained-original-nondisplay-custody')
            values.append(entry)
            presence.append({'path': prefix + [key], 'container': list(container),
                'response_sequence': event['sequence'], 'attempt': event['attempt'], 'present': True})
    return {'form': 'L10-B', 'kind': L10B_KIND, 'builds': dict(proof['builds']),
            'route': route, 'attempt': event['attempt'], 'values': values,
            'presence_facts': presence,
            **({'visibility_binding': proof['visibility_binding']} if 'visibility_binding' in proof else {})}


def l10b_nondisplay_covered(section, provenance):
    """A validated source-specific report may cover only its unchanged raw table.

    No display-filter lookup, empty-table permission, field placeholder or
    name-only exemption. The adapter report and original event must both exist.
    """
    if (section.get('name') != 'L10-B' or section.get('fields') != [] or section.get('text') != ''
            or not isinstance(provenance, dict)):
        return False
    reports = [r for r in provenance.get('projections', [])
               if isinstance(r, dict) and r.get('form') == 'L10-B']
    if len(reports) != 1:
        return False
    report = reports[0]
    if (set(report) - {'visibility_binding'} != {'form', 'kind', 'builds', 'route', 'attempt', 'values',
                        'presence_facts'}
            or 'visibility_binding' in report and report['visibility_binding'] != 'current-induk-enabled-v1'
            or report['kind'] != L10B_KIND or not _l10b_pins(report['builds'])
            or not isinstance(report['values'], list) or not isinstance(report['presence_facts'], list)):
        return False
    if not report['values'] or not isinstance(report['values'][0], dict):
        return False
    sequence = report['values'][0].get('response_sequence')
    if type(sequence) is not int or sequence < 1:
        return False
    # Select the one original report-bound event before reconstruction. An
    # earlier admitted catalog is not a competing primary; mixed report values
    # and duplicate/conflicting events for this sequence are still refused.
    events = [event for event in provenance.get('events', []) if isinstance(event, dict)
              and event.get('attempt') == report['attempt'] and event.get('frame_url') == report['route']
              and type(event.get('sequence')) is int and event['sequence'] == sequence]
    if len(events) != 1:
        return False
    for event in events:
        # Rebuild the admission from typed retained originals; a partial report
        # or a changed lifecycle predicate must not become a gate exemption.
        root, payload = {}, {}
        try:
            from coretax_json import _capture_component_lifetime, _capture_l10b_lifetime
            if (event.get('url') != ORIGIN + '/returnsheet/api/prefillreturnsheet/corporate-income'
                    or event.get('method') != 'POST'):
                return False
            options = {'attempt': event['attempt'], 'record_id': event['record_id'],
                       'source_url': event['component_lifetime']['source_url'], 'detail_url': event['frame_url']}
            _capture_component_lifetime(event['component_lifetime'], **options)
            _capture_l10b_lifetime(event['corporate_l10b_lifetime'], **options)
            for value in report['values']:
                if set(value) != {'path', 'type', 'value', 'container', 'response_sequence', 'attempt', 'rule'}:
                    return False
                if value['response_sequence'] != event['sequence'] or value['attempt'] != event['attempt']:
                    return False
                item = (_CorporateNumber(value['value']) if value['type'] == 'number' else value['value'])
                if value['type'] != ('number' if type(item) is _CorporateNumber else
                        'boolean' if type(item) is bool else 'null' if item is None else
                        'string' if type(item) is str else 'unsupported'):
                    return False
                target = payload if value['container'] == ['Payload'] else root
                if value['container'] not in (['Payload'], ['Payload', 'CurrentFormData']):
                    return False
                for token in value['path'][:-1]:
                    target = target.setdefault(token, {})
                if value['path'][-1] in target:
                    return False
                target[value['path'][-1]] = item
            binding = {'name': 'L10-B', 'paths': [[L10B_ROOT]], 'projection': {
                'kind': L10B_KIND, 'builds': report['builds'], 'route': report['route'],
                **({'visibility_binding': report['visibility_binding']} if 'visibility_binding' in report else {})}}
            record = {'record_id': event['record_id'], 'source_status': 'SPT Dilaporkan',
                'meta': {'Model SPT': 'Normal'}, 'source_fields': {
                    'TaxpayerAggregateIdentifier': report['route'].split('/')[-4],
                    'TaxTypeCode': 'ICT_RCIT', 'ReturnSheetTypeCode': 'ICT_RCITR',
                    'ReturnSheetModel': 'Normal',
                    'TaxPeriodCode': root['TaxPeriodCode'],
                    'AggregateIdentifier': root['ReturnSheetAggregateIdentifier']}}
            rebuilt = _apply_l10b(binding, section, [{'name': 'Induk'}, binding],
                root=root, payload=payload, record=record, event=event)
            rows = [[f'/{L10B_ROOT}/{key}', 'boolean', value] for key, value in root[L10B_ROOT].items()]
            expected = {'name': '/' + L10B_ROOT, 'headers': ['JSON path', 'JSON type', 'Source value'],
                        'rows': rows, 'complete': True}
            if (_corporate_request_key(rebuilt) == _corporate_request_key(report)
                    and _corporate_request_key(section.get('tables')) == _corporate_request_key([expected])):
                return True
        except (KeyError, TypeError, IndexError, AttributeError, _UnsupportedMetadata, JsonSafetyError):
            return False
    return False


def apply_projections(sections, observed_forms, *, root, payload, record, event, country_packets=None,
                      reference_packets=None, auxiliary_packets=None, grid_packets=None):
    """Replace only explicitly declared semantic sections after packet safety."""
    projected = []
    for binding, section in zip(observed_forms, sections):
        if 'projection' not in binding:
            continue  # Preserve old evidence-leaf captures and caller contracts.
        # An Induk binding that also declares extra evidence roots is left as
        # plain evidence: only the reviewed single-root form is projected.
        if binding['name'] == 'Induk':
            if binding.get('paths') == [[INDUK_ROOT]]:
                projected.append(_apply_induk(binding, section, observed_forms, root=root,
                    payload=payload, record=record, event=event))
            continue
        if binding['name'] == 'L10-A':
            projected.append(_apply_l10a(binding, section, observed_forms, root=root,
                payload=payload, record=record, event=event, grid_packets=grid_packets or {},
                reference_packets=reference_packets or {}))
            continue
        if binding['name'] == 'L6':
            projected.append(_apply_l6(binding, section, observed_forms, root=root,
                payload=payload, record=record, event=event))
            continue
        if binding['name'] == 'L2':
            projected.append(_apply_l2(binding, section, observed_forms, root=root,
                payload=payload, record=record, event=event, reference_packets=reference_packets or {}))
            continue
        if binding['name'] == 'L10-B':
            projected.append(_apply_l10b(binding, section, observed_forms, root=root,
                payload=payload, record=record, event=event))
            continue
        if binding['name'] == 'L11-A':
            projected.append(_apply_l11a(binding, section, observed_forms, root=root, payload=payload,
                record=record, event=event, reference_packets=reference_packets or {},
                auxiliary_packets=auxiliary_packets or {}))
            continue
        if binding['name'] == 'L3':
            projected.append(_apply_l3(binding, section, observed_forms, root=root, payload=payload,
                record=record, event=event, reference_packets=reference_packets or {},
                auxiliary_packets=auxiliary_packets or {}))
            continue
        if binding['name'] == 'L1-D':
            projected.append(_apply_l1d(binding, section, observed_forms, root=root, payload=payload,
                record=record, event=event))
            continue
        if binding['name'] == 'L8':
            projected.append(_apply_l8(binding, section, observed_forms, root=root, payload=payload,
                record=record, event=event))
            continue
        if binding['name'] == 'L4':
            projected.append(_apply_l4(binding, section, observed_forms, root=root, payload=payload,
                record=record, event=event, auxiliary_packets=auxiliary_packets or {},
                reference_packets=reference_packets or {}))
            continue
        if binding['name'] == 'L9':
            projected.append(_apply_l9(binding, section, observed_forms, root=root, payload=payload,
                record=record, event=event, reference_packets=reference_packets or {},
                auxiliary_packets=auxiliary_packets or {}))
            continue
        if binding['name'] == 'L11-C':
            projected.append(_apply_l11c(binding, section, observed_forms, root=root, payload=payload,
                record=record, event=event, country_packets=country_packets or {}))
            continue
        if binding['name'] == 'L11-B':
            projected.append(_apply_l11b(binding, section, observed_forms, root=root,
                payload=payload, record=record, event=event))
            continue
        if binding['name'] == 'L10-C':
            projected.append(_apply_l10c(binding, section, observed_forms, root=root, payload=payload,
                record=record, event=event, reference_packets=reference_packets or {}))
            continue
        proof = binding['projection']
        if (binding['name'] != 'L7' or not isinstance(proof, dict)
                or set(proof) != {'kind', 'builds', 'route', 'locale', 'tables'}
                or proof['kind'] != 'corporate-l7-v1' or proof['builds'] != BUILD_DIGESTS
                or proof['route'] != event['frame_url'] or proof['locale'] != 'id-ID'
                or not isinstance(proof['tables'], list) or len(proof['tables']) != 1
                or binding.get('paths') != [[L7_ROOT]] or binding.get('grids', [])
                or binding.get('responses', []) or binding.get('dependencies', [])):
            raise _UnsupportedMetadata('unsupported_corporate_semantic_binding')
        fields = record.get('source_fields', {})
        route = (ORIGIN + '/returnsheets/id-ID/corporate-income-tax-return/' + '/'.join(
            str(value) for value in (fields.get('TaxpayerAggregateIdentifier'), record['record_id'],
                                    fields.get('TaxTypeCode'), fields.get('AggregateIdentifier'))))
        literal_model = record.get('meta', {}).get('Model SPT')
        model = ('NORMAL' if literal_model == 'Normal' else 'AMENDMENT'
                 if isinstance(literal_model, str) and re.fullmatch(r'Amendment [0-9]{3}', literal_model) else None)
        if (proof['route'] not in (route, route + '?view=true') or record.get('source_status') != 'SPT Dilaporkan'
                or payload.get('ReturnSheetStatusCode') != 'SUBMITTED'
                or model is None or payload.get('ReturnSheetModel') != model
                or fields.get('ReturnSheetModel') != literal_model
                or 'Induk' not in [form['name'] for form in observed_forms[:observed_forms.index(binding)]]):
            raise _UnsupportedMetadata('unverified_corporate_l7_submitted_lifecycle')
        if 'PreviousFormData' not in payload:
            raise _UnsupportedMetadata('missing_corporate_l7_previous_encoding')
        previous = payload['PreviousFormData']
        if previous is not None:
            if type(previous) is not str:
                raise _UnsupportedMetadata('unsupported_corporate_l7_previous_encoding')
            try:
                previous = _corporate_json(previous)
            except JsonSafetyError:
                raise _UnsupportedMetadata('unsupported_corporate_l7_previous_encoding') from None
            if previous is not None and not isinstance(previous, dict):
                raise _UnsupportedMetadata('unsupported_corporate_l7_previous_shape')
        table = proof['tables'][0]
        if (not isinstance(table, dict) or set(table) != {'component', 'headers', 'footer_spans'}
                or table['component'] != 'rsh-citr-l7-grid1'):
            raise _UnsupportedMetadata('unverified_corporate_l7_grid_owner')
        main = root.get('MainFormData')
        if not isinstance(main, dict):
            raise _UnsupportedMetadata('unsupported_corporate_l7_source_shape')
        negative = _integer(main.get('NetIncomeBeforeTax')) < 0
        if negative:
            proof = _l7_negative_profile(binding, root=root, payload=payload, record=record,
                                         event=event, route=route, table=table)
        result = project_l7(root.get(L7_ROOT), main_form=root.get('MainFormData'),
            period_year=payload.get('PeriodYear'), headers=table['headers'], footer_spans=table['footer_spans'],
            tax_type=fields.get('TaxTypeCode'), locale=proof['locale'])
        section['tables'] = [result['table']]
        if negative:
            # Typed originals retain their actual source owner. Absence is not
            # a null leaf and therefore belongs only in the presence report.
            for values, prefix, owner, keys in (
                    (main, ['MainFormData'], 'current',
                     ('TaxYear', 'IsIncomeUnder', 'IsIncomeSolely', 'IsCarriedForward')),
                    (root, [], 'current', ('TaxType',)),
                    (payload, [], 'primary', ('PeriodYear', 'ReturnSheetStatusCode',
                     'ReturnSheetModel', 'PreviousFormData', 'LastSubmittedFormData'))):
                for key in keys:
                    entry = _evidence(values[key], prefix + [key])
                    entry.update(source=owner, rule='retained-original-raw-negative-predicate',
                                 destination={'table': 'L7', 'control': 'stable-raw-negative'})
                    result['provenance'].append(entry)
        for entry in result['provenance']:
            entry.update(response_sequence=event['sequence'], container=(['Payload']
                if entry.get('source') == 'primary' else ['Payload', 'CurrentFormData']))
        projected.append({'form': 'L7', 'kind': proof['kind'], 'builds': dict(proof['builds']),
                          'route': proof['route'], 'values': result['provenance'],
                          **({'presence_facts': [{'response_sequence': event['sequence'],
                              'container': ['Payload'], 'path': ['IsCarriedForward'], 'present': False,
                              'rule': 'outer-carry-absent/current-induk-enable'}]} if negative else {})})
    return projected


# Static captions/control ownership from the pinned L1-D source; no source defaults.
_L1D_BALANCE_ROWS = [[('group', 'body', None, 'Aset Lancar', None),
  ('amount', 'body', '1101', 'Kas dan Setara Kas', 'AC1101'),
  ('amount', 'body', '1122', 'Piutang Usaha - Pihak Ketiga', 'AC1122'),
  ('amount', 'body', '1123', 'Piutang Usaha - Pihak yang Mempunyai Hubungan Istimewa', 'AC1123'),
  ('amount', 'body', '1124', 'Piutang Lainnya - Pihak Ketiga', 'AC1124'),
  ('amount', 'body', '1125', 'Piutang Lainnya - Pihak yang Mempunyai Hubungan Istimewa', 'AC1125'),
  ('amount', 'body', '1131', 'Cadangan Kerugian Penurunan Nilai - Aset Lancar', 'AC1131'),
  ('amount', 'body', '1181', 'Aset Kontrak', 'AC1181'),
  ('amount', 'body', '1200', 'Investasi', 'AC1200'),
  ('amount', 'body', '1401', 'Persediaan', 'AC1401'),
  ('amount', 'body', '1421', 'Beban Dibayar di Muka', 'AC1421'),
  ('amount', 'body', '1422', 'Uang Muka', 'AC1422'),
  ('amount', 'body', '1423', 'Pajak Dibayar di Muka', 'AC1423'),
  ('amount', 'body', '1499', 'Aset lancar lainnya', 'AC1499'),
  ('group', 'body', None, 'Aset Tidak Lancar', None),
  ('amount', 'body', '1501', 'Piutang Jangka Panjang', 'AC1501'),
  ('amount', 'body', '1521', 'Aset tetap dan inventaris', 'AC1521'),
  ('amount', 'body', '1522', 'Dikurangi: Akumulasi penyusutan aset tetap dan inventaris', 'AC1522'),
  ('amount',
   'body',
   '1551',
   'Investasi pada Perusahaan Asosiasi, Ventura Bersama dan Anak Perusahaan',
   'AC1551'),
  ('amount', 'body', '1599', 'Investasi Jangka Panjang Lainnya', 'AC1599'),
  ('amount', 'body', '1600', 'Aset Tak Berwujud', 'AC1600'),
  ('amount', 'body', '1601', 'Dikurangi : Akumulasi Amortisasi-Aset Tak Berwujud', 'AC1601'),
  ('amount', 'body', '1611', 'Aktiva Pajak Tangguhan', 'AC1611'),
  ('amount', 'body', '1651', 'Klaim atas pengembalian pajak', 'AC1651'),
  ('amount', 'body', '1658', 'Cadangan Kerugian Penurunan Nilai - Aset Tidak Lancar', 'AC1658'),
  ('amount', 'body', '1698', 'Aset Tidak Lancar Lainnya', 'AC1698'),
  ('footer_total', 'footer', '1700', 'Jumlah Aset', 'AC1700')],
 [('group', 'body', None, 'Liabilitas Jangka Pendek', None),
  ('amount', 'body', '2102', 'Utang Usaha - Pihak Ketiga', 'AC2102'),
  ('amount', 'body', '2103', 'Utang Usaha - Pihak yang Mempunyai Hubungan Istimewa', 'AC2103'),
  ('amount', 'body', '2111', 'Utang Bunga', 'AC2111'),
  ('amount', 'body', '2186', 'Liabilitas Kontrak', 'AC2186'),
  ('amount', 'body', '2187', 'Liabilitas Sewa Jangka Pendek', 'AC2187'),
  ('amount', 'body', '2191', 'Utang Pajak', 'AC2191'),
  ('amount', 'body', '2192', 'Utang Dividen', 'AC2192'),
  ('amount', 'body', '2195', 'Beban yang Masih Harus Dibayar', 'AC2195'),
  ('amount', 'body', '2201', 'Utang Bank Jangka Pendek', 'AC2201'),
  ('amount', 'body', '2202', 'Utang Jangka Panjang yang Jatuh Tempo dalam Satu Tahun', 'AC2202'),
  ('amount', 'body', '2203', 'Pendapatan Diterima di Muka', 'AC2203'),
  ('amount', 'body', '2228', 'Liabilitas Jangka Pendek Lainnya', 'AC2228'),
  ('group', 'body', None, 'Liabilitas Jangka Panjang', None),
  ('amount', 'body', '2301', 'Utang Bank Jangka Panjang', 'AC2301'),
  ('amount', 'body', '2303', 'Utang Jangka Panjang-Pihak Ketiga', 'AC2303'),
  ('amount',
   'body',
   '2304',
   'Utang Jangka Panjang - Pihak yang Mempunyai Hubungan Istimewa',
   'AC2304'),
  ('amount', 'body', '2312', 'Liabilitas Sewa Jangka Panjang', 'AC2312'),
  ('amount', 'body', '2321', 'Liabilitas Pajak Tangguhan', 'AC2321'),
  ('amount', 'body', '2322', 'Liabilitas Imbalan Kerja', 'AC2322'),
  ('amount', 'body', '2998', 'Liabilitas Jangka Panjang Lainnya', 'AC2998'),
  ('body_total', 'body', '2999', 'Jumlah Liabilitas', 'AC2999'),
  ('group', 'body', None, 'Ekuitas', None),
  ('amount', 'body', '3102', 'Modal Saham', 'AC3102'),
  ('amount', 'body', '3120', 'Tambahan Modal Disetor', 'AC3120'),
  ('amount', 'body', '3200', 'Laba Ditahan', 'AC3200'),
  ('amount', 'body', '3297', 'Pendapatan Komprehensif Lainnya', 'AC3297'),
  ('amount', 'body', '3298', 'Ekuitas Lainnya', 'AC3298'),
  ('body_total', 'body', '3299', 'Jumlah Ekuitas', 'AC3299'),
  ('footer_total', 'footer', '3300', 'Jumlah Liabilitas dan Ekuitas', 'AC3300')]]

_L1D_FIELDS = ('Amount', 'NonTaxableObject', 'SubjectToFinalTax', 'NonFinal',
               'PositiveFiscalCorrection', 'NegativeFiscalCorrection', 'FinalAmount')
L1D_OMISSION_LAYOUT = 'absent-5322-34x10-v1'
_L1D_ORDER = ['Pendapatan:', '4021', '4013', '5020', '4300', '4199', 'Beban Usaha',
    *[str(code) for code in range(5311, 5323)], '5399', '5400', '4500',
    'Pendapatan Non Usaha', '4501', '4503', '4511', '4599', '4600',
    'Beban Non Usaha', '5405', '5409', '5421', '5499', '5500', '4700']
_L1D_HEADERS = [['KODE AKUN', 'NAMA AKUN', 'NILAI KOMERSIAL', 'TIDAK TERMASUK OBJEK PAJAK',
    'DIKENAKAN PPh BERSIFAT FINAL', 'OBJEK PAJAK TIDAK FINAL', 'PENYESUAIAN FISKAL POSITIF',
    'PENYESUAIAN FISKAL NEGATIF', 'KODE PENYESUAIAN FISKAL', 'NILAI FISKAL'],
    ['KODE AKUN', 'NAMA AKUN', 'NILAI'], ['KODE AKUN', 'NAMA AKUN', 'NILAI']]
_L1D_ASSET_CALC = ['1101', '1122', '1123', '1124', '1125', '-1131', '1181', '1200', '1401',
    '1421', '1423', '1422', '1499', '1501', '1521', '-1522', '1551', '1599',
    '1600', '-1601', '1611', '1651', '-1658', '1698']
_L1D_DEBT_CALC = ['2102', '2103', '2111', '2186', '2187', '2191', '2192', '2195',
    '2201', '2202', '2203', '2228', '2301', '2303', '2304', '2312', '2322', '2321', '2998']
_L1D_EQUITY_CALC = ['3102', '3120', '3200', '3297', '3298']
_L1D_UNCHANGED = {'4021', '4199', '4501', '4503', '4511', '4599'}
_L1D_SUBTOTALS = {'4300', '5400', '4500', '4600', '5500', '4700'}
_L1D_MASKS = {'NonTaxableObject', 'SubjectToFinalTax',
              'PositiveFiscalCorrection', 'NegativeFiscalCorrection'}


def _l1d_integer(value, *, nullish=False):
    if value is None and nullish:
        return 0
    if type(value) is not _CorporateNumber:
        raise _UnsupportedMetadata('unsupported_corporate_l1d_numeric_type')
    number = _decimal(value)
    if abs(number) > _MAX_INTEGER or number != number.to_integral_value():
        raise _UnsupportedMetadata('unsupported_corporate_l1d_numeric_precision')
    return int(number)


def _l1d_sum(values):
    result = 0
    for value in values:
        result += value
        if abs(result) > _MAX_INTEGER:
            raise _UnsupportedMetadata('unsafe_corporate_l1d_ordered_sum')
    return result


def project_l1d(form, *, migrated, headers, footer_spans, tax_type, locale, timezone_name,
                body_layout=None):
    """Pure source transformation; caller must separately prove fresh lifetime.

    This helper cannot authorize a native record. It copies reported totals
    only after exact consumer reconciliation, preserving original source paths.
    """
    if (type(migrated) is not bool or tax_type != 'ICT_RCIT' or locale != 'id-ID'
            or timezone_name != 'Asia/Jakarta' or headers != _L1D_HEADERS
            or footer_spans != [[[1] * 10], [[1, 1, 1]], [[1, 1, 1]]]
            or body_layout is not None and body_layout != L1D_OMISSION_LAYOUT):
        raise _UnsupportedMetadata('unverified_corporate_l1d_structure')
    roots = {'L1dTreeData', 'L1dTreeTotalRow', 'L1dAssets', 'L1dLiabilitiesAndEquity'}
    if (not isinstance(form, dict) or set(form) != roots
            or not isinstance(form['L1dTreeData'], list) or not form['L1dTreeData']):
        raise _UnsupportedMetadata('unsupported_corporate_l1d_source_shape')
    codes = {value for value in _L1D_ORDER if value.isdecimal()}
    nodes, provenance = {}, []
    data_fields = {*_L1D_FIELDS, 'AccountCode', 'Description', 'CorrectionCode'}
    metadata_fields = {'BlockFields', 'RowOptions', 'StyleOptions'}

    def evidence(value, path, destination, rule='literal-source'):
        item = _evidence(value, ['L1dFormData', *path])
        provenance.append({**item, 'destination': destination, 'rule': rule})

    def walk(rows, path, depth=0):
        if depth > 32 or not isinstance(rows, list):
            raise _UnsupportedMetadata('unsupported_corporate_l1d_tree')
        for index, node in enumerate(rows):
            if (not isinstance(node, dict) or set(node) - {'Data', 'Expanded', 'Children'}
                    or not isinstance(node.get('Data'), dict)):
                raise _UnsupportedMetadata('unsupported_corporate_l1d_tree_node')
            data = node['Data']
            if (set(data) - data_fields - metadata_fields
                    or type(data.get('AccountCode')) is not str or data['AccountCode'] not in codes
                    or data['AccountCode'] in nodes or type(data.get('Description')) is not str):
                raise _UnsupportedMetadata('ambiguous_corporate_l1d_account')
            code = data['AccountCode']
            if code in _L1D_UNCHANGED:
                style = data.get('StyleOptions')
                if style is not None and (not isinstance(style, dict)
                        or set(style) - {'Style', 'DescriptionStyle'}
                        or any(value not in ('', None) for value in style.values())):
                    raise _UnsupportedMetadata('unverified_corporate_l1d_effective_style')
            for field in _L1D_FIELDS:
                _l1d_integer(data.get(field), nullish=True)
            masks = data.get('BlockFields')
            if (masks is not None and not isinstance(masks, dict)
                    or code in _L1D_UNCHANGED and isinstance(masks, dict)
                    and any(masks.get(key) is not None and type(masks[key]) is not bool
                            for key in _L1D_MASKS)):
                raise _UnsupportedMetadata('unsupported_corporate_l1d_mask')
            correction = data.get('CorrectionCode')
            if not (correction is None or type(correction) is str or
                    isinstance(correction, list) and len(correction) <= 10000
                    and all(type(value) is str for value in correction)):
                raise _UnsupportedMetadata('unsupported_corporate_l1d_correction_code')
            nodes[code] = (data, [*path, index, 'Data'])
            if len(nodes) > 10000:
                raise _UnsupportedMetadata('corporate_l1d_tree_budget')
            children = node.get('Children')
            if children is not None:
                walk(children, [*path, index, 'Children'], depth + 1)

    walk(form['L1dTreeData'], ['L1dTreeData'])
    # The pinned lookup returns undefined for absent 5322. With the owned
    # 34x10 proof, pTableBody renders no row; never manufacture a node or zero.
    omitted_codes = ['5322'] if body_layout is not None else []
    if set(nodes) != codes - set(omitted_codes):
        raise _UnsupportedMetadata('missing_corporate_l1d_account')
    body = []
    for code in _L1D_ORDER:
        if code in omitted_codes:
            continue
        if code not in codes:
            body.append(['', code, *([''] * 8)])
            continue
        data, path = nodes[code]
        row, destination = [code, data['Description']], {'table': 'L1-D/tree', 'row': len(body)}
        evidence(code, [*path, 'AccountCode'], {**destination, 'column': 0})
        evidence(data['Description'], [*path, 'Description'], {**destination, 'column': 1})
        masks = data.get('BlockFields') or {}
        if code in _L1D_UNCHANGED:
            for field in sorted(_L1D_MASKS):
                value = masks.get(field)
                provenance.append({'path': ['L1dFormData', *path, 'BlockFields', field],
                    'type': 'missing' if field not in masks else
                            'null' if value is None else 'boolean',
                    'value': value, 'destination': dict(destination), 'rule': 'captured-mask-truthiness'})
        for column, field in enumerate(_L1D_FIELDS[:6], 2):
            masked = field in _L1D_MASKS and (
                field in ('NonTaxableObject', 'SubjectToFinalTax') and code not in _L1D_UNCHANGED
                or code in _L1D_SUBTOTALS
                or code in _L1D_UNCHANGED and masks.get(field) is True)
            row.append('' if masked or data.get(field) is None else _number(data.get(field), 0, locale=locale))
            evidence(data.get(field), [*path, field], {**destination, 'column': column},
                     'source-mask' if masked else 'angular-number-1.0-0-id')
        correction = data.get('CorrectionCode')
        row.append('; '.join(correction) if isinstance(correction, list) else correction or '')
        if isinstance(correction, list):
            for index, value in enumerate(correction):
                evidence(value, [*path, 'CorrectionCode', index], {**destination, 'column': 8})
        else:
            evidence(correction, [*path, 'CorrectionCode'], {**destination, 'column': 8})
        final_amount = data.get('FinalAmount')
        row.append('' if final_amount is None else _number(final_amount, 0, locale=locale))
        evidence(final_amount, [*path, 'FinalAmount'], {**destination, 'column': 9})
        body.append(row)
    reported = form['L1dTreeTotalRow']
    if (not isinstance(reported, dict) or not set(_L1D_FIELDS) <= set(reported)
            or set(reported) - data_fields - metadata_fields):
        raise _UnsupportedMetadata('unsupported_corporate_l1d_tree_totals')
    footer = ['4800', 'Laba (Rugi) Sebelum Pajak']
    for field in _L1D_FIELDS:
        value = _l1d_integer(reported[field])
        if not migrated and value != _l1d_sum(
                [_l1d_integer(nodes[code][0].get(field), nullish=True) for code in ('4500', '4700')]):
            raise _UnsupportedMetadata('unreconciled_corporate_l1d_tree_total')
        footer.append(_number(reported[field], 0, locale=locale))
        evidence(reported[field], ['L1dTreeTotalRow', field], {'table': 'L1-D/tree', 'footer': 0},
                 'migrated-reported-total' if migrated else 'reconciled-reported-total')
    footer.insert(8, '')

    def table(index, rows, foot):
        return {'name': ['L1-D/tree', 'L1-D/assets', 'L1-D/liabilities-equity'][index],
            'headers': list(headers[index]), 'rows': rows + [foot], 'footer': [foot],
            'footer_spans': deepcopy(footer_spans[index]), 'body_row_count': len(rows),
            'source_total': len(rows), 'complete': True, 'source_structure': {'form': 'L1-D',
                'component': f'rsh-citr-l1d-grid{index + 1}',
                'groups': ['A. LAPORAN LABA RUGI' if index == 0 else 'B. LAPORAN POSISI KEUANGAN']}}

    tables = [table(0, body, footer)]
    for index, root in enumerate(('L1dAssets', 'L1dLiabilitiesAndEquity'), 1):
        data = form[root]
        descriptors = _L1D_BALANCE_ROWS[index - 1]
        expected = {entry[4] for entry in descriptors if entry[4] is not None}
        if not isinstance(data, dict) or set(data) - expected:
            raise _UnsupportedMetadata('unsupported_corporate_l1d_balance_source')
        values = {key: _l1d_integer(data.get(key), nullish=True) for key in expected}
        calculations = [('AC1700', _L1D_ASSET_CALC)] if index == 1 else [
            ('AC2999', _L1D_DEBT_CALC), ('AC3299', _L1D_EQUITY_CALC),
            ('AC3300', ['2999', '3299'])]
        for total, operands in calculations:
            computed = _l1d_sum([(-1 if code.startswith('-') else 1) * values['AC' + code.lstrip('-')]
                                 for code in operands])
            if _l1d_integer(data.get(total)) != computed:
                raise _UnsupportedMetadata('unreconciled_corporate_l1d_balance_total')
        rows, foot = [], None
        for _, location, code, caption, key in descriptors:
            row = [code or '', caption, '' if key is None or data.get(key) is None
                   else _number(data.get(key), 0, locale=locale)]
            if key is not None:
                evidence(data.get(key), [root, key], {'table': f'L1-D/grid{index + 1}',
                    'footer': 0} if location == 'footer' else {'table': f'L1-D/grid{index + 1}',
                    'row': len(rows), 'column': 2}, 'reconciled-reported-total' if key in
                    {total for total, _ in calculations} else 'angular-number-1.0-0-id')
            if location == 'footer':
                foot = row
            else:
                rows.append(row)
        tables.append(table(index, rows, foot))
    return {'tables': tables, 'provenance': provenance,
            **({'omitted_account_codes': omitted_codes} if body_layout is not None else {})}


_L3_ROOT = 'ListIncomeTaxWithheldByOtherParties'
_L3_OWNERS = ('rsh-citr-l3-grid1', 'rshshr-citr-l3-grid2')
_L3_GROUPS = ('A. PENGHASILAN DARI LUAR NEGERI', 'B. PPh YANG DIPOTONG/DIPUNGUT PIHAK LAIN')
_L3_HEADERS = [['NO.', 'PEMOTONG PAJAK / NAMA', 'PEMOTONG PAJAK / NEGARA',
    'TANGGAL TRANSAKSI/PEMBAYARAN PPh', 'JENIS PENGHASILAN', 'PENGHASILAN NETO (RUPIAH)',
    'PPh YANG DIBAYAR/DIPOTONG/TERUTANG DI LUAR NEGERI / NILAI (Rp)',
    'PPh YANG DIBAYAR/DIPOTONG/TERUTANG DI LUAR NEGERI / MATA UANG',
    'PPh YANG DIBAYAR/DIPOTONG/TERUTANG DI LUAR NEGERI / NILAI DALAM MATA UANG ASING',
    'JUMLAH KREDIT PAJAK YANG DAPAT DIPERHITUNGKAN (Rp)'],
    ['NO.', 'NAMA PEMOTONG/PEMUNGUT', 'NPWPW PEMOTONG/PEMUNGUT', 'Jenis Pajak',
     'DASAR PENGENAAN PAJAK (Rupiah)', 'PPH YANG DIPOTONG/DIPUNGUT (Rupiah)',
     'BUKTI POTONG/SSP/SSPCP - NOMOR', 'BUKTI POTONG/SSP/SSPCP - TANGGAL']]
_L3_SCALARS = ('OverseasTotalNetIncome', 'OverseasTotalTaxPayable', 'OverseasTotalTaxCredit',
    'OverseasRefundPreviousYear', 'OverseasTotalCalculatedCurrentYear', 'OtherPartiesTotalTaxBase',
    'OtherPartiesIncomeTaxWithheld', 'OtherPartiesIncomeTaxWithheldUsd',
    'OtherPartiesOverseasIncomeTax', 'OtherPartiesTotalCredit', 'OtherPartiesTotalCreditUsd')
_L3_A_FIELDS = ('Name', 'CountryCode', 'DateOfTransaction', 'IncomeCode', 'NetIncome',
    'PayableRupiah', 'PayableCurrency', 'AmountForeignCurrency', 'CreditCalculated')
_L3_B_FIELDS = ('Name', 'TIN', 'TaxType', 'TaxBase', 'IncomeTax',
    'WithholdingSlipsNumber', 'WithholdingSlipsDate')
_L3_B_METADATA = ('IncomeTaxUsd', 'IsManually', 'TableSource', 'Index', 'Action')
# The pinned L3-B grid emits rows from these two source grids (plus manual rows
# with a null TableSource). Any other TableSource is unproved and refuses.
_L3_B_TABLE_SOURCES = frozenset((None, 'EBUPOTBPU_GRID', 'TAXPAYER_ACCOUNTING'))
# The two pinned source grids a non-manual (grid-sourced) row may name.
_L3_B_GRID_SOURCES = frozenset(('EBUPOTBPU_GRID', 'TAXPAYER_ACCOUNTING'))
_L3_B_ROW_FIELDS = frozenset(('RecordId', *_L3_B_FIELDS))
_L3_B_EXTENDED_FIELDS = _L3_B_ROW_FIELDS | frozenset(_L3_B_METADATA)
_L3_LABELS = ('COUNTRY_CODE', 'CURRENCY', 'FOREIGN_INCOME_TYPE_CIT', 'TAX_TYPE_BY_OTHER_PARTIES')
# The pinned L3-B grid emits the tax type of some rows as the bare label
# without the "PPh " prefix ("Pasal 23") instead of the catalog code
# (ARTICLE23, whose label is "PPh Pasal 23"). This source-bound mapping is
# pinned to the observed contract; the resolved code must still be present in
# the observed TAX_TYPE_BY_OTHER_PARTIES catalog, so the label binds through
# the normal catalog lookup and nothing is fabricated. Any other bare label
# stays unbound and refuses.
_L3_B_TAX_TYPE_BARE_LABELS = {'Pasal 23': 'ARTICLE23'}
_L3_CAPTIONS = (
    'PENGEMBALIAN/PENGURANGAN PAJAK PENGHASILAN LUAR NEGERI (PASAL 24) YANG TELAH DIKREDITKAN UNTUK TAHUN SEBELUMNYA',
    'JUMLAH PAJAK PENGHASILAN YANG DIBAYAR DI LUAR NEGERI YANG DAPAT DIPERHITUNGKAN DALAM TAHUN BERJALAN')
# The portal renamed these two header-only controls to English in the reviewed
# redeploy. The worksheet labels stay the approved Indonesian template text; only
# the structural layout proof accepts either exact source pair.
_L3_LAYOUT_CAPTIONS = (
    _L3_CAPTIONS,
    ('REFUND/DEDUCTION OF CREDITED OVERSEAS INCOME TAXES(ARTICLE 24) THAT HAS BEEN CREDITED FOR PREVIOUS YEAR',
     'TOTAL INCOME TAX PAID IN OVERSEAS THAT CAN BE CALCULATED IN CURRENT YEAR'))


def _l3_integer(value, *, nullish=False):
    if value is None and nullish:
        return 0
    if type(value) is not _CorporateNumber:
        raise _UnsupportedMetadata('unsupported_corporate_l3_number_type')
    number = _decimal(value)
    if abs(number) > _MAX_INTEGER or number != number.to_integral_value():
        raise _UnsupportedMetadata('unsupported_corporate_l3_number_precision')
    return int(number)


def _l3_usd(value, *, nullish=False):
    # Foreign-currency (USD) amounts carry a 2-decimal fraction, unlike the
    # whole-rupiah controls. Never invent precision: reject beyond 2 decimals.
    if value is None and nullish:
        return Decimal(0)
    if type(value) is not _CorporateNumber:
        raise _UnsupportedMetadata('unsupported_corporate_l3_number_type')
    number = _decimal(value)
    if abs(number) > _MAX_INTEGER or number != number.quantize(Decimal('0.01')):
        raise _UnsupportedMetadata('unsupported_corporate_l3_number_precision')
    return number


def _l3_usd_exact(value, *, nullish=False):
    # Hidden USD totals (the footer callback and row metadata) keep the portal's
    # exact source lexeme. The observed portal emits up to 8 decimals, but the
    # contract is a bounded finite decimal (|value| <= _MAX_INTEGER) of any
    # scale, preserved exactly and never rounded. The 2-decimal scalar controls
    # stay on _l3_usd.
    if value is None and nullish:
        return Decimal(0)
    if type(value) is not _CorporateNumber:
        raise _UnsupportedMetadata('unsupported_corporate_l3_number_type')
    number = _decimal(value)
    if not number.is_finite() or abs(number) > _MAX_INTEGER:
        raise _UnsupportedMetadata('unsupported_corporate_l3_number_precision')
    return number


def _l3_sum(values):
    result = 0
    for value in values:
        result += value
        if abs(result) > _MAX_INTEGER:
            raise _UnsupportedMetadata('unsafe_corporate_l3_ordered_sum')
    return result


def _l3_date(value, *, offline=False, domestic_jakarta_midnight=False):
    if value is None or offline and value == '':
        return ''
    if type(value) is not str or not (re.fullmatch(
            r'[0-9]{4}-[0-9]{2}-[0-9]{2}(?:T(?:[01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]'
            r'(?:\.[0-9]{1,3})?Z)?', value)
            or domestic_jakarta_midnight is True and not offline and re.fullmatch(
                r'[0-9]{4}-[0-9]{2}-[0-9]{2}T00:00:00\+07:00', value)):
        raise _UnsupportedMetadata('unsupported_corporate_l3_date')
    try:
        date = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if not 1970 <= date.year <= 2100:
            raise ValueError('Unreviewed date range')
        date = date.replace(tzinfo=timezone.utc) if date.tzinfo is None else date
        return date.astimezone(timezone(timedelta(hours=7))).strftime('%d-%m-%Y')
    except (ValueError, OverflowError):
        raise _UnsupportedMetadata('unsupported_corporate_l3_date') from None


def project_l3(form, *, pages, footer_payload, headers, footer_spans, tax_type, locale,
               timezone_name, labels):
    """Pure consumer projection; callers must separately prove every packet/owner.

    Normalized page bounds are metadata, never original business identifiers.
    This helper grants no native eligibility or reference/footer transport access.
    """
    spans = [[[1, 4, 1, 1, 2, 1]], [[4, 1, 1, 2]] * 3]
    if (tax_type != 'ICT_RCIT' or locale != 'id-ID' or timezone_name != 'Asia/Jakarta'
            or headers != _L3_HEADERS or footer_spans != spans
            or not isinstance(form, dict) or set(form) - {'IncomeOverseas', *_L3_SCALARS}
            or not ({'IncomeOverseas'} | set(_L3_SCALARS) - {'OverseasRefundPreviousYear'}) <= set(form)
            or not isinstance(labels, dict) or set(labels) != set(_L3_LABELS)
            or any(not isinstance(labels[k], dict) for k in _L3_LABELS)):
        raise _UnsupportedMetadata('unverified_corporate_l3_source_structure')
    overseas = [] if form['IncomeOverseas'] is None else form['IncomeOverseas']
    if not isinstance(overseas, list) or len(overseas) > 100000:
        raise _UnsupportedMetadata('unsupported_corporate_l3_overseas_body')
    if (not isinstance(footer_payload, dict) or set(footer_payload) != {'TaxBase', 'IncomeTax', 'IncomeTaxUsd'}
            or not isinstance(pages, list) or not 1 <= len(pages) <= 1000):
        raise _UnsupportedMetadata('missing_corporate_l3_footer_or_pages')
    provenance, arows, brows = [], [], []

    def evidence(value, path, destination, *, source='current', page_index=None, rule='literal-source'):
        item = {**_evidence(value, path), 'source': source, 'destination': destination, 'rule': rule}
        if page_index is not None:
            item['page_index'] = page_index
        provenance.append(item)

    def text(value):
        if value is None:
            return ''
        if type(value) is not str:
            raise _UnsupportedMetadata('unsupported_corporate_l3_text')
        return value

    def label(value, kind, *, offline=False):
        if offline and (value is None or type(value) is str and value == ''):
            return ''
        if (type(value) is not str or not value or type(labels[kind].get(value)) is not str
                or not labels[kind][value].strip()):
            raise _UnsupportedMetadata('missing_corporate_l3_reference_label')
        return labels[kind][value]

    def number(value, fraction=0):
        _l3_integer(value)
        return _number(value, fraction, locale=locale)

    for field in _L3_SCALARS:
        value = form.get(field)
        if field.endswith('Usd'):
            _l3_usd(value, nullish=True)
        else:
            _l3_integer(value, nullish=True)
        evidence(value, [_L3_ROOT, field], {'control': field})
    sums = []
    for field, reported in zip(('NetIncome', 'PayableRupiah', 'CreditCalculated'), _L3_SCALARS[:3]):
        if any(not isinstance(row, dict) or set(row) != set(_L3_A_FIELDS) for row in overseas):
            raise _UnsupportedMetadata('unsupported_corporate_l3_overseas_row')
        total = _l3_sum(_l3_integer(row[field]) for row in overseas)
        if _l3_integer(form[reported]) != total:
            raise _UnsupportedMetadata('unreconciled_corporate_l3_overseas_total')
        sums.append(total)
    foreign_credit = _l3_sum([sums[2], -_l3_integer(form.get('OverseasRefundPreviousYear'), nullish=True)])
    for index, row in enumerate(overseas):
        arows.append([str(index + 1), text(row['Name']), label(row['CountryCode'], 'COUNTRY_CODE', offline=True),
            _l3_date(row['DateOfTransaction'], offline=True), label(row['IncomeCode'], 'FOREIGN_INCOME_TYPE_CIT', offline=True),
            number(row['NetIncome']), number(row['PayableRupiah']), label(row['PayableCurrency'], 'CURRENCY', offline=True),
            number(row['AmountForeignCurrency'], 2), number(row['CreditCalculated'])])
        for column, field in enumerate(_L3_A_FIELDS, 1):
            evidence(row[field], [_L3_ROOT, 'IncomeOverseas', index, field],
                     {'table': 'L3/overseas', 'row': index, 'column': column},
                     rule='bound-reference-label' if field in ('CountryCode', 'IncomeCode', 'PayableCurrency')
                     else 'date-id-jakarta' if field == 'DateOfTransaction'
                     else 'number-id-fraction-2' if field == 'AmountForeignCurrency'
                     else 'number-id-fraction-0' if field in ('NetIncome', 'PayableRupiah', 'CreditCalculated')
                     else 'literal-source')
    for field, column in zip(_L3_SCALARS[:3], (5, 6, 9)):
        evidence(form[field], [_L3_ROOT, field], {'table': 'L3/overseas', 'footer': 0, 'column': column},
                 rule='reconciled-model-ordered-sum')
    total = None
    for page_index, page in enumerate(pages):
        if (not isinstance(page, dict) or set(page) != {'offset', 'rows', 'total', 'data'}
                or any(type(page[k]) is not int for k in ('offset', 'rows', 'total'))
                or page['rows'] not in (10, 25, 50, 100, 250, 500)
                or not 0 <= page['total'] <= 100000 or page['offset'] != len(brows)
                or page['offset'] > page['total'] or not isinstance(page['data'], list)
                or len(page['data']) != min(page['rows'], page['total'] - page['offset'])
                or total is not None and total != page['total']
                or page_index and page['offset'] == page['total']):
            raise _UnsupportedMetadata('incomplete_corporate_l3_pages')
        total = page['total']
        for local_index, row in enumerate(page['data']):
            if not isinstance(row, dict) or set(row) not in (_L3_B_ROW_FIELDS, _L3_B_EXTENDED_FIELDS):
                raise _UnsupportedMetadata('unsupported_corporate_l3_domestic_row')
            extended = set(row) == _L3_B_EXTENDED_FIELDS
            if extended:
                # The pinned grid emits two proved variants: manual rows
                # (IsManually true, a null TableSource) and grid-sourced rows
                # (IsManually false, one of the two pinned source grids) with a
                # bounded nonnegative USD lexeme. Admit exactly those; the
                # cross-product (a manual row naming a grid source, or a
                # grid-sourced row with a null source), negative USD, nonzero
                # Index, non-null Action and malformed/unproved values are
                # inconsistent and refuse. A manually entered USD amount is
                # unproved by the pinned consumer, so manual rows keep the
                # traditional zero-only contract; only grid-sourced rows carry
                # a nonzero (fractional) USD lexeme.
                try:
                    usd = _l3_usd_exact(row['IncomeTaxUsd'])
                    index_ok = _l3_integer(row['Index']) == 0
                except _UnsupportedMetadata:
                    raise _UnsupportedMetadata('unsupported_corporate_l3_domestic_row') from None
                if (type(row['IsManually']) is not bool
                        or type(row['TableSource']) not in (str, type(None))
                        or row['TableSource'] not in _L3_B_TABLE_SOURCES
                        or row['Action'] is not None or not index_ok
                        or usd < 0):
                    raise _UnsupportedMetadata('unsupported_corporate_l3_domestic_row')
                if row['IsManually'] is True:
                    # A manual row has no grid source and no proved USD amount.
                    if row['TableSource'] is not None or usd != 0:
                        raise _UnsupportedMetadata('unsupported_corporate_l3_domestic_row')
                elif row['TableSource'] not in _L3_B_GRID_SOURCES:
                    # A grid-sourced row names one of the two pinned source grids.
                    raise _UnsupportedMetadata('unsupported_corporate_l3_domestic_row')
            text(row['RecordId'])
            # The source-bound bare-label mapping: some pinned L3-B rows carry
            # "Pasal 23" where the catalog code is ARTICLE23; the resolved
            # code still must bind through the observed catalog.
            tax_type = row['TaxType']
            tax_type = (_L3_B_TAX_TYPE_BARE_LABELS.get(tax_type, tax_type)
                        if type(tax_type) is str else tax_type)
            brows.append([str(local_index + 1), text(row['Name']), text(row['TIN']),
                label(tax_type, 'TAX_TYPE_BY_OTHER_PARTIES'), number(row['TaxBase']), number(row['IncomeTax']),
                text(row['WithholdingSlipsNumber']),
                _l3_date(row['WithholdingSlipsDate'], domestic_jakarta_midnight=True)])
            evidence(row['RecordId'], ['Data', local_index, 'RecordId'],
                {'table': 'L3/domestic', 'row': len(brows) - 1}, source='grid', page_index=page_index,
                rule='non-displayed-row-key')
            for column, field in enumerate(_L3_B_FIELDS, 1):
                evidence(row[field], ['Data', local_index, field],
                    {'table': 'L3/domestic', 'row': len(brows) - 1, 'column': column}, source='grid', page_index=page_index,
                    rule='bound-reference-label' if field == 'TaxType' else 'date-id-jakarta'
                    if field == 'WithholdingSlipsDate' else 'number-id-fraction-0'
                    if field in ('TaxBase', 'IncomeTax') else 'literal-source')
            if extended:
                for field in _L3_B_METADATA:
                    path = ['Data', local_index, field]
                    destination = {'table': 'L3/domestic', 'row': len(brows) - 1, 'metadata': field}
                    if field == 'IsManually':
                        # Only the reviewed literal true is admitted above. Do not
                        # widen shared Masa scalar evidence to accept booleans.
                        provenance.append({'path': path, 'type': 'boolean', 'value': row[field],
                            'source': 'grid', 'page_index': page_index, 'destination': destination,
                            'rule': 'non-displayed-domestic-row-metadata'})
                    else:
                        evidence(row[field], path, destination, source='grid', page_index=page_index,
                                 rule='non-displayed-domestic-row-metadata')
    if len(brows) != total:
        raise _UnsupportedMetadata('incomplete_corporate_l3_pages')
    amounts = {key: (_l3_usd_exact(value, nullish=True) if key == 'IncomeTaxUsd'
                     else _l3_integer(value, nullish=True)) for key, value in footer_payload.items()}
    credit = _l3_sum([foreign_credit, amounts['IncomeTax']])
    _l3_sum([foreign_credit, amounts['IncomeTaxUsd']])  # The same callback writes the hidden USD total.
    for field, value in footer_payload.items():
        destination = ({'table': 'L3/domestic', 'footer': 0, 'column': 4 if field == 'TaxBase' else 5}
                       if field != 'IncomeTaxUsd' else {'hidden_control': 'OtherPartiesIncomeTaxWithheldUsd'})
        evidence(value, [field], destination, source='footer', rule='captured-footer-nullish-zero')
    for footer_index in (1, 2):
        destination = {'table': 'L3/domestic', 'footer': footer_index, 'column': 5}
        for index, row in enumerate(overseas):
            evidence(row['CreditCalculated'], [_L3_ROOT, 'IncomeOverseas', index, 'CreditCalculated'],
                     destination, rule='credit-sum-minus-refund')
        evidence(form.get('OverseasRefundPreviousYear'), [_L3_ROOT, 'OverseasRefundPreviousYear'],
                 destination, rule='credit-sum-minus-refund')
        if footer_index == 2:
            evidence(footer_payload['IncomeTax'], ['IncomeTax'], destination, source='footer',
                     rule='overseas-model-plus-footer-income-tax')
    def render(value):
        return _number(str(value), 0, locale=locale)

    afooter = [['', 'JUMLAH', number(form[_L3_SCALARS[0]]), number(form[_L3_SCALARS[1]]),
                '', number(form[_L3_SCALARS[2]])]]
    bfooter = [['JUMLAH', render(amounts['TaxBase']), render(amounts['IncomeTax']), ''],
        ['KREDIT PAJAK LUAR NEGERI', '', render(foreign_credit), ''], ['JUMLAH KREDIT PAJAK', '', render(credit), '']]
    tables = []
    for index, (body, footer) in enumerate(((arows, afooter), (brows, bfooter))):
        tables.append({'name': ('L3/overseas', 'L3/domestic')[index], 'headers': list(headers[index]),
            'rows': body + footer, 'footer': footer, 'footer_spans': deepcopy(spans[index]),
            'body_row_count': len(body), 'source_total': len(body), 'complete': True})
    fields = [{'field': field, 'label': caption,
               'value': ('' if form.get(field) is None else number(form.get(field))),
               'group': 'A. PENGHASILAN DARI LUAR NEGERI'}
              for field, caption in zip(_L3_SCALARS[3:5], _L3_CAPTIONS)]
    return {'tables': tables, 'fields': fields, 'provenance': provenance}


def _current_induk_visibility(payload, main, flag, proof):
    """Pinned callback plus an owned enabled form may bind an absent outer flag."""
    current = main.get(flag) if isinstance(main, dict) else None
    if type(current) is not _CorporateNumber or _decimal(current) != 1:
        return False
    if flag not in payload:
        return proof.get('visibility_binding') == 'current-induk-enabled-v1'
    outer = payload[flag]
    return type(outer) is _CorporateNumber and _decimal(outer) == 1


def _active_grid_payload(source):
    """The pinned Data/TotalRecords consumer ignores only this null envelope slot."""
    return (isinstance(source, dict) and set(source) in (
        {'Data', 'TotalRecords'}, {'Data', 'TotalRecords', 'Index'})
        and source.get('Index') is None)


def _unused_grid_index(source, event, form):
    if 'Index' not in source:
        return []
    return [{**_evidence(None, ['Index']), 'response_sequence': event['sequence'],
             'container': ['Payload'], 'rule': 'unused-null-envelope-index',
             'destination': {'table': form, 'metadata': 'Index'}}]


def _apply_l3(binding, section, observed_forms, *, root, payload, record, event,
              reference_packets, auxiliary_packets):
    proof = binding['projection']
    keys = {'kind', 'builds', 'route', 'locale', 'timezone', 'tables', 'references'}
    if (not isinstance(proof, dict)
            or set(proof) - {'standalone_layout', 'visibility_binding'} != keys
            or 'standalone_layout' in proof and proof['standalone_layout'] != 'overseas-controls-v1'
            or 'visibility_binding' in proof and proof['visibility_binding'] != 'current-induk-enabled-v1'
            or proof['kind'] != 'corporate-l3-v1' or proof['builds'] != L3_BUILD_DIGESTS
            or proof['route'] != event['frame_url'] or binding.get('paths') != [[_L3_ROOT]]
            or binding.get('grids', []) or event.get('component_lifetime') is None):
        raise _UnsupportedMetadata('unverified_corporate_l3_semantic_binding')
    fields = record.get('source_fields', {})
    route = ORIGIN + '/returnsheets/id-ID/corporate-income-tax-return/' + '/'.join(
        str(value) for value in (fields.get('TaxpayerAggregateIdentifier'), record['record_id'],
                                fields.get('TaxTypeCode'), fields.get('AggregateIdentifier'))) + '?view=true'
    literal = record.get('meta', {}).get('Model SPT')
    model = ('NORMAL' if literal == 'Normal' else 'AMENDMENT'
             if isinstance(literal, str) and re.fullmatch(r'Amendment [0-9]{3}', literal) else None)
    main = root.get('MainFormData')
    if (proof['route'] != route or record.get('source_status') != 'SPT Dilaporkan'
            or payload.get('ReturnSheetStatusCode') != 'SUBMITTED' or model is None
            or payload.get('ReturnSheetModel') != model or fields.get('ReturnSheetModel') != literal
            or 'Induk' not in [f['name'] for f in observed_forms[:observed_forms.index(binding)]]
            or not _current_induk_visibility(payload, main, 'IsIncomeTaxOverseas', proof)):
        raise _UnsupportedMetadata('unverified_corporate_l3_submitted_lifecycle')
    if 'PreviousFormData' not in payload:
        raise _UnsupportedMetadata('missing_corporate_l3_previous_encoding')
    previous = payload['PreviousFormData']
    if previous is not None:
        if type(previous) is not str:
            raise _UnsupportedMetadata('unsupported_corporate_l3_previous_encoding')
        previous = _corporate_json(previous)
        if previous is not None and not isinstance(previous, dict):
            raise _UnsupportedMetadata('unsupported_corporate_l3_previous_shape')
    tables = proof['tables']
    if not isinstance(tables, list) or len(tables) != 2:
        raise _UnsupportedMetadata('unverified_corporate_l3_table_catalog')
    for index, table in enumerate(tables):
        structure = {'form': 'L3', 'component': _L3_OWNERS[index], 'groups': [_L3_GROUPS[index]]}
        if (not isinstance(table, dict)
                or set(table) != {'component', 'source_structure', 'headers', 'footer_spans'}
                or table['component'] != structure['component'] or table['source_structure'] != structure):
            raise _UnsupportedMetadata('unverified_corporate_l3_grid_owner')
    responses, dependencies = binding.get('responses'), binding.get('dependencies')
    footer_request = {'ReturnSheetRecordId': record['record_id']}
    if (not isinstance(responses, list) or len(responses) != 1
            or not isinstance(responses[0], dict) or set(responses[0]) != {'name', 'endpoint', 'requests'}
            or responses[0]['name'] != 'L3/domestic' or responses[0]['endpoint'] != CORPORATE_L3_GRID_URL
            or dependencies != [{'endpoint': CORPORATE_L3_FOOTER_URL, 'request_json': footer_request}]):
        raise _UnsupportedMetadata('unverified_corporate_l3_auxiliary_binding')
    requests = responses[0]['requests']
    if not isinstance(requests, list) or not 1 <= len(requests) <= 1000:
        raise _UnsupportedMetadata('missing_corporate_l3_page_requests')
    period = fields.get('TaxPeriodCode')
    for request in requests:
        if (not isinstance(request, dict) or set(request) != {'ReturnSheetRecordId', 'PeriodYear',
                'First', 'Rows', 'SortField', 'SortOrder', 'Filters', 'LanguageId'}
                or request['ReturnSheetRecordId'] != record['record_id']
                or request['LanguageId'] != 'id-ID'
                or not isinstance(period, str) or request['PeriodYear'] != period[-4:]
                or type(request['First']) is not int or request['First'] < 0
                or type(request['Rows']) is not int or request['Rows'] != 10
                or request['SortField'] != 'WithholdingSlipsDate'
                or type(request['SortOrder']) is not int or request['SortOrder'] != 1
                or request['Filters'] != []):
            raise _UnsupportedMetadata('unsupported_corporate_l3_page_request')
    requests = sorted(requests, key=lambda value: value['First'])
    page_sources, pages, expected = [], [], set()
    index_provenance = []
    for request in requests:
        key = (CORPORATE_L3_GRID_URL, _corporate_request_key(request))
        expected.add(key)
        packet = auxiliary_packets.get(key)
        source = packet['payload'] if packet is not None else None
        if not _active_grid_payload(source):
            raise _UnsupportedMetadata('unsupported_corporate_l3_page_payload')
        pages.append({'offset': request['First'], 'rows': request['Rows'],
                      'total': _corporate_integer(source['TotalRecords']), 'data': source['Data']})
        page_sources.append(packet['event'])
        index_provenance.extend(_unused_grid_index(source, packet['event'], 'L3'))
    footer_key = (CORPORATE_L3_FOOTER_URL, _corporate_request_key(footer_request))
    expected.add(footer_key)
    if expected != {key for key in auxiliary_packets
                    if key[0] in (CORPORATE_L3_GRID_URL, CORPORATE_L3_FOOTER_URL)}:
        raise _UnsupportedMetadata('incomplete_corporate_l3_auxiliary_packets')
    footer = auxiliary_packets[footer_key]
    references = proof['references']
    if not isinstance(references, list) or len(references) != 4:
        raise _UnsupportedMetadata('missing_corporate_l3_reference_bindings')
    catalogs, sources, labels, seen_kinds = {}, {}, {}, set()
    for ref in references:
        if (not isinstance(ref, dict) or set(ref) != {'endpoint', 'method', 'sequences'}
                or ref['method'] != 'GET' or not isinstance(ref['sequences'], list) or not ref['sequences']):
            raise _UnsupportedMetadata('unsupported_corporate_l3_reference_binding')
        kind = next((kind for kind, url in CORPORATE_L3_REFERENCE_URLS.items() if url == ref['endpoint']), None)
        if kind is None or kind in seen_kinds:
            raise _UnsupportedMetadata('unsupported_corporate_l3_reference_binding')
        seen_kinds.add(kind)
        sequences = ref['sequences']
        if any(type(n) is not int or n <= 0 for n in sequences) or len(set(sequences)) != len(sequences):
            raise JsonSafetyError('Corporate L3 reference sequence is invalid or repeated')
        actual = {n for n, packet in reference_packets.items() if packet['event']['url'] == ref['endpoint']}
        if set(sequences) != actual or any(not reference_packets[n]['successful'] for n in actual):
            raise _UnsupportedMetadata('missing_or_failed_corporate_l3_catalog')
        source = reference_packets[sequences[0]]
        catalogs[kind] = _project_corporate_catalog(source['payload'], kind=kind,
            clock_interval=source['event'].get('clock_interval'))
        sources[kind], labels[kind] = source['event'], catalogs[kind]['lookups']
    if 'corporate_reference_providers' in event:
        catalogs = bind_corporate_reference_catalogs(references, reference_packets,
            kinds=tuple(CORPORATE_L3_REFERENCE_URLS), event=event, builds=proof['builds'])
        sources = {kind: catalog['source'] for kind, catalog in catalogs.items()}
        labels = {kind: catalog['lookups'] for kind, catalog in catalogs.items()}
    result = project_l3(root.get(_L3_ROOT), pages=pages, footer_payload=footer['payload'],
        headers=[t['headers'] for t in tables], footer_spans=[t['footer_spans'] for t in tables],
        tax_type=fields.get('TaxTypeCode'), locale=proof['locale'], timezone_name=proof['timezone'], labels=labels)
    for index, table in enumerate(result['tables']):
        table['source_structure'] = deepcopy(tables[index]['source_structure'])
    section['tables'], section['fields'] = result['tables'], result['fields']
    label_fields = {'CountryCode': 'COUNTRY_CODE', 'PayableCurrency': 'CURRENCY',
                    'IncomeCode': 'FOREIGN_INCOME_TYPE_CIT', 'TaxType': 'TAX_TYPE_BY_OTHER_PARTIES'}
    for entry in tuple(result['provenance']):
        source = (page_sources[entry['page_index']] if entry['source'] == 'grid'
                  else footer['event'] if entry['source'] == 'footer' else event)
        entry.update(response_sequence=source['sequence'],
                     container=['Payload', 'CurrentFormData'] if source is event else ['Payload'])
        kind = label_fields.get(entry['path'][-1]) if entry['rule'] == 'bound-reference-label' else None
        if kind is not None and entry['value'] in catalogs[kind]['selected']:
            result['provenance'].append({**deepcopy(catalogs[kind]['selected'][entry['value']]),
                'response_sequence': sources[kind]['sequence'], 'container': ['Payload'],
                'destination': deepcopy(entry['destination'])})
    for kind, catalog in catalogs.items():
        result['provenance'].extend({**entry, 'response_sequence': sources[kind]['sequence'],
            'container': ['Payload'], 'destination': {'table': 'L3', 'reference': kind}}
            for entry in catalog['provenance'])
    result['provenance'].extend(index_provenance)
    return {'form': 'L3', 'kind': proof['kind'], 'builds': dict(proof['builds']),
            'route': proof['route'], 'values': result['provenance'],
            **({'visibility_binding': proof['visibility_binding']} if 'visibility_binding' in proof else {})}


# Active L11-A consumers in the pinned corporate build; no taxpayer defaults.
_L11A_ROOT = 'L11AFormData'
_L11A_COSTS = ('ResidencyCost', 'HealthServiceCost', 'EducationCost', 'WorshipCost',
               'TransportationCost', 'SportsCost')
_L11A_RECAP = ('LocationAddress', 'NumberOfDecreeOfSpecificAreasDetermination',
    'DateOfDecreeOfSpecificAreasDetermination', 'NumberOfDecreeOfExtensificationOfSpecificAreasDetermination',
    'DateOfDecreeOfExtensificationOfSpecificAreasDetermination', *_L11A_COSTS, 'TotalAmountofCosts')
_L11A_CAPTIONS = ('Alamat Lokasi', 'Nomor Surat Keputusan Penetapan Daerah Tertentu',
    'Tanggal Surat Keputusan Penetapan Daerah Tertentu',
    'Nomor Surat Keputusan Perpanjangan Penetapan Daerah Tertentu',
    'Tanggal Surat Keputusan Perpanjangan Penetapan Daerah Tertentu',
    'Biaya yang dikeluarkan untuk tempat tinggal, termasuk perumahan untuk pegawai dan keluarganya',
    'Biaya yang dikeluarkan untuk pelayanan kesehatan',
    'Biaya yang dikeluarkan untuk pendidikan bagi pegawai dan keluarganya',
    'Biaya yang dikeluarkan untuk peribadatan',
    'Biaya yang dikeluarkan untuk pengangkutan bagi pegawai dan keluarganya',
    'Biaya yang dikeluarkan untuk olahraga bagi pegawai dan keluarganya, tidak termasuk golf, '
    'power boating, pacuan kuda, dan terbang layang', 'Jumlah Biaya yang dikeluarkan')
_L11A_GROUP = ('IV.B RINCIAN PENGGANTIAN ATAU IMBALAN DALAM BENTUK NATURA DAN/ATAU KENIKMATAN '
               'YANG DIBERIKAN BERKENAAN DENGAN PELAKSANAAN PEKERJAAN DI DAERAH TERTENTU')
_L11A_FIELDS = [
    ('Index', 'RecipientIdentityNumber', 'RecipientName', 'RecipientAddress', 'RecipientDate',
     'RecipientFormAndTypeOfPromotionCost', 'RecipientAmountOfPromotionCost', 'RecipientDescription',
     'IncomeTax', 'WithholdingSlipNumber'),
    ('EntertainmentDate', 'EntertainmentPlace', 'EntertainmentAddress', 'EntertainmentType',
     'EntertainmentAmount', 'PartnerName', 'PartnerPosition', 'PartnerCompanyName', 'PartnerTypeOfBusiness', 'Description'),
    ('Index', 'IdentityNumber', 'Name', 'Address', 'DebtCeiling', 'UncollectibleDebt', 'DeductionMethod', 'TypeOfFulfillment'),
    ('TypeOfTangibleAssets', 'YearOfAcquisition', 'AcquisitionValue', 'UpToPreviousYear', 'CurrentYear', 'UpToCurrentYear'),
    ('Index', 'IdentityNumber', 'Name', 'Address', 'AmountBeginning', 'AmountEnd', 'AmountInterestCurrentYear', 'Category')]
_L11A_HEADERS = [
    ['No.', 'NOMOR IDENTITAS PENERIMA', 'NAMA PENERIMA', 'ALAMAT PENERIMA', 'TANGGAL', 'JENIS BIAYA',
     'NILAI (Rp.)', 'KETERANGAN', 'PPh YANG DIPOTONG/DIPUNGUT (Rp.)Rp.)', 'NOMOR BUKTI POTONG'],
    ['TANGGAL PEMBERIAN ENTERTAINMENT', 'TEMPAT PEMBERIAN ENTERTAINMENT', 'ALAMAT PEMBERIAN ENTERTAINMENT',
     'JENIS PEMBERIAN ENTERTAINMENT', 'NILAI PEMBERIAN ENTERTAINMENTRp.)', 'NAMA RELASI USAHA',
     'JABATAN RELASI USAHA', 'NAMA PERUSAHAAN RELASI USAHA', 'JENIS USAHA RELASI USAHA', 'DESKRIPSI'],
    ['No.', 'NOMOR IDENTITAS', 'NAMA DEBITUR', 'ALAMAT', 'PLAFON PIUTANG',
     'PIUTANG YANG NYATA-NYATA TIDAK DAPAT DITAGIH', 'METODE PEMBEBANAN',
     'JENIS DOKUMEN PEMBUKTIAN PEMENUHAN PERSYARATAN'],
    ['NO.', 'JENIS HARTA BERWUJUD', 'TAHUN PEROLEHAN', 'NILAI PEROLEHAN', 'PENYUSUTAN / S.D. TAHUN LALU',
     'PENYUSUTAN / PENYUSUTAN TAHUN INI', 'PENYUSUTAN / S.D. TAHUN INI'],
    ['No.', 'NOMOR IDENTITAS', 'NAMA DEBITUR', 'ALAMAT', 'NILAI KREDIT KURANG LANCAR AWAL TAHUN BUKU',
     'NILAI KREDIT KURANG LANCAR AKHIR TAHUN BUKU', 'JUMLAH BUNGA PADA TAHUN BUKU (AKRUAL)', 'KATEGORI']]
_L11A_LABELS = {'RecipientFormAndTypeOfPromotionCost': 'TYPE_OF_PROMOTION_COST',
    'TypeOfTangibleAssets': 'TANGIBLE_ASSET_INCLUDING_BUILDINGS', 'Category': 'NON_PERFORMING_LOAN_CATEGORY',
    'DeductionMethod': 'DEDUCTION_METHOD', 'TypeOfFulfillment': 'TYPE_OF_FULFILLMENT'}
_L11A_MONEY = {'RecipientAmountOfPromotionCost', 'IncomeTax', 'EntertainmentAmount', 'DebtCeiling',
    'UncollectibleDebt', 'AcquisitionValue', 'UpToPreviousYear', 'CurrentYear', 'UpToCurrentYear',
    'AmountBeginning', 'AmountEnd', 'AmountInterestCurrentYear'}
_L11A_ENDPOINTS = {index: f'l11a-table-{index + 1}-grid' for index in (0, 1, 2, 4)}
_L11A_OWNERS = ('rshshr-citr-l11a-grid1', 'rshshr-citr-l11a-grid2', 'rshshr-citr-l11a-grid3',
                'rsh-citr-l11a-grid4', 'rshshr-citr-l11a-grid5')
_L11A_GROUPS = [
    ['I. DAFTAR NOMINATIF BIAYA PROMOSI DAN PENJUALAN, SERTA PENGGANTIAN ATAU IMBALAN DALAM BENTUK NATURA DAN/ATAU KENIKMATAN'],
    ['II. DAFTAR NOMINATIF BIAYA ENTERTAINMENT'],
    ['III. DAFTAR PIUTANG YANG NYATA-NYATA TIDAK DAPAT DITAGIH'],
    ['IV. RINCIAN BAGI WAJIB PAJAK PEMBERI NATURA DAN/ATAU KENIKMATAN',
     'IV.A DAFTAR SARANA DAN FASILITAS SERTA PENYUSUTANNYA'],
    ['V. DAFTAR DEBITUR NON-PERFORMING LOAN']]


def _apply_l11a(binding, section, observed_forms, *, root, payload, record, event,
                 reference_packets, auxiliary_packets):
    proof = binding['projection']
    if (not isinstance(proof, dict)
            or set(proof) - {'visibility_binding'} != {'kind', 'builds', 'route', 'locale', 'timezone', 'tables', 'references'}
            or 'visibility_binding' in proof and proof['visibility_binding'] != 'current-induk-enabled-v1'
            or proof['kind'] != 'corporate-l11a-v1' or proof['builds'] != L11A_BUILD_DIGESTS
            or proof['route'] != event['frame_url'] or binding.get('paths') != [[_L11A_ROOT]]
            or binding.get('grids', []) or binding.get('dependencies', [])
            or event.get('component_lifetime') is None):
        raise _UnsupportedMetadata('unverified_corporate_l11a_semantic_binding')
    fields = record.get('source_fields', {})
    route = ORIGIN + '/returnsheets/id-ID/corporate-income-tax-return/' + '/'.join(
        str(value) for value in (fields.get('TaxpayerAggregateIdentifier'), record['record_id'],
                                fields.get('TaxTypeCode'), fields.get('AggregateIdentifier'))) + '?view=true'
    literal = record.get('meta', {}).get('Model SPT')
    model = ('NORMAL' if literal == 'Normal' else 'AMENDMENT'
             if isinstance(literal, str) and re.fullmatch(r'Amendment [0-9]{3}', literal) else None)
    main = root.get('MainFormData')
    if (proof['route'] != route or record.get('source_status') != 'SPT Dilaporkan'
            or payload.get('ReturnSheetStatusCode') != 'SUBMITTED' or model is None
            or payload.get('ReturnSheetModel') != model or fields.get('ReturnSheetModel') != literal
            or 'Induk' not in [f['name'] for f in observed_forms[:observed_forms.index(binding)]]
            or not _current_induk_visibility(payload, main, 'IsDeclareEntertainmentExpense', proof)):
        raise _UnsupportedMetadata('unverified_corporate_l11a_submitted_lifecycle')
    if 'PreviousFormData' not in payload:
        raise _UnsupportedMetadata('missing_corporate_l11a_previous_encoding')
    previous = payload['PreviousFormData']
    if previous is not None:
        if type(previous) is not str:
            raise _UnsupportedMetadata('unsupported_corporate_l11a_previous_encoding')
        previous = _corporate_json(previous)
        if previous is not None and not isinstance(previous, dict):
            raise _UnsupportedMetadata('unsupported_corporate_l11a_previous_shape')
    previous_form = previous.get(_L11A_ROOT) if previous is not None else None
    tables = proof['tables']
    if not isinstance(tables, list) or len(tables) != 5:
        raise _UnsupportedMetadata('unverified_corporate_l11a_table_catalog')
    for index, table in enumerate(tables):
        structure = {'form': 'L11-A', 'component': _L11A_OWNERS[index], 'groups': _L11A_GROUPS[index]}
        if (not isinstance(table, dict)
                or set(table) != {'component', 'source_structure', 'headers', 'footer_spans'}
                or table['component'] != structure['component'] or table['source_structure'] != structure):
            raise _UnsupportedMetadata('unverified_corporate_l11a_grid_owner')
    responses = binding.get('responses')
    if not isinstance(responses, list) or len(responses) != 4:
        raise _UnsupportedMetadata('unverified_corporate_l11a_auxiliary_binding')
    page_sources, pages, expected = {}, {}, set()
    index_provenance = []
    for response in responses:
        if (not isinstance(response, dict) or set(response) != {'name', 'endpoint', 'requests'}
                or response['endpoint'] not in CORPORATE_L11A_GRID_URLS):
            raise _UnsupportedMetadata('unverified_corporate_l11a_auxiliary_binding')
        endpoint = response['endpoint'].rsplit('/', 1)[-1]
        if response['name'] != 'L11-A/' + endpoint or endpoint in pages:
            raise _UnsupportedMetadata('unverified_corporate_l11a_auxiliary_binding')
        requests = response['requests']
        if not isinstance(requests, list) or not 1 <= len(requests) <= 1000:
            raise _UnsupportedMetadata('missing_corporate_l11a_page_requests')
        for request in requests:
            if (not isinstance(request, dict) or set(request) != {'ReturnSheetRecordId',
                    'First', 'Rows', 'SortField', 'SortOrder', 'Filters', 'LanguageId'}
                    or request['ReturnSheetRecordId'] != record['record_id']
                    or request['LanguageId'] != 'id-ID' or type(request['First']) is not int
                    or request['First'] < 0 or type(request['Rows']) is not int or request['Rows'] != 10
                    or request['SortField'] != '' or type(request['SortOrder']) is not int
                    or request['SortOrder'] != 1 or request['Filters'] != []):
                raise _UnsupportedMetadata('unsupported_corporate_l11a_page_request')
        pages[endpoint], page_sources[endpoint] = [], []
        for request in sorted(requests, key=lambda value: value['First']):
            key = (response['endpoint'], _corporate_request_key(request))
            expected.add(key)
            packet = auxiliary_packets.get(key)
            source = packet['payload'] if packet is not None else None
            if not _active_grid_payload(source):
                raise _UnsupportedMetadata('unsupported_corporate_l11a_page_payload')
            pages[endpoint].append({'offset': request['First'], 'rows': request['Rows'],
                'total': _corporate_integer(source['TotalRecords']), 'data': source['Data']})
            page_sources[endpoint].append(packet['event'])
            index_provenance.extend(_unused_grid_index(source, packet['event'], 'L11-A'))
    if expected != {key for key in auxiliary_packets if key[0] in CORPORATE_L11A_GRID_URLS}:
        raise _UnsupportedMetadata('incomplete_corporate_l11a_auxiliary_packets')
    references = proof['references']
    if not isinstance(references, list) or not 4 <= len(references) <= 6:
        raise _UnsupportedMetadata('missing_corporate_l11a_reference_bindings')
    catalogs, sources = {}, {}
    contributors = []
    urls = set()
    for ref in references:
        if (not isinstance(ref, dict) or set(ref) != {'endpoint', 'method', 'sequences'}
                or type(ref['endpoint']) is not str or ref['endpoint'] in urls
                or ref['method'] != 'GET' or not isinstance(ref['sequences'], list) or not ref['sequences']):
            raise _UnsupportedMetadata('unsupported_corporate_l11a_reference_binding')
        kinds = CORPORATE_REFERENCE_REQUESTS.get(ref['endpoint'])
        if kinds is None or any(kind not in CORPORATE_L11A_REFERENCE_URLS for kind in kinds):
            raise _UnsupportedMetadata('unsupported_corporate_l11a_reference_binding')
        urls.add(ref['endpoint'])
        sequences = ref['sequences']
        if any(type(n) is not int or n <= 0 for n in sequences) or len(set(sequences)) != len(sequences):
            raise JsonSafetyError('Corporate L11-A reference sequence is invalid or repeated')
        actual = {n for n, packet in reference_packets.items() if packet['event']['url'] == ref['endpoint']}
        if set(sequences) != actual or any(not reference_packets[n]['successful'] for n in actual):
            raise _UnsupportedMetadata('missing_or_failed_corporate_l11a_catalog')
        source = reference_packets[min(sequences)]
        for kind in kinds:
            catalog = _project_corporate_catalog(source['payload'], kind=kind, requested_types=kinds,
                clock_interval=source['event'].get('clock_interval'))
            if kind in catalogs and catalog['lookups'] != catalogs[kind]['lookups']:
                raise JsonSafetyError('Corporate L11-A catalog selection changed across admitted transports')
            contributors.append((kind, catalog, source['event']))
            if kind not in sources or source['event']['sequence'] < sources[kind]['sequence']:
                catalogs[kind], sources[kind] = catalog, source['event']
    actual_urls = {packet['event']['url'] for packet in reference_packets.values()
                  if all(kind in CORPORATE_L11A_REFERENCE_URLS
                         for kind in CORPORATE_REFERENCE_REQUESTS[packet['event']['url']])}
    if urls != actual_urls:
        raise _UnsupportedMetadata('unbound_corporate_l11a_catalog')
    if set(catalogs) != set(CORPORATE_L11A_REFERENCE_URLS):
        raise _UnsupportedMetadata('missing_corporate_l11a_catalogs')
    result = project_l11a(root.get(_L11A_ROOT), previous=previous_form, pages=pages,
        headers=[t['headers'] for t in tables], footer_spans=[t['footer_spans'] for t in tables],
        tax_type=fields.get('TaxTypeCode'), locale=proof['locale'], timezone_name=proof['timezone'],
        labels={kind: catalog['lookups'] for kind, catalog in catalogs.items()})
    for index, table in enumerate(result['tables']):
        table['source_structure'] = deepcopy(tables[index]['source_structure'])
    section['tables'], section['fields'] = result['tables'], result['fields']
    for entry in tuple(result['provenance']):
        source = (page_sources[entry['endpoint']][entry['page_index']] if entry['source'] == 'grid' else event)
        entry.update(response_sequence=source['sequence'],
                     container=['Payload', 'CurrentFormData'] if source is event else ['Payload'])
        kind = _L11A_LABELS.get(entry['path'][-1]) if entry['rule'] == 'bound-reference-description' else None
        if kind is not None and entry['value'] in catalogs[kind]['selected']:
            result['provenance'].append({**deepcopy(catalogs[kind]['selected'][entry['value']]),
                'response_sequence': sources[kind]['sequence'], 'container': ['Payload'],
                'destination': deepcopy(entry['destination'])})
    for kind, catalog, source in contributors:
        result['provenance'].extend({**entry, 'response_sequence': source['sequence'],
            'container': ['Payload'], 'destination': {'table': 'L11-A', 'reference': kind}}
            for entry in catalog['provenance'])
    result['provenance'].extend(index_provenance)
    return {'form': 'L11-A', 'kind': proof['kind'], 'builds': dict(proof['builds']),
            'route': proof['route'], 'values': result['provenance'],
            **({'visibility_binding': proof['visibility_binding']} if 'visibility_binding' in proof else {})}


def _l11a_integer(value, *, nullish=False):
    if value is None and nullish:
        return 0
    if type(value) is not _CorporateNumber:
        raise _UnsupportedMetadata('unsupported_corporate_l11a_number_type')
    number = _decimal(value)
    if abs(number) > _MAX_INTEGER or number != number.to_integral_value():
        raise _UnsupportedMetadata('unsupported_corporate_l11a_number_precision')
    return int(number)


def project_l11a(form, *, previous, pages, headers, footer_spans, tax_type, locale,
                  timezone_name, labels):
    """Pure current-only consumer; no native observation or transport admission."""
    if (previous is not None or tax_type != 'ICT_RCIT' or locale != 'id-ID'
            or timezone_name != 'Asia/Jakarta' or headers != _L11A_HEADERS
            or footer_spans != [[], [], [], [], []] or not isinstance(labels, dict)
            or set(labels) != set(_L11A_LABELS.values())
            or any(not isinstance(value, dict) for value in labels.values())):
        raise _UnsupportedMetadata('unverified_corporate_l11a_current_structure')
    if (not isinstance(form, dict) or set(form) != {'Facilities', 'Recapitulation'}
            or not isinstance(form['Recapitulation'], dict)
            or set(form['Recapitulation']) not in (set(_L11A_RECAP),
                                                   set(_L11A_RECAP) - {'TotalAmountofCosts'})
            or not isinstance(pages, dict) or set(pages) != set(_L11A_ENDPOINTS.values())):
        raise _UnsupportedMetadata('unsupported_corporate_l11a_source_shape')
    absent_total = 'TotalAmountofCosts' not in form['Recapitulation']
    facilities = [] if form['Facilities'] is None else form['Facilities']
    if not isinstance(facilities, list) or len(facilities) > 10000:
        raise _UnsupportedMetadata('unsupported_corporate_l11a_facilities')
    if absent_total and (form['Facilities'] is not None
                         or any(form['Recapitulation'].get(cost) is not None for cost in _L11A_COSTS)):
        # The live build omits the recap total only for a section with no
        # facilities and no cost amounts; any amount still demands the key.
        raise _UnsupportedMetadata('unsupported_corporate_l11a_missing_total')
    provenance = []

    def evidence(value, path, destination, *, endpoint=None, page_index=None, rule='literal-source'):
        entry = _evidence(value, path)
        entry.update(source='current' if endpoint is None else 'grid', destination=destination, rule=rule)
        if endpoint is not None:
            entry.update(endpoint=endpoint, page_index=page_index)
        provenance.append(entry)

    def text(value):
        if value is None:
            return ''
        if type(value) is not str:
            raise _UnsupportedMetadata('unsupported_corporate_l11a_text')
        return value

    def number(value, fraction=0):
        if value is None:
            return ''
        _l11a_integer(value)
        return _number(value, fraction, locale=locale)

    def render(value, key):
        if key in _L11A_LABELS:
            choices = labels[_L11A_LABELS[key]]
            if (type(value) is not str or not value or value not in choices
                    or type(choices[value]) is not str or not choices[value].strip()):
                raise _UnsupportedMetadata('unbound_corporate_l11a_description')
            return choices[value], 'bound-reference-description'
        if key in _L11A_MONEY:
            return number(value), 'source-number-id/null-blank'
        if key in ('RecipientDate', 'EntertainmentDate'):
            # Live L11-A row dates are jakarta midnight with an explicit +07:00
            # offset, the same shape already admitted for L3 withholding dates.
            return _l3_date(value, domestic_jakarta_midnight=True), 'validated-iso/jakarta-dd-MM-yyyy'
        if key == 'PartnerName':
            if type(value) is _CorporateNumber:
                return number(value, 2), 'source-number-id-1.2-2'
            if type(value) is str and re.match(r'^(0[0-9]|1[0-9]|2[0-3]):[0-5][0-9]', value):
                raise _UnsupportedMetadata('unproved_corporate_l11a_time_like_name')
        return text(value), 'literal-string/null-blank'

    tables = []
    for table_index, keys in enumerate(_L11A_FIELDS):
        body, endpoint = [], _L11A_ENDPOINTS.get(table_index)
        if endpoint is None:
            source_pages = [(None, facilities)]
        else:
            declarations = pages[endpoint]
            if not isinstance(declarations, list) or not 1 <= len(declarations) <= 1000:
                raise _UnsupportedMetadata('missing_corporate_l11a_pages')
            source_pages, cursor, total, capacity = [], 0, None, None
            for page_index, page in enumerate(declarations):
                if (not isinstance(page, dict) or set(page) != {'offset', 'rows', 'total', 'data'}
                        or any(type(page[key]) is not int for key in ('offset', 'rows', 'total'))
                        or page['offset'] != cursor or page['rows'] not in (10, 25, 50)
                        or not 0 <= page['total'] <= 100000 or not isinstance(page['data'], list)):
                    raise _UnsupportedMetadata('unsupported_corporate_l11a_page')
                if total is None:
                    total, capacity = page['total'], page['rows']
                if (page['total'] != total or page['rows'] != capacity or page_index and cursor >= total
                        or len(page['data']) != min(capacity, total - cursor)):
                    raise _UnsupportedMetadata('incomplete_corporate_l11a_pages')
                source_pages.append((page_index, page['data']))
                cursor += len(page['data'])
            if cursor != total:
                raise _UnsupportedMetadata('incomplete_corporate_l11a_pages')
        for page_index, values in source_pages:
            for row_index, row in enumerate(values):
                expected = set(keys) | ({'RecordId'} if endpoint is not None else set())
                if not isinstance(row, dict):
                    raise _UnsupportedMetadata('unsupported_corporate_l11a_row')
                extras = set(row) - expected
                # Live grid rows carry two non-column metadata fields: Action is
                # always null and Index is the numeric row ordinal.
                if (not expected <= set(row) or extras - {'Action', 'Index'}
                        or ('Action' in extras and row['Action'] is not None)
                        or ('Index' in extras
                            and type(row['Index']) not in (int, _CorporateNumber))):
                    raise _UnsupportedMetadata('unsupported_corporate_l11a_row')
                path = (['Data', row_index] if endpoint is not None else [_L11A_ROOT, 'Facilities', row_index])
                if endpoint is not None:
                    if type(row['RecordId']) is not str or not row['RecordId']:
                        raise _UnsupportedMetadata('unsupported_corporate_l11a_row_id')
                    evidence(row['RecordId'], [*path, 'RecordId'], {'table': f'L11-A/grid{table_index + 1}',
                        'row': len(body), 'key': 'RecordId'}, endpoint=endpoint, page_index=page_index)
                rendered = [] if endpoint is not None else [str(row_index + 1)]
                for column, key in enumerate(keys, 0 if endpoint is not None else 1):
                    value, rule = render(row[key], key)
                    rendered.append(value)
                    evidence(row[key], [*path, key], {'table': f'L11-A/grid{table_index + 1}',
                        'row': len(body), 'column': column}, endpoint=endpoint, page_index=page_index, rule=rule)
                body.append(rendered)
        tables.append({'name': f'L11-A/grid{table_index + 1}', 'headers': list(headers[table_index]),
            'rows': body, 'footer': [], 'footer_spans': [], 'body_row_count': len(body),
            'source_total': len(body), 'complete': True})

    recap, total = form['Recapitulation'], 0
    for key in _L11A_COSTS:
        operand = _l11a_integer(recap[key], nullish=True)
        # PrimeNG keeps a signed-zero cost control distinct from Angular's
        # normalized number display. Refuse this unproved presentation branch.
        if recap[key] is not None:
            original = _decimal(recap[key])
            if original.is_zero() and original.is_signed():
                raise _UnsupportedMetadata('unproved_corporate_l11a_signed_zero_cost')
        total += operand
        if abs(total) > _MAX_INTEGER:
            raise _UnsupportedMetadata('unsafe_corporate_l11a_ordered_cost_sum')
    if not absent_total and _l11a_integer(recap['TotalAmountofCosts']) != max(0, total):
        raise _UnsupportedMetadata('unreconciled_corporate_l11a_total_costs')
    fields = []
    for key, caption in zip(_L11A_RECAP, _L11A_CAPTIONS):
        value = recap.get(key)
        if key in _L11A_COSTS or key == 'TotalAmountofCosts':
            display, rule = number(value), 'input-number-id/null-blank'
            if key == 'TotalAmountofCosts':
                rule = ('absent-inert-zero-total' if absent_total
                        else 'reconciled-six-cost-ordered-sum/final-nonnegative-clamp')
        elif key.startswith('DateOfDecree'):
            if type(value) is not str or not value:
                raise _UnsupportedMetadata('unsupported_corporate_l11a_decree_date')
            decree = re.fullmatch(r'([0-9]{4})-([0-9]{2})-([0-9]{2})T07:00:00\+07:00', value)
            if decree:
                # Live decree dates are the literal date at 07:00+07:00 (Jakarta
                # midnight in UTC terms); the calendar date is unambiguous.
                display, rule = (f'{decree.group(3)}-{decree.group(2)}-{decree.group(1)}',
                                 'literal-date-jakarta-0700-offset')
            else:
                display, rule = _l3_date(value), 'validated-new-Date/jakarta-dd-MM-yyyy'
        else:
            display, rule = text(value), 'literal-input/null-blank'
        fields.append({'group': _L11A_GROUP, 'field': key, 'label': caption, 'value': display})
        evidence(value, [_L11A_ROOT, 'Recapitulation', key], {'field': key}, rule=rule)
    return {'tables': tables, 'fields': fields, 'provenance': provenance}
