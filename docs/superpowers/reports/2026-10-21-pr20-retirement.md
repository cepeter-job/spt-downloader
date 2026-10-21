# PR20 retirement — residual scenario disposition

## Scope and immutable sources

The owner approved refreshing documentation PR #50 and retaining only useful
residual test scenarios before retiring PR #20. This is not permission to
restore the old implementation, stale templates, or historic live-account
acceptance claims. No deployment or real-taxpayer access is part of this work.

- Current product reviewed: `ecbd9878aa732a379ba94ef848764f9815445003`.
- Legacy PR20 head: `acf77a11cc7928d301791150163735350347c109`.
- Documentation PR50 original head: `7a36b2e6c1c5d0490652be0db15ae94d50f12f42`.
- [Source-only evidence run 39543484013](https://github.com/cepeter-job/spt-downloader/actions/runs/39543484013), artifact `12321025319`, SHA-256 `265651f83ac76417c3d4abd31cc1145afda888a810235ed0bb50753d90e13653`: all three tracked source archives and their manifests were verified. No product execution was needed for this static comparison.

Of PR20's 43 changed paths, 10 are byte-identical to current main, 26 differ,
and seven are absent by path: three historical documents and four test modules.
The absent filenames do not demonstrate missing implementations. The old branch
has broad merge conflicts and predates the separately merged tax-specific/native
and output work. Do not resolve it wholesale by choosing the old versions.

## All 31 legacy test functions

This is a scenario disposition, not a claim that every replacement assertion is
identical. **Identical** is checked by function AST. **Covered** identifies an
existing scenario. **Updated contract** retains the safety purpose under newer
numeric/layout/custody rules. **Superseded** explicitly rejects an obsolete
expectation or cites current source enforcement. **Extracted** is a narrowly
retained characterization test in [PR #60](https://github.com/cepeter-job/spt-downloader/pull/60).
Parameterized functions remain parameterized in their own tests; 31 is the
number of legacy function definitions, not an executed-case count.

### `test_masa_dom_context.py`

| Legacy function | Disposition | Current reference | Reason |
| --- | --- | --- | --- |
| `test_dom_keeps_visible_group_and_footer_boundary` | Covered | [test_ppn_dom_context.py](https://github.com/cepeter-job/spt-downloader/blob/ecbd9878aa732a379ba94ef848764f9815445003/tests/test_ppn_dom_context.py): `test_dom_keeps_visible_group_and_footer_boundary` | Same boundary; synthetic heading renamed. |
| `test_dom_field_context_keeps_visible_group_and_column_label` | Identical | [test_ppn_dom_context.py](https://github.com/cepeter-job/spt-downloader/blob/ecbd9878aa732a379ba94ef848764f9815445003/tests/test_ppn_dom_context.py): `test_dom_field_context_keeps_visible_group_and_column_label` | Function AST identical. |
| `test_dom_does_not_take_group_from_sibling_table` | Identical | [test_ppn_dom_context.py](https://github.com/cepeter-job/spt-downloader/blob/ecbd9878aa732a379ba94ef848764f9815445003/tests/test_ppn_dom_context.py): `test_dom_does_not_take_group_from_sibling_table` | Function AST identical. |

### `test_masa_live_layout.py`

| Legacy function | Disposition | Current reference | Reason |
| --- | --- | --- | --- |
| `test_unifikasi_annotated_header_maps_body` | Updated contract | [test_unifikasi_dom_repair.py](https://github.com/cepeter-job/spt-downloader/blob/ecbd9878aa732a379ba94ef848764f9815445003/tests/test_unifikasi_dom_repair.py): `test_induk_rincian_money_and_reported_total` | Current annotated headers, numeric money and row 10; do not restore row 12/text amounts. |
| `test_unifikasi_explicit_footer_spans_align_total_slots` | Updated contract | [test_unifikasi_dom_repair.py](https://github.com/cepeter-job/spt-downloader/blob/ecbd9878aa732a379ba94ef848764f9815445003/tests/test_unifikasi_dom_repair.py): `test_induk_rincian_money_and_reported_total` | Current totals at row 25 with explicit spans, not legacy row 27. |
| `test_unifikasi_prefixed_bppu_caption_maps_known_columns` | Updated contract | [test_unifikasi_dom_repair.py](https://github.com/cepeter-job/spt-downloader/blob/ecbd9878aa732a379ba94ef848764f9815445003/tests/test_unifikasi_dom_repair.py): `test_daftar_i_dpp_numeric_and_body_boundary_style` | Current BPPU ownership and numeric slots; later approved layout differs. |
| `test_ppn_observed_four_column_layout_binds_headers_not_input_order` | Updated contract | [test_ppn_dom_layout.py](https://github.com/cepeter-job/spt-downloader/blob/ecbd9878aa732a379ba94ef848764f9815445003/tests/test_ppn_dom_layout.py): `test_ppn_observed_four_column_layout_binds_headers_not_input_order` | Preserve empty positions and explicit headers; monetary cells are numeric now. |
| `test_ppn_grid_never_borrows_sibling_accordion_headers` | Identical | [test_ppn_dom_layout.py](https://github.com/cepeter-job/spt-downloader/blob/ecbd9878aa732a379ba94ef848764f9815445003/tests/test_ppn_dom_layout.py): `test_ppn_grid_never_borrows_sibling_accordion_headers` | Function AST identical. |
| `test_unifikasi_unknown_footer_spans_remain_raw` | Extracted | [test_pr20_residual_contracts.py](https://github.com/cepeter-job/spt-downloader/blob/d43dbaf4a609f60642cb9fc6a8b6cac8f976bb8d/tests/test_pr20_residual_contracts.py): `test_unifikasi_induk_wrong_footer_spans_remain_unmapped` | Retain malformed-span safety at current row 25, mapping PARTIAL and Induk raw evidence. |
| `test_ppn_observed_labels_bind_reference_slots_without_restating_template` | Updated contract | [test_ppn_dom_layout.py](https://github.com/cepeter-job/spt-downloader/blob/ecbd9878aa732a379ba94ef848764f9815445003/tests/test_ppn_dom_layout.py): `test_ppn_observed_labels_bind_reference_slots_without_restating_template` | Current reference slots and numeric values, not old string-money assertions. |
| `test_ppn_semantic_aliases_do_not_escape_their_verified_sections` | Updated contract | [test_ppn_dom_layout.py](https://github.com/cepeter-job/spt-downloader/blob/ecbd9878aa732a379ba94ef848764f9815445003/tests/test_ppn_dom_layout.py): `test_ppn_semantic_aliases_do_not_escape_their_verified_sections` | Fail-closed section binding retained; later clean-display rules replace raw-block expectations. |
| `test_ppn_grid_does_not_assign_amount_units_to_plain_text_metadata` | Identical | [test_ppn_dom_layout.py](https://github.com/cepeter-job/spt-downloader/blob/ecbd9878aa732a379ba94ef848764f9815445003/tests/test_ppn_dom_layout.py): `test_ppn_grid_does_not_assign_amount_units_to_plain_text_metadata` | Function AST identical. |

### `test_masa_mapping_regressions.py`

| Legacy function | Disposition | Current reference | Reason |
| --- | --- | --- | --- |
| `test_observed_alias_selects_template` | Covered | [test_ppn_dom_mapping.py](https://github.com/cepeter-job/spt-downloader/blob/ecbd9878aa732a379ba94ef848764f9815445003/tests/test_ppn_dom_mapping.py): `test_observed_alias_selects_template` | PPN aliases here; Unifikasi aliases in test_hyphenated_dom_forms_use_template. |
| `test_pph21_ordinal_table_bound_by_entire_row_signature` | Superseded | [test_pph21_dom_mapping.py](https://github.com/cepeter-job/spt-downloader/blob/ecbd9878aa732a379ba94ef848764f9815445003/tests/test_pph21_dom_mapping.py): `test_induk_generic_names_use_groups_labels_and_exact_tooltip_alias` | Current coretax_pph21._induk requires visible owner/caption; do not restore ordinal-only positive inference. |
| `test_ordinal_single_ambiguous_pph21_row_not_guessed` | Superseded | [test_pph21_dom_mapping.py](https://github.com/cepeter-job/spt-downloader/blob/ecbd9878aa732a379ba94ef848764f9815445003/tests/test_pph21_dom_mapping.py): `test_induk_ambiguity_is_reported_not_guessed_or_shifted` | Current owner/mapping checks reject unbound rows. Old raw-display assertion is obsolete; source inspection is not an exact duplicate test claim. |
| `test_lia_date_header_maps_body_but_not_short_footer` | Updated contract | [test_pph21_dom_mapping.py](https://github.com/cepeter-job/spt-downloader/blob/ecbd9878aa732a379ba94ef848764f9815445003/tests/test_pph21_dom_mapping.py): `test_lia_reported_totals_use_g_and_i_not_condensed_c_and_e` | Current annotated-header fixture and explicit body/footer spans; invalid boundary cases separately stay partial. |
| `test_numeric_zero_body_values_are_not_treated_as_empty` | Extracted | [test_pr20_residual_contracts.py](https://github.com/cepeter-job/spt-downloader/blob/d43dbaf4a609f60642cb9fc6a8b6cac8f976bb8d/tests/test_pr20_residual_contracts.py): `test_zero_only_body_row_is_not_confused_with_blank_or_footer` | Direct shared-boundary contract avoids masking numeric zero with other nonempty columns. Existing export numeric tests remain. |
| `test_pph21_group_evidence_not_ordinal` | Covered | [test_pph21_template.py](https://github.com/cepeter-job/spt-downloader/blob/ecbd9878aa732a379ba94ef848764f9815445003/tests/test_pph21_template.py): `test_two_groups_are_bound_to_captions_not_capture_order` | Current caption/group selection preserves source-order independence. |
| `test_unifikasi_qualified_headers_preserve_raw` | Updated contract | [test_unifikasi_dom_repair.py](https://github.com/cepeter-job/spt-downloader/blob/ecbd9878aa732a379ba94ef848764f9815445003/tests/test_unifikasi_dom_repair.py): `test_induk_rincian_money_and_reported_total` | Current alias handling and export deepcopy guard preserve source; obsolete text-money expectations are not restored. |
| `test_ppn_scalar_field_maps_to_amount_slot` | Updated contract | [test_ppn_dom_mapping.py](https://github.com/cepeter-job/spt-downloader/blob/ecbd9878aa732a379ba94ef848764f9815445003/tests/test_ppn_dom_mapping.py): `test_ppn_scalar_field_maps_to_amount_slot` | Current verified slot uses native numeric money. |
| `test_ppn_duplicate_scalar_not_arbitrarily_selected` | Updated contract | [test_ppn_dom_mapping.py](https://github.com/cepeter-job/spt-downloader/blob/ecbd9878aa732a379ba94ef848764f9815445003/tests/test_ppn_dom_mapping.py): `test_ppn_duplicate_scalar_not_arbitrarily_selected` | Ambiguity remains unmapped; clean forms use audit/checkpoint rather than duplicated raw block. |
| `test_ppn_repeated_label_uses_group_column_not_order` | Updated contract | [test_ppn_dom_mapping.py](https://github.com/cepeter-job/spt-downloader/blob/ecbd9878aa732a379ba94ef848764f9815445003/tests/test_ppn_dom_mapping.py): `test_ppn_repeated_label_uses_group_column_not_order` | Group/column ownership retained with numeric monetary output. |
| `test_ppn_appendix_dom_headers_and_extra_source_column` | Updated contract | [test_ppn_dom_mapping.py](https://github.com/cepeter-job/spt-downloader/blob/ecbd9878aa732a379ba94ef848764f9815445003/tests/test_ppn_dom_mapping.py): `test_ppn_appendix_dom_headers_and_extra_source_column` | Known columns retained; raw-display expectation replaced by current clean-layout contract. |
| `test_unifikasi_observed_group_and_extra_headers_do_not_invent_gross_income` | Superseded | [test_unifikasi_dom_repair.py](https://github.com/cepeter-job/spt-downloader/blob/ecbd9878aa732a379ba94ef848764f9815445003/tests/test_unifikasi_dom_repair.py): `test_daftar_i_dpp_numeric_and_body_boundary_style` | Approved DAFTAR-I layout now names the DPP column, stores numeric DPP, preserves spacer and omits redundant extras. Do not reinstate the old blank-gross-column layout. |
| `test_resume_reports_unmapped_template_evidence` | Covered | [test_ppn_dom_mapping.py](https://github.com/cepeter-job/spt-downloader/blob/ecbd9878aa732a379ba94ef848764f9815445003/tests/test_ppn_dom_mapping.py): `test_resume_reports_unmapped_template_evidence` | Current resume mapping status remains distinct from capture completeness. |

### `test_pph21_observed_panels.py`

| Legacy function | Disposition | Current reference | Reason |
| --- | --- | --- | --- |
| `test_nested_primeng_titles_bind_own_tables` | Extracted | [test_pr20_residual_contracts.py](https://github.com/cepeter-job/spt-downloader/blob/d43dbaf4a609f60642cb9fc6a8b6cac8f976bb8d/tests/test_pr20_residual_contracts.py): `test_nested_primeng_tables_use_their_own_visible_heading` | Pin generic DOM capture group, independently from corporate source_structure and native observer tests. |
| `test_named_government_block_accepts_observed_label` | Updated contract | [test_pph21_dom_mapping.py](https://github.com/cepeter-job/spt-downloader/blob/ecbd9878aa732a379ba94ef848764f9815445003/tests/test_pph21_dom_mapping.py): `test_induk_generic_names_use_groups_labels_and_exact_tooltip_alias` | Fixture includes government aliases at rows 21/35; values now numeric and reference labels preserved. |
| `test_induk_annotation_keeps_amount_and_literal_label` | Superseded | [test_pph21_dom_mapping.py](https://github.com/cepeter-job/spt-downloader/blob/ecbd9878aa732a379ba94ef848764f9815445003/tests/test_pph21_dom_mapping.py): `test_induk_generic_names_use_groups_labels_and_exact_tooltip_alias` | Annotated source remains immutable; approved reference labels are no longer overwritten by source tooltips. |
| `test_appendix_projects_known_extras_but_not_footer` | Updated contract | [test_pph21_dom_mapping.py](https://github.com/cepeter-job/spt-downloader/blob/ecbd9878aa732a379ba94ef848764f9815445003/tests/test_pph21_dom_mapping.py): `test_optional_second_group_and_reported_totals_remain_separate` | Current fixtures include known extra columns and body/footer boundaries; obsolete extra raw display is not revived. |
| `test_government_alias_never_fills_deducted_block` | Updated contract | [test_pph21_dom_mapping.py](https://github.com/cepeter-job/spt-downloader/blob/ecbd9878aa732a379ba94ef848764f9815445003/tests/test_pph21_dom_mapping.py): `test_induk_ambiguity_is_reported_not_guessed_or_shifted` | Current _induk limits government aliases to owned government blocks and exact row labels. Assessment includes source, not a claimed byte-identical old case. |
| `test_unknown_appendix_column_still_blocks_projection` | Covered | [test_pph21_dom_mapping.py](https://github.com/cepeter-job/spt-downloader/blob/ecbd9878aa732a379ba94ef848764f9815445003/tests/test_pph21_dom_mapping.py): `test_invalid_appendix_evidence_stays_partial_without_displaying_raw_block` | Unknown-column parameter rejects mapping; source retained without reinstating raw display. |

## Extraction boundary and verification

Only three characterization tests are added in `tests/test_pr20_residual_contracts.py`:
nearest visible PrimeNG table heading, a numeric zero-only body row versus blanks
and declared footer, and invalid Unifikasi Induk footer spans with current row25,
truthful incomplete mapping and preserved Induk evidence. The single private
helper contract is deliberate: an exporter row with other nonempty identity
cells could mask loss of a numeric zero-only row at the shared boundary.

No production source, resources, dependencies, existing tests, workflow or
consent/output rule changes are needed. Existing code is expected to satisfy
these characterization tests; this is not a fabricated new bugfix RED/GREEN
claim. Full runtime verification and exact package results belong to PR60's
pinned CI record, not to documentation-only CI for PR50. The old branch's green
run38842825670 is historical and does not validate a merge with current main.

Independent source review found no blocking omission and confirmed the three
retained tests are meaningful and nonredundant. One exact legacy negative case,
`test_government_alias_never_fills_deducted_block`, has no standalone current
equivalent. Current `coretax_pph21._induk` restricts government-alias
normalization to government-owned blocks and matches labels within the selected
block. That source guard is present; the optional extra negative test remains a
coverage limitation, not a claim of identical test coverage or a missing
implementation. Do not recreate obsolete string-money/raw-display assertions
merely to make the old module run unchanged.

The three historical PR20 documents remain available in that immutable branch
and its PR history. They are not restored as active instructions: their earlier
native-Masa eligibility/merge gates and display requirements were superseded by
separate deliveries. Closing PR20 means its implementation branch is retired,
not that every tax type has new live-account acceptance. Existing data/privacy,
PARTIAL, native eligibility and output verification boundaries remain in force.

The current UI/UX documentation uses the 21October product snapshot, 54 text IDs,
implemented folder validation, the measured filter improvement and explicit
unmet opening/full-size200% objectives. The 20October baseline is preserved
verbatim below a historical banner, never silently relabelled as current.

## Exact execution record for the retained tests

[PR #60](https://github.com/cepeter-job/spt-downloader/pull/60) merged as
`c6e2c4031338c335653cc2bf4e13e8c57918239f`. Its only delta from runtime baseline
`ecbd987` is `tests/test_pr20_residual_contracts.py`; no production source or
existing test changed. Exact head `d43dbaf4a609f60642cb9fc6a8b6cac8f976bb8d`
and runner checkout `d4babaaee93cb2873371d8b8fb99d1fc23ffc3e6` share the actual
merge tree `f755d41be9884a344a1539eee97dcf92f480d234`.

[Run 39543975621](https://github.com/cepeter-job/spt-downloader/actions/runs/39543975621)
completed successfully on attempt 1: **3,380 Windows cases and 456 portable
cases**, zero failures/errors/skips. All three retained cases appear in Windows
JUnit. Both collectors contain the same 3,380 unique nodes; portable is an
explicit subset, so the two passing counts are not added as unique coverage.

Dependency audit, CodeQL, fresh managed-worker setup/reuse, source/frozen GUI
checks, exact-ID artifact download and the aggregate gate passed. Package
`12321477756`, ZIP SHA-256
`bffd47d2c8fadcbc7f6427d3ba7e177773d17fda2da8ed17c43d8e4f852a0f84`, was downloaded
independently: six CI artifact ZIP digests, five package files, four payload
checksums and the exact 39 worker resources all matched. Frozen metadata keeps
CPython 3.14.8/x64/GIL, uv 0.13.4, `credentials_accessed=false` and
`live_scrape=false`. The executable was not run locally or installed.

The PR50 documentation-only route is separate from this test/build evidence.
This record supports retiring the superseded PR20 branch after preserving the
three scenarios; it does not establish new live-account acceptance, resolve
the existing opening-time/DPI objectives, or authorize a release/deployment.
