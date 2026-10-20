# Checklist perubahan dan template fitur baru

[Kembali ke panduan](README.md)

## Periksa baseline sebelum membuka pekerjaan

Mulai dari [baseline aktif 20 Oktober 2026](baseline-2026-10-20.md), lalu periksa kembali `main` dan PR yang sudah merged. Catat commit sumber dan bukti yang berlaku; tanggal file desain bukan bukti bahwa fiturnya belum dibuat. Pisahkan **existing**, **diusulkan**, **diimplementasikan**, dan **diverifikasi untuk commit tertentu**. Tahap 2 tidak membangun ulang shell, pemilihan/sorting, JSON-hybrid atau tombol log yang sudah ada.

## Alur kerja

Mulai dari masalah pengguna, bukan dari komponen yang ingin ditambahkan. Baca kode dan state yang terdampak. Perubahan bahasa cukup ditangani sebagai revisi copy jika tidak mengubah aksi atau kondisi. Perubahan layar perlu menunjukkan alur lengkap termasuk gagal dan batal. Perubahan status, penyimpanan, atau akses adalah perubahan perilaku dan harus memiliki rencana serta tes kontrak.

Sebelum implementasi, minta review desain tertulis. Sesudah disetujui, buat PR kecil hanya untuk delta yang belum selesai pada baseline: misalnya perbaikan dialog pemilihan/penggantian, Pengaturan, atau polish Windows. Fondasi presentasi tahap 1 tidak dibangun ulang. Jangan menggabungkan migrasi toolkit, runtime, fitur pajak, dan redesign dalam satu PR. Tidak perlu menambah dependensi visual jika ttk sudah mencukupi.

## Template usulan fitur

Salin bagian ini ke issue atau dokumen desain. Bagian yang tidak relevan harus ditulis **Tidak berlaku** beserta alasan, bukan dibiarkan kosong saat review.

### Kebutuhan

Masalah yang dialami pengguna: [jelaskan satu masalah].

Pengguna dan situasi penggunaan: [siapa yang berwenang, kapan tugas dilakukan].

Hasil yang ingin dicapai: [tindakan atau pemahaman yang bisa diuji].

Bukti kebutuhan: [laporan pengguna atau pengamatan; bedakan asumsi].

Baseline: [SHA `main` yang dibaca, PR terkait yang sudah merged, source/test yang membuktikan perilaku].

Delta: [perilaku existing → usulan; jangan mencampur target desain dengan status implementasi].

### Batas perubahan

Termasuk: [perubahan yang diperlukan].

Tidak termasuk: [perubahan yang sengaja ditunda].

Kontrak yang tidak berubah: [NPWP/tahun, akses baca, output, login, Stop, dan lainnya yang relevan].

Alasan pola B yang ada belum cukup: [isi sebelum menambah halaman/panel baru].

### Layar dan keadaan

Lokasi masuk dan kembali: [pemicu serta tujuan kembali].

Keadaan: [awal, sedang bekerja, perlu tindakan, kosong, sebagian berhasil, selesai, gagal, sedang berhenti, dibatalkan].

Untuk setiap keadaan tulis: pemicu, sumber bukti, judul, isi, tombol beserta akibatnya, fokus, dan apakah output bisa dibuka. Tandai keadaan yang tidak berlaku.

### Bahasa

Copy ID yang ditambah/diubah: [ID stabil].

Teks utama: [judul, pesan, tombol].

Istilah yang perlu penjelasan: [penjelasan dalam bahasa pengguna].

Kondisi yang tidak boleh disimpulkan: [misalnya timeout bukan password salah].

### Teknis dan privasi

Modul terdampak: [path yang sudah dibaca; modul baru ditandai usulan].

Event/field yang dipakai: [bukti tersedia; jangan mengarang data baru].

Data yang disimpan: [lokasi, umur simpan, cara hapus, izin].

Batas pekerjaan latar belakang: [worker/controller; tidak memblokir Tk].

Kegagalan dan pembatalan: [apa yang tetap tersimpan, tidak terjadi, atau belum pasti].

### Penerimaan

Skenario sintetis: [awal, berhasil, gagal, batal, event terlambat, output hilang, dan lainnya].

Keyboard/fokus: [urutan dan hasil].

Layout/DPI: [ukuran, skala, teks panjang].

Performa: [baseline, mesin, pengukuran, batas yang disepakati].

Bukti: [tes dan screenshot sintetis; apa yang belum diuji].

Keputusan pemilik: [disetujui/perlu revisi, tanggal, catatan]. Persetujuan desain tidak otomatis mengizinkan merge/deploy.

## Checklist reviewer sebelum kode

- [ ] Fitur menyelesaikan masalah yang nyata dan tidak menambah navigasi yang tidak perlu.
- [ ] Arah B dan Tkinter/ttk tetap dipertahankan, atau perubahan arah mendapat keputusan terpisah.
- [ ] Seluruh keadaan relevan, termasuk gagal, sebagian lengkap, dan batal, memiliki rancangan.
- [ ] Judul, pesan, dan tombol mudah dipahami tanpa membaca dokumentasi teknis.
- [ ] Tidak ada kode status, arahan untuk developer, slogan, atau janji yang tidak terbukti di pesan utama.
- [ ] Origin Satu tetap (tanpa URL bebas), arti tahun pajak, NPWP, serta pemisahan workbook masa/model tetap akurat.
- [ ] Default desktop JSON-hybrid dan preferensi tersimpan tidak disamakan dengan default CLI/library DOM; fallback tidak dilabeli sukses JSON.
- [ ] Search yang menghapus pilihan dibedakan dari sorting yang mempertahankannya; indeks resume gabungan tidak disamakan dengan cakupan COMPLETE job.
- [ ] Semua tombol memiliki aksi yang benar-benar didukung; tidak ada resume/antrean semu.
- [ ] Kriteria keyboard, DPI, pembaca layar, privasi, dan performa dapat diuji.

## Checklist PR implementasi

- [ ] Tes membuktikan keadaan yang berubah; jangan hanya menguji string ada di source.
- [ ] Event job lama, operasi login versus ekspor, exit mismatch, dan pembatalan tidak menghasilkan sukses palsu.
- [ ] 99% tidak mengaktifkan hasil; COMPLETE tetap memerlukan bukti controller.
- [ ] Hasil kosong berasal dari inventaris lengkap, bukan exception atau total yang belum diketahui.
- [ ] PARTIAL selalu tampak belum lengkap, meskipun folder boleh dibuka.
- [ ] Cek login tidak memicu ekspor; simpan tidak otomatis berarti login berhasil.
- [ ] SSO/timeout tidak dianggap password valid/salah; tidak ada retry kredensial otomatis.
- [ ] Hapus login hanya pada origin Satu aplikasi; kegagalan simpan kedua sumber tidak diberi status sukses.
- [ ] Footer nama pribadi tidak dipulihkan; kontak bugreport, subtitle, dan teks pemilik yang berlaku tetap sesuai katalog/test commit baseline.
- [ ] NPWP tidak dinormalisasi atau kehilangan nol awal; nilai sumber dan tautan Excel tidak berubah.
- [ ] Callback Tk tidak mengerjakan browser/Excel/I/O besar; detail status dan queue tetap terbatas.
- [ ] Keyboard, fokus balik dialog, layar kecil, DPI, High Contrast, dan pembaca layar diperiksa di Windows.
- [ ] Source dan frozen self-test dilakukan sesuai panduan repo; artifact dirujuk dengan run/commit/ID yang tepat.
- [ ] Katalog teks, mockup, dokumentasi, dan catatan keputusan diperbarui dalam perubahan yang sama.
- [ ] Tidak ada data pajak asli, akun, password, token, log privat, atau font bundel dalam PR.

Checkbox berarti bukti tersedia, bukan sekadar pekerjaan direncanakan. Untuk PR dokumentasi saja, tandai tes runtime **Tidak dijalankan: tidak ada perubahan executable**, dan jalankan pemeriksaan tautan, konsistensi copy, manifest, serta render aset yang berubah. Jangan melaporkan hasil tes lama sebagai hasil revisi baru.

## Review dengan pengguna

Gunakan data contoh dan tugas singkat: mulai unduh, perbaiki NPWP, selesaikan login, jelaskan hasil belum lengkap, hentikan proses, cek login, dan cari folder hasil. Minta pengguna menjelaskan apa yang baru terjadi dan apa langkah berikutnya. Catat kesalahan tafsir, bukan hanya apakah layar disukai.

Jangan menerima desain bila pengguna mengira hasil belum lengkap sudah lengkap, SSO sudah menguji password, atau Mulai lagi melanjutkan data sementara. Perbaiki teks/layout yang menyebabkan tafsir tersebut, lalu ulangi tugas terkait. Studi kecil membantu menemukan friksi, bukan dasar klaim persentase keberhasilan umum.

## Pemeliharaan setelah rilis

Catat penambahan copy ID dan alasan perubahan. Hapus teks yang tidak lagi dipakai setelah memastikan tidak ada referensi. Jangan membuat dua istilah untuk aksi yang sama. Simpan baseline perilaku per release agar screenshot terbaru tidak disalahartikan sebagai bukti kontrak lama. Perbarui kontrak aktif bila backend berubah melalui review yang sah; arsip desain lama tetap diberi label historis.
