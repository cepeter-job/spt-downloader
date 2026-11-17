"""Runner-only real DOM proof of the D child/history boundary."""
import pytest

import coretax_corporate_l10d as owner
from support_isolated_browser import browser as browser, context as context

CHAIN = '''
<style>rshshr-corporate-income-tax-return,rshshr-citr-main-form,rshshr-citr-l10d-form{display:block}</style>
<rshshr-corporate-income-tax-return><div class="p-tabview">
<ul class="p-tabview-nav"><li><a role="tab" aria-controls="d">L10-D</a></li></ul>
<div class="p-tabview-panels"><p-tabpanel><div class="p-tabview-panel" id="main"><rshshr-citr-main-form></rshshr-citr-main-form></div></p-tabpanel>
<p-tabpanel><div class="p-tabview-panel" id="d"><rshshr-citr-l10d-form><div class="ordinary-child"></div></rshshr-citr-l10d-form></div></p-tabpanel></div>
</div></rshshr-corporate-income-tax-return>
'''


@pytest.fixture
def page(context):
    result = context.new_page()
    result.route('**/*', lambda item: item.abort())
    result.set_default_timeout(500)
    return result


def arm(page):
    page.set_content('<main id="host"></main>')
    document = page.evaluate_handle('() => document')
    return document.evaluate_handle(owner.HISTORY_JS)


def bind(page, history, phase):
    handles = {key: page.query_selector(selector) for key, selector in (
        ('form', 'rshshr-citr-l10d-form'), ('tab', '[role=tab]'), ('panel', '#d'))}
    try:
        return history.evaluate('(h,args) => h.bind(args)', {**handles, 'phase': phase})
    finally:
        for handle in handles.values(): handle.dispose()


def build(page):
    page.evaluate('html => document.querySelector("#host").innerHTML=html', CHAIN)


def test_real_history_has_independent_fresh_main_and_d_owners_and_no_business_reads(page):
    history = arm(page)
    build(page)
    assert bind(page, history, 'start') == {'available': True, 'changed': False, 'complete': False}
    assert bind(page, history, 'end') == {'available': True, 'changed': False, 'complete': True}
    assert history.evaluate('(h) => h.sample()') == {'available': True, 'changed': False, 'complete': True}
    history.evaluate('(h) => h.disconnect()')


@pytest.mark.parametrize('change', ['replace', 'remove-reinsert', 'main-replace', 'root-reinsert',
    'tab-disable', 'aria-disable', 'tab-replace', 'panel-reparent', 'duplicate', 'transient-wrapper',
    'foreign-owner', 'control-binding'])
def test_transient_no_network_child_or_selection_structure_change_cannot_recover(page, change):
    history = arm(page)
    build(page)
    assert bind(page, history, 'start')['available']
    assert bind(page, history, 'end')['complete']
    page.evaluate('''change => {
      const form=document.querySelector('rshshr-citr-l10d-form'),main=document.querySelector('rshshr-citr-main-form');
      const tab=document.querySelector('[role=tab]'),panel=document.querySelector('#d'),li=tab.closest('li');
      if(change==='replace')form.replaceWith(form.cloneNode(true));
      else if(change==='remove-reinsert'){const parent=form.parentNode;form.remove();parent.append(form);}
      else if(change==='main-replace')main.replaceWith(main.cloneNode(true));
      else if(change==='root-reinsert'){const root=document.querySelector('rshshr-corporate-income-tax-return');const parent=root.parentNode;root.remove();parent.append(root);}
      else if(change==='tab-disable'){li.classList.add('p-disabled');li.classList.remove('p-disabled');}
      else if(change==='aria-disable'){tab.setAttribute('aria-disabled','true');tab.removeAttribute('aria-disabled');}
      else if(change==='tab-replace')tab.replaceWith(tab.cloneNode(true));
      else if(change==='panel-reparent'){const parent=panel.parentNode;panel.remove();parent.append(panel);}
      else if(change==='duplicate'){const node=form.cloneNode(true);panel.append(node);node.remove();}
      else if(change==='transient-wrapper'){const w=document.createElement('div');panel.append(w);w.append(document.createElement('rshshr-citr-l10d-form'));w.replaceChildren();w.remove();}
      else if(change==='foreign-owner'){const w=document.createElement('foreign-form');panel.append(w);w.append(form);}
      else {tab.setAttribute('aria-controls','other');tab.setAttribute('aria-controls','d');}
    }''', change)
    state = history.evaluate('(h) => h.sample()')
    assert state['changed'] or not state['available']
    assert not state['complete']


def test_large_unrelated_row_churn_does_not_spend_d_budget_but_later_detach_still_refuses(page):
    history = arm(page)
    build(page)
    assert bind(page, history, 'start')['available']
    assert bind(page, history, 'end')['complete']
    page.evaluate('''() => {
      const table=document.createElement('table');document.body.append(table);
      for(let i=0;i<5000;i++){const row=table.insertRow();row.insertCell().textContent='SYNTHETIC';}
      table.remove();
    }''')
    assert history.evaluate('(h) => h.sample()')['complete']
    page.evaluate("() => document.querySelector('rshshr-citr-l10d-form').remove()")
    assert history.evaluate('(h) => h.sample()')['changed']


@pytest.mark.parametrize('defect', ['stale', 'wrong-caption', 'disabled', 'wrong-panel', 'foreign-main'])
def test_initial_unproved_profile_never_becomes_complete(page, defect):
    if defect == 'stale':
        page.set_content(CHAIN)
        history = page.evaluate_handle('() => document').evaluate_handle(owner.HISTORY_JS)
    else:
        history = arm(page)
        html = CHAIN
        if defect == 'wrong-caption': html = html.replace('>L10-D<', '>L10-B<')
        elif defect == 'disabled': html = html.replace('<li>', '<li class="p-disabled">')
        elif defect == 'wrong-panel': html = html.replace('aria-controls="d"', 'aria-controls="other"')
        else: html = html.replace('<rshshr-citr-main-form>', '<foreign-form><rshshr-citr-main-form>').replace('</rshshr-citr-main-form>', '</rshshr-citr-main-form></foreign-form>')
        page.evaluate('html => document.querySelector("#host").innerHTML=html', html)
    assert not bind(page, history, 'start')['complete']
    assert not bind(page, history, 'end')['complete']


def test_two_boundaries_are_required_and_rebinding_is_not_permission(page):
    history = arm(page)
    build(page)
    assert not history.evaluate('(h) => h.sample()')['complete']
    assert not bind(page, history, 'end')['complete']
    assert not bind(page, history, 'start')['complete']
