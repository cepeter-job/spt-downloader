# Phase 2 Dialog Performance Implementation Plan

> **For agentic workers:** use superpowers:executing-plans for inline execution, tests first, followed by source review and exact runner evidence.

**Goal:** reduce native selection/overwrite opening and content-update latency without changing business behavior or weakening consent safeguards.

**Architecture:** keep App-owned modal callbacks and the existing single `layout_after` token. Distinguish initial/content readiness from user resizing: idle work for the former, existing 75 ms coalescing for the latter. Synchronize the scrollable body with measured geometry; avoid nested event loops, new threads and speculative row batching.

**Tech Stack:** Python 3.14.8/GIL, native Tkinter/ttk, current hash-locked dependencies. Product execution remains GitHub-runner-only.

**Spec:** [approved Phase 2 dialog design](../specs/2026-10-20-magicpath-b-phase2-dialogs-design.md), plus the owner's 21 October 2026 instruction to implement and merge a separate Performance PR after compatible pending PRs. Earlier design snapshots are historical and remain unchanged.

## Global constraints

Preserve literal identifiers and paths, empty initial selection, search reset versus sort preservation, original inventory-order replies, safe overwrite focus, stale request/deadline/Stop guards, named widget contracts, work-area clamping, native fonts and 54 copy IDs. No backend/capture/output changes, toolkit migration, row limits, background work in Tk, production sharding or new dependencies. Full nominal 200% display coverage remains an explicit independent acceptance gap.

## Baseline and hypothesis

Merged UI baseline `198edaf` is source-equivalent to the previously verified Phase 2 app. Fresh run `39529637127` reproduced opening medians about137–170 ms; opening handlers were about28–51 ms. Both dialog builders and filter updates currently share the resize-only 75 ms delay. This is a profiling hypothesis, not proof that subtracting75ms gives the final result. Integration baseline must include accepted PR55/56 changes before the final Performance PR merge.

## Task 1 — Readiness contracts and observed RED

Create `tests/test_desktop_dialog_readiness.py`: after only idle processing, initial selection (0/3/1000 records) and overwrite (1/101 files) must fit the viewport, have a valid scroll region and leave no owned initial-layout timer. Filtering at minimum size must finish content layout, clear selection, retain reset/no-match explanation and send no reply. Stop before initial work runs must cancel its token, preserve an unrelated root sentinel and never consent later.

Run this file on the exact test-only commit on a Windows runner. Expected RED is incomplete geometry or a still-pending resize timer, not collection/setup failure. No product implementation is written until that failure is observed. Existing native resize/ownership/keyboard tests remain mandatory.

### Native mapping clarification from observed failures

Windows Map/Configure work is not entirely in the idle queue. The readiness
fixture processes native WINDOW_EVENTS and IDLE_EVENTS while excluding
TIMER_EVENTS; it still proves no dependency on the fixed resize delay.
Diagnostic trace39533874431 shows obsolete Toplevel Configure notifications
arriving after the measured viewport is already arranged. Deduplicate using
actual viewport width/height, not the event's possibly obsolete payload.
Explicit content invalidation must still run at unchanged viewport size.
Ownership/terminal fixtures now create a real native resize before demanding a
pending resize token; their original assertion ASTs remain unchanged. Added
no-op Configure tests reject redundant delayed work. These are narrow fixture
corrections, not removal of lifecycle or safety coverage.

## Task 2 — Minimal measured correction

Modify only the selection/overwrite layout closures in `spt_desktop/app.py`. Initial and content requests may replace queued resize work with one owned idle callback; real Configure events retain coalesced75ms scheduling. Use measured requested body height after wrapping, updating only when it differs, so idle completion does not leave stale scroll extents. Preserve guards and cancellation. No forced `update()` loop or arbitrary shorter global timer.

Run new contracts plus all existing dialog/theme/consent tests. Inspect profiling traces for repeated reflow or unsettled geometry. If evidence does not support this approach, record the cause and revise the narrow hypothesis rather than adding batching speculatively.

## Task 3 — Paired evidence, full validation and merge

On one Windows job, run separate exact-baseline/candidate processes with identical synthetic payloads:1/100/1000 selection records and101 long overwrite paths. Exclude one warm-up and retain at least10 samples per action, handler/settled-layout durations and separate cancellation-service samples. Add a distinct profiled pass for initial-ready/first-visible/reflow diagnostics; do not mix instrumentation overhead into the primary comparison. Record requested and actual sizes, versions and source SHA. Capture native regular/compact/minimum states and preserve keyboard/focus/cleanup evidence.

Target median settled opening below100ms for all four scenarios; report every sample and p95/max, not a guaranteed hardware-independent result. Cancellation must not regress above100ms in the sampled cases. Performance targets are measured acceptance, not flaky per-run timing assertions. Run the full unchanged Windows/portable suites, dependency audit, source/frozen self-test and exact package readback. Preserve privacy and all39worker resources. Merge only after the final diff and exact evidence are reviewed; close temporary evidence PR without merging its workflow.

## Review focus

Idle work must not survive Stop or replace another job's callback; content wrapping must update scroll extents; real resize storms must remain bounded; initial safe focus and original-order consent must remain unchanged; measured first visibility must not be confused with stable layout. The new readiness/Stop tests and existing Phase 2 lifetime/keyboard suite cover these conditions. No claim of new real-account, long-duration RAM, or sufficient-display200% acceptance.
