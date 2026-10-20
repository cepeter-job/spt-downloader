"""Approved Indonesian copy; no UI, runtime, or tax-data dependencies."""
from types import MappingProxyType
from typing import Mapping


COPY: Mapping[str, str] = MappingProxyType({'app.title': 'Coretax SPT downloader : kalau bisa ribet, kenapa dibikin gampang',
 'settings.background.label': 'jalankan proses sedot di background',
 'results.location_hint': 'Hasil Sedot berada di folder Downloads Windows',
 'app.subtitle': 'Coretax → Excel · for personal use only',
 'app.bugreport': 'bugreport : sharmila@kemenkeu.go.id',
 'selection.confirm': 'Sedot SPT terpilih',
 'form.title': 'Masukkan NPWP dan tahun pajak',
 'form.help': 'Setelah daftar muncul, pilih SPT yang ingin diunduh.',
 'form.npwp.label': 'NPWP (16 digit)',
 'form.npwp.help': 'Ketik 16 angka, tanpa spasi, titik, atau tanda hubung.',
 'form.npwp.error': 'Isi NPWP dengan 16 angka (0–9), tanpa pemisah.',
 'form.year.help': 'Gunakan tahun pajak, bukan tahun pelaporan.',
 'form.year.error': 'Gunakan 4 angka, dari 1900 sampai 2100.',
 'action.start': 'Mulai unduh',
 'action.stop': 'Hentikan unduhan',
 'action.open_result': 'Buka folder hasil',
 'action.open_partial': 'Buka hasil sementara',
 'action.new': 'Unduh SPT lain',
 'action.details': 'Lihat rincian',
 'selection.title': 'Pilih SPT yang akan diunduh',
 'selection.help': 'Pilih SPT yang ingin diunduh. Rincian hanya diambil setelah Anda mengonfirmasi pilihan.',
 'selection.search.label': 'Cari jenis pajak, masa, pembetulan, atau ID SPT',
 'selection.empty': 'Daftar ini tidak memuat SPT yang bisa dipilih.',
 'selection.focused_id': 'ID SPT yang disorot',
 'selection.keyboard_hint': 'Pilih beberapa SPT dengan Ctrl atau Shift. Urutkan jenis: Alt+J.',
 'selection.summary': '{selected} SPT dipilih · {visible} dari {inventory} SPT ditampilkan.',
 'selection.no_match': 'Tidak ada SPT yang cocok dengan pencarian.',
 'selection.filter_reset': 'Pencarian berubah. Pilih lagi SPT yang akan diunduh.',
 'download.details.body': '{processed} dari {total} SPT sudah diproses. Kelengkapan '
                          '{verified} SPT sudah diperiksa.',
 'download.exported.title': 'File Excel sudah dibuat',
 'download.publish.title': 'Menyimpan hasil unduhan',
 'download.complete.title': 'File Excel sudah siap',
 'download.complete.body': 'Hasil untuk SPT yang dipilih sudah disimpan dan diperiksa.',
 'download.partial.title': 'Hasil unduhan belum lengkap',
 'download.stopping.title': 'Menghentikan unduhan…',
 'download.cancelled.title': 'Unduhan dihentikan',
 'download.error.title': 'Unduhan belum berhasil',
 'overwrite.title': 'Ganti hasil sebelumnya?',
 'overwrite.folder.label': 'Folder hasil sebelumnya',
 'overwrite.help': 'File dalam daftar ini akan diganti seluruhnya. Isi file lama tidak digabung dengan hasil baru.',
 'overwrite.files_count': '{count} file akan diganti.',
 'overwrite.keep_hint': 'Pilih Jangan ganti untuk menghentikan publikasi dan mempertahankan hasil sebelumnya.',
 'overwrite.context_missing': 'Folder hasil sebelumnya belum tersedia. Keputusan penggantian belum dikirim.',
 'overwrite.decline': 'Jangan ganti',
 'overwrite.confirm': 'Ganti file tersebut',
 'settings.origin.label': 'Situs login',
 'settings.account.label': 'Nama pengguna',
 'settings.password.help': 'Kosongkan jika tidak diganti',
 'settings.background.help': 'Jika memungkinkan. Browser tetap muncul saat perlu login.',
 'settings.check': 'Cek login',
 'settings.cancel_check': 'Batalkan cek',
 'settings.delete': 'Hapus login',
 'settings.dirty.title': 'Perubahan belum disimpan',
 'login.unverified.title': 'Password belum bisa dipastikan'} )

STAGE_LABELS = ('Masuk ke Coretax', 'Daftar SPT',
                'Mengambil rincian', 'Hasil unduhan')

_COUNT_PARAMETERS = {
    'selection.summary': frozenset({'selected', 'visible', 'inventory'}),
    'overwrite.files_count': frozenset({'count'}),
    'download.details.body': frozenset({'processed', 'total', 'verified'}),
}


def copy_text(key: str, **values: str | int) -> str:
    """Reject broken templates rather than rendering misleading counts."""
    template = COPY[key]
    expected = _COUNT_PARAMETERS.get(key, frozenset())
    if values.keys() != expected:
        raise ValueError('Copy parameters do not match the named template')
    for value in values.values():
        if type(value) is not int:
            raise TypeError('Copy counters must be integers, not booleans or text')
        if value < 0:
            raise ValueError('Copy counters cannot be negative')
    return template.format(**values)
