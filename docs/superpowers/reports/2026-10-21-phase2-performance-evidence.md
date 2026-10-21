# Phase 2 Performance — evidence and remaining limits

## 1. Scope and exact revisions

This report records the owner-authorized performance follow-up in PR #58. The
owner also authorized resolving #52/#53/#55/#56 first. #53 merged at `198edaf`,
#52 closed as superseded, #56 merged at `09aa697`, and #55 merged at `df8e758`.
No installation, live export, deployment or new release is part of this work.
PR #50's unique documentation and PR #20 remain separate.

- Baseline: `df8e7589fe6550d639142971483c65beef4b37d9`.
- Tested product: `d59a019c9c7cfc24af617ace824c69d7ede58d53`.
- Full-suite runner checkout: `0def09cea665686a63b0bc566a88f8fefc23c3e9`;
  its tree exactly matches the tested product (`dbc9f0a845543c45b900f41250d6869839edd9bd`).
- The later report-only commit does not change product, tests, locks, resources
  or production CI. Its own CI result must be reported separately.

The product delta is limited to the two existing native dialog layout closures
in `spt_desktop/app.py`. Initial mapping and explicit content invalidation use
one owned idle callback; genuine resizing still uses the existing coalesced
75 ms callback. Duplicate/obsolete Configure notifications are checked against
the actual viewport dimensions. Wrapped body height and scroll extents remain
reachable. Literal data, initial empty selection, safe overwrite focus,
original-order replies, job/deadline/Stop guards and cleanup are unchanged.

**Outcome: a verified incremental performance improvement, not completion of
all performance objectives. Filtering is substantially faster. The median
settled-opening target below 100 ms remains unmet in every measured scenario.**
No target was silently relaxed, and correctness GREEN is not performance PASS.

## 2. Paired performance measurements

[Diagnostic run 39535106941](https://github.com/cepeter-job/spt-downloader/actions/runs/39535106941)
uses separate baseline/candidate processes on the same Windows 2022 runner,
CPython 3.14.8/GIL and Tcl/Tk 9.0.4. Each pair uses identical payload bytes and
SHA-256, default client geometry and actual 100% monitor scaling at 1600×1200.
Selection uses approximately 921×600 logical client pixels, overwrite 801×520.
One warm-up is excluded, then ten observations per operation. The immutable
historical harness `67396564dd12b8a3d9eb8cd08920316cf83ae2d3` is reused without
changing its timer/geometry settlement method. No screenshot or separate
profiling pass is included in these primary timings.

All values below are milliseconds. Positive reduction means a lower observed
median, not a claim of statistical significance from ten samples.

| Dialog / inventory | Operation | Baseline median | Candidate median | Candidate p95 | Observed median reduction |
| --- | --- | ---: | ---: | ---: | ---: |
| selection / 1 | open | 144.23 | 137.33 | 147.17 | 4.79% |
| selection / 1 | filter | 77.94 | 4.86 | 6.29 | 93.77% |
| selection / 1 | sort | 3.83 | 3.39 | 4.35 | 11.41% |
| selection / 100 | open | 168.14 | 150.22 | 159.54 | 10.66% |
| selection / 100 | filter | 79.27 | 9.55 | 10.58 | 87.96% |
| selection / 100 | sort | 7.07 | 7.58 | 10.27 | -7.17% |
| selection / 1000 | open | 175.26 | 166.72 | 169.76 | 4.87% |
| selection / 1000 | filter | 85.15 | 15.73 | 17.16 | 81.52% |
| selection / 1000 | sort | 14.89 | 15.34 | 18.01 | -3.06% |
| overwrite / 101 | open | 196.56 | 185.26 | 196.46 | 5.75% |

For filtering, the absolute median reduction is 69–73 ms (81.52–93.77%).
Sorting remains below 19 ms p95; the 100- and 1,000-record medians are about
0.51 and 0.46 ms higher, so this report does not call every operation faster.
All 40 opening observations remain over 100 ms. Their medians are 137.33,
150.22, 166.72 and 185.26 ms. The modest lower opening medians are observations,
not a hardware-independent speed guarantee.

Cancellation uses separate trials, scheduling Stop after 1 ms without truncating
the ordinary layout sample. Every observed cancellation-service value is under
100 ms; maximum **73.3302 ms**. Root timers, consent and cleanup behavior remain
covered independently. With ten samples the nearest-rank p95 equals the maximum;
this is not a population-tail estimate or a broad hardware benchmark.

The primary settled metric includes native event processing and repeated widget
geometry observations. It is not first paint, pure callback CPU time, photon
latency or time spent continuously blocking the UI. The same observer is used
for both revisions. Its overhead was not independently subtracted.

## 3. Root cause, tests and the residual opening objective

Native trace [39533874431](https://github.com/cepeter-job/spt-downloader/actions/runs/39533874431)
showed obsolete Toplevel Configure notifications after the measured viewport
was already arranged. Merely replacing one `after(75)` with `after_idle` did not
solve the lifecycle: native mapping can initially expose a 1-pixel placeholder,
and redundant native events could schedule another delayed callback.

The final behavior contracts first fail against the unchanged original App:
[run 39534323942](https://github.com/cepeter-job/spt-downloader/actions/runs/39534323942)
records **8 intended readiness/no-op failures and 5 passing lifecycle cases**,
with no collection/setup errors. Applying the minimal candidate produces
**133 passing targeted cases**, zero failures/errors/skips. Original assertion
ASTs (135 assertions in the existing dialog-layout test module) are identical.
Resize fixtures now produce a real native geometry change before demanding a
pending resize callback; new no-op tests forbid redundant waits. Readiness tests
process WINDOW_EVENTS and IDLE_EVENTS but not TIMER_EVENTS. This is a behavioral
contract, not a flaky wall-clock threshold test.

A separate post-verification trace,
[run 39537929626](https://github.com/cepeter-job/spt-downloader/actions/runs/39537929626),
observes the unchanged candidate with the full event loop. In its three single
instrumented openings, final reflow returns at about 42.80, 91.33 and 70.18 ms
(selection 1, selection 1,000, overwrite 101), with no queued 75 ms layout timer
after final usable geometry. Native Expose events occur at roughly 43.35, 95.52
and 60.18 ms. These values include instrumentation and come from a different
1024×768 diagnostic display; **they must not replace the primary paired table**.

The trace disproves the simple claim that the remaining primary delay is still
necessarily a queued modal 75 ms timer. It does not fully partition the remaining
native rendering, geometry observation and widget-construction costs. The
100 ms settled-opening objective stays open. Further work should profile those
costs separately before proposing batching or changing the window structure.
No speculative optimization, new Tk thread, reduced inventory limit or global
debounce reduction was added to chase that target.

The first detailed trace attempt (`39535873543`) was invalid: its observer queried
an already-dispatched Tcl timer and interrupted the observed callback. The
harness was corrected to record that state without throwing, and to preserve
partial traces. This was a diagnostic-only failure, not a product regression;
it is not counted as passing performance evidence.

## 4. Native visual, keyboard and scaling evidence

The paired run preserves **90 original physical PNGs**, 30 each at actual Windows
100%, 150% and 200% monitor scaling. All frame digests, foreground-window status,
recorded source revisions and work-area bounds were checked against JSON.
Eighteen dialog/size cases cover regular, compact and minimum layouts; eighteen
close/Stop/terminal cases explicitly cancel pending owned callbacks before their
75 ms deadline and keep focus stable after expiry. Six fresh keyboard-entry
checks preserve navigation, raw ID/path inspection and no accidental consent.
Representative native captures were inspected for wrapping, table headings,
visible actions and scroll reachability. At minimum size some explanatory
content is reached by scrolling; not every field is claimed above the fold.

**P2-14 remains partial.** A 1600×1200 physical display at 200% has only an
approximately 800×560 logical work area. Normal selection is therefore clamped
to 784×521 logical client pixels; compact requested height is also clamped.
These captures verify clamping and the tested smaller layouts, not full nominal
regular/compact windows on a sufficiently large 200% display. App awareness is
0 and captured native window DPI is 96; the screenshot helper is DPI-aware.
No per-monitor-DPI, High Contrast, screen-reader, long-session RAM, real-account,
network, Excel/PDF throughput or universal accessibility acceptance is implied.

## 5. Full product pipeline and exact artifact readback

[Production run 39534942103](https://github.com/cepeter-job/spt-downloader/actions/runs/39534942103),
at the exact tested head above, completed **SUCCESS on attempt 1**:
**3,377/3,377 Windows cases** and **456/456 portable cases**, zero failures,
errors or skips. The collectors contain the same 3,377 unique nodes; Windows
selects all, portable selects its reviewed subset. All ten new readiness cases
are present. Do not add the overlapping suites to invent unique coverage.
Windows test inventory duration is 1,197.433 seconds; portable is 35.615 seconds.

Routing/actionlint, lock freshness, strict dependency audit, fresh managed worker
setup/reuse, source GUI self-test, frozen build/self-test, exact-ID artifact
download, byte/hash validation and aggregate gate passed. CodeQL also passed.
The 30-minute Windows job cap, production serial execution and every gate remain
unchanged by this performance PR.

Six original CI artifact ZIPs were independently downloaded and verified:

| Artifact ID | ZIP bytes | ZIP SHA-256 |
| --- | ---: | --- |
| 12317936044 | 105337 | `c14d4d0cb455175915e7c7e4a9b5527c0afe7f530abca5ac6ad3ad0912215970` |
| 12317691371 | 60825 | `044aa1a81f8cdb7d3033b2646be232a41124e28cffe117951d6dd2b0fd5ac147` |
| 12317446744 | 28485588 | `faad2f5233f303bf0428cd7e67e4a526d141c21b5196a5792d431e5dfd396341` |
| 12317152531 | 9274 | `ea331add8408f1c80ba7e09f96af775738a63263d64411ec1fb0a9d44ee191c2` |
| 12316907747 | 60309 | `7d3f256a3d79677a41408aa0cc02bca36e2c84ea42418490c3ff6eee2a887573` |
| 12316234136 | 765 | `700fa831d69151a1e9ca6b4c853a94dec61525bb6667f22b7d711e6b71d73998` |

Final package **12317446744** contains exactly `SPTDownloader.exe`, `LICENSE.txt`,
`README.txt`, `build-selftest.json` and `SHA256SUMS.txt`, with all four payload
checksums matching. Frozen metadata confirms Python 3.14.8/x64/GIL, uv 0.13.4
source pin, Tcl/Tk 9.0.4, and the exact **39 worker resources**, including
`coretax_badan_template.py` and `resources/corporate_format.xlsx`.
`credentials_accessed=false` and `live_scrape=false`. The package was not run
locally. The LICENSE content is unchanged; Windows checkout CRLF versus Git LF
was explicitly accounted for rather than mistaken for a source modification.

Additional original evidence:

| Purpose | Run / artifact | ZIP SHA-256 |
| --- | --- | --- |
| RED/GREEN and exact source blobs | 39534323942 / 12317011800 | `652b250ba5e15882d6bf43975bea60830a05b9912ced226842ce4df7d9c9faf8` |
| Paired timings and 90 native PNGs | 39535106941 / 12316784071 | `593515c02154a2e21382888d9b86289431614bd7399e61ad4aaf37e6d0bb3ae3` |
| Final read-only opening trace | 39537929626 / 12318377853 | `6176c7f7d44e05eb3dc2ef2b88d18c33b6dedae2d14401bbb71126fe4f4120b1` |

## 6. Review, disposition and follow-up

Independent read-only source review found no Critical/Important defect. It
verified exact candidate blobs, current-interaction/token guards, content
invalidation, resize coalescing and unchanged business logic. Minor coverage
caveats remain: resize-back-to-original, resize-during-idle and the initial 1px
branch were assessed from source rather than dedicated extra parameterized
assertions. Existing cleanup and native resize tests remain intact.

The merge recommendation is to retain this **tested incremental improvement**
while recording the unmet opening target and P2-14 gap rather than declaring
all performance acceptance complete. No current measured operation is silently
excluded from the table. Repository issues are disabled, so remaining work is
tracked here and in the PR instead of inventing an issue link.

The remaining opening work should separate construction, native Map/Expose,
layout callbacks and geometry-observer overhead on the same display/payload;
then test a narrowly supported change. Preserve current filter gains, cancellation
below the target in the sampled cases, literal data and the complete suite.
Changes to output/capture, new features, speculative batching and deployment
remain outside this performance PR. Temporary diagnostic #57 must be closed
without merging its workflow after the original evidence is preserved.
