"""Fallback visibility never weakens an already observed tab binding."""
from copy import deepcopy

import pytest

import coretax_browser as driver
from test_financial_capture import browser, routed, RECORD, DETAIL


def periodic_record():
    record = deepcopy(RECORD)
    record['meta']['Jenis Pajak'] = 'PPh Pasal 21/26'
    return record


@pytest.mark.parametrize('inactive', ['css', 'ancestor', 'ambiguous'])
def test_unbound_fallback_requires_one_actually_visible_panel(
        routed, tmp_path, monkeypatch, inactive):
    page, requests = routed()
    monkeypatch.setattr(driver, 'DETAIL_PANEL_TIMEOUT', 2)
    page.evaluate('''inactive => {
        document.querySelector('a[aria-controls="l1d"]').closest('li').remove();
        const tab = document.querySelector('a[aria-controls="induk"]');
        tab.removeAttribute('aria-controls');
        tab.onclick = () => {
            const active = document.getElementById('induk');
            const other = document.getElementById('l1d');
            active.hidden = false;
            other.hidden = false;
            if (inactive === 'css') other.style.display = 'none';
            if (inactive === 'ancestor') other.parentElement.hidden = true;
        };
    }''', inactive)

    result = driver.capture_detail(page, record=periodic_record(), folder=tmp_path)

    if inactive == 'ambiguous':
        assert result['capture_complete'] is False
        assert result['sections'] == [] and result['errors']
    else:
        assert result['capture_complete'] is True, result['errors']
        assert [section['name'] for section in result['sections']] == ['Induk']
        assert result['sections'][0]['fields'][0]['value'] == '0000123'
    assert requests == [('GET', DETAIL)]
    assert result['attachments'] == [] and not list(tmp_path.rglob('*.pdf'))


@pytest.mark.parametrize('restore_binding', [False, True])
def test_controlled_tab_never_downgrades_to_the_previous_visible_form(
        routed, tmp_path, monkeypatch, restore_binding):
    page, requests = routed()
    monkeypatch.setattr(driver, 'DETAIL_PANEL_TIMEOUT', 2)
    page.evaluate('''() => {
        const tab = document.querySelector('a[aria-controls="induk"]');
        const click = tab.onclick;
        tab.onclick = event => {
            window.syntheticGapClicked = true;
            return click.call(tab, event);
        };
        tab.addEventListener('synthetic-gap', () => {
            tab.removeAttribute('aria-controls');
            document.getElementById('induk').hidden = true;
            document.getElementById('l1d').hidden = false;
            window.syntheticBindingGap = true;
        }, {once:true});
        tab.addEventListener('synthetic-restore', () => {
            const current = document.getElementById('induk');
            current.id = 'synthetic-restored';
            current.hidden = false;
            document.getElementById('l1d').hidden = true;
            tab.setAttribute('aria-controls', current.id);
            window.syntheticBindingRestored = true;
        }, {once:true});
    }''')
    locator_type = type(page.locator('body'))
    original_get_attribute = locator_type.get_attribute
    gap = restored = False

    def get_attribute(locator, name, *args, **kwargs):
        nonlocal gap, restored
        value = original_get_attribute(locator, name, *args, **kwargs)
        if name == 'aria-controls':
            if (not gap and value == 'induk'
                    and page.evaluate('Boolean(window.syntheticGapClicked)')):
                gap = True
                locator.dispatch_event('synthetic-gap')
            elif gap and restore_binding and not restored and value is None:
                restored = True
                locator.dispatch_event('synthetic-restore')
        return value

    monkeypatch.setattr(locator_type, 'get_attribute', get_attribute)

    result = driver.capture_detail(page, record=periodic_record(), folder=tmp_path)

    assert page.evaluate('Boolean(window.syntheticBindingGap)')
    if restore_binding:
        assert page.evaluate('Boolean(window.syntheticBindingRestored)')
        assert result['capture_complete'] is True, result['errors']
        assert [section['name'] for section in result['sections']] == ['Induk', 'L1D']
        assert result['sections'][0]['fields'][0]['value'] == '0000123'
    else:
        assert result['capture_complete'] is False
        assert [section['name'] for section in result['sections']] == ['L1D']
        assert result['errors']
    assert result['attachments'] == []
    assert requests == [('GET', DETAIL)]
    assert not list(tmp_path.rglob('*.pdf'))


def test_tab_reordering_during_wait_cannot_relabel_another_panel(routed, tmp_path, monkeypatch):
    page, requests = routed()
    monkeypatch.setattr(driver, 'DETAIL_PANEL_TIMEOUT', 2)
    page.evaluate('''() => {
        const tab = document.querySelector('a[aria-controls="induk"]');
        const click = tab.onclick;
        tab.onclick = event => {
            window.syntheticReorderClicked = true;
            return click.call(tab, event);
        };
        tab.addEventListener('synthetic-reorder', () => {
            const list = tab.closest('ul');
            list.prepend(document.querySelector('a[aria-controls="l1d"]').closest('li'));
            document.getElementById('induk').hidden = true;
            document.getElementById('l1d').hidden = false;
            window.syntheticTabsReordered = true;
        }, {once:true});
    }''')
    locator_type = type(page.locator('body'))
    original_inner_text = locator_type.inner_text
    reordered = False

    def inner_text(locator, *args, **kwargs):
        nonlocal reordered
        value = original_inner_text(locator, *args, **kwargs)
        if (not reordered and value == 'Induk'
                and page.evaluate('Boolean(window.syntheticReorderClicked)')):
            reordered = True
            locator.dispatch_event('synthetic-reorder')
        return value

    monkeypatch.setattr(locator_type, 'inner_text', inner_text)

    result = driver.capture_detail(page, record=periodic_record(), folder=tmp_path)

    assert page.evaluate('Boolean(window.syntheticTabsReordered)')
    assert result['capture_complete'] is False
    assert result['errors']
    assert len(result['sections']) == 1
    assert result['sections'][0]['name'] == 'Induk'
    assert result['sections'][0]['fields'][0]['value'] == '0000123'
    assert result['attachments'] == [] and requests == [('GET', DETAIL)]
    assert not list(tmp_path.rglob('*.pdf'))
