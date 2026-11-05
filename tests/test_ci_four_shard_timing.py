"""Contract tests for measured four-way Windows CI rebalancing."""

import hashlib

import pytest

from scripts import ci_tests


# Source/target identities are independent of the production routing table.
# All ten cases recur in successful runs 41993752432, 42030885787, 42044216523.
MEASURED_MOVES = (
    ("tests/test_corporate_template_layout.py::test_binding_stage_preserves_reference_geometry_and_approved_styles", 0, 3),
    ("tests/test_financial_discovery.py::test_financial_link_outside_the_detail_content_is_not_downloaded", 0, 2),
    ("tests/test_financial_discovery.py::test_financial_text_does_not_bind_an_unrecognized_file_table[<thead><tr><th>Other document</th></tr></thead>]", 0, 2),
    ("tests/test_mpn_detail_readiness_browser.py::test_detail_grid_failure_keeps_partial_and_one_inspected_action[missing-json-first]", 0, 2),
    ("tests/test_desktop_dialog_layout.py::test_selection_reflow_preserves_data_and_owned_resources", 0, 2),
    ("tests/test_ppn_json_build_budget.py::test_ppn_main_build_budget_is_bounded_and_scope_specific[ppn-main-ceiling]", 0, 2),
    ("tests/test_mpn_capture_browser.py::test_inspected_detail_action_has_a_bounded_dispatch_budget_without_repeating[5500-False-close]", 0, 2),
    ("tests/test_mpn_capture_browser.py::test_inspected_detail_action_has_a_bounded_dispatch_budget_without_repeating[5500-False-open]", 0, 2),
    ("tests/test_financial_capture.py::test_unsupported_or_absent_financial_control_keeps_structured_capture_partial[]", 1, 2),
    ("tests/test_financial_attachments.py::test_absent_financial_control_is_explicitly_partial_without_an_invented_file", 1, 2),
)


def _hash_shard(nodeid, count):
    digest = hashlib.sha256(nodeid.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") % count


@pytest.mark.parametrize("nodeid, source, target", MEASURED_MOVES)
def test_measured_four_shard_cases_move_only_in_four_way_mode(nodeid, source, target):
    assert _hash_shard(nodeid, 4) == source
    assert ci_tests.workload_for(nodeid) == "windows"
    assert ci_tests.shard_for(nodeid, 4) == target

    expected_two = 1 if nodeid in ci_tests._TIMED_SHARD_ONE else _hash_shard(nodeid, 2)
    assert ci_tests.shard_for(nodeid, 2) == expected_two
    assert ci_tests.shard_for(nodeid, 3) == _hash_shard(nodeid, 3)


def test_unknown_nodes_remain_on_stable_hash_shards():
    nodes = [f"tests/test_future_feature.py::test_new_case[{i}]" for i in range(128)]
    nodes.append("tests/test_financial_discovery.py::test_another_case")
    for node in nodes:
        assert ci_tests.shard_for(node, 4) == _hash_shard(node, 4)


def _completed_outcomes(nodes):
    return {
        node: {phase: ["passed"] for phase in ("setup", "call", "teardown")}
        for node in nodes
    }


def test_four_way_inventory_gate_rejects_hash_only_reversion():
    nodes = [node for node, _, _ in MEASURED_MOVES]
    nodes += [f"tests/test_synthetic.py::test_case[{i}]" for i in range(100)]
    common = {
        "all": sorted(nodes), "workload": "windows", "platform": "win32",
        "python": "3.14.8", "commit": "a" * 40, "exitstatus": 0,
        "run_id": "123", "run_attempt": "1",
    }
    reports = []
    for index in range(4):
        selected = sorted(node for node in nodes if ci_tests.shard_for(node, 4) == index)
        reports.append({
            **common, "selected": selected,
            "shard": {"index": index, "count": 4},
            "outcomes": _completed_outcomes(selected),
        })
    assert all(reports)
    assert ci_tests.check_windows_inventories(
        reports, "3.14.8", "a" * 40, run_id="123", run_attempt="1"
    ) == set(nodes)

    moved, source, target = MEASURED_MOVES[0]
    assert moved in reports[target]["selected"]
    reports[target]["selected"].remove(moved)
    reports[source]["selected"].append(moved)
    reports[source]["outcomes"] = _completed_outcomes(reports[source]["selected"])
    reports[target]["outcomes"] = _completed_outcomes(reports[target]["selected"])
    with pytest.raises(ValueError, match="partition"):
        ci_tests.check_windows_inventories(
            reports, "3.14.8", "a" * 40, run_id="123", run_attempt="1"
        )
