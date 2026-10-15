# Consolidation of PR18 and PR19 — Implementation Plan

**Goal:** Integrate JSON-hybrid, the latest period/model workbook and flat PDF layouts, and private diagnostic logging without changing their safety contracts.
**Architecture:** Preserve PR18 bc3cc40b00590a28062fc9c4b850b7a17b52449e and PR19 1b076ffc45cd6094f6d23f8e78dd15501c73e9f3 as ancestors. Use PR18 as the integration PR, with a two-parent merge and normal main-branch checks.
**Tech Stack:** CPython 3.14.8 x64/GIL, uv 0.13.0, existing locked dependencies and Tkinter/ttk.
**Spec:** User consolidation request; AGENTS.md, the approved JSON-hybrid design and diagnostics plan. Manual/live acceptance remains deferred.

## Constraints and review focus

- Run all product imports, tests, Tk/browser fixtures, builds and EXE only on GitHub runners. Local work is source/AST/Git and static archive/hash inspection. No CI/ruleset/dependency/pin changes or private data publication.
- Keep source mode optional and default DOM. Preserve identity/authorization failures before safe fallback, exact selected IDs, no automatic consent, early Stop, source-aware checkpoints and full-record fallback.
- Preserve each literal period/model workbook, form-only names, three sanitized reference templates and flat record-bound financial PDFs. Old output validation must precede a new folder, without deleting or silently rewriting old results.
- Retain privacy-safe diagnostics and its non-authoritative status. Logging must not persist tax values, identities, URLs, paths, secrets, raw messages or protocol output.
- Reconcile Settings mode/status/log rows, worker authorization and mode forwarding, capture exception ordering, source/frozen reports and the union of worker resources.

## Execution

1. Add seven cross-PR regression cases in tests/test_pr18_logging_integration.py, then observe exact test-only runner RED on unchanged PR18. Tests cover DOM/JSON-first with INFO/OFF, Settings row separation/mode saving, actual unsafe401 hybrid handling under private logging, and the combined source self-test.
2. Resolve the three conflicting files at function level: coretax_browser.py, spt_desktop/app.py and spt_desktop/worker.py. Preserve auto-merged CLI/output/runtime/self-test behavior from both branches. The log button must follow credential status at row10.
3. Independently review the combined source when tooling permits; verify the full Windows inventory, portable subset, CodeQL, worker fresh/reuse, source/frozen self-tests and exact package/inventory/audit artifacts. Any tooling limitation must be explicit, not described as an independent PASS.
4. Recheck current heads, resolve evaluated comments and merge through normal protections only after full combined GREEN. Confirm both histories and post-merge main checks. No deployment, portal access, VirusTotal or manual acceptance.

## Checkpoint and tool outage

The initial isolated checkout is /tmp/spt-consolidate-18-19-20261015-6HqLdd/repo on vm148. It contains the unpushed plan/tests and an independent overlap review. That review identified Settings row9 collision, mode/session forwarding and JSON catch-order risks; its initial diagnostics-source inspection was limited by lazy Git blobs. Both public source archives were then materialized. Remote Desktop Commander subsequently stopped responding before the test review could be read or changes published. No source merge or push was issued on that machine.

Ruling: Continue through the GitHub connector and an isolated static container rather than retrying unknown remote mutations. Recovered packages11956274814 and11950682479 match their API/previously verified ZIP and payload hashes. Extracted worker source is never executed and must match original Git blob hashes before use. Preserve the interrupted checkout; record exact final evidence and any review limits on the PR.

Standalone baselines (not combined evidence): PR18 run38702560323 passed1296 Windows/375 portable; PR19 run38686816805 passed795 Windows including47 diagnostic cases/369 portable. Final run/tree/artifact coordinates belong in the PR discussion.
