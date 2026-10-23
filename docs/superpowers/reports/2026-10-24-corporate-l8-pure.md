# Bounded corporate L8 pure projection

The reviewed Rupiah facility branch has a pure projection in the existing
worker module. It reconciles captured values and emits the approved eight-row
table and one footer. **Native L8 is not enabled.** Form discovery, observers,
dispatch, transport and whole-record fallback are unchanged.

[PR113](https://github.com/cepeter-job/spt-downloader/pull/113) merged as
`2a679ffec7f352ff74eab85b848373e710551420`, tree `e288a19c84f3bed96394529e7dbf75195ff23273`.
The [source plan](../plans/2026-10-24-corporate-l8-pure.md) records the pinned
asset hashes, UTF16 offsets, exact captions/geometry and arithmetic proof.

## Supported source contract

- ICT_RCIT/id-ID, exact Rupiah headers and spans; matching original numeric
  main/outer years 2020 through 2100.
- Explicit nonnegative integral JSON amount operands within 15 digits, with
  signed zero refused; turnover at most 4.8 billion and research zero.
- Captured shares equal the main thousand-mask and zero; captured taxes equal
  the exact bounded 11% result and zero; captured total reconciles with both.
  Mismatches remain unsupported and are never replaced by calculated amounts.
- Preserve all original numeric tokens/types/paths and destination cells,
  including both tax operands supporting the footer and the primary outer year.
  Optional numeric/null ExchangeRateValue remains unused parent-control evidence.
- Caller must prove stable original main inputs and the effective grid-rate
  invariant. Conditional fresh-grid Rupiah rate of 1 source proof alone supplies no
  owned lifetime, visibility-cache, async readiness or final callback admission.

The existing formatter, exporter, approved template, resources, 45-worker
allowlist, workflows, dependencies and LICENSE are unchanged. All 23 previous
projection definitions remain AST-identical. The PPh21 documentation now keeps
the two verified benchmark cohorts separate: e25aa5e8 JSON 3.53% slower and the
earlier period-fix cohort 5.80% faster. No newer live benchmark is implied.

## Tests first and review finding

Initial tests-only [run 40017761585](https://github.com/cepeter-job/spt-downloader/actions/runs/40017761585),
attempt 1, tested merge `9a38c537a2ece72007ee3dfd65db3676bc447ecc`, tree
`f04873188b65eec5fb90220fa560efb4c7ac4704`. All 5,589 baseline cases passed;
exactly 192 new cases failed at the intended missing-helper assertion. All six
actual archives were independently reconciled before implementation.

Source review then found that valid large exponent tokens could escape the L8
refusal as Decimal Overflow in the shared conversion helper. Sixteen parsed-wire
regressions cover both signs across all eight amount inputs. One additional
case proves the unused exchange control retains its token without conversion.
[Review-RED run 40021242729](https://github.com/cepeter-job/spt-downloader/actions/runs/40021242729),
attempt 1, tested merge `e763b78ec69710d4e253200c59c972052d6de12f`, tree
`84cd0954738373c8fd48e623df951152d2458109`: 5,782 passed and exactly 16 targeted
Overflow failures, with zero errors/skips and passing setup/teardown. All six
archives were independently read before the narrow L8 exception translation.
Shared conversion helpers and all 209 tests stayed unchanged by the repair.
The superseded initial candidate 40020528808 was cancelled; it is not GREEN.

## Final runner and package evidence

[Run 40023866774](https://github.com/cepeter-job/spt-downloader/actions/runs/40023866774),
attempt 1, tested merge `0c615fb2f1ea29b4fe5cf4cdcb5192dc8564af21`, exact tree
`e288a19c84f3bed96394529e7dbf75195ff23273`, API head
`dba21c9592ec02cecb9292dd5d94aeb87e1f793a`. Local source
`e08727eed4513bb7899c727348d7d621ca74d912` has the identical tree.

There are **5,798 distinct Windows passes**, in disjoint partitions of 2,963
and 2,835: all 5,589 baseline cases plus all 209 L8 cases. There are zero
failures/errors/skips. All six downloaded inventory/JUnit archives reconcile
hashes, sizes, run/attempt, CPython 3.14.8, platform/workload, complete collection
universes, all setup/call/teardown phases, unique full JUnit identities and
measurement/suite totals. The 710 portable passes overlap Windows and are not
added to that total. Saved/reopened synthetic exports exercise both literal
Normal and Amendment 002 workbooks, final compaction, values, styles, merges,
widths, page setup, truthful Audit counts, relative links and preserved captures.
Required CI jobs, dependency audit and CodeQL completed successfully; existing
PR-only provenance/cleanup skips were unchanged.

| Downloaded evidence | Artifact ID | Bytes | SHA256 |
| --- | --- | --- | --- |
| Windows 0 inventory | 12532781588 | 188859 | `eeac44d93709ad9a3c7b40f518ac7c84ec42267c858d206934273b46d7dc14ab` |
| Windows 0 JUnit | 12533300072 | 59065 | `fb28647695481371dfefc6d3338f6eb74ef55e8fb3f20fb9a107db9771e4fa2c` |
| Windows 1 inventory | 12532676697 | 188054 | `74f62758eb61055429b421d55367a1addbbc65a35401ec1f46e6f5cbae3fa021` |
| Windows 1 JUnit | 12532202857 | 58893 | `b7ec2d7d69d8c324fc9857f187ad26c3050d216fcd9f0abdb329522376918b3b` |
| Portable inventory | 12531757147 | 103816 | `dc36ae03a17c00f1cace6230d5d81ac9e5a53db48e350f29279f0acf8144f180` |
| Portable JUnit | 12532385647 | 177572 | `b9998cac6b3871e8b16eb0182f0038d0cd1955d9401e915c4ab87b06bdbcae95` |
| distribution.zip | 12533095769 | 28781453 | `592a2bc5bd74b66d15eb9a1d212959e642a8bab52a0473d0254ef0fe415caad4` |
| bootstrap.zip | 12533140706 | 1024 | `764c37b01d8ef4e8169f50a9e4df0067f821d6aea999b8cccc44d9931020bb7c` |

Both exact package archives were read back. The seven-member distribution,
manifest, build identity, SBOM, runtime lock and all 45 embedded worker files
match the tested source. The packaged frozen self-test record and bootstrap cold
install, reuse, cancellation and owned cleanup checks pass. EXE SHA256 is
`95abf985b7b445f533c54c475e3dfcb5991464258d972b4f14a807b95ed49474`.
These are verified PR-run artifacts, not an attested main release.

Independent final source review accepted the narrow repair and documentation.
A separate reader independently verified all eight archives, the complete test
identities and package bytes with no findings. Source GUI self-test cases are
included in the Windows universe; the standalone source-selftest.json was not
downloaded. The packaged frozen report and workflow prerequisite were checked.
Immediately before merging, actual main remained
`84928e86bd595c94c844cb5c28643daddf2ced7f`; preceding other-session PR108 remained
`374c6da8b494871535e82da430255d95984e3877`. Its reviewed layout, omission/Audit
contracts and protected formatter/template blobs are preserved. Required checks
were complete and there were no open inline review threads. The actual PR113
merge tree was read back and exactly matches the tested tree above.

These are synthetic runner/package results. No product imports, tests, browser
fixtures, builds or EXE were executed locally. They do not establish native L8,
whole-corporate mapping/PDF completion, a new live capture or interactive Excel
visual acceptance. Unknown enabled forms and unsupported lifecycle branches
retain explicit whole-record fallback; the overall program remains open.
