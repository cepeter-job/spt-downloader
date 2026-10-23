"""Native observers must follow the current owned tab, without tax-value reads."""
from contextlib import contextmanager
import hashlib

import pytest

import coretax_browser as driver
from coretax_json_capture import DetailJsonCapture
from masa_json_fixtures import SCOPE
from pph21_observer_fixture import ARTICLE, BUILD as PPH21_BUILD, MAIN, observed as pph21_case
from support_isolated_browser import browser
from support_masa_native import observed as masa_case
from test_json_hybrid_native import NativeFixture
import support_json_corpus as corpus


FAMILIES = ('corporate', 'PPN', 'PPh Unifikasi', 'PPh Pasal 21/26')


@contextmanager
def native_case(browser, tmp_path, monkeypatch, family, *, corporate_groups=False):
    if family == 'corporate':
        fixture = NativeFixture(browser, tmp_path, monkeypatch, groups=corporate_groups)
        try:
            fixture.page.goto(corpus.LIST_URL)
            with DetailJsonCapture(fixture.context, fixture.page, fixture.record,
                                   corpus.SCOPE, tmp_path) as capture:
                fixture.page.goto(corpus.FRAME_URL)
                capture.bind_detail_page(fixture.page)
                driver.wait_idle(fixture.page)
                fixture.page.evaluate("""() => {
                    window.valueReads = 0;
                    for (const property of ['value', 'checked'])
                        Object.defineProperty(HTMLInputElement.prototype, property, {
                            get() { valueReads++; throw Error('SYNTHETIC DOM values forbidden'); }
                        });
                }""")
                yield fixture, capture, lambda **options: driver.observe_corporate_forms(
                    fixture.page, fixture.record, corpus.SCOPE, capture, **options)
        finally:
            fixture.close()
    elif family == 'PPh Pasal 21/26':
        import coretax_pph21_observer as module
        digest = hashlib.sha256(PPH21_BUILD).hexdigest()
        monkeypatch.setattr(module, 'BUILD_DIGESTS', {MAIN: digest, ARTICLE: digest})
        with pph21_case(browser, tmp_path) as (fixture, capture):
            yield fixture, capture, lambda **options: module.observe_pph21_forms(
                fixture.page, fixture.record, SCOPE, capture, **options)
    else:
        with masa_case(browser, tmp_path, monkeypatch, family) as (module, fixture, capture):
            yield fixture, capture, lambda **options: module.observe_masa_forms(
                fixture.page, fixture.record, SCOPE, capture, **options)


def rebind_at_control_read(page, monkeypatch, outcome='owned', *, after_click=False):
    """Return the real first binding, then make it stale deterministically.

    The default preserves the pre-click identity regression. With after_click,
    the first readiness read returns the old ID after the real click, forcing
    a retry against the actual current DOM without a timer race.
    """
    page.evaluate("""outcome => {
        window.nativeRebound = false;
        window.nativeReadinessRetries = 0;
        window.nativeTabClicks = [];
        window.valueReads = window.valueReads || 0;
        const view = document.querySelector('.main-content .p-tabview');
        const nav = view.querySelector('.p-tabview-nav');
        nav.addEventListener('click', e => {
            const tab = e.target.closest('a[role=tab]');
            if (tab && tab.closest('.p-tabview') === view)
                nativeTabClicks.push(tab.textContent.trim());
        }, true);
        const tab = nav.querySelector('a[role=tab]');
        window.nativeOriginalId = tab.getAttribute('aria-controls');
        tab.addEventListener('synthetic-native-rebind', () => {
            const panel = view.querySelector('[id="'+nativeOriginalId+'"]');
            const stale = document.createElement('div');
            stale.id = nativeOriginalId; stale.className = 'p-tabview-panel';
            stale.style.display = 'none';
            panel.id = 'synthetic-current-native-panel';
            panel.parentElement.append(stale);
            tab.setAttribute('aria-controls', panel.id);
            if (outcome === 'hidden') panel.style.visibility = 'hidden';
            if (outcome === 'foreign') {
                const foreign = document.createElement('div');
                foreign.className = 'p-tabview';
                document.querySelector('.main-content').append(foreign);
                foreign.append(panel);
            }
            if (outcome === 'duplicate') {
                const copy = panel.cloneNode(true);
                copy.removeAttribute('data-main-panel');
                panel.parentElement.append(copy);
            }
            if (outcome === 'missing') tab.removeAttribute('aria-controls');
            if (outcome === 'caption') tab.textContent = 'UNREVIEWED REORDERED TAB';
            if (outcome === 'reorder') {
                const first = tab.closest('li');
                nav.insertBefore(first.nextElementSibling, first);
            }
            window.nativeRebound = true;
        }, {once:true});
    }""", outcome)
    locator_type = type(page.locator('body'))
    original_attribute = locator_type.get_attribute
    original_wait = locator_type.wait_for
    released = False
    original_id = page.evaluate('nativeOriginalId')

    def get_attribute(locator, name, *args, **kwargs):
        nonlocal released
        value = original_attribute(locator, name, *args, **kwargs)
        if (not released and name == 'aria-controls' and value == original_id
                and (not after_click or page.evaluate('nativeTabClicks.length > 0'))):
            released = True
            locator.dispatch_event('synthetic-native-rebind')
        return value

    def wait_for(locator, *args, **kwargs):
        # Bound the legacy hard-coded wait; no fixture update relies on timing.
        if kwargs.get('timeout') == 30000:
            kwargs['timeout'] = 500
        try:
            return original_wait(locator, *args, **kwargs)
        except driver.PlaywrightTimeoutError:
            if (after_click and released and kwargs.get('state') == 'visible'
                    and 0 < kwargs.get('timeout', 0) <= 1000):
                page.evaluate('nativeReadinessRetries++')
            raise

    monkeypatch.setattr(locator_type, 'get_attribute', get_attribute)
    monkeypatch.setattr(locator_type, 'wait_for', wait_for)
    # Allow a stale owned panel's bounded read to fail before following the
    # current binding. Counter above observes a real failed readiness wait,
    # independent of its former fixed 100 ms allowance.
    monkeypatch.setattr(driver, 'DETAIL_PANEL_TIMEOUT', 2)


@pytest.mark.parametrize('family', FAMILIES)
def test_native_observer_follows_current_binding(browser, tmp_path, monkeypatch, family):
    with native_case(browser, tmp_path, monkeypatch, family) as (fixture, capture, observe):
        rebind_at_control_read(fixture.page, monkeypatch)
        forms = observe(max_pages=5)
        assert fixture.page.evaluate('nativeRebound') is True
        assert forms is not None
        assert len(forms) == {'corporate': 1, 'PPN': 7, 'PPh Unifikasi': 4,
                              'PPh Pasal 21/26': 5}[family]
        clicks = fixture.page.evaluate('nativeTabClicks')
        assert len(clicks) == len(forms) and len(set(clicks)) == len(clicks)
        assert fixture.page.evaluate('window.valueReads') == 0
        assert not fixture.unexpected
        assert capture.drain()['complete'] is True


@pytest.mark.parametrize('family', FAMILIES)
def test_native_observer_retries_stale_post_click_binding(browser, tmp_path, monkeypatch, family):
    with native_case(browser, tmp_path, monkeypatch, family,
                     corporate_groups=True) as (fixture, capture, observe):
        rebind_at_control_read(fixture.page, monkeypatch, after_click=True)
        forms = observe(max_pages=10)
        assert fixture.page.evaluate('nativeRebound') is True
        assert fixture.page.evaluate('nativeReadinessRetries') >= 1
        assert forms is not None
        assert len(forms) == {'corporate': 4, 'PPN': 7, 'PPh Unifikasi': 4,
                              'PPh Pasal 21/26': 5}[family]
        clicks = fixture.page.evaluate('nativeTabClicks')
        assert len(clicks) == len(forms) and len(set(clicks)) == len(clicks)
        assert fixture.page.evaluate('window.valueReads') == 0
        assert not fixture.unexpected
        assert capture.drain()['complete'] is True


@pytest.mark.parametrize('family', FAMILIES)
def test_native_observer_rejects_live_nth_tab_reorder(browser, tmp_path, monkeypatch, family):
    with native_case(browser, tmp_path, monkeypatch, family,
                     corporate_groups=True) as (fixture, capture, observe):
        first_caption = fixture.page.locator(
            '.main-content .p-tabview-nav a[role=tab]').first.inner_text().strip()
        rebind_at_control_read(fixture.page, monkeypatch, 'reorder', after_click=True)
        assert observe(max_pages=10) is None
        assert fixture.page.evaluate('nativeRebound') is True
        current_caption = fixture.page.locator(
            '.main-content .p-tabview-nav a[role=tab]').first.inner_text().strip()
        assert current_caption != first_caption
        assert fixture.page.evaluate('nativeTabClicks') == [first_caption]
        assert fixture.page.evaluate('window.valueReads') == 0
        assert not fixture.unexpected


@pytest.mark.parametrize('family', FAMILIES)
def test_native_observer_stop_during_post_click_readiness_retry(
        browser, tmp_path, monkeypatch, family):
    with native_case(browser, tmp_path, monkeypatch, family,
                     corporate_groups=True) as (fixture, capture, observe):
        rebind_at_control_read(fixture.page, monkeypatch, after_click=True)

        def stop_after_wait():
            if fixture.page.evaluate('nativeReadinessRetries > 0'):
                raise driver.CaptureCancelled('SYNTHETIC STOP DURING NATIVE READINESS RETRY')

        with pytest.raises(driver.CaptureCancelled):
            observe(max_pages=10, check_cancel=stop_after_wait)
        assert fixture.page.evaluate('nativeRebound') is True
        assert fixture.page.evaluate('nativeReadinessRetries') == 1
        assert len(fixture.page.evaluate('nativeTabClicks')) == 1
        assert fixture.page.evaluate('window.valueReads') == 0
        assert not fixture.unexpected


@pytest.mark.parametrize('family', FAMILIES)
def test_native_observer_accepts_unique_visible_initially_unbound_panel(
        browser, tmp_path, monkeypatch, family):
    with native_case(browser, tmp_path, monkeypatch, family) as (fixture, capture, observe):
        fixture.page.locator('.main-content .p-tabview-nav a[role=tab]').first.evaluate(
            "tab => tab.removeAttribute('aria-controls')")
        forms = observe(max_pages=5)
        assert forms is not None
        assert len(forms) == {'corporate': 1, 'PPN': 7, 'PPh Unifikasi': 4,
                              'PPh Pasal 21/26': 5}[family]
        assert fixture.page.evaluate('window.valueReads') == 0
        assert not fixture.unexpected


@pytest.mark.parametrize('family', FAMILIES)
@pytest.mark.parametrize('outcome', ['hidden', 'foreign', 'duplicate', 'missing', 'caption'])
def test_native_observer_rejects_invalid_rebinding(browser, tmp_path, monkeypatch, family, outcome):
    with native_case(browser, tmp_path, monkeypatch, family) as (fixture, capture, observe):
        rebind_at_control_read(fixture.page, monkeypatch, outcome)
        assert observe(max_pages=5) is None
        assert fixture.page.evaluate('nativeRebound') is True
        assert len(fixture.page.evaluate('nativeTabClicks')) <= 1
        assert fixture.page.evaluate('window.valueReads') == 0
        assert not fixture.unexpected


@pytest.mark.parametrize('family', FAMILIES)
def test_native_observer_stop_during_rebinding_propagates(browser, tmp_path, monkeypatch, family):
    with native_case(browser, tmp_path, monkeypatch, family) as (fixture, capture, observe):
        rebind_at_control_read(fixture.page, monkeypatch)

        def stop():
            if fixture.page.evaluate('Boolean(window.nativeRebound)'):
                raise driver.CaptureCancelled('SYNTHETIC STOP DURING NATIVE REBINDING')

        with pytest.raises(driver.CaptureCancelled):
            observe(max_pages=5, check_cancel=stop)
        assert len(fixture.page.evaluate('nativeTabClicks')) <= 1
        assert fixture.page.evaluate('window.valueReads') == 0
        assert not fixture.unexpected
