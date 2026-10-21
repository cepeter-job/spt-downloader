"""Proses browser sintetis bersama; context dan halaman tetap terisolasi per tes."""
from contextlib import contextmanager

import pytest
from playwright.sync_api import sync_playwright


@pytest.fixture(scope='module')
def browser():
    with sync_playwright() as engine:
        owned = engine.chromium.launch(channel='msedge', headless=True)
        try:
            yield owned
        finally:
            owned.close()


@contextmanager
def isolated_context(browser):
    owned = browser.new_context()
    try:
        yield owned
    finally:
        # Menutup context juga menutup popup, termasuk saat assertion gagal.
        owned.close()


@pytest.fixture
def context(browser):
    with isolated_context(browser) as owned:
        yield owned
