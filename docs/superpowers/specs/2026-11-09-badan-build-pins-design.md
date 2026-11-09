# SPT Badan build-pin refresh (frontend rebuild)

Baseline main: c4dadb9 (PR #203 merge).

## Live evidence

Latest Badan run (build 42560333266, job 3b19a7a8, 2026-11-09 04:38 UTC):

- CORPORATE ordinal 1: `forms_unavailable` via
  `corporate.observe_unavailable` with `corporate_observer_stage: build`
  (325ms `json_observe` bail). PPN/Unifikasi are unaffected.

Live CDP probe on the logged-in Badan detail
(`corporate-income-tax-return`, ICT_RCIT; 15 tabs):

- `performance` lists `525.32c49782948fc5ef.js` (4×, script + fetch). Pinned
  `525.ec1edffbb4a91d20.js` is dead — Coretax rolled a new chunk name.
- Fetch (same-origin, `cache:no-store`, twice identical): JS
  (`application/javascript`), 3,334,844 bytes, SHA-256
  `500e5aa4110d211c42ad4d901095e83ca0ae595791bc852a2cec12e00633b153`.
  Pinned digest for the old name was
  `fcd6d4a9244d6562a294675e802732562a9510621fbb9abbe651fa4de143048d`.
- Main `main.bed1449c3647a8ca.js` still matches
  (`ad856c925cddef51d84d49de2027cdb558ef64c0fbd7d4ecac630d54118c5b44`,
  4,467,267 bytes).
- Vendor also rolled names: live entry is `vendor.c32c4ee39d966e30.js`
  (588,921 transferred), while pinned `vendor.a03856633dae3544.js` now
  serves the ~8 KB fallback. Hash of the live bundle (2,525,901 bytes,
  twice stable): `6458fddb0ca985860e262293ea1251518f44df497dec987f58ae79eae110d173`
  vs pinned `1de6335b41d5431fd302ab7b7d00b6c593dfa6640c43ab8a88fbfbdb1b0f4b68`
  under the old name. Both URL and digest update together.

## Fix

Reviewed-data pin update (URL + digest together, per pin rules):

- `coretax_corporate.py`: `CIT_SOURCE_URL` → `525.32c4…`,
  `CIT_SOURCE_SHA256` → `500e5aa4…`.
- `coretax_corporate_projection.py`: `CIT_SOURCE` → same new URL
  (digests load by URL from `resources/build-pins.json`).
- `coretax_attachments.py`: `_PDF_PIN_PATHS` → same new 525 path.
- `resources/build-pins.json`: replace the 525 entry (new URL → new digest)
  and replace the vendor entry (new URL → new digest).
- `coretax_json.py`: `REFERENCE_ORDER_SOURCE` → new vendor URL
  (digest follows the pin; loader wiring is separate follow-up).
- Tests/fixtures: every occurrence (old 525 filename, old CIT digest,
  old vendor filename/digest) in `test_corporate_l7_native`,
  `test_corporate_l11c_native`, `test_json_hybrid_native`,
  `test_reference_order_safety`, `masa_observer_fixture`,
  `pph21_observer_fixture`. Historical `docs/` provenance untouched.

No observer/projection logic changes. MAIN and the other tax chunks
(640/693/803) are unchanged and still match.

## Verification

- CI: full green on the PR head, then merge.
- Live rerun on the merged EXE (SHA256-verified): expect Badan past the
  `build` stage; if another gate refuses, it will be the next precise
  `corporate_observer_stage`.
