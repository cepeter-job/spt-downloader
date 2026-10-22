# Promosi release dan verifikasi rollback

[Kembali ke CI/rilis](ci-dan-rilis.md)

[release-promotion.yml](../.github/workflows/release-promotion.yml) menyediakan
promosi opt-in dari **artifact ID yang persis** milik build push `main` yang telah
berhasil. Default `publish=false` hanya menyiapkan kandidat beserta bukti yang dapat
ditinjau. Workflow tidak membangun ulang aplikasi dan tidak memakai artifact dari
PR, fork, dispatch build, run gagal, atau attempt lain.

Fitur ini memerlukan format tujuh berkas dan kelima attestation yang diperkenalkan
bersamanya. Artifact lama yang hanya mempunyai lima berkas tidak memenuhi skema
promosi ini. Ketersediaan workflow dan tes sintetis tidak membuktikan bahwa release
produksi sudah diterbitkan atau rollback pada mesin pengguna sudah dilakukan.

## Identitas dan gate sumber

Operator memasukkan run ID, attempt, commit 40 karakter dan artifact ID dari satu
build `main` yang berhasil. Verifier membaca metadata run, seluruh job pada attempt
tersebut, serta metadata artifact. Route, portable, kedua shard Windows, audit,
package, provenance dan check gabungan harus tepat sekali berhasil pada identitas
yang sama. Nama artifact, ukuran, digest SHA-256, branch, repository asal dan status
kedaluwarsa diperiksa sebelum arsip diunduh.

Digest dan ukuran ZIP diperiksa sebelum ekstraksi. ZIP wajib berisi tepat tujuh
nama distribusi; path di luar root, direktori tambahan, tautan, duplikasi nama,
enkripsi dan ukuran di luar batas ditolak. Manifest enam berkas, core frozen
self-test, identitas build dan ikatan SBOM ke executable diverifikasi. Verifier
release menggunakan kontrak pengiriman yang stabil; pemulihan release lama tidak
bergantung pada daftar kontrol GUI pada source terbaru.

Kelima subject berikut wajib mempunyai provenance yang cocok:

| Subject | Fungsi |
| --- | --- |
| `SPTDownloader.exe` | Mengikat byte executable akhir. |
| `SHA256SUMS.txt` | Mengikat manifest enam berkas distribusi. |
| `build-info.json` | Mengikat commit, run ID dan attempt yang tertanam dalam aplikasi. |
| `distribution-sbom.json` | Mengikat inventaris native dan ruang lingkup worker. |
| `SPTDownloader-Windows-x64.zip` | Mengikat byte arsip Actions asli, termasuk setelah retensinya berakhir. |

Verifikasi memakai `gh attestation verify` dengan repository, signer workflow
`.github/workflows/windows-build.yml`, source ref `refs/heads/main`, source digest,
signer digest dan penolakan self-hosted runner. Bundle disimpan lalu diverifikasi
ulang; JSON hasil verifikasi sebelumnya tidak menggantikan pemeriksaan signature.
Opsi tersebut mengikuti [manual resmi GitHub CLI](https://cli.github.com/manual/gh_attestation_verify).
Pengunduhan bundle mengikuti [gh attestation download](https://cli.github.com/manual/gh_attestation_download).

## Menyiapkan kandidat tanpa publikasi

Gunakan GitHub Actions → **Verify or promote a retained Windows release** →
**Run workflow**, pilih `main`, isi identitas sumber dan tag baru, biarkan
`rollback_tag` kosong serta `publish=false`. Pemanggilan CLI yang ekuivalen:

```powershell
$SptRepo = "cepeter-job/spt-downloader"
$SptRun = "GANTI_RUN_ID"
$SptAttempt = "GANTI_ATTEMPT"
$SptCommit = "GANTI_SHA_MAIN_40_KARAKTER"
$SptArtifact = "GANTI_ARTIFACT_ID"
$SptNewTag = "v2026.10.22"
gh workflow run release-promotion.yml --repo $SptRepo --ref main -f source_run_id=$SptRun -f source_run_attempt=$SptAttempt -f source_commit=$SptCommit -f artifact_id=$SptArtifact -f tag=$SptNewTag -f publish=false
```

Perintah ini memicu verifikasi pada runner; tidak menjalankan produk di komputer
operator. Baca kembali run dispatch yang terbentuk dan cocokkan semua input serta
SHA workflow. Artifact `release-candidate-<workflow-sha>-attempt<nomor>` berisi ZIP
asli, receipt sumber, hasil verifikasi, lima bundle Sigstore dan manifest aset.
Kandidat ini mempunyai retensi 14 hari. Belum ada release/tag baru dan belum ada
klaim penerimaan akun nyata.

## Publikasi eksplisit

Setelah kandidat dan identitasnya ditinjau, dispatch ulang dengan input sama dan
`publish=true`. Job verify tetap berjalan penuh. Job publish hanya tersedia dari
`refs/heads/main`, mempunyai `contents: write` dan `attestations: read`, serta
membaca kandidat menggunakan artifact ID output job verify pada run yang sama.
Job verify hanya mempunyai `contents: read`, `actions: read` dan `attestations: read`.

Publisher memverifikasi ulang kandidat dan kelima signature sebelum mutasi remote.
Tag/release yang sudah ada ditolak. Ref baru dibuat secara create-only pada SHA
sumber, kemudian release draft dibuat dengan aset eksplisit. Setiap aset draft
diunduh kembali berdasarkan asset ID, diperiksa digest/ukurannya, dibandingkan
dengan kandidat, dan diverifikasi lagi. Baru sesudah itu draft dipublikasikan
sebagai release terbaru; aset serta tag dibaca kembali setelah publikasi.

Tidak ada force-update, `--clobber`, penghapusan otomatis atau penggantian release
lama. Bila publikasi gagal di tengah, draft/tag yang sudah dibuat dibiarkan untuk
ditinjau; jangan menganggap rerun dapat menimpanya. Proses mengikuti perilaku
[gh release create](https://cli.github.com/manual/gh_release_create) dan
[gh release edit](https://cli.github.com/manual/gh_release_edit). Immutability
release adalah pengaturan GitHub yang terpisah; workflow tidak mengaktifkannya dan
tidak menyimpulkan bahwa pengaturan itu sudah aktif.

## Memeriksa dan menggunakan release terdahulu

Isi `rollback_tag` dengan tag release terdahulu, identitas sumber dengan run,
attempt, SHA dan artifact ID asli yang tercatat pada receipt release tersebut,
serta `publish=false`. `tag` diisi nama kandidat pemulihan baru yang aman. Jalur ini
membaca aset release berdasarkan ID dan memverifikasi tag → commit, digest aset,
manifest, identitas payload dan kelima bundle provenance. Ia tidak memerlukan
artifact atau run Actions lama masih tersedia.

Setelah verifikasi sukses, operator dapat memilih executable release lama untuk
distribusi sesuai prosedur penerimaan yang berizin. Bila perlu menerbitkan ulang
byte lama sebagai release terbaru, gunakan **tag baru** dan `publish=true`; sumber
dan byte lama tetap sama, release sebelumnya tetap utuh. Pemulihan executable
tidak melakukan downgrade otomatis, menghapus output, mengubah checkpoint,
mengganti credential store atau mengklaim kompatibilitas data pengguna. Simpan
identitas build yang akan dipulihkan dan verifikasi ruang lingkup penerimaan
sesuai [panduan penerimaan manual](penerimaan-manual.md).

Tes delivery memakai metadata, arsip dan adapter signature yang jelas sintetis
untuk membuktikan penolakan sumber salah, perubahan byte/receipt/bundle, kegagalan
readback draft serta upaya publish di luar main. Tes tersebut tidak menyatakan
signature sintetis sebagai signature GitHub yang sah. Keberhasilan promosi nyata
memerlukan run dispatch yang membaca dan memverifikasi attestation GitHub aktual;
penerimaan rollback nyata memerlukan bukti terpisah pada target berizin.
