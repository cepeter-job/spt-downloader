# Named SPT JSON folders

New CLI and desktop exports publish selected JSON evidence under `json/<SPT name>/<original ordinal>/<attempt>/`. Use exactly `PPh Badan`, `SPT PPh 21`, `SPT PPh Unifikasi`, and `PPN` for the four literal supported tax types. Other literal types use the fixed safe `SPT Lainnya`; never interpolate source text into a directory. Keep the original ordinal to distinguish records of the same type, period or model.

New exports declare `json_output_layout: tax-kind-v1` in run metadata. Missing layout means the existing `json/<ordinal>/<attempt>/` layout; an explicit invalid layout is refused. Readers support both. Offline reexport reads its source layout and writes the new layout, including in-place migration; preserve existing legacy files rather than renaming/deleting them.

Private `returns/json/` paths, every manifest reference, original response bytes, record metadata and capture eligibility/completion remain unchanged. Published manifests are evidence rather than standalone resumable captures. Preserve selected-only scope/record/attempt/hash/privacy/budget checks, held readers, case/reparse rejection, unselected JSON, consent snapshots, cancellation rollback and crash recovery. Check existing selected evidence in both layouts before replacement. Duplicate private evidence paths remain invalid even across different tax folders. DOM-only exports create no JSON directory. Private MPN JSON remains separate.

All pytest/product/build/package execution occurs on GitHub runners. Local work is limited to source/AST/Git and artifact byte/metadata inspection. Preserve CI, worker allowlists, dependencies, resources and LICENSE. Review latest other-session merges before integration. Deliver the full verified latest-main package to Downloads after merge.
