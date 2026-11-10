"""Clearly synthetic, runner-only REAL_SCAN ownership regressions; no portal data.

Unlike the section-per-grid fixture, all three document grids below share one
accordion owner. Each plain field-group div has its own preceding sibling label.
Only fixed test-owned markup is transformed; production scanner/helpers stay real.
"""
import pytest

from support_financial_browser import browser as browser
from support_financial_browser import attachments
from support_financial_modern import CURRENT_LABEL, modern_content
from support_financial_post import post_routed as post_routed


def common_owner_content(explicit_label_ids):
    content = modern_content()
    opening = '<rshshr-citr-main-form>'
    closing = '</rshshr-citr-main-form>'
    assert content.count(opening) == content.count(closing) == 1
    content = content.replace(
        opening, opening + '<div id="synthetic-common-accordion" class="p-accordion-tab">')
    content = content.replace(closing, '</div>' + closing)
    assert content.count('</section>') == 3
    content = content.replace('</section>', '</div>')
    for key in ('financial', 'neighbor-a', 'neighbor-b'):
        section = f'<section id="{key}-section">'
        assert content.count(section) == 1
        content = content.replace(section, f'<div id="{key}-field" class="synthetic-field-group">')
        if not explicit_label_ids:
            label_id = f' id="{key}-label"'
            label_ref = f' aria-labelledby="{key}-label"'
            assert content.count(label_id) == content.count(label_ref) == 1
            content = content.replace(label_id, '').replace(label_ref, '')
    return content


def assert_common_owner_layout(page, explicit_label_ids):
    # These assertions validate the fixture's geometry, not scanner admission.
    # The plain per-field divs must NOT become section/fieldset/panel owners.
    assert page.evaluate('''explicit => {
        const form = document.querySelector('rshshr-citr-main-form');
        const common = form.querySelector('#synthetic-common-accordion');
        const fields = [...common.children];
        const tables = [...form.querySelectorAll('table')];
        return common.classList.contains('p-accordion-tab') &&
            fields.length === 3 && tables.length === 3 &&
            form.querySelectorAll('.p-accordion-tab').length === 1 &&
            form.querySelectorAll('section,fieldset,.p-panel,p-panel,p-accordiontab').length === 0 &&
            fields.every(field => {
                const grid = field.querySelector('ui-grid-documents');
                const label = grid.previousElementSibling;
                const table = grid.querySelector('table');
                return field.tagName === 'DIV' && field.parentElement === common &&
                    grid.parentElement === field && label.tagName === 'LABEL' &&
                    label.parentElement === field &&
                    table.closest('.p-accordion-tab,.p-tabview-panel') === common &&
                    (explicit ? label.hasAttribute('id') && table.hasAttribute('aria-labelledby') :
                        !label.hasAttribute('id') && !table.hasAttribute('aria-labelledby'));
            });
    }''', explicit_label_ids)
    page.evaluate('''() => {
        window.syntheticActionTrace = [];
        document.addEventListener('click', event => {
            const button = event.target.closest('button');
            if (button) window.syntheticActionTrace.push(button.id);
        }, true);
    }''')


def real_scan(page):
    observed = page.evaluate(attachments()._SCAN)
    # Avoid vacuous negative passes on the old zero-table sentinel: each test
    # must first exercise recognition of all three real modern header shapes.
    assert observed['observations'] and all(
        item['attachment_tables'] == 3 for item in observed['observations'])
    return observed['controls']


def assert_no_click_or_wire(page, wire):
    assert page.evaluate('window.syntheticClicks') == 0
    assert page.evaluate('window.syntheticActionTrace') == []
    assert wire == []


@pytest.mark.parametrize('explicit_label_ids', [False, True], ids=['local-labels', 'explicit-label-ids'])
def test_common_owner_admits_only_its_local_financial_group(post_routed, explicit_label_ids):
    page, wire = post_routed(content=common_owner_content(explicit_label_ids))
    assert_common_owner_layout(page, explicit_label_ids)

    controls = real_scan(page)

    assert len(controls) == 1
    control = controls[0]
    assert control['method'] == 'POST'
    assert control['label'] == CURRENT_LABEL
    assert control['filename'] == 'synthetic-financial.pdf'
    assert control['button_index'] == 0 and control['identity']
    assert_no_click_or_wire(page, wire)


@pytest.mark.parametrize('neighbor', ['neighbor-a', 'neighbor-b'])
def test_same_owner_explicit_financial_reference_cannot_override_other_documents_caption(post_routed, neighbor):
    content = common_owner_content(True)
    original = f'<table id="{neighbor}-table" aria-labelledby="{neighbor}-label">'
    conflicting = f'<table id="{neighbor}-table" aria-labelledby="financial-label">'
    assert content.count(original) == 1
    page, wire = post_routed(content=content.replace(original, conflicting))
    assert_common_owner_layout(page, True)
    # Both the approved heading and contradictory local caption are inside the
    # SAME owner. A same-owner ID check alone therefore cannot reject this grid.
    assert page.evaluate('''key => {
        const table = document.getElementById(key + '-table');
        const grid = document.getElementById(key + '-grid');
        const referenced = document.getElementById(table.getAttribute('aria-labelledby'));
        return referenced.id === 'financial-label' &&
            referenced.closest('.p-accordion-tab') === table.closest('.p-accordion-tab') &&
            grid.previousElementSibling.textContent ===
                (key === 'neighbor-a' ? 'SYNTHETIC_OTHER_DOCUMENTS_A' : 'SYNTHETIC_OTHER_DOCUMENTS_B');
    }''', neighbor)

    controls = real_scan(page)

    # A whole-owner refusal is also safe; no neighbor may acquire POST scope.
    assert all(control['method'] == 'POST' and
               control['filename'] == 'synthetic-financial.pdf' and
               control['label'] == CURRENT_LABEL for control in controls)
    assert len(controls) <= 1
    assert_no_click_or_wire(page, wire)


@pytest.mark.parametrize('explicit_label_ids', [False, True], ids=['local-labels', 'explicit-label-ids'])
def test_duplicate_financial_groups_in_one_owner_refuse_all_post_controls(post_routed, explicit_label_ids):
    content = common_owner_content(explicit_label_ids)
    assert content.count('SYNTHETIC_OTHER_DOCUMENTS_A') == 1
    # Distinct field/grid/table/button IDs, not duplicate DOM IDs or cloned
    # controls: the ambiguity is two independently labelled approved groups.
    content = content.replace('SYNTHETIC_OTHER_DOCUMENTS_A', CURRENT_LABEL)
    page, wire = post_routed(content=content)
    assert_common_owner_layout(page, explicit_label_ids)
    assert page.evaluate('''() => [...document.querySelectorAll(
        '#synthetic-common-accordion > div > label')].map(label => label.textContent)''') == [
            CURRENT_LABEL, CURRENT_LABEL, 'SYNTHETIC_OTHER_DOCUMENTS_B']

    assert real_scan(page) == []
    assert_no_click_or_wire(page, wire)


@pytest.mark.parametrize('explicit_label_ids', [False, True], ids=['local-labels', 'explicit-label-ids'])
def test_multiple_pdf_rows_in_one_financial_group_are_not_duplicate_groups(post_routed, explicit_label_ids):
    content = common_owner_content(explicit_label_ids)
    second_row = '''<tr><td>2</td><td>synthetic-financial-second.pdf</td><td>
    <button id="financial-second-download" type="button" aria-label="Unduh"
    class="ng-actbtn p-button-secondary"><i class="pi pi-download"></i></button>
    </td></tr>'''
    # The first tbody is the financial grid; append one fixed, synthetic row
    # without adding a field group or changing either neighbor's local heading.
    content = content.replace('</tbody>', second_row + '</tbody>', 1)
    page, wire = post_routed(content=content)
    assert_common_owner_layout(page, explicit_label_ids)
    assert page.locator('#financial-table tbody tr').count() == 2

    controls = real_scan(page)

    assert len(controls) == 2
    assert [control['filename'] for control in controls] == [
        'synthetic-financial.pdf', 'synthetic-financial-second.pdf']
    assert [control['button_index'] for control in controls] == [0, 1]
    assert all(control['method'] == 'POST' and control['label'] == CURRENT_LABEL and
               control['identity'] for control in controls)
    assert len({control['identity'] for control in controls}) == 2
    assert_no_click_or_wire(page, wire)
