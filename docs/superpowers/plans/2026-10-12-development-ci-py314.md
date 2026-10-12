# Rencana pengembangan, CI, dan persiapan Python 3.14

**Tujuan:** satukan aplikasi desktop yang telah diaudit ke `main`, perkuat build yang dapat direproduksi, dan buktikan kesiapan Python 3.14 tanpa mengganti runtime produksi sebelum gerbang migrasi selesai.

**Dasar:** desktop `013dd196c2a41384cae515aed5f5a1ed8b9cfb42`, audit PR #1 dan #2. Pengguna telah mengizinkan implementasi, PR, merge, dan penghapusan cabang yang selesai.

## Keputusan desain

- Produksi memakai CPython terkelola 3.11.17; kandidat memakai 3.14.8. Keduanya diuji pada Linux dan Windows, termasuk Tk, browser fixture, proses native, dan executable beku. uv dipin 0.12.22 agar katalog unduhan mencakup patch produksi.
- Dependency langsung tetap mudah ditinjau pada `requirements*.txt`. Lock transitif pada `locks/` menyimpan versi dan hash; instalasi memakai `--require-hashes`. Lock worker menjadi bagian allowlist sumber serta fingerprint runtime.
- CI selalu menghasilkan satu status agregat. Perubahan dokumentasi yang diketahui dapat melewati pekerjaan mahal; berkas tidak dikenal memicu pengujian penuh. Test portabel, test Windows, audit dependency, dan packaging terpisah. Matrix dibatasi dua pekerjaan per kelompok; test Windows yang memakai state bersama tetap serial.
- Cache hanya untuk unduhan paket/interpreter. Kunci memisahkan OS, arsitektur, versi Python, peran dependency, dan isi lock. Penulisan cache serta attestation dibatasi pada event `main` tepercaya.
- Penghitungan progress detail membaca setiap hasil sekali. Angka terverifikasi tetap mengikuti urutan callback capture/checkpoint; sertifikasi COMPLETE tetap memerlukan verifikasi output yang ada.
- Pembersihan cabang berjalan setelah CI `main` lulus. Hanya cabang PR selesai dari repositori yang sama dengan SHA yang masih sesuai dan sudah menjadi ancestor `main` yang boleh dihapus. Cabang default, protected, atau yang dipakai PR terbuka dipertahankan.
- Dokumen pengembangan dan komentar yang menjelaskan keputusan keamanan memakai bahasa Indonesia. Identitas sumber, kontrak output, dan batas read-only tidak berubah.

## Urutan implementasi dan bukti

1. Integrasikan desktop melalui PR #3. Periksa CI, CodeQL, dan kesamaan tree dengan baseline yang sudah diverifikasi.
2. Buat lock ber-hash dan validasi pemilihan interpreter. Uji kegagalan versi/hash serta allowlist worker.
3. Pisahkan workload CI dan tambahkan pemeriksaan routing, status agregat, artifact, serta pembersihan cabang. Uji perilaku fail-closed dengan metadata sintetis.
4. Tambahkan regresi biaya linear dan ketepatan progress, lalu perbaiki implementasi.
5. Tulis panduan setup, arsitektur, kontribusi, CI/rilis, troubleshooting, migrasi, dan penerimaan manual.
6. Jalankan test portabel, review silang independen, lalu test Windows dan build kedua versi pada PR final. Unduh kembali artifact berdasarkan run/SHA/ID dan periksa digest, manifest, allowlist, lisensi, serta self-test.
7. Merge hanya setelah gerbang lulus. Periksa CI pascamerge, attestation, serta daftar cabang remote. Laporkan batas yang masih memerlukan akun Coretax atau sertifikat penandatanganan resmi.

## Batas penerimaan

Tidak ada kredensial, profil browser, NPWP nyata, atau keluaran pajak dalam commit, cache, dan artifact. Test browser memakai HTML sintetis. SHA-256 dan attestation asal build bukan pengganti sertifikat Authenticode. Pengujian akun Coretax nyata memerlukan otorisasi dan scope yang diberikan pengguna.
