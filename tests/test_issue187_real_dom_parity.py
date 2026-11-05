"""Issue #187 phase 3: real Chromium DOM reading versus source-owned JSON.

The HTML and wire bytes are invented. Browser extraction is NOT monkeypatched:
these tests exercise the actual DOM field reader and paginator in Edge. A
matching raw-source literal is not proof of live Coretax parser equivalence.
"""
import json
from html import escape
from pathlib import Path

import pytest

import coretax_browser as browser_driver
import coretax_json as json_adapter
import support_json_corpus as corpus
from support_isolated_browser import browser as browser, context as context


ROWS = (
    (("001", "000.00"), ("001", "000.00")),
    (("002", "123.4500"),),
)


def contract():
    path = Path(__file__).parent / "fixtures" / "capture_semantic_pair_v1.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["version"] == 1 and data["scope"] == corpus.SCOPE
    return data


def dom_html(*, reported=3, final_page=ROWS[1]):
    facts = {item["dom_field"]: item["literal"] for item in contract()["facts"]}
    assert facts["Tin"] == corpus.NPWP
    assert facts["NetIncomeBeforeTax"] == "123.4500"

    def html_rows(rows):
        return "".join(
            "<tr><td>" + escape(left) + "</td><td>" + escape(right) + "</td></tr>"
            for left, right in rows
        )

    first = html_rows(ROWS[0])
    last = html_rows(final_page)
    # The fixture observes a trusted static browser document, with no HTTP I/O,
    # no session/credentials and no live tax portal.
    return f"""<main class="main-content"><div class="p-tabview">
      <ul class="p-tabview-nav"><li><a role="tab" aria-controls="induk"
        onclick="document.querySelector('#induk').hidden=false">Induk</a></li></ul>
      <div class="p-tabview-panels"><p-tabpanel><div class="p-tabview-panel" id="induk">
      <label for="tin">NPWP</label>
      <input id="tin" formcontrolname="Tin" disabled value="{escape(facts['Tin'])}">
      <label for="net">Net income</label>
      <input id="net" formcontrolname="NetIncomeBeforeTax" disabled
        value="{escape(facts['NetIncomeBeforeTax'])}">
      <p-table><div class="p-datatable">
        <table><thead><tr><th>Kode</th><th>Nilai</th></tr></thead>
          <tbody>{first}</tbody></table>
        <div class="p-paginator">
          <button class="p-paginator-page p-highlight">1</button>
          <button class="p-paginator-next" type="button">Next</button>
          <span class="p-paginator-current">Showing 1 to 2 of {reported} entries</span>
        </div>
      </div></p-table></div></p-tabpanel></div></div></main>
      <script>
        window.moves=0;
        document.querySelector('.p-paginator-next').onclick=()=>{{
          window.moves++;
          document.querySelector('tbody').innerHTML={json.dumps(last)};
          document.querySelector('.p-highlight').textContent='2';
          document.querySelector('.p-paginator-current').textContent='Showing 3 to 3 of {reported} entries';
          document.querySelector('.p-paginator-next').disabled=true;
        }};
      </script>"""


def read_dom(page, *, reported=3, final_page=ROWS[1]):
    page.route("**/*", lambda route: route.abort())
    page.set_content(dom_html(reported=reported, final_page=final_page))
    return browser_driver.capture_detail(page, max_pages=3)


def test_real_browser_and_native_json_preserve_the_same_exact_literals(context):
    source = json_adapter.adapt_corporate_detail(
        [corpus.primary()], corpus.selected_record(), corpus.SCOPE, corpus.observed()
    )
    assert source["eligible"] and source["coverage"]["complete"]
    native_values = {
        row[0]: (row[1], row[2])
        for section in source["sections"] for table in section["tables"] for row in table["rows"]
    }
    page = context.new_page()
    dom = read_dom(page)
    assert dom["capture_complete"] and dom["errors"] == []
    assert [s["name"] for s in dom["sections"]] == ["Induk"]
    dom_fields = {item["field"]: item["value"] for item in dom["sections"][0]["fields"]}
    for item in contract()["facts"]:
        assert dom_fields[item["dom_field"]] == item["literal"]
    assert native_values["/MainFormData/Tin"] == ("string", dom_fields["Tin"])
    assert native_values["/MainFormData/NetIncomeBeforeTax"] == (
        "number", dom_fields["NetIncomeBeforeTax"]
    )
    table, = dom["sections"][0]["tables"]
    assert table["headers"] == ["Kode", "Nilai"]
    assert table["rows"] == [list(row) for page_rows in ROWS for row in page_rows]
    assert table["source_total"] == table["body_row_count"] == 3
    assert table["pages"] == 2 and table["complete"]
    assert page.evaluate("window.moves") == 1


@pytest.mark.parametrize("reported,final_page,expected_rows", [
    (4, ROWS[1], 3),
    (3, (), 2),
])
def test_real_dom_never_certifies_missing_or_unreconciled_page_rows(
    context, reported, final_page, expected_rows,
):
    page = context.new_page()
    captured = read_dom(page, reported=reported, final_page=final_page)
    assert not captured["capture_complete"]
    assert captured["errors"]
    table, = captured["sections"][0]["tables"]
    assert not table["complete"]
    assert table["source_total"] == reported
    assert table["body_row_count"] == expected_rows
    assert table["rows"] == [list(row) for rows in (ROWS[0], final_page) for row in rows]
    assert page.evaluate("window.moves") == 1


def test_real_dom_partial_capture_remains_partial_in_saved_xlsx_proof(
    context, tmp_path,
):
    from openpyxl import load_workbook
    import coretax_exporter as exporter

    page = context.new_page()
    captured = read_dom(page, reported=3, final_page=())
    assert not captured["capture_complete"]

    record = corpus.selected_record()
    record.update(
        sections=captured["sections"],
        capture_complete=False,
        attachments=[
            {"label": "Laporan Keuangan", "status": "PARTIAL",
             "relative_path": None, "bytes": 0, "hash": None}
        ],
    )
    run = {
        "npwp": corpus.NPWP, "year": 2025, "year_basis": "period",
        "inventory_complete": True, "complete": False,
        "taxpayer_name": "SYNTHETIC COMPANY", "started_at": "fixture",
        "errors": captured["errors"], "audit": [], "records": [record],
    }
    files = exporter.export_split_workbooks(run, tmp_path)
    filename, = set(files) - {"resume.xlsx"}
    workbook = load_workbook(files[filename])
    try:
        proof = exporter.read_workbook_proof(workbook)
        assert proof["complete"] is False
        assert proof["records"][0]["capture_complete"] is False
        assert proof["records"][0]["record_id"] == corpus.RECORD_ID
        assert proof["records"][0]["scope"] == corpus.SCOPE
        assert proof["records"][0]["attachments"][0]["status"] == "PARTIAL"
    finally:
        workbook.close()
    resume = load_workbook(files["resume.xlsx"])
    try:
        assert resume["Ringkasan"]["B6"].value == "PARTIAL"
        assert resume["Daftar SPT"]["I5"].value == "PARTIAL"
    finally:
        resume.close()

    with pytest.raises(ValueError, match="incomplete capture"):
        exporter.validate_export_run({
            **run, "complete": True, "errors": [],
        })
