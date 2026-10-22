# UI delivery follow-up — 22 October 2026

## Scope

The owner approved five follow-ups to the existing Tkinter flows: unsaved
Settings decisions, consistent login captions, settled dialog opening below
100 ms median, full nominal normal/compact layouts at actual 200% scaling,
and Windows accessibility evidence. Consent, Stop, cleanup, and completion
contracts remain in force. The owner will perform live Coretax/Excel acceptance.
Authenticode signing is explicitly deferred because no signing key is available;
the acceptance build will be unsigned.

The starting main commit is `d402b98a1a534f761e60500fc1cc17f367461298`.
All product execution, native fixtures, tests, measurements and builds use
GitHub runners. Local checks inspect source/AST and artifact bytes/metadata only.
Real taxpayer data, credentials, and live portal access are outside these tests.

## Behavior and regression evidence

Settings offers Simpan, Abaikan, and Kembali when preferences or a new password
are unsaved. Escape/X returns to Settings. Closing the application must use the
same decision before shutdown. A failed save keeps the dialog open. Successful
vault writes clear the password immediately and are not repeated when preference
persistence is retried. Successful deletion with failed preference persistence
is reported accurately; in-memory saved preferences change only after the disk
write succeeds. Cek login, Batalkan cek, and Hapus login use the existing catalog.

The synthetic Windows tests establish initial application focus, then exercise
actual modal focus/grabs, Settings Escape/X, root WM_DELETE_WINDOW, repeated
open/close, failed writes, partial writes, and changed/deleted accounts. They
mock the credential-store boundary, never use a real saved account.

| Exact head | Run / artifact | Observation |
| --- | --- | --- |
| `7ec15cb747cd798efd95e4304765dfe560e0edba` | [39709187703](https://github.com/cepeter-job/spt-downloader/actions/runs/39709187703), artifact `12396685413` | Initial Settings RED: 9 failed, 1 passed. Missing decision/captions and uncleared password after partial write. |
| `3e29d8398a8c065cb19aa1867ec6de045bb0f7b0` | [39709594011](https://github.com/cepeter-job/spt-downloader/actions/runs/39709594011), artifact `12396244016` | 92 passed, 5 failed, 1 teardown error. Two real deletion bugs; three focus/Escape failures addressed by establishing initial runner-window focus in the fixture. |
| `41a7862b29e3e410c7588f4f0de91e40d49aeb83` | [39710472833](https://github.com/cepeter-job/spt-downloader/actions/runs/39710472833), artifact `12396822791` | 114 passed, 7 failed. All existing Settings cases pass; five new root-close regressions and two native panel-unmapping regressions reproduce the next fixes. |

Downloaded archive SHA-256 values, matched to GitHub artifact metadata/upload:

| Artifact | SHA-256 |
| --- | --- |
| `12396685413` | `d8fb5cc81f23fd8950ae8db0aff45feec1660e37daa302b3d95635563974b043` |
| `12396244016` | `c71b1477e5d3f2408b37b04fe4431e0648dd43d33d10f92e5a053772468ed7af` |
| `12396822791` | `c34612210f66f9789c55031b7f3a0ea6703544608f6ca83529a2b64d503b680c` |

## Measurement method and initial diagnosis

The paired diagnostic keeps the historical observer from
`67396564dd12b8a3d9eb8cd08920316cf83ae2d3`: recursive geometry/owned-layout
settlement with three quiet cycles and the maximum of handler and settlement
duration. It does not subtract observer time or relabel first Expose as settled
opening. Baseline/candidate use separate processes on the same runner with
matching payload hashes, runtime, geometry and display metadata. One warm-up is
excluded, followed by ten measurements per scenario. Instrumented traces run in
separate processes and do not count as primary timings.

At `3e29d83`, opening medians were 127.69 / 139.53 / 159.88 ms for selection
inventories of 1 / 100 / 1,000 and 175.06 ms for 101 overwrite paths. The target
was still unmet. The trace showed redundant owner-window reflows unmapping and
remapping both content and summary panels; native regression tests reproduced
this in normal and compact layouts. The narrow performance fix removes those
two unconditional unmaps while retaining grid placement, callbacks and the
measurement observer.

## Display and accessibility limits

Run `39710472833` enumerated actual Windows 2022 display modes, with maximum
choices 1920×1080 and 1600×1200. None meets the diagnostic's 2560×1800 minimum
for full nominal 200% evaluation. It observed 100% scaling and Tk 9.0.4. These
facts do not establish full-size 200% acceptance.

That first UI Automation probe rejected every window because it compared the
actual interpreter's window owner with its virtualenv launcher PID. Those
rejections are diagnostic failures, not evidence of missing accessibility roles.
The probe must verify the interpreter's process ancestry and inspect its own
window before making UIA claims. Its incomplete final report also cannot prove
High Contrast restoration. Narrator/NVDA speech/navigation and movement between
distinct-DPI monitors remain separate acceptance requirements.

## Delivery status

Final focused GREEN, paired performance results, native accessibility results,
full CI and exact unsigned artifact readback are pending at this report revision.
Live acceptance remains pending the owner's checks using
[the manual checklist](../penerimaan-manual.md); synthetic tests cannot replace it.
