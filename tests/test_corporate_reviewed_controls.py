"""Actual paginator ownership, never a value-based legacy-control guess."""
import coretax_browser as driver
from support_isolated_browser import browser as browser, context as context
from test_ppn_capture_readiness import page as page


def test_new_dom_fields_exclude_paginator_controls_but_keep_unnamed_business(page):
    page.set_content('''<div class="p-tabview-panel" id="owned">
      <div><label for="year">TAHUN PAJAK</label><input id="year" formcontrolname="TaxPeriodYear" value="2025"></div>
      <div><input value="10"></div>
      <div class="p-paginator">
        <input value="10"><textarea>10</textarea><select><option>10</option></select>
        <p-dropdown><span class="p-dropdown-label">10</span></p-dropdown>
        <p-multiselect><span class="p-multiselect-label">10</span></p-multiselect>
      </div>
      <p-dropdown formcontrolname="BusinessChoice"><span class="p-dropdown-label">10</span></p-dropdown>
      <table><tbody><tr><td><input value="SYNTHETIC TABLE VALUE"></td></tr></tbody></table>
      <div class="p-tabview-panel"><input value="SYNTHETIC FOREIGN VALUE"></div>
    </div>''')
    fields = page.locator('#owned').evaluate(driver.FIELDS_JS)
    assert [(f['field'], f['value']) for f in fields] == [
        ('TaxPeriodYear', '2025'), ('', '10'), ('BusinessChoice', '10')]
