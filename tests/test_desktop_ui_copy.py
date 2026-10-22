"""User-visible copy is an explicit contract, separate from Tk and worker code."""
import ast
from pathlib import Path

import pytest


@pytest.mark.parametrize(('key', 'expected'), [
    ('app.title', 'Coretax SPT downloader : kalau bisa ribet, kenapa dibikin gampang'),
    ('app.subtitle', 'Coretax → Excel · for personal use only'),
    ('app.bugreport', 'bugreport : sharmila@kemenkeu.go.id'),
    ('settings.background.label', 'jalankan proses sedot di background'),
    ('results.location_hint', 'Hasil Sedot berada di folder Downloads Windows'),
    ('selection.confirm', 'Sedot SPT terpilih'),
])
def test_locked_owner_copy_is_literal(key, expected):
    from spt_desktop.ui_copy import copy_text
    assert copy_text(key) == expected


def test_main_copy_is_exact_and_selection_is_not_automatic():
    from spt_desktop.ui_copy import copy_text, STAGE_LABELS
    assert copy_text('action.start') == 'Mulai unduh'
    assert copy_text('form.help') == 'Setelah daftar muncul, pilih SPT yang ingin diunduh.'
    assert copy_text('selection.confirm') == 'Sedot SPT terpilih'
    assert STAGE_LABELS == ('Masuk ke Coretax', 'Daftar SPT',
                            'Mengambil rincian', 'Hasil unduhan')


def test_selection_summary_requires_named_integer_counts():
    from spt_desktop.ui_copy import copy_text
    assert copy_text('selection.summary', selected=2, visible=3, inventory=8) == (
        '2 SPT dipilih · 3 dari 8 SPT ditampilkan.')
    with pytest.raises(TypeError):
        copy_text('selection.summary', selected=True, visible=3, inventory=8)
    with pytest.raises(ValueError):
        copy_text('selection.summary', selected=2, visible=3)
    with pytest.raises(KeyError):
        copy_text('key.yang.tidak.ada')


@pytest.mark.parametrize(('values', 'error'), [
    ({'selected': 2, 'visible': 3, 'inventory': 8, 'extra': 1}, ValueError),
    ({'selected': -1, 'visible': 3, 'inventory': 8}, ValueError),
    ({'selected': '2', 'visible': 3, 'inventory': 8}, TypeError),
    ({'selected': 2, 'visible': False, 'inventory': 8}, TypeError),
    ({'selected': 2, 'visible': 3, 'inventory': 8.0}, TypeError),
])
def test_template_rejects_extra_or_negative_counts(values, error):
    from spt_desktop.ui_copy import copy_text
    with pytest.raises(error):
        copy_text('selection.summary', **values)


def test_detail_template_keeps_counts_separate_from_percentage():
    from spt_desktop.ui_copy import copy_text
    assert copy_text('download.details.body', processed=2, total=3, verified=1) == (
        '2 dari 3 SPT sudah diproses. Kelengkapan 1 SPT sudah diperiksa.')
    assert copy_text('selection.summary', selected=0, visible=0, inventory=0) == (
        '0 SPT dipilih · 0 dari 0 SPT ditampilkan.')
    with pytest.raises(ValueError):
        copy_text('action.start', percent=30)


def test_catalog_matches_approved_copy():
    from spt_desktop.ui_copy import COPY
    # Reviewed expectations are independent of implementation and design-document formatting.
    # Update these only for an intentional copy change, never by snapshotting runtime COPY.
    expected = {
        'app.title': 'Coretax SPT downloader : kalau bisa ribet, kenapa dibikin gampang',
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
        'selection.help': ('gunakan SHIFT untuk ngeblok SPT, dan CTRL untuk memilih multi SPT\n\n'
                           'Pilih SPT yang ingin diunduh. Rincian hanya diambil setelah Anda mengonfirmasi pilihan.'),
        'selection.search.label': 'Cari jenis pajak, masa, pembetulan, atau ID SPT',
        'selection.empty': 'Daftar ini tidak memuat SPT yang bisa dipilih.',
        'selection.focused_id': 'ID SPT yang disorot',
        'selection.keyboard_hint': 'Pilih beberapa SPT dengan Ctrl atau Shift. Urutkan jenis: Alt+J.',
        'selection.summary': '{selected} SPT dipilih · {visible} dari {inventory} SPT ditampilkan.',
        'selection.no_match': 'Tidak ada SPT yang cocok dengan pencarian.',
        'selection.filter_reset': 'Pencarian berubah. Pilih lagi SPT yang akan diunduh.',
        'download.details.body': (
            '{processed} dari {total} SPT sudah diproses. '
            'Kelengkapan {verified} SPT sudah diperiksa.'
        ),
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
        'login.unverified.title': 'Password belum bisa dipastikan',
    }
    assert dict(COPY) == expected
    assert 'app.credit' not in COPY


def test_copy_module_has_only_standard_library_imports():
    from spt_desktop import ui_copy
    tree = ast.parse(Path(ui_copy.__file__).read_text(encoding='utf-8'))
    modules = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name.split('.')[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0
            modules.append(node.module.split('.')[0])
    assert set(modules) <= {'typing', 'types', 'string', '__future__', 'collections'}


@pytest.mark.parametrize('key,expected', [
    ('selection.help', 'gunakan SHIFT untuk ngeblok SPT, dan CTRL untuk memilih multi SPT\n\n'
                       'Pilih SPT yang ingin diunduh. Rincian hanya diambil setelah Anda mengonfirmasi pilihan.'),
    ('selection.search.label', 'Cari jenis pajak, masa, pembetulan, atau ID SPT'),
    ('selection.empty', 'Daftar ini tidak memuat SPT yang bisa dipilih.'),
    ('selection.focused_id', 'ID SPT yang disorot'),
    ('selection.keyboard_hint', 'Pilih beberapa SPT dengan Ctrl atau Shift. Urutkan jenis: Alt+J.'),
])
def test_phase2_selection_copy_is_exact(key, expected):
    from spt_desktop.ui_copy import copy_text
    assert copy_text(key) == expected


@pytest.mark.parametrize('key,expected', [
    ('overwrite.folder.label', 'Folder hasil sebelumnya'),
    ('overwrite.help', 'File dalam daftar ini akan diganti seluruhnya. Isi file lama tidak digabung dengan hasil baru.'),
    ('overwrite.keep_hint', 'Pilih Jangan ganti untuk menghentikan publikasi dan mempertahankan hasil sebelumnya.'),
    ('overwrite.context_missing', 'Folder hasil sebelumnya belum tersedia. Keputusan penggantian belum dikirim.'),
])
def test_phase2_overwrite_copy_is_exact(key, expected):
    from spt_desktop.ui_copy import copy_text
    assert copy_text(key) == expected


@pytest.mark.parametrize('count,expected', [(0, '0 file akan diganti.'), (2, '2 file akan diganti.')])
def test_overwrite_count_template_is_strict(count, expected):
    from spt_desktop.ui_copy import copy_text
    assert copy_text('overwrite.files_count', count=count) == expected


@pytest.mark.parametrize('values,error', [
    ({'count': True}, TypeError), ({'count': False}, TypeError),
    ({'count': '2'}, TypeError), ({'count': 2.0}, TypeError),
    ({'count': -1}, ValueError), ({}, ValueError),
    ({'count': 1, 'extra': 0}, ValueError),
])
def test_overwrite_count_rejects_wrong_types_and_keys(values, error):
    from spt_desktop.ui_copy import copy_text
    with pytest.raises(error):
        copy_text('overwrite.files_count', **values)
