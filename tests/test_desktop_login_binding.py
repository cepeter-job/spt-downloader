"""Portable orchestration checks model Playwright's lazy locators; browser tests
exercise the same document changes with real DOMs on Windows.
"""
from types import SimpleNamespace

import pytest

from spt_desktop import auth
from spt_desktop.credentials import Login


ORIGIN = 'https://satu.intranet.pajak.go.id'


class Form:
    def __init__(self, page):
        self.page = page
        self.action = ORIGIN + '/session'

    def evaluate(self, expression, button):
        return self.page.form is self and button.form is self


class Element:
    def __init__(self, page, form, name):
        self.page, self.form, self.name = page, form, name

    def evaluate_handle(self, expression):
        return self.form

    def evaluate(self, expression, other=None):
        if other is not None:
            return self.form is self.page.form and self is other
        return {'action': self.form.action, 'method': 'post'}

    def fill(self, value, **kwargs):
        self.page.actions.append(self.name)
        if self.name == self.page.mutate_on_fill:
            self.form.action = ORIGIN + '/authentication'

    def click(self, **kwargs):
        self.page.actions.append('submit')


class Locator:
    def __init__(self, page, name):
        self.page, self.name = page, name

    def element_handle(self):
        return self.page.elements[self.name]

    def fill(self, *args, **kwargs):
        self.element_handle().fill(*args, **kwargs)

    def click(self, **kwargs):
        self.element_handle().click(**kwargs)


def new_document(page):
    page.form = Form(page)
    page.elements = {name: Element(page, page.form, name) for name in ('identifier', 'password', 'button')}


@pytest.fixture
def login_page(monkeypatch):
    page = SimpleNamespace(url=ORIGIN + '/login', actions=[], mutate_on_fill=None)
    new_document(page)
    monkeypatch.setattr(auth, '_login_fields', lambda current: (
        auth._origin(current.url), *(Locator(current, name) for name in ('identifier', 'password', 'button'))))
    return page


@pytest.mark.parametrize('change', ['origin', 'form', 'action'])
def test_credential_read_cannot_rebind_the_inspected_document(login_page, monkeypatch, change):
    page = login_page

    def read(origin):
        assert origin == ORIGIN
        if change == 'origin':
            page.url = 'https://evil.invalid/login'
            new_document(page)
        elif change == 'form':
            new_document(page)
        else:
            page.form.action = ORIGIN + '/authentication'
        return Login('SYNTHETIC_ACCOUNT', 'SYNTHETIC_PASSWORD_ONLY')

    monkeypatch.setattr(auth, 'read_login', read)
    assert not auth.try_saved_login(page, lambda: None)
    assert page.actions == []


@pytest.mark.parametrize('changed_by', ['identifier', 'password'])
def test_filling_a_field_cannot_change_the_next_inspected_action(login_page, monkeypatch, changed_by):
    page = login_page
    page.mutate_on_fill = changed_by
    monkeypatch.setattr(auth, 'read_login', lambda origin: Login('SYNTHETIC_ACCOUNT', 'SYNTHETIC_PASSWORD_ONLY'))
    assert not auth.try_saved_login(page, lambda: None)
    assert page.actions == (['identifier'] if changed_by == 'identifier' else ['identifier', 'password'])


def test_unchanged_inspected_login_can_submit_once(login_page, monkeypatch):
    monkeypatch.setattr(auth, 'read_login', lambda origin: Login('SYNTHETIC_ACCOUNT', 'SYNTHETIC_PASSWORD_ONLY'))
    assert auth.try_saved_login(login_page, lambda: None)
    assert login_page.actions == ['identifier', 'password', 'submit']
