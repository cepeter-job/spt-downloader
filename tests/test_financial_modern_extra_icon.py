"""Synthetic runner-only regression for the reviewed single-icon action shape."""
from support_financial_browser import browser as browser
from support_financial_browser import attachments
from support_financial_modern import CURRENT_LABEL, modern_content
from support_financial_post import post_routed as post_routed


def test_modern_action_rejects_an_extra_non_pi_icon_after_valid_admission(post_routed):
    page, wire = post_routed(content=modern_content())
    page.evaluate('''() => {
        window.syntheticActionTrace = [];
        document.addEventListener('click', event => {
            const button = event.target.closest('button');
            if (button) window.syntheticActionTrace.push(button.id);
        }, true);
    }''')
    before = page.evaluate(attachments()._SCAN)
    # Require real modern admission first; zero-table/zero-control refusal is
    # not evidence that the later extra-icon mutation was actually rejected.
    assert before['observations'] and all(
        item['attachment_tables'] == 3 for item in before['observations'])
    control, = before['controls']
    assert control['method'] == 'POST' and control['label'] == CURRENT_LABEL
    assert control['filename'] == 'synthetic-financial.pdf'
    page.evaluate('''() => {
        const button = document.querySelector('#financial-download');
        button.append(document.createElement('i'));
    }''')
    assert page.evaluate('''() => {
        const button = document.querySelector('#financial-download');
        return button.querySelectorAll('i').length === 2 &&
            button.querySelectorAll('i.pi.pi-download').length === 1 &&
            button.querySelectorAll('.pi').length === 1;
    }''')

    after = page.evaluate(attachments()._SCAN)

    assert after['observations'] and all(
        item['attachment_tables'] == 3 for item in after['observations'])
    assert after['controls'] == []
    assert page.evaluate('window.syntheticClicks') == 0
    assert page.evaluate('window.syntheticActionTrace') == []
    assert wire == []
