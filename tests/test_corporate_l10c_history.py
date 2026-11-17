"""Actual MutationObserver semantics for C-owned structure; hosted Edge only."""
import pytest

from test_json_hybrid_native import browser as browser

HTML = '''<style>rshshr-corporate-income-tax-return,rshshr-citr-main-form,
rshshr-citr-l10c-form,rsh-citr-l10c-grid1,ui-grid-offline,p-table{display:block}</style>
<rshshr-corporate-income-tax-return><rshshr-citr-main-form></rshshr-citr-main-form>
<div class="p-tabview"><ul><li><a role="tab" aria-controls="c" href="#c">L10-C</a></li></ul>
<div id="c" class="p-tabview-panel"><rshshr-citr-l10c-form><form>
<input formcontrolname="PeriodYear" disabled><input formcontrolname="CollectorTin" disabled>
<p-radiobutton formcontrolname="Question"><input type="radio" disabled></p-radiobutton>
<p-radiobutton formcontrolname="Question"><input type="radio" disabled></p-radiobutton>
<rsh-citr-l10c-grid1><ui-grid-offline><p-table><table><thead><tr><th>NO.</th></tr></thead>
<tbody><tr><td>DO NOT READ</td></tr></tbody></table><p-paginator><div class="p-paginator">
<p-dropdown><input type="text"></p-dropdown></div></p-paginator></p-table></ui-grid-offline></rsh-citr-l10c-grid1>
</form></rshshr-citr-l10c-form></div></div></rshshr-corporate-income-tax-return>'''


def armed(browser):
    import coretax_json_capture as capture
    script = getattr(capture, '_L10C_HISTORY', None)
    assert isinstance(script, str), 'Source-only RED: no independently owned C history'
    context = browser.new_context()
    page = context.new_page()
    document = page.evaluate_handle('() => document')
    history = document.evaluate_handle(script)
    page.set_content(HTML)
    page.evaluate('''() => {
      for(const prop of ['value','checked'])Object.defineProperty(HTMLInputElement.prototype,prop,
        {get(){throw Error('FORBIDDEN BUSINESS READ')},configurable:true});
    }''')
    return context, page, document, history


def bind(page, history, phase):
    args = page.evaluate_handle('''phase => ({phase,
        form:document.querySelector('rshshr-citr-l10c-form'),
        grid:document.querySelector('rsh-citr-l10c-grid1'),table:document.querySelector('table'),
        tab:document.querySelector('[role=tab]'),panel:document.querySelector('.p-tabview-panel')})''', phase)
    try:
        return history.evaluate('(h,args) => h.bind(args)', args)
    finally:
        args.dispose()


def test_corporate_observer_calls_the_real_c_owned_binding_protocol(browser):
    import coretax_corporate as observer
    from coretax_json_capture import DetailJsonCapture
    inspect = getattr(observer, '_observe_l10c_history', None)
    assert callable(inspect), 'Source-only RED: C child producer has no observer caller'
    context = browser.new_context()
    page = context.new_page()
    page.set_content(HTML)
    calls = []

    class Capture:
        def bind_l10c_structure(self, form, grid, table, tab, panel, *, phase, check_cancel=None):
            calls.append(phase)
            assert form.locator('rsh-citr-l10c-grid1').count() == 1
            assert grid.locator('table').count() == table.count() == tab.count() == panel.count() == 1
            return True

        def observe_l10c_lifetime(self, *, check_cancel=None):
            calls.append('sample')
            return {'kind': 'corporate-l10c-spa-v1'}

    try:
        assert callable(DetailJsonCapture.bind_l10c_structure)
        assert inspect(page.locator('rshshr-citr-l10c-form'), page.locator('[role=tab]'),
                       page.locator('.p-tabview-panel'), Capture(), None) is True
        assert calls == ['start', 'end', 'sample']
    finally:
        context.close()


@pytest.mark.parametrize('defect', ['protocol', 'controls', 'grid', 'start', 'end', 'sample'])
def test_c_observer_never_upgrades_an_unavailable_child_protocol(browser, defect):
    import coretax_corporate as observer
    context = browser.new_context()
    page = context.new_page()
    page.set_content(HTML)

    class Capture:
        def bind_l10c_structure(self, *args, phase, **kwargs):
            return defect != phase

        def observe_l10c_lifetime(self, **kwargs):
            return None if defect == 'sample' else {'kind': 'corporate-l10c-spa-v1'}

    try:
        if defect == 'controls':
            page.locator('[formcontrolname=PeriodYear]').evaluate('(e) => e.remove()')
        elif defect == 'grid':
            page.locator('table').evaluate('(e) => e.after(e.cloneNode(true))')
        assert observer._observe_l10c_history(page.locator('rshshr-citr-l10c-form'),
            page.locator('[role=tab]'), page.locator('.p-tabview-panel'),
            object() if defect == 'protocol' else Capture(), None) is False
    finally:
        context.close()


def test_real_l10c_history_binds_owned_disabled_controls_without_values(browser):
    context, page, document, history = armed(browser)
    try:
        assert bind(page, history, 'start') == {'available': True, 'changed': False, 'complete': False}
        assert bind(page, history, 'end') == {'available': True, 'changed': False, 'complete': True}
        assert history.evaluate('(h) => h.sample()')['complete'] is True
        from coretax_json_capture import _L10C_FINAL_SAMPLE
        final = history.evaluate(_L10C_FINAL_SAMPLE)
        assert final['state']['complete'] is True and type(final['clock']['epoch_ms']) is int
        assert isinstance(final['clock']['timezone'], str)
        page.evaluate('''() => {const li=document.querySelector('li');
            li.classList.add('p-highlight');li.classList.remove('p-highlight');}''')
        assert history.evaluate('(h) => h.sample()')['complete'] is True
        # Renderer row churn is not a new child or a shared history budget.
        page.evaluate('''() => {const body=document.querySelector('tbody');
            for(let i=0;i<5000;i++){const row=document.createElement('tr');
              row.innerHTML='<td>UNRELATED ROW CHURN</td>';body.append(row);row.remove();}}''')
        assert history.evaluate('(h) => h.sample()')['complete'] is True
    finally:
        history.evaluate('(h) => h.disconnect()')
        history.dispose()
        document.dispose()
        context.close()


@pytest.mark.parametrize('defect', ['remount', 'detach-reinsert', 'disable-reenable',
    'header-control-replaced', 'radio-enabled-restored', 'duplicate-grid', 'induk-replaced',
    'header-caption', 'footer-added', 'header-replaced-restored', 'footer-added-removed'])
def test_real_l10c_history_retains_same_turn_changes_after_final_shape_is_restored(browser, defect):
    context, page, document, history = armed(browser)
    changes = {
        'remount': "const n=document.querySelector('rshshr-citr-l10c-form');n.replaceWith(n.cloneNode(true));",
        'detach-reinsert': "const n=document.querySelector('rsh-citr-l10c-grid1'),p=n.parentNode;p.removeChild(n);p.append(n);",
        'disable-reenable': "const n=document.querySelector('li');n.classList.add('p-disabled');n.classList.remove('p-disabled');",
        'header-control-replaced': "const n=document.querySelector('[formcontrolname=PeriodYear]');n.replaceWith(n.cloneNode(true));",
        'radio-enabled-restored': "const n=document.querySelector('[type=radio]');n.removeAttribute('disabled');n.setAttribute('disabled','');",
        'duplicate-grid': "const n=document.querySelector('rsh-citr-l10c-grid1'),x=n.cloneNode(true);n.after(x);x.remove();",
        'induk-replaced': "const n=document.querySelector('rshshr-citr-main-form');n.replaceWith(n.cloneNode(true));",
        'header-caption': "document.querySelector('th').firstChild.data='UNREVIEWED HEADER';",
        'footer-added': "document.querySelector('table').createTFoot().insertRow().insertCell().textContent='UNREVIEWED FOOTER';",
        'header-replaced-restored': "const h=document.querySelector('thead');const t=h.parentElement;h.remove();t.prepend(h);",
        'footer-added-removed': "const f=document.querySelector('table').createTFoot();f.insertRow().insertCell().textContent='TRANSIENT FOOTER';f.remove();",
    }
    try:
        assert bind(page, history, 'start')['available'] is True
        assert bind(page, history, 'end')['complete'] is True
        page.evaluate('() => {' + changes[defect] + '}')
        assert history.evaluate('(h) => h.sample()')['changed'] is True
    finally:
        history.evaluate('(h) => h.disconnect()')
        history.dispose()
        document.dispose()
        context.close()
