"""Synthetic native-Masa helpers; no collected tests."""
from contextlib import contextmanager
import hashlib
import importlib
import importlib.util

import pytest
from playwright.sync_api import sync_playwright

from coretax_browser import CaptureCancelled as CaptureCancelled
from coretax_json import JsonSafetyError as JsonSafetyError
from coretax_json_capture import DetailJsonCapture
from masa_json_fixtures import SCOPE
from masa_observer_fixture import ASSETS, BUILD, FORMS as FORMS, FRAME, MAIN, Fixture


def observer_module():
    assert importlib.util.find_spec('coretax_masa_observer'), 'Value-free Masa observer is not implemented'
    module = importlib.import_module('coretax_masa_observer')
    assert callable(getattr(module, 'observe_masa_forms', None)), 'Masa traversal is not implemented'
    return module


@pytest.fixture(scope='module')
def browser():
    with sync_playwright() as playwright:
        instance = playwright.chromium.launch(channel='msedge', headless=True)
        yield instance
        instance.close()


@contextmanager
def observed(browser, tmp_path, monkeypatch, tax='PPN', *, defect=None, layout='direct', induk_fields=None, vendor=None):
    module = observer_module()
    monkeypatch.setattr(module, 'BUILD_DIGESTS', {
        MAIN: hashlib.sha256(BUILD).hexdigest(),
        **{url: hashlib.sha256(BUILD).hexdigest() for url in ASSETS.values()},
    })
    fixture = Fixture(browser, tax, defect=defect, layout=layout, induk_fields=induk_fields, vendor=vendor)
    try:
        fixture.page.goto(fixture.record['list_url'])
        with DetailJsonCapture(fixture.context, fixture.page, fixture.record, SCOPE, tmp_path) as capture:
            fixture.page.goto(FRAME)
            capture.bind_detail_page(fixture.page)
            # Tunggu request awal selesai, termasuk 403, tanpa menutup capture
            # yang masih harus menerima request grid selama traversal berikutnya.
            fixture.page.wait_for_function('window.primaryDone===true', timeout=5000)
            yield module, fixture, capture
    finally:
        fixture.context.close()



from openpyxl import load_workbook
import coretax_exporter as exporter
from support_templates import run_for


def exported(tmp_path, tax, sections):
    run = run_for(sections)
    run['records'][0]['meta']['Jenis Pajak'] = tax
    from support_masa_binding import reference_geometry
    with reference_geometry():
        files = exporter.export_split_workbooks(run, tmp_path)
    return load_workbook(tmp_path / next(f for f in files if f != 'resume.xlsx'))


def project(form, control, model='NORMAL'):
    implementation = getattr(importlib.import_module('coretax_masa_bindings'), 'project_ppn_amount', None)
    assert callable(implementation), 'PPN scalar projection is not implemented'
    return implementation(form, control, model=model)
