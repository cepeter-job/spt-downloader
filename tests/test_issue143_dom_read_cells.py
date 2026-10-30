"""Synthetic equivalence tests for safe, non-mutating large-table cell extraction."""
import pytest

import coretax_browser as driver
from support_isolated_browser import browser


@pytest.mark.parametrize('cell_markup', [
    '<td>A <span class="p-column-title">Hidden caption</span> B</td>',
    '<td><button>Ignore button</button><span>Visible <strong>Bold</strong></span></td>',
    '<td><input value="synthetic" /><select><option selected>Chosen</option></select></td>',
    '<td><span style="display:none">Hidden style but existing DOM text</span>'
    '<script>ignore</script><style>ignore</style><textarea>Value</textarea></td>',
    '<td><div><span class="p-hidden-accessible">Exclude</span><span>Include</span></div></td>',
    '<td> A <p-columnfilter>Marker</p-columnfilter><span> Z </span></td>',
])
def test_nonmutating_cell_extraction_matches_preexisting_clone_contract(
        browser, cell_markup):
    page = browser.new_page()
    try:
        page.set_content('<table><tbody><tr>'+cell_markup+'</tr></tbody></table>')
        cell = page.locator('td')
        original=cell.evaluate("""cell => {
          const clone=cell.cloneNode(true);
          clone.querySelectorAll('.p-column-title,button,script,style,.p-hidden-accessible')
            .forEach(e=>e.remove());
          clone.querySelectorAll('input,textarea,select').forEach(e=>e.remove());
          let text=(clone.textContent||'').replace(/\\s+/g,' ').trim();
          const vals=[...cell.querySelectorAll('input:not([type=password]):not([type=hidden]),textarea,select')]
            .filter(e=>e.getAttribute('role')!=='combobox' && !e.closest('.p-hidden-accessible')
              && (!(e.type==='radio'||e.type==='checkbox')||e.checked))
            .map(e=>(e.type==='checkbox'||e.type==='radio') ? String(e.checked) :
              (e.tagName==='SELECT' ? e.selectedOptions[0]?.textContent||e.value : e.value));
          return [text,...vals.filter(v=>v!=='' && v!==text)].filter(Boolean).join(' | ');
        }""")
        current=cell.evaluate(driver.CELL_JS)
        assert current==original
        assert cell.count()==1
    finally:
        page.close()


def test_repeated_large_synthetic_table_does_not_mutate_owned_cells(browser):
    page=browser.new_page()
    try:
        cells=''.join('<td>Cell <span class="p-column-title">Skip</span>'
                      '<strong>SYNTHETIC_'+str(i)+'</strong></td>' for i in range(20))
        page.set_content('<table><tbody>'+('<tr>'+cells+'</tr>')*100+'</tbody></table>')
        initial=page.locator('table').evaluate(driver.TABLE_JS)
        second=page.locator('table').evaluate(driver.TABLE_JS)
        assert len(initial['rows'])==100
        assert initial['rows']==second['rows']
        assert len(initial['rows'][0])==20
        assert page.locator('.p-column-title').count()==2000
    finally:
        page.close()
