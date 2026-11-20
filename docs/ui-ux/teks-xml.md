# Teks antarmuka dari XML (developer saja)

Teks presentasi desktop berada di [`resources/ui/id-ID.xml`](../../resources/ui/id-ID.xml).
Ini adalah **sumber yang diedit developer** melalui repository lokal atau PR GitHub.
Pengguna EXE tidak dapat mengubah teks, memuat ulang XML, atau mengesampingkan
teks yang telah dibundel.

## Cakupan

Katalog mengelola teks di `spt_desktop/ui_views.py`, `spt_desktop/app.py`,
dan dialog startup `spt_gui.py`, termasuk:

- Form utama, status dan tahapan, tombol, label tabel, pemilihan SPT, dan
  konfirmasi overwrite.
- **Pengaturan**, label browser/mode, penyimpanan login, notifikasi pembaruan.
- **Dashboard penyimpanan job**, pemangkasan job COMPLETE lama, pemilihan dan
  konfirmasi penghapusan job PARTIAL/gagal, kegagalan serta pesan hasilnya.
- Teks yang memuat angka/nilai dinamis (jumlah job, MiB, NPWP, tahun pajak).

**Batas yang sengaja tidak masuk:** kode sumber Coretax yang juga dipakai
untuk parsing, nama bulan yang dipakai mengidentifikasi masa, status/enum
COMPLETE/PARTIAL sebagai data, nilai browser `msedge`/`chrome` yang menjadi
pilihan backend, ID job, data perpajakan, serta pesan yang diterima dari
worker/controller melalui event. Mengedit XML tidak boleh mengubah keputusan
consent, aturan penghapusan, atau keberhasilan scraping.

## Mengubah teks

1. Edit isi `<string id="...">...</string>`. **Jangan ubah atau hapus ID.**
2. Escape karakter `&` sebagai `&amp;` dan `<` sebagai `&lt;`. Baris baru
   di dalam nilai merupakan bagian dari teks yang ditampilkan.
3. Untuk teks dinamis seperti `{total}`, `{removed}`, `{value1}`,
   dan `{value2}`, pertahankan placeholder yang sudah ada. Nama serta jumlah
   placeholder diatur oleh `spt_desktop/ui_text_schema.py` dan tervalidasi
   sebelum build. Jangan menaruh format specifier seperti `{value1:.2f}`.
4. Buka PR. CI harus lulus portable, Windows, audit, dan self-test EXE.
   **Perubahan redaksi nilai tidak memerlukan pembaruan ekspektasi literal di test.**
   Test mencocokkan teks widget dan hasil self-test dengan nilai XML yang
   dikompilasi. Penggantian ID atau placeholder, XML tidak valid, penghilangan
   widget, dan regresi fungsional tetap dapat menggagalkan CI.
   Teks persetujuan penghapusan dan pesan keselamatan harus tetap ditinjau
   secara substantif dalam review, meski tidak dikunci ke kalimat tertentu.

`copy_text(key, **values)` tetap menangani string statis dan tiga template
angka lama dengan pemeriksaan ketat: `selection.summary`,
`overwrite.files_count`, `download.details.body`. `format_text(key, **values)`
melayani teks presentasi dinamis dengan daftar parameter bernama yang dibatasi
`DISPLAY_PARAMETERS`; tipe nilai hanya `str` atau `int` (bukan `bool`).
Parameter dihitung dan diformat di Python sebelum masuk template jika
memerlukan penampilan desimal khusus.

## Alur build

- Di checkout developer, `spt_desktop/ui_copy.py` membaca XML repo.
- Pada Windows build, `build_desktop.py` menjalankan generator
  `scripts/compile_ui_copy.py`. Generator memvalidasi XML dan menolak ID
  statis yang masih direferensikan aplikasi tetapi hilang dari katalog.
- Generator menulis `spt_desktop/_ui_copy_generated.py` (diabaikan Git).
  PyInstaller memasukkan konstanta hasil generate ke dalam EXE `--onefile`.
- Saat dijalankan dalam EXE beku, UI mengambil konstanta Python internal,
  **bukan XML di filesystem pengguna**.

Untuk pemeriksaan sintetis: `tests/test_desktop_ui_copy.py`,
`tests/test_desktop_ui_xml.py`, dan `tests/test_desktop_ui_full_catalog.py`.
Semua runtime/test produk tetap dilaksanakan pada runner GitHub sesuai
[aturan repository](../../AGENTS.md).

Lacak tindak lanjut di [issue #302](https://github.com/cepeter-job/spt-downloader/issues/302).
