"""Synthetic, runner-only REAL_SCAN regressions for lost local collection binding."""
import pytest

from support_financial_browser import browser as browser
from support_financial_browser import attachments
from support_financial_modern import CURRENT_LABEL
from support_financial_post import post_routed as post_routed
from test_financial_modern_label_scope import (
    assert_common_owner_layout,
    assert_no_click_or_wire,
    common_owner_content,
)


@pytest.mark.parametrize('explicit_label_ids', [False, True], ids=['local-labels', 'explicit-label-ids'])
@pytest.mark.parametrize('local_heading', ['removed', 'hidden'])
def test_empty_financial_group_cannot_lend_its_heading_to_other_documents(
        post_routed, explicit_label_ids, local_heading):
    page, wire = post_routed(content=common_owner_content(explicit_label_ids))
    # Validate all three original plain field groups before removing any nodes;
    # this also installs the observational click trace without changing actions.
    assert_common_owner_layout(page, explicit_label_ids)

    assert page.evaluate('''({explicit, heading, financialCaption}) => {
        const form = document.querySelector('rshshr-citr-main-form');
        const common = form.querySelector('#synthetic-common-accordion');
        const financial = common.querySelector('#financial-field');
        const financialGrid = financial.querySelector('#financial-grid');
        const financialLabel = financialGrid.previousElementSibling;
        const other = common.querySelector('#neighbor-a-field');
        const grid = other.querySelector('#neighbor-a-grid');
        const localLabel = grid.previousElementSibling;
        const table = grid.querySelector('#neighbor-a-table');

        financialGrid.remove();
        common.querySelector('#neighbor-b-field').remove();
        if (heading === 'removed') localLabel.remove();
        else localLabel.hidden = true;
        if (explicit) table.setAttribute('aria-labelledby', 'financial-label');

        // Keep the preceding financial heading visible in its empty plain DIV.
        // Only OtherDocuments' unchanged modern grid survives: neither its PDF
        // filename nor its new ordinal establishes a financial collection.
        const fields = [...common.children];
        const tables = [...form.querySelectorAll('table')];
        return fields.length === 2 && fields[0] === financial && fields[1] === other &&
            financial.tagName === 'DIV' && financial.children.length === 1 &&
            financial.firstElementChild === financialLabel &&
            financialLabel.tagName === 'LABEL' &&
            financialLabel.innerText === financialCaption &&
            financialLabel.getClientRects().length > 0 &&
            !financial.querySelector('ui-grid-documents,table') &&
            !form.querySelector('#financial-grid,#financial-table,#neighbor-b-field') &&
            other.tagName === 'DIV' && grid.parentElement === other &&
            common.querySelectorAll('ui-grid-documents').length === 1 &&
            tables.length === 1 && tables[0] === table &&
            table.closest('ui-grid-documents') === grid &&
            table.closest('.p-accordion-tab') === common &&
            (heading === 'removed' ? !localLabel.isConnected && !grid.previousElementSibling :
                localLabel.hidden && !localLabel.getClientRects().length &&
                grid.previousElementSibling === localLabel) &&
            (explicit ? financialLabel.id === 'financial-label' &&
                table.getAttribute('aria-labelledby') === 'financial-label' :
                !financialLabel.hasAttribute('id') && !table.hasAttribute('aria-labelledby'));
    }''', {'explicit': explicit_label_ids, 'heading': local_heading,
           'financialCaption': CURRENT_LABEL})

    observed = page.evaluate(attachments()._SCAN)

    # Nonempty observations and one recognized table rule out a zero-table
    # sentinel pass: the surviving modern document table must remain valid.
    assert observed['observations'] and all(
        item['attachment_tables'] == 1 for item in observed['observations'])
    assert observed['controls'] == []
    assert_no_click_or_wire(page, wire)
