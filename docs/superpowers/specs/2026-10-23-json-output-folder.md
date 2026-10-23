# JSON files in the SPT output folder

The user requests that JSON mode retain its JSON files in a `json` directory inside the completed SPT output folder, then consolidate and close PRs #85/#86 after the work is finished.

Publish the original accepted response bytes and the original capture manifest at `json/<ordinal>/<attempt>/`. Keep private checkpoint storage at `returns/json/<ordinal>/<attempt>/` for compatibility; map only the physical publication prefix. Manifest contents remain unchanged, including their original private checkpoint references. The published manifest is evidence, not a standalone resumable job. Only captures declared by selected records are copied, including accepted evidence from a PARTIAL or DOM-fallback attempt. Do not scan and copy arbitrary job JSON, request headers, browser data or unrelated attempts. DOM-only jobs produce no JSON directory.

Validate manifest equality, scope, record, attempt, response hashes, privacy and byte budgets before export and again after staging/publication. Publish declared JSON files with workbooks/PDFs, through the existing consent, cancellation, collision and recovery transaction. Keep prior unselected JSON files unchanged. Never overwrite a selected JSON path whose bytes differ from its declared evidence. Do not change COMPLETE/PARTIAL or native eligibility because evidence files were copied.

All product/test/build execution remains GitHub-runner-only. Keep synthetic tests in Git and private evidence outside Git. Preserve recovery artifacts. Before merging the consolidated PR, inspect preceding merged PRs from other sessions, preserve their changes, verify the exact head/merge tree and read back its Windows artifact.
