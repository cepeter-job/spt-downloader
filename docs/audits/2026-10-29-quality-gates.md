# Pinned typing and security gates (issue 130)

The portable job installs a separate `locks/quality.txt` environment from exact
`requirements-quality.txt` pins: Bandit1.9.4 and mypy2.4.1, including universal
transitive hashes. `scripts.update_locks` checks all five locks atomically; a
quality resolution failure preserves every old lock. Runtime/test/build/audit
locks and the explicit worker/package allowlists remain independent. The
Windows dependency audit includes the installed quality environment too.

## Adopted typing boundary

`pyproject.toml` owns mypy's Python3.14 strict configuration and explicit files:
`spt_desktop/build_info.py` and `spt_desktop/ui_state.py`. Both are existing stdlib
owners, not wrappers added to make a typing metric pass. Keep unused-ignore
warnings and unimported-Any refusal; there are no global ignores, missing-stub
suppression or unchecked untyped bodies in this adopted scope.

BuildInfo/TypeGuard describe the already validated four-field public identity.
JSON is bound to object before runtime validation. Boolean, literal commit/run
syntax, resource bounds and unknown-metadata behavior are unchanged. The UI
counter cast occurs only after its existing present-value integer checks;
progress updates use a precise TypedDict after all runtime event validation.
No checkpoint, event, JSON or build schema is widened. Other modules remain
outside the incremental adoption, with full runtime/negative tests retained.

Runner baseline40801804002 (Python3.14.8) found15 errors in these two modules
in0.845s. The new gate must report zero. A synthetic int-return/string-result
example must produce mypy's actual return-value diagnostic; a generic command
failure is not accepted as proof. [Mypy project](https://pypi.org/project/mypy/2.4.1/)
provides the pinned release and Python compatibility metadata.

## Security triage and overlap

Bandit scans every root `coretax*.py` and `spt_desktop` Python module at all
severities; tests, captured evidence and environments are not inputs. Initial
unsuppressed scan:30 findings,2.963s, no scan errors. The B113 result was a local
dictionary called requests, not HTTP; rename it request_bindings without changing
its keys, values or order. The remaining29 reviewed intentional sites use only
a source-local named rule suppression with its rationale below. There are no
global disabled rules, severity filters, file exclusions or accepted baseline
that can hide a new occurrence elsewhere. Changes at an annotated boundary
still need contract review; the annotation grants no execution authority.

CodeQL remains a separate semantic/dataflow review. Bandit supplies quick AST
patterns for unsafe deserialization, subprocess, temporary-file and secret uses;
neither replaces negative behavior tests or original-byte custody. pip-audit
continues to examine installed locked dependencies, including the new toolchain;
package vulnerabilities are a separate surface. The gate's synthetic pickle
loads input is scanned, never executed, and must yield the real B301 finding.
[Bandit project](https://pypi.org/project/bandit/1.9.4/) documents the pinned tool.

| Source owner | Rule | Reviewed reason |
| --- | --- | --- |
| `coretax_attachments.py::_release_nodes` | `B110` | Owned cleanup is best effort; preserve the original outcome. |
| `coretax_attachments.py::_read_pdf` | `B110` | Owned cleanup is best effort; preserve the original outcome. |
| `coretax_browser.py::ListObserver._release_document` | `B110` | Owned cleanup is best effort; preserve the original outcome. |
| `coretax_browser.py::ListObserver.on_navigation` | `B110` | Owned cleanup is best effort; preserve the original outcome. |
| `coretax_browser.py::_SearchDiagnostics.__exit__` | `B110` | Owned cleanup is best effort; preserve the original outcome. |
| `coretax_browser.py::open_return_readonly` | `B110` | Owned cleanup is best effort; preserve the original outcome. |
| `coretax_browser.py::open_return_readonly` | `B110` | Owned cleanup is best effort; preserve the original outcome. |
| `coretax_financial_post.py::FinancialPost._route` | `B110` | Owned cleanup is best effort; preserve the original outcome. |
| `coretax_financial_post.py::FinancialPost.__exit__` | `B110` | Owned cleanup is best effort; preserve the original outcome. |
| `coretax_financial_post.py::FinancialPost.__exit__` | `B110` | Owned cleanup is best effort; preserve the original outcome. |
| `coretax_json_capture.py::DetailJsonCapture.close` | `B110` | Owned cleanup is best effort; preserve the original outcome. |
| `coretax_json_capture.py::DetailJsonCapture.close` | `B110` | Owned cleanup is best effort; preserve the original outcome. |
| `coretax_json_capture.py::DetailJsonCapture.close` | `B110` | Owned cleanup is best effort; preserve the original outcome. |
| `coretax_json_capture.py::DetailJsonCapture.close` | `B110` | Owned cleanup is best effort; preserve the original outcome. |
| `coretax_json_capture.py::DetailJsonCapture.close` | `B110` | Owned cleanup is best effort; preserve the original outcome. |
| `coretax_mpn_browser.py::AccountingObserver._release_document` | `B110` | Owned cleanup is best effort; preserve the original outcome. |
| `coretax_mpn_browser.py::AccountingObserver.on_navigation` | `B110` | Owned cleanup is best effort; preserve the original outcome. |
| `spt_desktop/app.py::App.open_logs` | `B606` | Open an inspected existing output/log folder, not a generated command. |
| `spt_desktop/app.py::App.open_result` | `B606` | Open an inspected existing output/log folder, not a generated command. |
| `spt_desktop/controller.py::` | `B404` | Reviewed owned process/runtime lifecycle; no untrusted command text. |
| `spt_desktop/diagnostics.py::DiagnosticLog.close` | `B110` | Owned cleanup is best effort; preserve the original outcome. |
| `spt_desktop/diagnostics.py::session` | `B110` | Owned cleanup is best effort; preserve the original outcome. |
| `spt_desktop/diagnostics.py::session` | `B110` | Owned cleanup is best effort; preserve the original outcome. |
| `spt_desktop/diagnostics.py::record` | `B110` | Owned cleanup is best effort; preserve the original outcome. |
| `spt_desktop/diagnostics.py::self_test` | `B106` | Deliberate synthetic privacy sentinel, never a credential. |
| `spt_desktop/diagnostics.py::self_test` | `B106` | Deliberate synthetic privacy sentinel, never a credential. |
| `spt_desktop/runtime.py::` | `B404` | Reviewed owned process/runtime lifecycle; no untrusted command text. |
| `spt_desktop/windows.py::` | `B404` | Reviewed owned process/runtime lifecycle; no untrusted command text. |
| `spt_desktop/windows.py::ProcessJob.spawn` | `B603` | Reviewed explicit argv; assign suspended owned child before resume. |

Subprocess import/argv annotations cover existing reviewed runtime/controller/
Job Object paths only. Caller-built interpreter/worker commands retain resource
and ownership validation; arbitrary free-text commands and new shell callers
are not admitted. Folder opening remains the inspected existing output/log
folder UI. Synthetic diagnostic sentinel arguments deliberately test privacy.
Cleanup pass sites preserve the original failure/Stop and never certify capture.

## Evidence and execution boundary

All tool execution and tests run on GitHub runners. Local work only inspected
source/AST/Git/locks/hashes. CI retains mypy XML, Bandit JSON and explicit negative
probe outcomes, with failures blocking the existing portable/build dependency
chain. The existing Ruff, complete Windows tests, portable coverage, security
checks, package readback and bootstrap gates remain. Gate/setup duration is
reported from actual runner measurements; do not infer live scrape performance.

GREEN [run40805141747](https://github.com/cepeter-job/spt-downloader/actions/runs/40805141747),
attempt1, commit0da21379808e9dc1d28bf49c41add2330fc6663c: mypy zero issues in
two files (0.572s), Bandit zero unsuppressed findings/no scan errors (2.030s),
both negative probes true, lock freshness passed, and173 focused cases passed
with zero failures/errors/skips (3.655s). Readback artifact12867777283 SHA256
eb4261a781ed939bc97cb9d3c3d4220bf7db7f74a8d0c9af9ebf26e7d1dad74f.
This isolates tool runtime from environment installation and the full Windows
pipeline; exact PR full-suite/build evidence is still required before merge.
