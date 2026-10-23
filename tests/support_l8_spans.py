"""Invented values in the inspected corporate L8 cell/owner shape."""
GROUP = ('PERHITUNGAN FASILITAS PENGURANGAN TARIF PPh BAGI WAJIB PAJAK BADAN '
         'DALAM NEGERI BERDASARKAN PASAL 31E AYAT (1) UNDANG-UNDANG PPh')
HEADERS = ['NO.', 'DESKRIPSI', 'AMOUNT (Rupiah)']
ROWS = [
    ['1.', 'SYNTHETIC TURNOVER'], ['', 'SYNTHETIC TURNOVER', 'Rp. | 8.000'],
    ['2.', 'SYNTHETIC TAXABLE'], ['', 'SYNTHETIC GRANTED', '0'],
    ['', 'SYNTHETIC NOT GRANTED', '200'], ['3.', 'SYNTHETIC TAX'],
    ['', 'SYNTHETIC TAX GRANTED', '0'], ['', 'SYNTHETIC TAX OTHER', '44'],
]
SPANS = [[1, 2], [1, 1, 1], [1, 2], [1, 1, 1], [1, 1, 1], [1, 2], [1, 1, 1], [1, 1, 1]]
FOOTER = [['', 'JUMLAH PPh Terutang', '44']]


def source():
    from copy import deepcopy
    return {'name': 'SYNTHETIC L8', 'group': GROUP, 'headers': list(HEADERS),
            'rows': deepcopy(ROWS + FOOTER), 'footer': deepcopy(FOOTER),
            'footer_spans': [[1, 1, 1]], 'body_row_count': 8, 'complete': True, 'pages': 1,
            'body_spans': deepcopy(SPANS), 'body_rowspans': [[1] * len(row) for row in ROWS],
            'source_structure': {'form': 'L8', 'component': 'rsh-citr-l8-form-grid1', 'groups': [GROUP]}}


def html(*, component='rsh-citr-l8-form-grid1', form='rshshr-citr-l8-form'):
    from html import escape
    body = ''.join('<tr>' + ''.join(f'<td colspan="{span}">{escape(value)}</td>'
        for value, span in zip(row, spans)) + '</tr>' for row, spans in zip(ROWS, SPANS))
    footer = '<tfoot><tr><td></td><td>JUMLAH PPh Terutang</td><td>44</td></tr></tfoot>'
    return ('<main class="main-content"><div class="p-tabview-panel"><' + form + '>'
        '<p-accordiontab><div class="p-accordion-header"><span class="p-accordion-header-text">' + GROUP + '</span></div>'
        '<div class="p-accordion-content"><' + component + '><p-table><table>'
        '<thead><tr>' + ''.join('<th>' + h + '</th>' for h in HEADERS) + '</tr></thead>'
        '<tbody>' + body + '</tbody>' + footer + '</table></p-table></' + component + '></div></p-accordiontab>'
        '</' + form + '></div></main>')
