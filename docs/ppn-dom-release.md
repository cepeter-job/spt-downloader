# Rilis bertahap: PPN Masa melalui DOM

Rilis ini memprioritaskan PPN Masa. Gunakan **Pengaturan → Sumber detail → DOM** (atau `--detail-source dom` pada CLI). Native JSON PPN serta perbaikan khusus Unifikasi/PPh 21 dikerjakan terpisah; rilis ini tidak menyatakan dukungan native JSON Masa.

## Perubahan PPN

- Nama lampiran A-1/A-2/B-1/B-2/B-3 diikat ke template yang sesuai tanpa mengubah nama form sumber.
- Nilai Induk diikat berdasarkan label, kelompok, dan posisi kolom yang terlihat; kolom kosong tidak menggeser nilai berikutnya.
- Kolom lampiran yang dikenali dipetakan; kolom tambahan dan footer yang belum mempunyai slot tetap dipertahankan sebagai bukti sumber di bawah form.
- Ringkasan/Audit melaporkan pemetaan template PPN secara terpisah dari kelengkapan capture. Nilai yang belum terpetakan tidak dianggap hilang atau lengkap secara diam-diam.
- `resume.xlsx` mengindeks hasil terpilih dan workbook lama dalam folder yang telah lolos verifikasi scope. Penggantian SPT/PDF tetap membutuhkan persetujuan; penolakan mempertahankan hasil lama.

## Batas verifikasi

CI harus lulus pada commit rilis untuk seluruh suite, bukan hanya tes PPN. Acceptance nyata mencakup PPN Januari dan Februari berisi data pada scope yang diizinkan, dengan hash berkas asli tetap sama. Status publikasi yang dibatalkan karena tidak menyetujui penggantian harus dibedakan dari capture/ekspor yang selesai.

Unduh ZIP dari build `main` yang berhasil dan cocokkan checksum. Ekstrak seluruh ZIP, jalankan `SPTDownloader.exe`, pilih **DOM**, lalu pilih hanya SPT PPN yang dibutuhkan. CAPTCHA/MFA tetap diselesaikan secara manual.
