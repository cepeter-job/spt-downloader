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
| `503dacebba7f4f81af79eada4c1b420beff95bd0` | [39711230214](https://github.com/cepeter-job/spt-downloader/actions/runs/39711230214), artifact `12397526850` | 121 focused checks passed. Removing panel unmapping did not improve settled opening; the accessibility probe still failed before its final report. |
| `168efb294aafe25129bbe01f1118789cc3194b9f` | [39711985686](https://github.com/cepeter-job/spt-downloader/actions/runs/39711985686), artifact `12398025428` | 273 focused checks passed. Moving initial dialog sizing before child creation improved opening, but the target remains unmet. Native probe completed 72 observations; see limitations below. |
| `3be932df738c0e11a1ead5de0d28417b48cdc095` | [39712931044](https://github.com/cepeter-job/spt-downloader/actions/runs/39712931044), artifact `12398150182` | New scheduling RED: 4 failed, 100 passed. Explicit content changes wait for resize timers and duplicate Configure events queue redundant layout. The real-resize control passes. Counts differ because this run uses a smaller focused selection. |

Downloaded archive SHA-256 values, matched to GitHub artifact metadata/upload:

| Artifact | SHA-256 |
| --- | --- |
| `12396685413` | `d8fb5cc81f23fd8950ae8db0aff45feec1660e37daa302b3d95635563974b043` |
| `12396244016` | `c71b1477e5d3f2408b37b04fe4431e0648dd43d33d10f92e5a053772468ed7af` |
| `12396822791` | `c34612210f66f9789c55031b7f3a0ea6703544608f6ca83529a2b64d503b680c` |
| `12397526850` | `03335754a9addf32e17573444684e353c95d24c9578b3e70806b560f7d1dde47` |
| `12398025428` | `d17dc41b822c60f8ccf286550e531ce4ab773074d4f14fdf2ce3f052a6eb8464` |
| `12398150182` | `68d696af1327974bf22d8b95b63a3e8b9766df628a7970ff0592c7fe35e1b41d` |

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

At `168efb2`, paired baseline opening medians were 134.40 / 138.10 / 157.56 /
175.79 ms; candidate medians were 110.43 / 128.56 / 143.64 / 161.32 ms for
selection sizes 1 / 100 / 1,000 and overwrite size 101 respectively. Filter and
sort costs increased in the larger selection scenarios. The trace still shows
delayed owner-window reflows. The next hypothesis distinguishes explicit content
invalidation from real resize debounce; its four intended failures are recorded
above. No below-100-ms claim is supported yet.

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

The repaired probe at `168efb2` verifies launcher/interpreter ancestry and window
ownership. It completed all 72 observations/screenshots at actual 100% scaling;
every observation lacked the expected Edit or tree/table/grid UIA roles. Tested
Tk inputs appeared as unnamed panes. This is evidence of the current provider
limitation, not screen-reader speech acceptance. A separate probe memory-ownership
bug was fixed before this run. Display and High Contrast enabled flags were
restored, but the original empty High Contrast scheme became `High Contrast Black`;
the probe correctly retained an exact-restoration failure. Full nominal 200%,
NVDA/Narrator operation and distinct-DPI monitor movement remain unqualified.

The upstream [Tk accessibility proposal](https://core.tcl-lang.org/tips/doc/main/tip/733.md)
targets Tk 9.1 and describes its Windows MSAA implementation, a limited UIA
bridge, and stronger NVDA support than Narrator. The
[9.1 accessible API](https://www.tcl-lang.org/man/tcl9.1/TkCmd/accessible.html)
provides roles/names/values/focus notifications. Neither source establishes
those capabilities for the pinned Tk 9.0.4 build. A runtime/provider change
needs a separate design and regression scope; a version bump alone cannot
establish Narrator/UIA acceptance.

## Delivery status

Settings and caption behavior have runner evidence. Final scheduling GREEN,
below-100-ms performance, full CI and exact unsigned artifact readback remain
pending. Full-size 200% and Windows accessibility remain open. The owner approved
a separate desktop-only runtime candidate design and requested its implementation
plan; production adoption still requires exact source/frozen identity, password
privacy and actual NVDA/Narrator qualification.
Live acceptance remains pending the owner's checks using
[the manual checklist](../penerimaan-manual.md); synthetic tests cannot replace it.
