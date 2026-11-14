"""Owned synthetic DOM for the scoped L7 detached-ambiguity rule.

Hosted Windows browser fixture; no accounts, endpoints or captured values.
"""
import pytest

from coretax_json_capture import _L7_HISTORY
from support_isolated_browser import browser as browser, context as context

CHAIN = """
<rshshr-corporate-income-tax-return>
  <div class="p-tabview">
    <ul class="p-tabview-nav"><li><a role="tab" aria-controls="l7">L7</a></li></ul>
    <div class="p-tabview-panels"><p-tabpanel>
      <div class="p-tabview-panel" id="l7">
        <rshshr-citr-l7-form><rsh-citr-l7-grid1><p-table><table><tbody></tbody></table></p-table></rsh-citr-l7-grid1></rshshr-citr-l7-form>
      </div>
    </p-tabpanel></div>
  </div>
</rshshr-corporate-income-tax-return>
"""


@pytest.fixture
def page(context):
    owned = context.new_page()
    owned.route('**/*', lambda route: route.abort())
    owned.set_default_timeout(500)
    return owned


def arm(page):
    page.set_content('<main id="host"></main>')
    document = page.evaluate_handle('() => document')
    return document.evaluate_handle(_L7_HISTORY)


def build(page):
    page.evaluate("html => { document.getElementById('host').innerHTML = html; }", CHAIN)


def churn(page, host_selector):
    page.evaluate("""selector => {
      const host = document.querySelector(selector);
      const wrapper = document.createElement('div');
      host.appendChild(wrapper);
      const table = document.createElement('p-table');
      table.innerHTML = '<table><tbody></tbody></table>';
      wrapper.appendChild(table);
      wrapper.remove();
    }""", host_selector)


def test_unrelated_detached_table_keeps_l7_history_available(page):
    history = arm(page)
    build(page)
    assert history.evaluate('(h) => h.sample()')['available'] is True
    churn(page, 'body')
    state = history.evaluate('(h) => h.sample()')
    assert state['available'] is True and state['changed'] is False
    assert history.evaluate('(h) => h.why()') == 'ok'


def test_detached_chain_ancestor_still_refuses(page):
    history = arm(page)
    build(page)
    page.evaluate("""() => {
      const panel = document.querySelector('.p-tabview-panel');
      const table = document.createElement('table');
      table.innerHTML = '<tbody></tbody>';
      panel.appendChild(table);
      panel.remove();
    }""")
    state = history.evaluate('(h) => h.sample()')
    assert state['available'] is False
    assert history.evaluate('(h) => h.why()') == 'detached'


def test_retained_role_removal_remains_fatal(page):
    history = arm(page)
    build(page)
    page.evaluate("""() => {
      document.querySelector('rsh-citr-l7-grid1').remove();
    }""")
    state = history.evaluate('(h) => h.sample()')
    assert state['changed'] is True
