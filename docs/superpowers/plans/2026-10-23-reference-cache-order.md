# Reference cache ordering repair

The pinned main bundle (`696ac66d…`) sorts catalog Details before the active
version consumer reads them. Existing native PPh21, Unifikasi and corporate
COUNTRY_CODE projectors incorrectly group the raw response order first. Duplicate
open-ended codes can therefore select a different label and original source row.

Reproduce only the source-proved ordinary catalog ordering: ascending literal
CodeDescription under JavaScript UTF-16 relational ordering, stable on ties. The
first raw catalog row globally switches the key to parsed ParameterData.DisplayIndex
only when its string contains the exact `"DisplayIndex":` spelling. Support
homogeneous safe integer keys or homogeneous literal string keys; unproved key
types, malformed triggered metadata and coercive mixtures stay unsupported.
Preserve original raw rows, duplicates and source indices. Group the sorted
index/row pairs, then apply the existing attempt-clock version selector. PERIOD
and model dropdown uniqueness gates remain strict and separate.

The source chain is cache.add at main UTF-16 offset3008210, Details assignment
3008441, applyReferenceDataOrderBy3006443, getSingleReferenceData3018067 and
getActiveReferenceDataValue3017141. Vendor (`1de6335b…`) Lodash orderBy460288,
an427348, Np427715 and Bp432292 establish relational keys and stable original
index ties. COUNTRY_CODE has no direct raw-response bypass. No browser cache
inspection or extra catalog requests are authorized by this repair.

1. Publish source-bound regressions and correct the earlier raw-order expected
   dated result. Read intended failing assertions from GitHub runners before
   implementing the repair. Strengthen existing native/saved PPh21 and Unifikasi
   regressions by reversing the raw version order.
2. Add one shared bounded ordering helper and use it in the three ordinary label
   projectors, retaining ParameterData evidence and original selected paths.
3. Run the full unchanged Windows/portable/package workflows, inspect exact
   artifacts, obtain fresh source review, review preceding other-session merge
   and latest main, then merge the repair with an exact head lease.

This is synthetic/source validation. The completed matched PPh21 benchmark keeps
its original tested tree and private evidence; it is not silently rebound to a
later build. Corporate native/capture/PDF/mapping gates remain independent.
