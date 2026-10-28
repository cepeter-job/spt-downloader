# Sequential MPN workbook proof verification

Normal offline export of a valid partial capture with 1032 selected MPN rows
spent more than nine CPU minutes after writing its staged workbook set. The
read-only verifier calls Worksheet.cell for each of fifteen cells in every row;
openpyxl's read-only cell access reopens and scans the worksheet XML each time.

Read the fixed header and all bounded MPN body rows in one ordered iterator.
Read the fixed audit scope in one bounded iterator. Preserve every existing
sheet/state/dimension/header, original-value, literal-type, empty-cell, scope,
provenance, precision, status and evidence check. Reject missing/extra iterator
rows rather than silently truncating with zip. No output, source, capture budget
or completion contract changes. Existing normal and read-only workbook readers
must remain compatible.

Prove XML stream-open counts independently of wall-clock timing on synthetic
empty/nonempty and safe/unsafe numeric cases. Keep rejection of late changed
amounts, formula-typed literal identifiers and contradictory audit status. Runner
RED precedes production changes. Validate normal offline publication of the
unchanged private capture using exact runner exporter bytes; capture components
must remain byte-identical to its original verified worker.
