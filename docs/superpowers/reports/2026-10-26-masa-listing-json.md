# Source-bound submitted Masa listing JSON

This increment extends submitted-list metadata, preserving independent detail,
mapping, PDF and publication gates. It does not certify all JSON detail branches
or live portal throughput.

## Supported behavior

The existing inspected `returnsheetssubmitted` request/response binding remains
the source. Four reviewed tax/return pairs support mixed pages: ordinary Rupiah
corporate, PPN, PPh21/26 and Unifikasi. A supported page reads six current
reference/model captions instead of the complete DOM grid, preserves original
response bytes and source fields, and retains literal IDs, model, period,
display captions and pagination.

Corporate codes require January-to-December; Masa codes require the same month
01..12 at both ends, eight ASCII digits and a nonzero year. Each current period
cell must contain its exact source code or reviewed Indonesian caption. Both
equivalent renderings may coexist for one code; page-wide evidence is checked
before each original row display is preserved. An unknown family stays
unsupported even when a known row establishes its shared period equivalence.
Other conflicting captions remain fatal. No source metadata is normalized.

Source-only known pair contradictions are checked before structural fallback.
Known family/model/recognizable period contradictions cannot hide behind an
earlier unsupported row. Unknown rendering, null codes, monthly ranges,
unreviewed families and ambiguous layouts retain whole-page DOM fallback.
The narrow caption reader removes controls without reading value/checked state
and requires unspanned body geometry. Stop, selected taxpayer, status, filter,
offset/total, date rendering, raw bytes and hash custody retain their gates.

## Regression and review evidence

Tests-only RED: published head `6f4c6f86c3df60a171553bd663225dc95f2c8fd9`,
tested merge `9859615fd66f34b886d9b53150fcc6f45d2d8a62`, matching tree
`026a7f9080495ca2e70a57f17cbae17f05410076`.
[Run 40284941486](https://github.com/cepeter-job/spt-downloader/actions/runs/40284941486),
attempt 1, has 6,236 Windows cases: 86 intended failures among 96 new cases,
all 6,140 prior cases passing, no errors/skips. The 710 overlapping portable
cases passed. All six JUnit/inventory archives were downloaded by exact ID,
hash/size checked and reconciled with phase outcomes, environment and node IDs.

A fresh source reviewer identified two Important boundary errors: layout
refusal could mask a source pair contradiction, and opaque period captions
were incorrectly fatal. Tests-only review regressions used published head
`758bb0a2b256414f1c3369b1572d6dda1218bdfc`, tested merge
`0d8932d11f230d2d2da8a5fab8e9897298b4cca4`, tree
`7f38513daa41b9b974745329f9bee5fa5073b968`.
[Run 40287590060](https://github.com/cepeter-job/spt-downloader/actions/runs/40287590060),
attempt 1, reproduced eight new cases and also exposed 15 prior cases broken
by the initial equivalent-code/caption handling. This run has 23 failures among
6,244 Windows cases, no errors/skips, and 710 portable passes. It was not
baseline-clean. The 15 failures are retained as discovered integration
regressions; their existing tests remain unchanged.

One focused repair resolves all three Important findings. Seven additional
acceptance cases cover corporate/Masa rendering orders, unknown-family
non-promotion and unreviewed-caption non-equivalence, for 111 new cases in total.
The reviewer inspected the actual repair at local
`abbdcbc1bdbd362d2e3947b7a3e5baaaa52e3c40`, tree
`89c12d35d55f48ca1577dacd33081ee81b84dcd4`, and approved source readiness with
no additional material findings. Both code-quality import comments were
addressed and resolved. Superseded intermediate runs are not acceptance proof.

## Latest-main interaction

The earlier other-session PR #115's list restoration and literal annual L7
header behavior were reviewed. The listing change leaves `ListObserver`,
`_restore_list_response`, `_verify_restored_metadata`, `collect_inventory` and
`collect_details` structurally unchanged.

Before integration, other-session [PR #118](https://github.com/cepeter-job/spt-downloader/pull/118)
merged as `392c88f1ce9608ec9521b537ba90caf1e4f593ab`, tree
`a2c573d461019dd93fb89fd4eeeed9d22a5daee9`. Its separate post-detail Accounting
MPN capture, private JSON, resume layout/scope and publication declarations
remain unchanged. Only six intended listing/tests/docs text files differ from
that baseline; no CI, dependency, resource, license or worker-allowlist change
is introduced by this increment.

PR118 baseline [run 40285485821](https://github.com/cepeter-job/spt-downloader/actions/runs/40285485821),
attempt 1, tested `1aa8cef60e03f25d60b43cea862b2b3f2dda3a9b` with that exact
main tree. Independent six-archive reconciliation confirms all 6,236 Windows
cases (6,140 prior plus 96 upstream MPN/resume cases), 710 portable, zero
failures/errors/skips and no removed node IDs.

## Final latest-base verification

Published code/test head `9e6efd14bfe13867960bc69cf82503ac1d2d556b` includes
main `392c88f1ce9608ec9521b537ba90caf1e4f593ab`. Local integration
`3d8d9f88786936331ed3c80cf3961d1013fd916a`, synthetic merge
`1966aeadfc9dc92a65e38556b056a6d4006ac1c9`, and the published head share tree
`90489db6a962d92b7170e8e69a6e9247acd8fe90`.

[Run 40290398876](https://github.com/cepeter-job/spt-downloader/actions/runs/40290398876),
attempt 1, passes 6,347 Windows cases (3,239 + 3,108): all 6,236 latest-main
baseline cases plus 111 listing cases, no failures/errors/skips and no removed
coverage. The 710 overlapping portable cases pass. Every review-run failure,
including all 15 discovered baseline regressions, has a passing successor.
Six exact archive readbacks reconcile collection, shard union, all three test
phases, JUnit, measurements, runtime platform and run/attempt/commit.

| Archive | Artifact ID | Downloaded ZIP SHA256 |
| --- | ---: | --- |
| 0.zip | 12637245080 | 9bff79b10de9a50271fe114a8ac13d29e9f2d867373990db17261724df148c96 |
| 1.zip | 12636328723 | 46353c2f0b7cef525349ad01b1f7102b4e7cf733e8d8fd22f2e409bbca7a4bcc |
| bootstrap.zip | 12636259152 | 6977d9e6b4f2a86ce7804b9f1a24e501b8a6f80c576a1c6c4e3cb0704d001197 |
| distribution.zip | 12635689932 | 246ae1d779305b0fc97e1e4cd9626fb2d6905ae2d1de8c94f80643f80e091d96 |
| inventory-0.zip | 12636970615 | 2ed12ae638c9da05ef9df874417a1e6ea18582b9b5fc40a92958f1499c80dcc6 |
| inventory-1.zip | 12636063967 | 1532b8da87ce54b868f65f15e6e2c095a644516c428670c553ff18169fc9d819 |
| inventory-portable.zip | 12636131811 | 4e175c7b426a539970a11332292f0abe18f5674538d0352c833107e25f823cf1 |
| portable.zip | 12635532987 | 868a2a22f0d0ed0128149f6263b50e72e1a8bddc818874b4bcfbe70c89d5fb55 |

The exact seven-file package and six internal manifest hashes match. External
and embedded build identity, SBOM/runtime-lock identity and all 51 embedded
worker files match the reviewed source. EXE SHA256:
`5461b7b37f41892fb1217d59a95f84d6c3486743282ced8649faa5d608d00f1e`.
Frozen self-test reports production CPython 3.14.8 x64/GIL, successful GUI
self-test, no credential access and no live scrape. The separate bootstrap
report binds the exact distribution artifact/run/attempt/EXE and passes cold
install, reuse, cancellation and owned cleanup.

Later report/plan commits change documentation only. This evidence remains
bound to the code/test head, synthetic merge, tree, run and artifact IDs above.
It is a CI-verified PR package, not a claim of installed/live acceptance or
an attested production release.


## Acceptance limits

All product imports, tests, real Edge/Tk/native fixtures, source/frozen
self-tests, builds and executable runs belong to GitHub runners. Local work
uses source/AST/Git, ZIP/XML/PE metadata and hashes only. The latest private job
audit and its files remain outside version control. Capture/export byte
reconciliation does not replace a terminal publication result; no publication
guard was relaxed. Remaining unproved detail forms/lifecycles keep whole-record
DOM fallback, and synthetic acceptance does not establish live speed, portal
coverage, interactive Excel acceptance or production release attestation.

