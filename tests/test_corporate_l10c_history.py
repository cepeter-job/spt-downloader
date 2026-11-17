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
<tbody><tr><td>DO NOT READ</td></tr></tbody></table></p-table></ui-grid-offline></rsh-citr-l10c-grid1>
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


def test_real_l10c_history_binds_owned_disabled_controls_without_values(browser):
    context, page, document, history = armed(browser)
    try:
        assert bind(page, history, 'start') == {'available': True, 'changed': False, 'complete': False}
        assert bind(page, history, 'end') == {'available': True, 'changed': False, 'complete': True}
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
    'header-control-replaced', 'radio-enabled-restored', 'duplicate-grid', 'induk-replaced'])
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
