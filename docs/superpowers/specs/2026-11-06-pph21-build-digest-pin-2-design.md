# PPh21 build digest pin refresh, round 2 (real bundle)

Baseline main: 48c510cb7cbc7067ace0b284b6b13ed5328cad6d (PR #196 merge).

## Evidence

Live test on the PR #196 build (main 48c510cb, COMPLETE run) still fired
`pph21.observer_gate=build_digest` → DOM fallback. Round-1 pins (5535c900…)
had been measured from legacy bundle URLs — but those URLs now serve the
SPA index HTML (text/html, 8,359 bytes), which the observer correctly
rejects as non-JS. The pins were never for JS bytes.

## Live measurement

Opened the PPh 21/26 return detail from the latest `run.json` in a
logged-in Coretax session (CDP), enumerated `performance` resources,
and SHA-256'd the response bytes:
- `/returnsheets/id-ID/main.bed1449c3647a8ca.js` — 4,467,267 bytes,
  `ad856c925c…c5b44`
- `/returnsheets/id-ID/803.3216dd51e4f24bf3.js` (article chunk) —
  113,215 bytes, `e4fb6888…41af`

## Design

`MAIN_SOURCE` and `ARTICLE_SOURCE` URLs + digests updated to the live
bundle. The same URL pins exist in corporate projection and the PDF
guard — updated to the same live values, since they hash the same file.
PPN/Unifikasi chunk URLs remain stale (their detail pages were not
opened); they are a follow-up measurement, noted here and in the PR.
Fixture pins synced to the new production values.

## Verification

CI, then live rerun on a PPh 21/26 record: expect
`detail.source=native_verified` (or the next honest gate).
