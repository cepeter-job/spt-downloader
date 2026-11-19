# Teks antarmuka dari XML (developer saja)

Teks antarmuka yang sudah dipindah ke katalog disimpan di
[`resources/ui/id-ID.xml`](../../resources/ui/id-ID.xml). XML ini **hanya
diedit developer** dalam checkout repository atau GitHub PR. EXE tidak
menawarkan editor, muat ulang, ataupun override XML.

## Mengubah teks

1. Edit teks di dalam elemen `<string id="...">...</string>`. Jangan
   mengubah ID tanpa memperbarui pemanggil dan tes.
2. Escape `&` menjadi `&amp;` dan `<` menjadi `&lt;`. Baris baru
   di dalam elemen dipertahankan apa adanya.
3. Jalankan `python -m pytest tests/test_desktop_ui_copy.py tests/test_desktop_ui_xml.py`
   di lingkungan development yang didukung, atau validasi lewat runner CI.
   Perubahan teks owner-locked memerlukan pembaruan tes dan review yang disengaja.
4. Uji perubahan melalui PR dan Windows build; teks baru tersedia setelah EXE
   baru diterbitkan.

`copy_text(key, **values)` tetap API UI. Placeholder hitungan yang diizinkan
hanya untuk `selection.summary`, `overwrite.files_count`, dan
`download.details.body`; nama placeholder tidak boleh diubah tanpa revisi
kontrak. XML harus UTF-8, memiliki root `<resources language="id-ID">`,
serta ID unik.

Dalam development, `spt_desktop/ui_copy.py` membaca XML dari repository.
Saat Windows build, `build_desktop.py` memanggil
`python -m scripts.compile_ui_copy` secara internal, menghasilkan
`spt_desktop/_ui_copy_generated.py`, lalu PyInstaller memasukkan modul
Python tersebut ke dalam EXE `--onefile`. Berkas generated diabaikan Git;
**tidak ada file XML yang disalin ke folder keluaran atau dimuat dari
direktori pengguna**. Aplikasi yang sudah terpasang memakai teks dari
build-nya sendiri.

Migrasi tahap pertama mencakup seluruh katalog lama `ui_copy.py`, judul
empat tahap, dan beberapa label umum pada `ui_views.py`.
Masih ada literal dalam `app.py` dan bagian lain. Pindahkan bertahap dalam
PR terpisah dengan uji perilaku; jangan menyamakan pesan consent/status
COMPLETE/PARTIAL dengan sekadar copy kosmetik.

Referensi: [Issue #302](https://github.com/cepeter-job/spt-downloader/issues/302).
