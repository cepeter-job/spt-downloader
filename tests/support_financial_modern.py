"""Invented document-grid DOM matching reviewed structure, never portal data."""

CURRENT_LABEL = 'a. 1. Laporan Keuangan/Laporan Keuangan yang Telah Diaudit*'
CURRENT_CAPTIONS = ('NO.', 'FILENAME', 'TINDAKAN')
RENAMED_CAPTIONS = ('NO.', 'NAMA DOKUMEN', 'TINDAKAN')


def modern_grid(key, label, captions=CURRENT_CAPTIONS):
    return f'''<section id="{key}-section"><label id="{key}-label">{label}</label>
    <ui-grid-documents id="{key}-grid"><nui-grid><p-table>
    <table id="{key}-table" aria-labelledby="{key}-label">
    <thead><tr><th>{captions[0]}</th><th>{captions[1]}</th><th>{captions[2]}</th></tr>
    <tr class="ng-filterrow"><th></th><th><nui-grid-filter-control>
    <input type="text" value="SYNTHETIC_FILTER_SENTINEL">
    </nui-grid-filter-control></th><th></th></tr></thead>
    <tbody><tr><td>1</td><td>synthetic-{key}.pdf</td><td>
    <button id="{key}-download" type="button" aria-label="Unduh"
    class="ng-actbtn p-button-secondary"><i class="pi pi-download"></i></button>
    </td></tr></tbody></table></p-table></nui-grid></ui-grid-documents></section>'''


def modern_content(captions=CURRENT_CAPTIONS):
    # post_routed/routed supply the sole .main-content wrapper. Keep three
    # equivalent grids: only the explicit financial label grants POST scope.
    return '''<style>rshshr-citr-main-form,ui-grid-documents,nui-grid,p-table,
    nui-grid-filter-control {display:block}</style>
    <div class="p-tabview"><ul class="p-tabview-nav"><li>
    <a role="tab" aria-selected="true" aria-controls="synthetic-induk-panel">Induk</a>
    </li></ul><div id="synthetic-induk-panel" class="p-tabview-panel" role="tabpanel">
    <rshshr-citr-main-form>''' + modern_grid('financial', CURRENT_LABEL, captions) + modern_grid(
        'neighbor-a', 'SYNTHETIC_OTHER_DOCUMENTS_A', captions) + modern_grid(
        'neighbor-b', 'SYNTHETIC_OTHER_DOCUMENTS_B', captions) + '''</rshshr-citr-main-form></div></div>'''
