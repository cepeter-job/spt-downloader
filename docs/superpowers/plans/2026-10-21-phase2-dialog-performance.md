# Phase 2 Dialog Performance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove avoidable initial/content-layout waiting while preserving the Phase 2 interface and consent safety; compare median settled opening against the 100 ms target.

**Architecture:** Keep the two existing App dialog closures and their owned callback token. Initial mapping/content invalidation may use idle work; real resizing remains coalesced. Measure actual viewport dimensions rather than assuming each queued Configure requires another layout. Do not introduce a dialog framework, threading, or batching without evidence.

**Tech Stack:** Production CPython 3.14.8/GIL, native Tkinter/ttk, reviewed hash-locked environment; all product/test/build execution on GitHub runners.

**Spec:** Owner-authorized performance follow-up to [B-TK-P2-D1](../specs/2026-10-20-magicpath-b-phase2-dialogs-design.md) and [Phase 2 evidence](../reports/2026-10-20-ui-b-phase2-evidence.md), section 7. The owner explicitly requested this performance PR and merge, after resolving PRs #52/#53/#55/#56. Historical approved design/plan snapshots remain unchanged.

## Global Constraints

- Preserve Tkinter/ttk, literal NPWP/year/IDs/paths, original-order selection replies, safe overwrite focus, stale/deadline checks, cancellation, and callback ownership.
- Preserve the full Windows suite, portable inventory coverage, dependency audit, source/frozen tests, exact artifact readback and checksum gates. No production CI changes or test exclusions for speed.
- Baseline for final comparison must include merged #53, #55 and #56 (`main@df8e7589fe6550d639142971483c65beef4b37d9`). Early diagnostics against #53 are historical root-cause evidence, not final integration proof.
- Do not access accounts, portal or private taxpayer files. Use synthetic inventories and paths only. No installation/deployment requested.
- Keep full nominal normal/compact 200% DPI coverage explicitly unresolved until separately demonstrated. Performance evidence is not a DPI waiver.

## Review Focus

1. Native mapping may supply usable viewport geometry only after an earlier idle callback; no 1px placeholder may be treated as final layout.
2. Queued or duplicate Configure events may describe old geometry even after the viewport is correct; they must not add artificial readiness delay.
3. Changed content can require wrapping/height updates at unchanged viewport size; explicit content invalidation must still run.
4. Stop/terminal during idle or timer work must retire the modal token and bindings without later consent, focus theft, or root timer cancellation.
5. Real resize bursts must remain coalesced and preserve selection/query/raw IDs, fixed actions and scroll reachability. Synthetic events alone do not establish an actual resize.

## Task 1 — Root cause and behavior contracts

**Files:** `tests/test_desktop_dialog_readiness.py`; narrowly update real-resize fixtures in `tests/test_desktop_dialog_layout.py` only when required by the clarified behavior.

**Interfaces:** Existing `App._interaction`, named dialog widgets, `ConsentController`, `consent_event`; no product API changes.

- [ ] Preserve observed RED runs and native mapping/event traces with exact source/harness/artifact coordinates.
- [ ] Require initial layout and filter-content reflow to settle after native mapping plus idle work, without servicing TIMER_EVENTS; assert actual geometry, data, safe focus and no consent.
- [ ] Cover Stop retiring initial callbacks, no-op Configure requests, real resize coalescing, and unchanged root sentinels. Fixture corrections must retain safety assertions and use real size changes instead of requiring pointless work from synthetic Configure alone.
- [ ] Run contracts against the original App and observe expected behavioral failures. Collection/setup errors are not RED.
- [ ] Commit tests separately from production optimization; retain the failing evidence.

## Task 2 — Minimal measured layout correction

**File:** `spt_desktop/app.py`, only selection/overwrite layout closures.

**Interfaces:** Retain `interaction['layout_after']` ownership and current-interaction guards. No new reply schema, worker resource, UI copy or dependency.

- [ ] Distinguish first usable viewport mapping from later resizes; do not spin idle callbacks on unmapped geometry.
- [ ] Schedule explicit initial/content invalidation promptly and ignore redundant native geometry notifications where no layout input changed.
- [ ] Refresh scroll extent after wrapped body geometry settles, without another fixed delay or recursive layout loop.
- [ ] Run readiness and all existing dialog/selection/theme/lifecycle contracts. Investigate failures rather than reducing assertions.
- [ ] Commit the verified minimal App delta and inspect that unrelated application files remain unchanged.

## Task 3 — Paired proof and integration

**Files:** temporary diagnostic branch/PR #57 only for runner harness; product report `docs/superpowers/reports/2026-10-21-phase2-performance-evidence.md` after results.

- [ ] Compare exact baseline/candidate on the same Windows runner with identical payloads: 1/100/1,000 SPT and 101 overwrite files; one excluded warm-up and at least ten samples. Record handler and settled geometry separately, filter/sort, and cancellation service time. Keep window configuration comparable and report p95 limitations.
- [ ] Review representative native screenshots and verify label wrapping, visible actions, raw ID/path inspection, keyboard behavior and no late callbacks. Do not claim untested scaling/multi-monitor coverage.
- [ ] Run complete Windows/portable tests, dependency audit, source/frozen and package verification on the exact integrated candidate. Verify all 39 worker resources and hashes without executing the package locally.
- [ ] Review exact diff, new review comments and integration provenance. Publish numerical before/after results, including any remaining missed target; do not call a timing win from reduced coverage or a fixture wait change.
- [ ] Merge only after verified checks/review, preserve evidence, and close diagnostic #57 without merging its harness. Leave unrelated documentation PR #50 intact.
