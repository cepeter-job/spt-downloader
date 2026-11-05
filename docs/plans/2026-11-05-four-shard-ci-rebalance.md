# Four-shard Windows CI runtime evidence and bounded rebalancing

Date: 2026-11-05. Scope: `scripts/ci_tests.py`, Windows pytest profiling, synthetic sharding contracts. No application runtime, finance/export behavior, timeout budget, coverage threshold, or completeness gate is weakened.

## Prior successful runs (P4)

These are **Windows pytest step wall times**, not full workflow durations; all four shards completed successfully. Runs are independent and contain minor test-suite changes, so use as directional rather than controlled A/B evidence.

| Successful run | Shard 0 | Shard 1 | Shard 2 | Shard 3 | Slowest | Slowest–fastest |
|---|---:|---:|---:|---:|---:|---:|
| [41993752432](https://github.com/cepeter-job/spt-downloader/actions/runs/41993752432) | 686s | 689s | 572s | 640s | 689s | 117s |
| [42030885787](https://github.com/cepeter-job/spt-downloader/actions/runs/42030885787) | 756s | 710s | 528s | 657s | 756s | 228s |
| [42044216523](https://github.com/cepeter-job/spt-downloader/actions/runs/42044216523) | 760s | 619s | 624s | 645s | 760s | 141s |

The same asymmetric assignment recurs: shard 0 is slowest in two samples and within 3s of slowest in the third, while shard 2 is usually the lightest. Shard 2 has *more* passing tests than shard 0 in all three runs. Runner queue and setup do not explain the test-time imbalance.

## Implementation (P1)

Retain the SHA-256 modulo partition for every previously unmeasured or renamed node. For **exact recorded node IDs**, assign:

| Original hash shard | New shard | Synthetic test | Typical slow-test call |
|---|---|---|---:|
| 0 | 3 | corporate template geometry/style preservation | 16–19s |
| 0 | 2 | financial discovery: link outside detail content | ~10.5s |
| 0 | 2 | financial discovery: unrelated HTML table | ~10.5s |
| 0 | 2 | MPN detail: missing JSON-first grid | ~7s |
| 0 | 2 | desktop dialog: selection reflow | ~7s |
| 0 | 2 | PPN main build-budget ceiling | ~7s |
| 0 | 2 | MPN inspected dispatch: closed budget | ~7s |
| 0 | 2 | MPN inspected dispatch: open budget | ~7s |
| 1 | 2 | financial capture: absent/unsupported control | ~11.7s |
| 1 | 2 | financial attachments: absent control | ~10.5s |

Approximately 69s are removed from shard 0, 22s from shard 1, 72s are assigned to shard 2, and 19s to shard 3 based on repeated, single-case timings. These are **modelled** shifts, not a CI wall-time guarantee: phase setup/teardown and runner variability can change results. Do not move additional nodes without new successful-run evidence.

## Integrity requirements (P2)

- Keep two-shard historical overrides unchanged, and serial execution unsharded.
- Keep the production Windows suite serial **per runner** and its full original collection preserved across shard manifests.
- The inventory verifier must reject missing/duplicated nodes, incorrect shard assignments, wrong commit/attempt, incomplete phases, skipped tests, or coverage mismatch.
- The new portable tests assert every exact measured relocation, stable routing for unknown node IDs and two-/three-shard behavior, plus rejection of a hash-only reversion with unchanged aggregate coverage.
- The red behavior was established before the production change: the baseline hash-only four-shard router disagrees with all ten specified targets.

## Fixture profile (P3)

The most consistently expensive `call` phases are corporate template geometry/style preservation (16–19s), two financial discovery cases (~10.5s each), two financial capture/attachment cases (~10–12s), and MPN readiness/capture (~6–8s). Independent `teardown` phases of approximately 6.5s also recur in browser/financial cases. A few slow tests cannot explain all 7,000+ test calls; monitor aggregate fixture startup and Edge process reuse before altering waits or resource cleanup.

Windows CI now reports the **30 slowest pytest phases** (up from 10), while the existing synthetic JUnit, measurement, coverage and inventory artifacts remain intact. P3 here is observational profiling only: no test expectations, timeouts or production waits have been changed without reproducible root-cause evidence.

## Acceptance

1. A fresh four-shard PR run is green with the complete source inventory and package/quality gates.
2. Collect its four test-step durations, test counts and slowest phases, comparing against the table above without normalizing away slower runs.
3. Merge only on a green, mergeable PR. Evaluate whether additional fixture-level changes deserve a separate evidence-first PR.
