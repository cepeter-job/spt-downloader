"""Named integer placeholders approved for dynamic UI text."""

COUNT_PARAMETERS = {
    'selection.summary': frozenset({'selected', 'visible', 'inventory'}),
    'overwrite.files_count': frozenset({'count'}),
    'download.details.body': frozenset({'processed', 'total', 'verified'}),
}

# Non-count UI templates: named fields have no Python format specifiers.
DISPLAY_PARAMETERS = {
    'settings.storage.size_display': frozenset({'prefix', 'size'}),
    'main.status.spt.diproses.0.total.terverifikasi': frozenset({'total'}),
    'main.status.value1.menghentikan.unduhan': frozenset({'value1'}),
    'main.status.value1.value2': frozenset({'value1', 'value2'}),
    'selection.message.npwp.permintaan.npwp.tahun.pajak': frozenset({'npwp', 'year'}),
    'selection.table.heading.jenis.pajak.value2': frozenset({'value2'}),
    'settings.dialog.body.removed.job.lama.berhasil.dipangkas': frozenset({'removed'}),
    'settings.dialog.body.removed.job.selesai.dipangkas.tetapi': frozenset({'removed'}),
    'settings.dialog.body.total.job.lama.memenuhi.syarat': frozenset({'total', 'value2'}),
    'settings.dialog.body.value1.job.dihapus.sepenuhnya.ada': frozenset({'value1'}),
    'settings.dialog.body.value1.job.partial.gagal.berhasil': frozenset({'value1'}),
    'settings.dialog.body.value1.job.partial.gagal.dipilih': frozenset({'value1', 'value2'}),
    'settings.message.value1.tetapi.pengaturan.belum.tersimpan': frozenset({'value1'}),
    'view.metric.baris.terbaca.scanned': frozenset({'scanned'}),
    'view.metric.belum.pasti.lengkap.value1': frozenset({'value1'}),
    'view.metric.caption.processed.total': frozenset({'caption', 'processed', 'total'}),
    'view.metric.lengkap.verified': frozenset({'verified'}),
    'view.widget.value1.label': frozenset({'label', 'value1'}),
}
