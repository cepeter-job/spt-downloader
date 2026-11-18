"""Named integer placeholders approved for dynamic UI text."""

COUNT_PARAMETERS = {
    'selection.summary': frozenset({'selected', 'visible', 'inventory'}),
    'overwrite.files_count': frozenset({'count'}),
    'download.details.body': frozenset({'processed', 'total', 'verified'}),
}
