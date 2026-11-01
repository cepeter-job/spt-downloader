"""Safety-preserving, layout-free pagination state observation."""
import json

import coretax_browser as driver
from support_isolated_browser import browser as browser


def test_state_poll_reads_all_rows_without_asking_browser_for_layout(browser):
    assert 'innerText' not in driver.STATE_JS
    page=browser.new_page()
    try:
        page.set_content("""<p-table><table><tbody>
          <tr><td>A <span>ONE</span></td></tr>
          <tr><td>B <span>HIDDEN</span></td></tr>
        </tbody></table><div class="p-paginator">
          <button class="p-paginator-page p-highlight">1</button>
        </div></p-table>""")
        owner=page.locator('p-table')
        first=json.loads(owner.evaluate(driver.STATE_JS))
        assert first['p']==['1']
        assert first['rows']==['A ONE','B HIDDEN']
        assert json.loads(owner.evaluate(driver.STATE_JS)) == first
        page.locator('tbody tr').last.locator('span').evaluate(
            "(e)=>e.textContent='CHANGED'")
        second=json.loads(owner.evaluate(driver.STATE_JS))
        assert second['rows'] != first['rows']
        page.locator('.p-highlight').evaluate("(e)=>e.textContent='2'")
        assert json.loads(owner.evaluate(driver.STATE_JS))['p']==['2']
    finally:
        page.close()
