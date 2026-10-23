"""Observed corporate route shape, with invented identifiers and isolated Edge."""
from copy import deepcopy

import pytest

from support_financial_browser import browser as browser
from support_financial_browser import ORIGIN, RECORD, attachments, downloaded
from support_financial_post import TAXPAYER
from support_financial_post import post_routed as post_routed


CONTEXT = '11111111-2222-4333-8444-555555555555'
DETAIL = (ORIGIN + '/returnsheets/id-ID/corporate-income-tax-return/' + TAXPAYER
          + '/' + RECORD['record_id'] + '/ICT_RCIT/' + CONTEXT)


def record():
    result = deepcopy(RECORD)
    result['list_url'] = ORIGIN + '/returnsheets/id-ID/submitted-returnsheets/' + TAXPAYER
    return result


def test_submitted_corporate_route_downloads_existing_pdf_once(post_routed, tmp_path):
    page, wire = post_routed(detail_url=DETAIL)
    result = attachments().download_financial_attachments(page, record(), tmp_path)
    downloaded(result, tmp_path)
    assert page.evaluate('window.syntheticClicks') == 1
    assert len(wire) == 1
    assert wire[0]['headers']['request_from'] == DETAIL


@pytest.mark.parametrize('detail', [
    DETAIL.replace('/corporate-income-tax-return/', '/unification-return/'),
    DETAIL.replace('/ICT_RCIT/', '/OTHER_FORM/'),
    DETAIL.rsplit('/', 1)[0],
    DETAIL.replace(CONTEXT, 'not-a-context'),
    DETAIL + '/extra',
    DETAIL + '?next=other',
    DETAIL + '#other',
])
def test_other_routes_never_arm_financial_post(post_routed, tmp_path, detail):
    page, wire = post_routed(detail_url=detail)
    result = attachments().download_financial_attachments(page, record(), tmp_path)
    assert result and all(item['status'] == 'PARTIAL' for item in result)
    assert page.evaluate('window.syntheticClicks') == 0
    assert wire == [] and not list(tmp_path.rglob('*.pdf'))


def test_actual_route_scope_change_aborts_before_replay(post_routed, tmp_path):
    page, wire = post_routed(detail_url=DETAIL,
                            change_scope=DETAIL.replace(CONTEXT, '66666666-7777-4888-8999-000000000000'))
    result = attachments().download_financial_attachments(page, record(), tmp_path)
    assert result and all(item['status'] == 'PARTIAL' for item in result)
    assert wire == [] and not list(tmp_path.rglob('*.pdf'))


@pytest.mark.parametrize('detail', [DETAIL.replace(TAXPAYER, 'OTHER_SYNTHETIC_TAXPAYER'),
                                    DETAIL.replace(RECORD['record_id'], 'OTHER_SYNTHETIC_RETURN')])
def test_other_selected_identity_is_rejected_before_discovery(post_routed, tmp_path, detail):
    page, wire = post_routed(detail_url=detail)
    with pytest.raises(RuntimeError, match='selected'):
        attachments().download_financial_attachments(page, record(), tmp_path)
    assert page.evaluate('window.syntheticClicks') == 0
    assert wire == [] and not list(tmp_path.rglob('*.pdf'))


def test_archive_list_is_not_submitted_post_provenance(post_routed, tmp_path):
    page, wire = post_routed(detail_url=DETAIL)
    selected = record()
    selected['list_url'] = selected['list_url'].replace('submitted-returnsheets', 'archivedreturnsheets')
    result = attachments().download_financial_attachments(page, selected, tmp_path)
    assert result and all(item['status'] == 'PARTIAL' for item in result)
    assert page.evaluate('window.syntheticClicks') == 0 and wire == []
