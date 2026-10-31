"""Synthetic browser-only timing and route classification; no live source or values."""
import json

import pytest

import coretax_browser as driver
from coretax_mpn import ORIGIN
from coretax_mpn_ui import REFERENCE_PATH, _reference_route_kind
from spt_desktop import diagnostics
from support_isolated_browser import browser, context
from test_corporate_dom_page_size import fixture, assert_rows
from test_diagnostics import records


@pytest.mark.parametrize("cap,pages", [(100, 7), (250, 3)])
def test_l3_page_size_counterfactual_has_identical_verified_rows_and_safe_page_timings(
        context, tmp_path, cap, pages):
    page = context.new_page()
    page.route("**/*", lambda route: route.abort())
    page.set_default_timeout(500)
    table = fixture(page, total=601, sizes=(10, 100, 250, 500), selected=100)
    with diagnostics.session(tmp_path / "log", "worker") as log:
        result = driver.capture_table(page, table, 1, 1000, max_page_size=cap)
        assert log.flush()
    assert_rows(result, 601)
    assert result["pages"] == pages
    assert page.evaluate("size") == cap
    assert page.evaluate("moves") == pages - 1
    rows = [e for e in records(tmp_path / "log") if e["event"] == "table.page_timing"]
    assert len(rows) == pages
    assert rows[0]["table_page_stage"] == "initial"
    assert all(e["table_page_stage"] == "advanced" for e in rows[1:])
    assert [e["pages"] for e in rows] == list(range(1, pages + 1))
    assert sum(e["page_rows"] for e in rows) == 601
    assert all(e["page_size_cap"] == cap for e in rows)
    assert all("duration_ms" in e and "table_dom_ms" in e for e in rows)
    assert all("table_poll_ms" in e and "table_idle_ms" in e for e in rows[1:])
    assert all("table_click_ms" in e and "table_verify_ms" in e for e in rows[1:])
    assert all(0 <= e["table_click_ms"] <= e["duration_ms"] for e in rows[1:])
    assert all(0 <= e["table_verify_ms"] <= e["duration_ms"] for e in rows[1:])
    assert all("rows" not in e and "url" not in e and "headers" not in e for e in rows)
    page.close()


@pytest.mark.parametrize("url, expected", [
    (ORIGIN + REFERENCE_PATH, "not_observed"),
    (ORIGIN + REFERENCE_PATH + "?query_variant=1", "query_variant"),
    (ORIGIN + "/referencedata/api/currentreferencedata/id-ID/OTHER_REFERENCE", "path_variant"),
    ("https://synthetic.invalid/referencedata/api/currentreferencedata/id-ID/OTHER", "not_observed"),
    (ORIGIN + "/accounting/id-ID/balancesheet/OTHER", "not_observed"),
])
def test_reference_route_classification_only_uses_owned_origin_and_path(url, expected):
    assert _reference_route_kind(url) == expected


def test_new_diagnostics_reject_unbounded_and_untrusted_values(tmp_path):
    secret = "SYNTHETIC_PRIVATE_ACCOUNT_OR_REFERENCE"
    with diagnostics.session(tmp_path / "log", "worker") as log:
        diagnostics.record("table.page_timing", table_page_stage=secret, pages=-1,
                           page_rows=-100, page_size_cap=secret,
                           duration_ms=-15, table_dom_ms=secret, table_click_ms=secret,
                           table_verify_ms=-5, url=secret, body=secret)
        diagnostics.record("table.page_timing", table_page_stage="advanced",
                           pages=2, page_rows=100, page_size_cap=250,
                           duration_ms=12.5, table_click_ms=1.4, table_verify_ms=0.6,
                           table_poll_ms=2.1, table_idle_ms=3.2,
                           table_dom_ms=7.2)
        diagnostics.record("mpn.catalog_readiness", mpn_catalog_variant_kind=secret,
                           url=secret, body=secret)
        diagnostics.record("mpn.catalog_readiness", mpn_catalog_variant_kind="path_variant")
        assert log.flush()
    rows = records(tmp_path / "log")
    page_events = [e for e in rows if e["event"] == "table.page_timing"]
    route_events = [e for e in rows if e["event"] == "mpn.catalog_readiness"]
    assert len(page_events) == len(route_events) == 2
    assert "table_page_stage" not in page_events[0]
    assert "pages" not in page_events[0]
    assert page_events[1]["table_dom_ms"] == 7.2
    assert page_events[1]["table_click_ms"] == 1.4
    assert page_events[1]["table_verify_ms"] == 0.6
    assert "mpn_catalog_variant_kind" not in route_events[0]
    assert route_events[1]["mpn_catalog_variant_kind"] == "path_variant"
    assert secret not in json.dumps(rows)
