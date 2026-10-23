# PPN final-choice invariants and submitted Normal verification

Date: 2026-10-23. [PR99](https://github.com/cepeter-job/spt-downloader/pull/99)
merged as `4af0c5a1363e8cd2f867ffb49671d214b98fb970`. This closes the
reviewed source-invariant subset; active-calendar, Normal-negative and
unproved nonnegative FORWARD_REFUND clearing remain unsupported.

## Resulting behavior

Every PPN primary, including Normal, must explicitly bind
ReturnSheetStatusCode=SUBMITTED before semantic projection or structural fallback.
Missing status is ineligible. Contradictory/null/wrong-type status is fatal.
The submitted-list route alone cannot repair contradictory primary bytes.
This gate excludes the draft-only IA6 writer that would invalidate a fixed
output-VAT operand.

Negative submitted amendments preserve a raw choice only when the facility
null-write is excluded and the calendar assignment is blocked. The blocker
covers both initial and final export stages, the exact invoice/uncollected
quartet predicate, or a stable inactive capture-owned interval bound to outer
PeriodYear. A final A1 export alone is insufficient. The exact source facility
codes are AS.09-01/AS.09-02. With calendar blocked, a proven facility null-write
clears only raw null/FAST_REFUND/CARRY_FORWARD. Nonnegative FORWARD_REFUND cannot
assume a distinct post-raw clear event.

The narrow Normal nonnegative branch reconciles captured self-collected output
VAT against four ordered components and captured calculated input VAT against
six ordered components. Deposit/collector and all operands must be present with
supported source types. Every ordered intermediate must remain exact and within
fifteen digits. The final balance uses those reconciled captured operands,
never a stale stored normal/amendment balance. Choice inputs are integral; the
shared final-balance amount helper separately retains binary-exact direct
fractions only when every intermediate operation is also exact. The definite
percentage reset supplies the reviewed late calculation path; underflow cannot
fabricate a distinct change.

All contributing source paths and original numeric tokens are retained.
Calendar provenance binds to original outer Payload.PeriodYear and the same
attempt's clock, never replay time. Missing or unproved dependencies cause
whole-record fallback. Privacy, identity, authentication, source/snapshot drift
and Stop retain their existing fatal/cancellation boundaries. This invariant
does not prove arbitrary malformed reactive graphs terminate; successful
structural observation and capture completion remain separate gates.

## RED and review correction

Tests-first run39933025119 had 42 genuine new behavioral failures, one separate
saved-fixture failure, and zero errors/skips; all 4,437 existing Windows nodes
passed. The saved fixture was corrected to use literal sheet case and actual
save_output/verify_outputs/final compaction, without a geometry-suppressing
helper. Two additional arithmetic edge regressions cover inexact direct
fractions and an underflowing percentage.

Fresh source review found the missing submitted-status gate on Normal. The
tests-only correction run39937841176, tested merge
`dacdb930358265b744a9c7a8bdbe34733baf27fd`, had exactly nine intended status
failures. All 4,538 existing L11-C-baseline cases and the other 48 PPN cases
passed. The primary guard was repaired and the reviewer confirmed the P1 closed
before merge. No local product execution was used.

## Exact final runner and package evidence

Run [39939789665](https://github.com/cepeter-job/spt-downloader/actions/runs/39939789665)
attempt1 tested head `99e92f11d6fe0363d1632f3908d327dc56f3a4e9`, merge
`a81953b9f8fd8f19a72c430ba7ba0fa64027c811`, tree
`7e909782485c04020c6e56880b407917385e55ab`. Downloaded inventories reconcile
4,595 distinct Windows passes in disjoint shards of 2,340 and 2,255; 710 portable
passes overlap Windows. No failures/errors/skips occurred. All prior behavior,
fixture and status regression nodes have passing successors.

| Read-back artifact | ID | SHA256 |
| --- | --- | --- |
| Windows shard 0 | 12496570617 | `9d82f88f59a83d4d1673b2c7396d26db96116e211938f849416eac08c7e41f16` |
| Windows shard 1 | 12495449378 | `5bab032f720a32a0fb37d82ced39afd66aa9580e0a12f5f6e362605d5e1fa3a5` |
| Portable | 12494844044 | `e16f5f38e8e0d37f4390f1cfe90b4ebd606e736043a34e1399957cf544d8b8c7` |
| Distribution | 12495703873 | `fa477e0b89a114c45058eb61e2a0b163144b4afe811f8f63ab731e3085086781` |
| Packaged bootstrap | 12495698997 | `c11ad616a30680d1f48e2c3ef0785829f2a93234ccdae8edaa3e5f750543d129` |

ZIP digests matched the API. Readback verified the exact seven-member
allowlist/manifest, external/embedded identity, SBOM/runtime lock and all 45
bundled worker files. Executable SHA256:
`d18045b33f1404cc922ed3a745074fdf85d45c68c94cf99412fe9abc39c5493f`.
No-account source/frozen self-tests and packaged cold/reuse/cancel/owned-cleanup
checks passed. Required Actions/CodeQL checks passed. Latest main and preceding
other-session PR96 were reviewed; L11-C, financial PDF, layout, route and Audit
contracts remain intact.

This is CI-verified PR packaging. No new live PPN acceptance, DOM/JSON speed claim,
installed package replacement or attested main release follows from it. The
separate [PPh21 benchmark](2026-10-23-json-period-and-benchmark.md) and historical
[selected PPN amendment acceptance](../../ppn-native-integration.md) retain their
own exact scope/build evidence. Current-build live PPN acceptance needs a
selected authorized return. The remaining unproved lifecycle branches continue
to fall back without inventing compensation/refund values.
