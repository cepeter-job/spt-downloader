# Issue 134 metadata and lint audit (2026-11-01)

Baseline production source: `8971bbcb8a981c98e7990a81dd2b7467d4a47231`
(PR165). User selected EXE distribution with commit/run identity and tooling-only
pyproject. See [distribution metadata policy](../ci-dan-rilis.md#kebijakan-metadata-distribusi).

## Original lint evidence

Pinned Ruff0.17.2 on Python3.14.8, [runner41327572683](https://github.com/cepeter-job/spt-downloader/actions/runs/41327572683),
attempt1, diagnostic commit `24ce2c0c75f75b66a66613a455d07da6379d656a`.
Its only additional tracked file is the isolated probe workflow; production/test
bytes match the named baseline. Artifact13091039618 SHA256
`f650c178831e269bb5d4e1000c8824546679cce5901b584df373e39eb720c7b3`
was downloaded and reconciled before editing. This is a finding inventory, not
a passing product/lint gate. No taxpayer material is an input.

`ruff check --select F401,B --output-format json .` reported262findings:
135F401,111B905,8B023,5B007,2B008,1B009. The baseline already has zero findings
for newly adopted B006/B012/B016/B018/B020. Candidate lint and actual negative
rule probes must pass before merge; exact CI/head/artifact evidence belongs in
the PR and issue, rather than rewriting this baseline snapshot.

## Import decisions

33dead bindings are removed after source/cross-module review: two production
bindings (`collections.defaultdict` in exporter and `json` in desktop output)
and31test bindings. There is no remaining consumer in the reviewed import
namespace; this is not a claim about hypothetical external consumers of tests.
The two production compatibility names `coretax.detail_sheet_title` and
`coretax_masa_projection.project_unifikasi_text` remain the original objects.

The first candidate [probe41329808908](https://github.com/cepeter-job/spt-downloader/actions/runs/41329808908)
rejected two remaining parent `importlib` imports after their unused
`importlib.util` imports were removed. These two newly exposed F401 findings in
financial-attachment/Masa test modules are included in the33removals; the
original135finding baseline is retained above. No rule was suppressed.

104bindings become explicit same-name exports:86pytest fixtures, including
forwarded fixtures, and18compatibility names. Pytest resolves those through
module registration/injection; an apparently unused import is not sufficient
reason to remove it. Import order, local binding names and function/decorator
AST bodies remain unchanged. These are targeted reviewed import edits, not Ruff
autofix, formatting or helper relocation. F401 is repository-wide with no new
per-file exclusions or rule suppressions. Full collection/behavior remains a
runner gate, including real isolated synthetic browser fixtures.

## Bugbear decisions

The table below records every baseline finding at its original source location.
S callbacks are invoked/exhausted synchronously inside the same iteration:
financial scope checks, polling, held-reader copies and workflow predicates.
They are not stored for a later iteration. If a future caller defers them,
loop values must be bound explicitly and that lifetime needs a regression test.

N defaults are fixture-only Number(str) tokens; the helpers serialize/read the
text without mutating shared state. P retains getattr for sys._MEIPASS, which
PyInstaller supplies dynamically and the stdlib type stub does not declare.
D names are unused tuple/index slots, not omitted loop bodies or swallowed
assertions. These findings are triaged by behavior, not exempted because tests.

B905 is not enabled in this change. C/M/R pairings retain separate admission,
source count, identity, ordered-row and physical proof checks; L pairings retain
unsupported/unmapped behavior. A/U include bounded known headers/slots.
T includes fixture construction and assertion comparisons. This inventory does
not prove that every zip has equal lengths for arbitrary inputs, or declare
all test comparisons safe. A strictness change must decide each owner's
length policy and test unequal/missing inputs. Neither adding strict=False
mechanically nor silently switching to strict=True is part of this hygiene PR.
No iteration, source gate, truncation, exception or callback behavior changes.

| Source at baseline | Rule | Owner | Disposition |
| --- | --- | --- | --- |
| `coretax.py:124:28` | B905 | `_legacy_resume_proof` | R: record/form/manifest plan pairing; keep physical scope validation |
| `coretax.py:194:31` | B905 | `write_folder_resume` | R: record/form/manifest plan pairing; keep physical scope validation |
| `coretax.py:252:72` | B905 | `_verify_workbook_outputs` | R: record/form/manifest plan pairing; keep physical scope validation |
| `coretax_attachments.py:341:28` | B023 | `check_scope` | S: synchronous callback consumed before its loop advances |
| `coretax_attachments.py:342:29` | B023 | `check_scope` | S: synchronous callback consumed before its loop advances |
| `coretax_badan_template.py:249:37` | B905 | `_l8_body` | L: layout/source pairing; preserve unsupported/unmapped handling |
| `coretax_badan_template.py:521:46` | B905 | `_footer_plan` | L: layout/source pairing; preserve unsupported/unmapped handling |
| `coretax_badan_template.py:541:28` | B905 | `_footer_plan` | L: layout/source pairing; preserve unsupported/unmapped handling |
| `coretax_badan_template.py:632:24` | B905 | `_l1d_growth` | L: layout/source pairing; preserve unsupported/unmapped handling |
| `coretax_badan_template.py:658:22` | B905 | `_body_plan` | L: layout/source pairing; preserve unsupported/unmapped handling |
| `coretax_badan_template.py:739:60` | B905 | `render_template_form` | L: layout/source pairing; preserve unsupported/unmapped handling |
| `coretax_browser.py:510:63` | B023 | `unchanged` | S: synchronous callback consumed before its loop advances |
| `coretax_browser.py:1408:30` | B905 | `_inventory_metadata` | C: source/control/schema pairing; preserve original admission and count gates |
| `coretax_browser.py:1462:26` | B905 | `_inventory_metadata` | C: source/control/schema pairing; preserve original admission and count gates |
| `coretax_browser.py:1868:77` | B905 | `collect_inventory` | C: source/control/schema pairing; preserve original admission and count gates |
| `coretax_browser.py:1869:64` | B905 | `collect_inventory` | C: source/control/schema pairing; preserve original admission and count gates |
| `coretax_browser.py:2481:49` | B905 | `collect_details` | C: source/control/schema pairing; preserve original admission and count gates |
| `coretax_corporate_projection.py:618:29` | B905 | `apply_projections` | C: source/control/schema pairing; preserve original admission and count gates |
| `coretax_corporate_projection.py:1071:28` | B905 | `project_l3` | C: source/control/schema pairing; preserve original admission and count gates |
| `coretax_corporate_projection.py:1092:26` | B905 | `project_l3` | C: source/control/schema pairing; preserve original admission and count gates |
| `coretax_corporate_projection.py:1156:37` | B905 | `project_l3` | C: source/control/schema pairing; preserve original admission and count gates |
| `coretax_corporate_projection.py:1612:25` | B905 | `project_l11a` | C: source/control/schema pairing; preserve original admission and count gates |
| `coretax_exporter.py:602:48` | B905 | `_export_form_workbook` | R: record/form/manifest plan pairing; keep physical scope validation |
| `coretax_exporter.py:604:17` | B905 | `_export_form_workbook` | R: record/form/manifest plan pairing; keep physical scope validation |
| `coretax_exporter.py:752:71` | B905 | `export_workbook` | R: record/form/manifest plan pairing; keep physical scope validation |
| `coretax_exporter.py:819:31` | B905 | `export_split_workbooks` | R: record/form/manifest plan pairing; keep physical scope validation |
| `coretax_json.py:520:32` | B905 | `adapt_inventory_page` | C: source/control/schema pairing; preserve original admission and count gates |
| `coretax_json.py:759:75` | B905 | `_check_corporate_route` | C: source/control/schema pairing; preserve original admission and count gates |
| `coretax_json_capture.py:1044:43` | B023 | `copy_held_json` | S: synchronous callback consumed before its loop advances |
| `coretax_masa_bindings.py:657:67` | B905 | `project_ppn_footer` | C: source/control/schema pairing; preserve original admission and count gates |
| `coretax_masa_templates.py:158:34` | B905 | `_ppn_induk` | L: layout/source pairing; preserve unsupported/unmapped handling |
| `coretax_masa_templates.py:283:34` | B905 | `_unifikasi_induk` | L: layout/source pairing; preserve unsupported/unmapped handling |
| `coretax_masa_templates.py:330:27` | B905 | `_unifikasi_footer` | L: layout/source pairing; preserve unsupported/unmapped handling |
| `coretax_masa_templates.py:404:58` | B905 | `_unifikasi_appendix` | L: layout/source pairing; preserve unsupported/unmapped handling |
| `coretax_masa_templates.py:417:34` | B905 | `_unifikasi_appendix` | L: layout/source pairing; preserve unsupported/unmapped handling |
| `coretax_masa_templates.py:493:25` | B905 | `_ppn_footer` | L: layout/source pairing; preserve unsupported/unmapped handling |
| `coretax_masa_templates.py:502:19` | B905 | `_ppn_footer` | L: layout/source pairing; preserve unsupported/unmapped handling |
| `coretax_masa_templates.py:503:25` | B905 | `_ppn_footer` | L: layout/source pairing; preserve unsupported/unmapped handling |
| `coretax_masa_templates.py:551:30` | B905 | `_ppn_appendix` | L: layout/source pairing; preserve unsupported/unmapped handling |
| `coretax_mpn.py:267:32` | B905 | `dom_numbers_match` | M: ordered MPN pairing; retain independent counts, identity and physical proof |
| `coretax_mpn_browser.py:517:49` | B905 | `_collect_mpn_owned` | M: ordered MPN pairing; retain independent counts, identity and physical proof |
| `coretax_mpn_browser.py:520:76` | B905 | `_collect_mpn_owned` | M: ordered MPN pairing; retain independent counts, identity and physical proof |
| `coretax_mpn_export.py:92:49` | B905 | `export_mpn_workbook` | M: ordered MPN pairing; retain independent counts, identity and physical proof |
| `coretax_mpn_export.py:178:34` | B905 | `read_mpn_proof` | M: ordered MPN pairing; retain independent counts, identity and physical proof |
| `coretax_mpn_ui.py:809:28` | B905 | `_detail_dom` | M: ordered MPN pairing; retain independent counts, identity and physical proof |
| `coretax_pdf.py:112:43` | B023 | `copy_held_pdfs` | S: synchronous callback consumed before its loop advances |
| `coretax_pph21.py:138:65` | B905 | `_induk` | L: layout/source pairing; preserve unsupported/unmapped handling |
| `coretax_pph21.py:194:49` | B905 | `_footer_targets` | L: layout/source pairing; preserve unsupported/unmapped handling |
| `coretax_pph21.py:275:34` | B905 | `_appendix` | L: layout/source pairing; preserve unsupported/unmapped handling |
| `coretax_pph21.py:293:30` | B905 | `_appendix` | L: layout/source pairing; preserve unsupported/unmapped handling |
| `coretax_pph21_projection.py:153:61` | B905 | `project_pph21_forms` | C: source/control/schema pairing; preserve original admission and count gates |
| `coretax_pph21_projection.py:164:58` | B905 | `project_pph21_forms` | C: source/control/schema pairing; preserve original admission and count gates |
| `coretax_pph21_projection.py:174:43` | B905 | `project_pph21_forms` | C: source/control/schema pairing; preserve original admission and count gates |
| `coretax_resume.py:75:48` | B905 | `persist_selection` | R: record/form/manifest plan pairing; keep physical scope validation |
| `coretax_resume_layout.py:122:46` | B905 | `apply_resume_layout` | R: record/form/manifest plan pairing; keep physical scope validation |
| `scripts/ci_shard_benchmark.py:46:53` | B905 | `verify` | A: fixed admin headers or validated benchmark input pairing |
| `scripts/sanitize_resume_template.py:30:47` | B905 | `<module>` | A: fixed admin headers or validated benchmark input pairing |
| `scripts/sanitize_resume_template.py:37:47` | B905 | `<module>` | A: fixed admin headers or validated benchmark input pairing |
| `scripts/sanitize_resume_template.py:39:48` | B905 | `<module>` | A: fixed admin headers or validated benchmark input pairing |
| `spt_desktop/app.py:481:37` | B905 | `selection_dialog` | U: fixed UI slots or owned-control identity pairing |
| `spt_desktop/auth.py:92:42` | B905 | `current` | U: fixed UI slots or owned-control identity pairing |
| `spt_desktop/build_info.py:20:17` | B009 | `resource_root` | P: dynamic PyInstaller attribute at the adopted typed boundary |
| `spt_desktop/output.py:234:45` | B905 | `_workbook_scope` | R: record/form/manifest plan pairing; keep physical scope validation |
| `spt_desktop/ui_views.py:252:50` | B905 | `show_errors` | U: fixed UI slots or owned-control identity pairing |
| `tests/l11a_observer_fixture.py:114:47` | B905 | `document` | T: fixture/assertion pairing; review negative cardinality before strictness changes |
| `tests/l3_observer_fixture.py:94:35` | B905 | `detail` | T: fixture/assertion pairing; review negative cardinality before strictness changes |
| `tests/pph21_projection_fixture.py:39:24` | B905 | `case` | T: fixture/assertion pairing; review negative cardinality before strictness changes |
| `tests/support_l8_spans.py:27:28` | B905 | `html` | T: fixture/assertion pairing; review negative cardinality before strictness changes |
| `tests/support_l8_spans.py:27:73` | B905 | `html` | T: fixture/assertion pairing; review negative cardinality before strictness changes |
| `tests/support_pph21_dom.py:41:17` | B905 | `appendix_table` | T: fixture/assertion pairing; review negative cardinality before strictness changes |
| `tests/support_workflows.py:436:89` | B023 | `validate_measurements` | S: synchronous callback consumed before its loop advances |
| `tests/support_workflows.py:496:79` | B023 | `validate_windows_coverage` | S: synchronous callback consumed before its loop advances |
| `tests/support_workflows.py:515:85` | B023 | `validate_windows_coverage` | S: synchronous callback consumed before its loop advances |
| `tests/test_ci_sharding.py:271:25` | B905 | `test_production_inventory_cli_reads_the_original_manifests` | T: fixture/assertion pairing; review negative cardinality before strictness changes |
| `tests/test_ci_sharding.py:492:25` | B905 | `test_benchmark_comparison_json_is_tied_to_verified_inputs` | T: fixture/assertion pairing; review negative cardinality before strictness changes |
| `tests/test_corporate_dom_structure.py:182:28` | B905 | `test_l1d_corporate_tables_carry_exact_source_structure` | T: fixture/assertion pairing; review negative cardinality before strictness changes |
| `tests/test_corporate_dom_structure.py:203:28` | B905 | `test_l9_corporate_tables_carry_exact_source_structure` | T: fixture/assertion pairing; review negative cardinality before strictness changes |
| `tests/test_corporate_l11a_native.py:120:61` | B905 | `test_l11a_original_packets_keep_five_tables_recap_and_compact_saved_form` | T: fixture/assertion pairing; review negative cardinality before strictness changes |
| `tests/test_corporate_l11a_native.py:130:42` | B905 | `test_l11a_original_packets_keep_five_tables_recap_and_compact_saved_form` | T: fixture/assertion pairing; review negative cardinality before strictness changes |
| `tests/test_corporate_l11a_observer.py:41:94` | B905 | `test_owned_l11a_view_keeps_original_pages_catalogs_checkpoint_and_compact_saved_form` | T: fixture/assertion pairing; review negative cardinality before strictness changes |
| `tests/test_corporate_l11a_projection.py:57:18` | B905 | `inputs` | T: fixture/assertion pairing; review negative cardinality before strictness changes |
| `tests/test_corporate_l11a_projection.py:80:35` | B905 | `inputs` | T: fixture/assertion pairing; review negative cardinality before strictness changes |
| `tests/test_corporate_l11a_projection.py:123:65` | B905 | `test_l11a_preserves_actual_five_tables_source_indices_and_all_unmapped_recap_values` | T: fixture/assertion pairing; review negative cardinality before strictness changes |
| `tests/test_corporate_l11a_projection.py:166:40` | B905 | `test_l11a_clamps_only_the_final_six_cost_sum` | T: fixture/assertion pairing; review negative cardinality before strictness changes |
| `tests/test_corporate_l11a_projection.py:235:27` | B905 | `test_unproved_l11a_predecessor_source_arithmetic_pages_or_metadata_remains_unsupported` | T: fixture/assertion pairing; review negative cardinality before strictness changes |
| `tests/test_corporate_l11c_projection.py:33:16` | B905 | `raw_source` | T: fixture/assertion pairing; review negative cardinality before strictness changes |
| `tests/test_corporate_l11c_projection.py:39:20` | B905 | `raw_source` | T: fixture/assertion pairing; review negative cardinality before strictness changes |
| `tests/test_corporate_l11c_projection.py:107:23` | B905 | `test_l11c_unsafe_ordered_partial_sum_is_not_hidden_by_later_cancellation` | T: fixture/assertion pairing; review negative cardinality before strictness changes |
| `tests/test_corporate_l11c_projection.py:110:26` | B905 | `test_l11c_unsafe_ordered_partial_sum_is_not_hidden_by_later_cancellation` | T: fixture/assertion pairing; review negative cardinality before strictness changes |
| `tests/test_corporate_l7_projection.py:39:16` | B008 | `main` | N: Number(str) token is read/serialized, not mutated by these helpers |
| `tests/test_corporate_l7_projection.py:43:55` | B008 | `project` | N: Number(str) token is read/serialized, not mutated by these helpers |
| `tests/test_corporate_l7_regressions.py:18:23` | B905 | `test_l7_rejects_intermediate_overflow_even_when_final_reported_total_is_safe` | T: fixture/assertion pairing; review negative cardinality before strictness changes |
| `tests/test_corporate_l8_projection.py:51:18` | B905 | `inputs` | T: fixture/assertion pairing; review negative cardinality before strictness changes |
| `tests/test_corporate_l8_projection.py:93:29` | B905 | `test_l8_exact_eight_physical_rows_spans_footer_and_source_destinations` | T: fixture/assertion pairing; review negative cardinality before strictness changes |
| `tests/test_corporate_reviewed_layout.py:23:35` | B905 | `income_fields` | T: fixture/assertion pairing; review negative cardinality before strictness changes |
| `tests/test_corporate_template_layout.py:308:32` | B905 | `test_l9_scalars_follow_labels_through_multiple_table_growths` | T: fixture/assertion pairing; review negative cardinality before strictness changes |
| `tests/test_dated_reference_catalogs.py:59:16` | B007 | `test_dated_grid_labels_follow_reviewed_order_and_date_semantics` | D: unused destructured test slot; iteration and assertions stay unchanged |
| `tests/test_desktop_requested_output_layout.py:104:29` | B905 | `test_every_observed_periodic_tab_and_amendment_has_its_own_sheet` | T: fixture/assertion pairing; review negative cardinality before strictness changes |
| `tests/test_desktop_worker.py:115:49` | B905 | `test_worker_counts_verified_details_once_and_keeps_partial_below_100` | T: fixture/assertion pairing; review negative cardinality before strictness changes |
| `tests/test_financial_publication.py:60:25` | B905 | `test_cli_declares_bound_pdfs_separately_and_preserves_private_bytes` | T: fixture/assertion pairing; review negative cardinality before strictness changes |
| `tests/test_json_inventory.py:556:75` | B905 | `synthetic_listing_browser` | T: fixture/assertion pairing; review negative cardinality before strictness changes |
| `tests/test_json_inventory.py:560:52` | B905 | `synthetic_listing_browser` | T: fixture/assertion pairing; review negative cardinality before strictness changes |
| `tests/test_masa_compact_export.py:72:42` | B905 | `test_pph21_matches_reference_body_capacity_headers_spacers_and_totals` | T: fixture/assertion pairing; review negative cardinality before strictness changes |
| `tests/test_masa_compact_export.py:155:46` | B905 | `test_pph21_growing_groups_keep_all_rows_styles_and_footer_custody` | T: fixture/assertion pairing; review negative cardinality before strictness changes |
| `tests/test_masa_compact_export.py:160:34` | B905 | `test_pph21_growing_groups_keep_all_rows_styles_and_footer_custody` | T: fixture/assertion pairing; review negative cardinality before strictness changes |
| `tests/test_model_workbook_publication.py:139:29` | B905 | `test_corporate_pdf_proof_follows_each_model_file_not_a_fixed_badan_filename` | T: fixture/assertion pairing; review negative cardinality before strictness changes |
| `tests/test_model_workbooks.py:37:39` | B905 | `test_grouping_never_combines_normal_or_distinct_amendment_numbers` | T: fixture/assertion pairing; review negative cardinality before strictness changes |
| `tests/test_mpn_capture_browser.py:64:31` | B905 | `portal` | T: fixture/assertion pairing; review negative cardinality before strictness changes |
| `tests/test_mpn_capture_browser.py:69:28` | B905 | `portal` | T: fixture/assertion pairing; review negative cardinality before strictness changes |
| `tests/test_mpn_parent_binding_diagnostics.py:52:26` | B905 | `inspected_binding` | T: fixture/assertion pairing; review negative cardinality before strictness changes |
| `tests/test_mpn_parent_binding_diagnostics.py:68:47` | B905 | `<module>` | T: fixture/assertion pairing; review negative cardinality before strictness changes |
| `tests/test_period_layout.py:92:42` | B905 | `test_nested_corporate_sections_keep_full_source_identity` | T: fixture/assertion pairing; review negative cardinality before strictness changes |
| `tests/test_pph21_json_footers.py:45:29` | B905 | `fixture` | T: fixture/assertion pairing; review negative cardinality before strictness changes |
| `tests/test_pph21_json_footers.py:93:21` | B905 | `test_null_parent_is_not_misattributed_to_nonexistent_json_children` | T: fixture/assertion pairing; review negative cardinality before strictness changes |
| `tests/test_pph21_json_grids.py:52:16` | B905 | `test_all_grids_preserve_duplicates_literal_identity_page_local_ordinals_and_source` | T: fixture/assertion pairing; review negative cardinality before strictness changes |
| `tests/test_pph21_json_references.py:26:28` | B905 | `source` | T: fixture/assertion pairing; review negative cardinality before strictness changes |
| `tests/test_ppn_json_vat_balance.py:100:25` | B905 | `test_unsafe_component_partial_sum_is_not_hidden_by_safe_final_reported_total` | T: fixture/assertion pairing; review negative cardinality before strictness changes |
| `tests/test_ppn_numeric_layout.py:100:28` | B905 | `test_only_monetary_appendix_columns_become_numeric` | T: fixture/assertion pairing; review negative cardinality before strictness changes |
| `tests/test_ppn_unifikasi_templates.py:172:34` | B905 | `test_induk_identity_fields_use_the_original_slots_without_reformatting` | T: fixture/assertion pairing; review negative cardinality before strictness changes |
| `tests/test_ppn_unifikasi_templates.py:192:34` | B007 | `test_ppn_induk_keeps_repeated_row_labels_bound_to_their_visible_section` | D: unused destructured test slot; iteration and assertions stay unchanged |
| `tests/test_ppn_unifikasi_templates.py:198:13` | B007 | `test_ppn_induk_keeps_repeated_row_labels_bound_to_their_visible_section` | D: unused destructured test slot; iteration and assertions stay unchanged |
| `tests/test_ppn_unifikasi_templates.py:198:26` | B007 | `test_ppn_induk_keeps_repeated_row_labels_bound_to_their_visible_section` | D: unused destructured test slot; iteration and assertions stay unchanged |
| `tests/test_ppn_unifikasi_templates.py:198:49` | B007 | `test_ppn_induk_keeps_repeated_row_labels_bound_to_their_visible_section` | D: unused destructured test slot; iteration and assertions stay unchanged |
| `tests/test_resume_template.py:245:42` | B905 | `legacy_administration` | T: fixture/assertion pairing; review negative cardinality before strictness changes |
| `tests/test_simple_sheet_names.py:80:48` | B905 | `test_amendments_keep_all_forms_in_separate_file_namespaces` | T: fixture/assertion pairing; review negative cardinality before strictness changes |
| `tests/test_simple_sheet_names.py:174:29` | B905 | `test_resume_links_resolve_to_the_right_return_not_only_an_existing_duplicate_form` | T: fixture/assertion pairing; review negative cardinality before strictness changes |
| `tests/test_simple_sheet_names.py:224:28` | B905 | `test_pre_change_forms_only_v1_workbook_remains_verifiable` | T: fixture/assertion pairing; review negative cardinality before strictness changes |

## Deferred architecture work

Literal-mode validation already has a stdlib-only import owner in coretax_json;
filesystem/recovery still depends on coretax and desktop output through multiple
paths. This PR does not claim dependency separation, relocate monkeypatch
namespaces, unify differently bound source readers, or add a worker module.
Those conditional issue134 items retain their separate acceptance requirements.
Historical source counts, old CI results and per-branch native boundaries are
not rewritten. Preceding PR165 renderer timing and PR164 cursor ownership are
preserved; latest main must be reviewed again before merge.
