"""Runner-only synthetic DOM regressions; execute the real attachment scanner."""
from copy import deepcopy

import pytest

from support_financial_browser import browser as browser, routed as routed
from support_financial_browser import DETAIL, PDF_URL, RECORD, attachments, downloaded
from support_financial_modern import CURRENT_LABEL, modern_content
from support_financial_post import post_routed as post_routed


def scan(page):
    return page.evaluate(attachments()._SCAN)


def mutate_financial(page, expression):
    page.evaluate('''() => {
        const table = document.querySelector('#financial-table');
        const grid = document.querySelector('#financial-grid');
        const button = document.querySelector('#financial-download');
        const header = table.tHead;
        const filter = header.rows[1];
        const row = table.tBodies[0].rows[0];
        const label = document.querySelector('#financial-label');
        // Fixed test-owned fixture code, never portal or user-provided text.
    ''' + expression + '\n}')


def assert_no_action(page, wire):
    assert scan(page)['controls'] == []
    assert page.evaluate('window.syntheticClicks') == 0
    assert wire == []


def test_modern_headers_are_observed_before_action_caption_admission(post_routed):
    page, wire = post_routed(content=modern_content())
    page.evaluate('''() => document.querySelectorAll('button').forEach(button =>
        button.setAttribute('aria-label', 'SYNTHETIC_UNSUPPORTED_ACTION'))''')

    observed = scan(page)

    # Expected first hosted RED on the old scanner: its zero-table sentinel
    # cannot satisfy this assertion. This must not depend on action admission.
    assert observed['observations'] and all(
        item['attachment_tables'] == 3 for item in observed['observations'])
    buttons = [item for item in observed['observations'] if item['control_kind'] == 'button']
    assert len(buttons) == 3
    assert sorted(item['binding_state'] for item in buttons) == ['bound', 'unbound', 'unbound']
    assert observed['controls'] == []
    assert page.evaluate('window.syntheticClicks') == 0 and wire == []


def test_modern_aria_only_action_is_scoped_to_one_financial_row(post_routed):
    page, wire = post_routed(content=modern_content())
    # Throwing getters catch accidental business/filter-value reads. Structural
    # input counts/type are permitted; their values are not discovery evidence.
    page.evaluate('''() => document.querySelectorAll('input[type=text]').forEach(input =>
        Object.defineProperty(input, 'value', {get() {throw new Error('SYNTHETIC_VALUE_READ');}}))''')

    controls = scan(page)['controls']

    assert len(controls) == 1
    control = controls[0]
    assert control['method'] == 'POST' and control['label'] == CURRENT_LABEL
    assert control['filename'] == 'synthetic-financial.pdf'
    assert control['document_url'] == DETAIL
    assert control['identity'] and control['button_index'] == 0
    assert set(control) == {'label', 'method', 'document_url', 'button_index',
                            'identity', 'row_text', 'filename'}
    assert scan(page)['controls'] == controls  # Same actual WeakMap node.
    assert page.evaluate('window.syntheticClicks') == 0 and wire == []


@pytest.mark.parametrize('expression', [
    "header.rows[0].cells[0].textContent = 'NUMBER'",
    "header.rows[0].insertBefore(header.rows[0].cells[1], header.rows[0].cells[0])",
    "header.rows[0].cells[1].textContent = 'NO.'",
    "header.rows[0].append(document.createElement('th'))",
    "header.rows[0].cells[0].colSpan = 2",
    "header.rows[0].cells[1].rowSpan = 2",
    "header.rows[0].cells[1].hidden = true",
    "header.append(filter.cloneNode(true))",
    "filter.classList.remove('ng-filterrow')",
    "filter.cells[0].textContent = 'SYNTHETIC_EXTRA_CAPTION'",
    "filter.cells[1].colSpan = 2",
    "filter.cells[1].rowSpan = 2",
    "filter.hidden = true",
    "filter.cells[1].style.visibility = 'hidden'",
    "filter.cells[0].append(filter.querySelector('nui-grid-filter-control'))",
    "filter.querySelector('nui-grid-filter-control').remove()",
    "filter.cells[1].append(filter.querySelector('nui-grid-filter-control').cloneNode(true))",
    "filter.querySelector('input').remove()",
    "filter.querySelector('input').type = 'checkbox'",
    "filter.cells[1].append(document.createElement('input'))",
    "filter.cells[2].append(document.createElement('button'))",
    "header.rows[0].cells[1].append(document.createElement('input'))",
    "header.rows[0].cells[1].append(document.createElement('table'))",
], ids=[
    'wrong-caption', 'reordered-captions', 'duplicate-caption', 'extra-caption-cell',
    'caption-colspan', 'caption-rowspan', 'hidden-caption-cell', 'extra-header-row',
    'unknown-second-row', 'filter-caption', 'filter-colspan', 'filter-rowspan',
    'hidden-filter-row', 'hidden-filter-cell', 'filter-in-number-cell', 'missing-filter-host',
    'duplicate-filter-host', 'missing-filter-input', 'nontext-filter', 'extra-filter-input',
    'filter-action', 'control-in-caption-row', 'nested-header-table',
])
def test_unreviewed_modern_headers_never_admit_actions(post_routed, expression):
    page, wire = post_routed(content=modern_content())
    mutate_financial(page, expression)
    assert_no_action(page, wire)


@pytest.mark.parametrize('expression', [
    "grid.closest('rshshr-citr-main-form').outerHTML = grid.closest('rshshr-citr-main-form').outerHTML.replaceAll('rshshr-citr-main-form', 'synthetic-foreign-form')",
    "grid.closest('rshshr-citr-main-form').hidden = true",
    "const second = document.createElement('rshshr-citr-main-form'); second.textContent = 'SYNTHETIC_COMPETING_FORM'; document.querySelector('.main-content').append(second)",
    "document.querySelector('.p-tabview-panel').append(grid.closest('section'))",
    "grid.querySelector('nui-grid').replaceWith(grid.querySelector('p-table'))",
    "grid.querySelector('p-table').replaceWith(table)",
    "grid.querySelector('nui-grid').append(document.createElement('p-table'))",
    "grid.append(document.createElement('nui-grid'))",
    "const nested = document.createElement('nui-grid'); grid.querySelector('nui-grid').append(nested); nested.append(grid.querySelector('p-table'))",
    "const nested = document.createElement('ui-grid-documents'); grid.append(nested); nested.append(grid.querySelector('nui-grid'))",
    "grid.append(table.cloneNode(true))",
    "grid.hidden = true",
    "table.style.visibility = 'hidden'",
    "label.hidden = true",
    "label.textContent = 'SYNTHETIC_OTHER_DOCUMENTS'",
    "label.remove()",
    "label.after(label.cloneNode(true))",
    "table.setAttribute('aria-labelledby', 'financial-label neighbor-a-label')",
    "table.setAttribute('aria-labelledby', 'neighbor-a-label')",
    "const caption = table.createCaption(); caption.textContent = 'SYNTHETIC_OTHER_DOCUMENTS'",
    "document.querySelector('#neighbor-a-section').append(label)",
], ids=[
    'foreign-form', 'hidden-form', 'duplicate-form', 'outside-form', 'missing-nui-grid',
    'missing-p-table', 'competing-p-table', 'competing-nui-grid', 'nested-nui-grid',
    'nested-document-grid', 'competing-actual-table', 'hidden-grid', 'hidden-table',
    'hidden-label', 'foreign-label', 'missing-label', 'duplicate-label-id',
    'multiple-label-references', 'foreign-label-reference', 'contradictory-caption',
    'foreign-label-owner',
])
def test_modern_discovery_requires_unambiguous_owned_financial_grid(post_routed, expression):
    page, wire = post_routed(content=modern_content())
    mutate_financial(page, expression)
    assert_no_action(page, wire)


@pytest.mark.parametrize('expression', [
    "button.setAttribute('title', 'Generate')",
    "button.setAttribute('title', 'Unduh')",
    "button.setAttribute('title', '')",
    "button.removeAttribute('aria-label')",
    "button.setAttribute('aria-label', 'Download')",
    "button.setAttribute('aria-label', ' Unduh ')",
    "button.classList.remove('ng-actbtn')",
    "button.classList.remove('p-button-secondary')",
    "button.removeAttribute('type')",
    "button.type = 'submit'",
    "button.disabled = true",
    "button.setAttribute('aria-disabled', 'true')",
    "button.hidden = true",
    "button.setAttribute('onclick', 'void 0')",
    "button.setAttribute('onmousedown', 'void 0')",
    "button.setAttribute('onpointerdown', 'void 0')",
    "button.setAttribute('href', '/synthetic-generation')",
    "button.append(button.querySelector('i').cloneNode(true))",
    "button.querySelector('i').outerHTML = '<span class=\"pi pi-download\"></span>'",
    "row.cells[2].append(button.cloneNode(true))",
    "row.cells[2].append(document.createElement('input'))",
    "row.cells[1].append(button)",
    "row.cells[0].textContent = 'one'",
    "row.cells[1].textContent = 'synthetic-financial.txt'",
    "row.cells[0].colSpan = 2",
    "row.cells[1].rowSpan = 2",
    "row.cells[1].hidden = true",
    "row.hidden = true",
    "const nested = document.createElement('table'); row.cells[2].append(nested); const child = nested.insertRow(); child.insertCell().append(button)",
], ids=[
    'contradictory-title', 'unreviewed-title-aria-hybrid', 'present-empty-title',
    'missing-aria', 'unreviewed-aria', 'nonliteral-aria', 'missing-action-class',
    'missing-secondary-class', 'missing-button-type', 'submit-action', 'disabled',
    'aria-disabled', 'hidden-button', 'inline-click', 'inline-mousedown',
    'inline-pointerdown', 'button-href', 'duplicate-download-icon', 'legacy-icon-tag',
    'extra-body-action', 'body-input', 'action-in-filename', 'nonliteral-row-number',
    'nonpdf-filename', 'body-colspan', 'body-rowspan', 'hidden-body-cell',
    'hidden-body-row', 'nested-body-table',
])
def test_modern_action_and_body_shape_are_not_general_download_permission(post_routed, expression):
    page, wire = post_routed(content=modern_content())
    mutate_financial(page, expression)
    assert_no_action(page, wire)


@pytest.mark.parametrize('expression', [
    "filter.remove()",
    "filter.remove(); button.setAttribute('title', 'Unduh')",
    "button.setAttribute('title', 'Unduh'); button.removeAttribute('aria-label'); button.classList.remove('ng-actbtn')",
], ids=['single-header-aria-only', 'single-header-title-aria', 'modern-header-legacy-action'])
def test_unreviewed_header_action_hybrids_do_not_cross_admission_branches(post_routed, expression):
    page, wire = post_routed(content=modern_content())
    mutate_financial(page, expression)
    assert_no_action(page, wire)


def test_legacy_exact_title_does_not_override_contradictory_aria(post_routed):
    page, wire = post_routed()
    page.evaluate('''() => document.querySelector('#financial-download').setAttribute('aria-label', 'Generate')''')
    assert_no_action(page, wire)


def test_modern_table_binding_does_not_expand_filename_get_links(routed, tmp_path):
    page, requests = routed(modern_content())
    page.evaluate('''url => document.querySelectorAll('tbody tr').forEach(row => {
        row.cells[2].replaceChildren();
        const anchor = document.createElement('a'); anchor.href = url;
        anchor.textContent = row.cells[1].textContent; row.cells[1].replaceChildren(anchor);
    })''', PDF_URL)

    assert scan(page)['controls'] == []
    result = attachments().download_financial_attachments(page, deepcopy(RECORD), tmp_path)

    assert result and all(item['status'] == 'PARTIAL' for item in result)
    assert all(not item['relative_path'] for item in result)
    assert requests == [('GET', DETAIL)]
    assert not list(tmp_path.rglob('*.pdf'))


def test_direct_approved_get_link_keeps_its_existing_scope(routed, tmp_path):
    page, requests = routed(modern_content() + f'<a href="{PDF_URL}">{CURRENT_LABEL}</a>')
    # The unrelated grids are unsupported; only the existing direct-caption
    # anchor is admitted. Table-derived filename anchors above remain refused.
    page.evaluate('''() => document.querySelectorAll('button').forEach(button => button.remove())''')
    result = attachments().download_financial_attachments(page, deepcopy(RECORD), tmp_path)
    item, _ = downloaded(result, tmp_path)
    assert item['label'] == CURRENT_LABEL
    assert requests == [('GET', DETAIL), ('GET', PDF_URL)]
