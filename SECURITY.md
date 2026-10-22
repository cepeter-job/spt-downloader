# Pelaporan keamanan

SPT Downloader berjalan lokal dan menangani data yang dapat bersifat rahasia. Jangan
menaruh kredensial, cookie, profil browser, NPWP, capture, workbook/PDF nyata, atau
log privat di issue, PR, artifact CI, maupun komentar publik.

## Melaporkan kerentanan secara privat

Gunakan [Report a vulnerability](https://github.com/cepeter-job/spt-downloader/security/advisories/new)
di tab **Security** repository. Jika tombol/form privat tidak tersedia untuk akun
Anda, jangan menggantinya dengan issue publik berisi detail eksploitasi. Minta
maintainer **@cepeter** mengaktifkan private vulnerability reporting melalui kanal
privat yang sudah Anda miliki; pengaktifan pengaturan GitHub tidak dilakukan oleh
kode repository ini.

Laporan awal cukup memuat lima hal berikut:

1. Commit atau versi aplikasi, run/attempt dan artifact ID bila tersedia.
2. Batas yang dilanggar, misalnya scope output, kepemilikan proses, atau isolasi kredensial.
3. Langkah reproduksi dengan data sintetis dan hasil yang diharapkan.
4. Dampak dan prasyarat yang benar-benar diamati, tanpa mengirim rahasia untuk membuktikannya.
5. Cara menghubungi pelapor kembali melalui percakapan privat tersebut.

Pertahankan bukti asli secara lokal sesuai kebijakan instansi. Sanitasi salinan
sebelum dibagikan, dan jangan menguji akses di luar akun/sistem yang diizinkan.

## Tanggung jawab maintainer

Maintainer utama **@cepeter** meninjau laporan privat, kegagalan workflow `main`,
dan temuan Dependabot/CodeQL. Target triase adalah **dua hari kerja**; ini target
operasional proyek, bukan layanan dukungan 24 jam atau bukti notifikasi telah diuji.
Catat status, penanggung jawab, revisi perbaikan, dan bukti verifikasi dalam laporan
privat sampai koordinasi pengungkapan selesai.

### Notifikasi dan bukti penerimaan

Pengaturan repository dan preferensi notifikasi akun adalah kontrol yang berbeda.
Maintainer memeriksa jalur penerimaan berikut pada akun yang bertugas:

1. Pilih **Watch → Custom → Security alerts** atau **All Activity** pada repository.
2. Pada [pengaturan notifikasi](https://github.com/settings/notifications), aktifkan
   **Email** dan **On GitHub** untuk **Watching** sesuai kanal yang dipantau.
3. Pada bagian **Actions**, aktifkan notifikasi dan pilih **Only notify for failed
   workflows** bila hanya kegagalan yang perlu dikirim. Notifikasi bawaan Actions
   mengikuti pemicu run; notifikasi schedule mengikuti pemilik jadwal. Preferensi
   ini bukan bukti semua kegagalan `main` akan diterima oleh orang yang sama.
4. Cocokkan satu kejadian yang benar-benar diterima dengan URL dan waktu run/laporan.
   Catat penerima, waktu penerimaan, serta maintainer cadangan yang telah menyetujui
   tanggung jawabnya. Jangan menaruh isi laporan privat atau alamat rahasia dalam
   catatan publik, dan jangan menganggap pengaturan aktif sebagai bukti pengiriman.

Panduan resmi: [notifikasi keamanan](https://docs.github.com/en/subscriptions-and-notifications/how-tos/managing-security-notifications)
dan [notifikasi Actions](https://docs.github.com/en/subscriptions-and-notifications/how-tos/managing-github-actions-notifications).
Jika belum ada maintainer cadangan atau bukti penerimaan, tandai keduanya belum
terverifikasi; jangan mencantumkan orang lain tanpa persetujuan mereka.

Saat menyiapkan distribusi, maintainer memeriksa advisory baru, commit yang
didukung, checksum/provenance, serta ketersediaan build rollback. Jangan memakai
hasil audit dependensi lama sebagai jaminan bebas kerentanan saat ini.

## Versi dan lingkup dukungan

Perbaikan ditujukan ke `main` dan distribusi terverifikasi yang dipromosikan dari
`main`. Build PR dan artifact historis adalah bukti pengujian revisi tertentu,
bukan jalur dukungan tersendiri. Lihat [promosi dan rollback](docs/promosi-dan-rollback.md).

Checksum dan attestation mengikat isi/asal build; keduanya tidak menggantikan
Authenticode dari penerbit. Penerbitan dengan tanda tangan penerbit memerlukan
sertifikat atau layanan signing resmi yang disediakan maintainer. Jangan membuat
sertifikat self-signed lalu menyebutnya identitas penerbit tepercaya.

## Pemeriksaan pengaturan GitHub

Sebelum menyatakan kontrol administratif aktif, maintainer memeriksa private
vulnerability reporting, secret scanning/push protection, akses alert, izin
Actions, dan notifikasi pada akun/repository yang sebenarnya. Ketiadaan field
API atau akses `403` tidak membuktikan kontrol mati maupun aktif. Simpan tanggal
dan hasil pemeriksaan tanpa token atau payload alert privat.
