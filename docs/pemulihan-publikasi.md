# Pemulihan publikasi desktop yang terputus

[Kembali ke dokumentasi](README.md)

Gunakan prosedur ini bila proses desktop mati saat mengganti hasil yang sebelumnya
disetujui. Journal baru disimpan sebelum file lama dipindahkan. Folder job asal
memiliki satu `publication-recovery-*.json` yang menunjuk `manifest.json` di
`jobs/.spt-publish-*`; backup dan journal tetap privat. Jangan menaruhnya di
Downloads, mengedit path/hash, atau mengunggahnya ke issue.

## Langkah operator

1. Hentikan aplikasi dan pastikan job/browser miliknya sudah berakhir. Tutup Excel yang membuka hasil tersebut. Jangan menjalankan pemulihan bersama ekspor baru.
2. Simpan salinan privat seluruh job, notice, folder recovery dan hasil yang terpengaruh sesuai kebijakan instansi. Jangan memindahkan lokasi asli: journal mengikat identitas direktori dan lokasi Downloads aktual.
3. Dari checkout versi yang cocok dan environment CLI yang telah disiapkan, jalankan perintah di bawah dengan job ID sebenarnya.
4. Periksa keluaran. Journal `pending` mengembalikan byte hasil terdahulu; `restored` memeriksa ulang hasil pemulihan; `committed` memverifikasi publikasi yang sudah selesai sebelum interupsi cleanup. Exit 0 hanya menyatakan pemeriksaan pemulihan lokal berhasil, bukan bahwa capture SPT COMPLETE.
5. Periksa workbook, scope, jumlah dan tautan secara privat. Pertahankan backup/journal sampai pemilik data menyetujui pembersihan melalui [prosedur pemeliharaan](pemeliharaan-privat.md).

Contoh **Command Prompt**, tanpa membuka browser atau mengambil kredensial:

```bat
.venv\Scripts\python.exe -m spt_desktop.publication_recovery --job "%LOCALAPPDATA%\SPTDownloader\jobs\JOB_ID_ASLI"
```

## Bila pemulihan ditolak

Perubahan file setelah crash, backup yang berubah, junction/symlink, identitas
direktori yang berganti, file terkunci, beberapa notice untuk satu job, dan journal
lama/tidak lengkap memerlukan pemeriksaan privat. Pemulihan tidak menimpa file
yang tidak dikenali untuk memaksa keberhasilan. Salinan rekonstruksi yang terputus
tetap berupa `.spt-restore-*.partial`; percobaan berikutnya memakai file baru dan
tetap mempertahankan salinan yang belum lengkap untuk pemeriksaan. Pertahankan semua versi; jangan
menghapus `.recovery`, `.spt-publish-*`, `run.json` atau manifest secara otomatis.
Capture yang masih dapat dibaca bisa dibentuk ulang ke **folder baru** dengan
`coretax.py --from-json ... --output ...`, seperti contoh di README. Rebuild
offline tidak memberi izin untuk mengganti versi hasil yang berubah setelah crash.

Uji regresi mematikan proses nyata setelah pemindahan file lama, pemasangan file
SPT, dan pemasangan index. Pemeriksaan tersebut memakai data sintetis pada Windows
runner. Ia tidak membuktikan pemulihan dari media rusak, kebijakan sinkronisasi
endpoint, kehilangan listrik pada seluruh lapisan storage, atau validitas data
pajak di portal.
