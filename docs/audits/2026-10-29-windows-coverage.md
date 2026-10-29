# Representative Windows coverage and security behavior evidence

Issue130 adopts separate line, branch, module and changed-line gates. The full
Windows suite, including local synthetic Edge, native sharing/Job Objects and Tk
fixtures, runs under pinned coverage7.17.0 with the existing `.coveragerc`.
Both fixed shards (or the complete serial mode) retain their raw data, original
test inventory and line/branch reports. Before packaging, the existing complete
Windows/portable inventory gate still runs. A separate gate validates the exact
Windows commit/run/attempt, successful setup/call/teardown for every collected
node and the fixed disjoint partition before combining only its declared files.
Missing, reversed, failed, foreign or incomplete evidence cannot authorize a
package. Portable data is never an input to the Windows ratchet.

Each original raw database must independently load with nonempty branch
measurements. Combination uses a direct data update for every declared input;
read/update errors fail the job. The coverage CLI's warning-and-skip combine
behavior is deliberately not used. Actual pinned-database regressions cover a
nonempty corrupt shard, an empty database and a line-only database, even when the
other shard alone exceeds deliberately low floors. A positive case proves both
separate line contributions survive into the published gate report.

The Windows Python parent measures native/browser orchestration and in-process
worker logic. Isolated managed-worker/bootstrap subprocesses and browser
JavaScript remain unmeasured by this Python report. Their existing source/frozen,
cold/reuse/cancel and package checks remain independent. No subprocess coverage
injection or runtime dependency is added. No source omit pattern is added:
`tests/*` and `.venv/*` remain the sole existing omissions.

## Metrics and policy

`coverage-policy.json` owns the separate acceptance floors; `.coveragerc` remains
the sole source/branch/omit/reporting policy. Coverage's combined percentage is
not used as a line or branch percentage. Every adopted module must be present
with a nonempty statement denominator. A zero-branch module can have only a zero
branch floor. All counters and source line lists must agree, including global
totals. Exact integer products decide acceptance; display rounding cannot turn
79.9 into80. Changed executable production lines have an80% line floor. Blank,
comment and docstring-only changes do not manufacture covered statements.
Changed excluded lines and changed unmeasured production modules are refused.
PRs use the literal base commit; main pushes use their literal preceding commit.
Pure comment-only files are excluded only when their entire non-comment Python
token stream is identical in both immutable commits. Indentation, statement
boundaries, strings, annotations and operators remain significant. Mixed
code/comment files are conservatively counted in full, and new files always
count; a comment cannot hide an actual executable change or lower the80% floor.
Manual/scheduled runs without a diff base record no diff metric, while all
global/module and complete-Windows gates remain mandatory.

Synthetic gate tests cover missing shard/module/data, reversed or previous-run
evidence, unsuccessful cases, malformed counters/lists, case aliases, separate
line/branch regressions, fractional boundaries, changed exclusions and exact Git
added-line parsing. Workflow mutation tests additionally reject missing raw
data/inventory, wrong artifact names/slots, missing instrumentation/config,
masked failures and a gate moved after packaging.

## Enumerated critical behaviors

The following matrix defines the security acceptance behaviors for this change.
Every named test and its parameter cases must pass in the complete Windows
inventory. This is explicit behavior coverage, not a claim of100% Python lines,
all possible attacks or live Coretax acceptance. The broader unchanged negative
test suite also remains mandatory.

| Behavior | Actual synthetic assertions |
| --- | --- |
| Exception contents and hostile conversion stay out of public/checkpoint output; safe original type/frames remain | `test_browser_safety.py::test_detail_failure_keeps_private_exception_text_out_of_outputs`, `test_detail_failure_does_not_stringify_the_exception`; `test_cli_failure_recovery.py::test_safe_diagnostics_keep_original_failure_type_without_exception_content` |
| Closed diagnostic schema drops secret fields and arbitrary objects without conversion; storage faults preserve the operation | `test_diagnostics.py::test_sensitive_fields_and_exception_content_never_enter_any_log`, `test_untrusted_values_are_not_stringified_or_used_as_numeric_counters`, `test_storage_failure_is_silent_and_does_not_change_original_exception` |
| Failed capture/Stop preserves verified bytes and exit1/130, attempts all owned cleanup and handles partial driver startup | `test_cli_failure_recovery.py::test_capture_failure_checkpoints_partial_without_retrying_export`, `test_failed_atomic_checkpoint_keeps_old_bytes_and_original_exit`, `test_original_failure_survives_cleanup_errors_and_all_resources_are_attempted`, `test_partially_acquired_driver_is_closed_when_enter_raises` |
| Foreign/pre-attempt and secret responses never become JSON evidence; Stop after body read prevents persistence | `test_json_capture.py::test_foreign_or_pre_epoch_requests_never_become_detail_evidence`, `test_secret_bearing_outer_or_embedded_json_is_rejected_whole_not_redacted`, `test_stop_after_driver_body_read_never_persists_that_body` |
| Selected evidence changes, wrong taxpayer, collisions and interrupted publication cannot overwrite or advertise success | `test_output_safety.py::test_cli_keeps_changed_selected_json_before_replacing_any_output`, `test_checkpoint_manifest_cannot_authorize_overwriting_other_taxpayer`, `test_case_insensitive_existing_filename_collision_is_rejected`, `test_interrupt_immediately_after_replace_rolls_back_that_file` |
| Credentials bind only exact authorized origins and invalid values are rejected before native writes | `test_desktop_credentials.py::test_credential_binding_rejects_nonexact_origin`, `test_invalid_credential_is_rejected_before_native_write` |
| Financial POST requires approved source/owner/selected request, and Stop blocks replay | `test_financial_post.py::test_unapproved_owner_or_source_never_clicks_or_posts`, `test_wrong_final_body_never_reaches_the_backend`, `test_changed_or_multiple_requests_never_replay`, `test_stop_after_button_capture_prevents_post_replay` |
| Verified output and terminal/cleanup state remain independent of a zero process exit | `test_diagnostics.py::test_controller_exit_mismatch_is_recorded_but_never_certified`; `test_desktop_worker.py::test_worker_counts_verified_details_once_and_keeps_partial_below_100` |

## Calibration and acceptance

Calibration run [40806785945](https://github.com/cepeter-job/spt-downloader/actions/runs/40806785945),
attempt1, source08dd6f1784b87b73b623d51cd801637bb8690696, executed all6,669
Windows cases across the unchanged fixed partitions. Shard0 had two old workflow
artifact-count assertion failures; shard1 passed. These two failures were fixed
without dropping any evidence checks, and all335 focused cases passed in
[40808369065](https://github.com/cepeter-job/spt-downloader/actions/runs/40808369065).
The calibration run remains failed diagnostic evidence, not acceptance. Original
JSON line/branch unions give the following initial floors, with roughly two
percentage points of headroom. Final acceptance additionally requires a new
complete passing Windows run and the actual combined-data gate before packaging.

| Scope | Observed line / branch | Floor line / branch |
| --- | ---: | ---: |
| All measured source | 89.1710 /81.9634 | 87 /80 |
| coretax_browser | 92.9119 /86.4353 | 90 /84 |
| coretax_json_capture | 89.7536 /84.4156 | 87 /82 |
| coretax_exporter | 95.6182 /92.6282 | 93 /90 |
| diagnostics | 88.9610 /80.0000 | 86 /78 |
| output | 91.5835 /84.5638 | 89 /82 |
| worker parent | 88.5057 /66.6667 | 86 /64 |
| build_info | 93.9394 /75.0000 | 91 /72 |
| ui_state | 95.2381 /90.7407 | 93 /88 |

The initial union has16,329/18,312 statements and6,721/8,200 branches. Shard test
times were1095.76s and1197.00s; the matching uninstrumented accepted source
maintenance run40806773507 supplies comparison timing. Different hosted runner
conditions preclude claiming a controlled performance benchmark. New gate code
changes the all-source denominator; the final combined report is authoritative.
Changing a floor requires explicit review of the new measured baseline and its
effect, rather than lowering it automatically after a failure.
