# Pilihan cepat SPT

Empat checkbox di atas daftar: All, Pemb. Terakhir, PPh Potput dan PPN.
Operator menyetujui kombinasi kategori dan modifier pembetulan. Pemilihan awal
tetap kosong dan rincian baru diambil setelah konfirmasi eksplisit.

Implementasi hanya mengubah GUI stdlib/Tk, copy, self-test sintetis dan dokumen.
Peringkat model memakai seluruh inventaris dan arti masa/tahun yang dibuktikan
oleh sintaks kode/caption sumber yang didukung; nilai sumber, model dan ID tidak
ditulis ulang. Peringkat numerik menjaga
Pembetulan 10 > 2, leading-zero ties tetap berbeda ID dan Normal menjadi fallback.
Model tak dikenal membuat kelompok memerlukan pemilihan manual. Semua preset
diiriskan dengan baris terlihat; perubahan pencarian menghapus pilihan/preset.
Manual selection mengganti preset dan sorting mempertahankan pilihan.

## Bukti runner

- Baseline main `97f5784d988724420a9e744599c43e04d76ad2ca`, termasuk PR #173.
  Main push run `41504216464` selesai sukses.
- Tes-dahulu head `d92cb62dd20d549bfa99f47c14a473e43ff9960f`, run
  `41561796144` attempt1: 123 tes lama lulus; tepat24 tes baru gagal karena
  kontrol belum ada. Artifact `13197375659` diunduh dan dibaca ulang:
  SHA256 `75356210629886d8bfeae9371d68ab196df236c1f09ec81c51491d57c40c730a`.
- Kandidat awal `675005f1231bcee04f700c49db12d2c89d5bce45`, run
  `41562392354` attempt1: 149 kasus lulus (26 baru, 123 lama), nol gagal/error/skip.
  Artifact `13198395524` diunduh/dibaca ulang, SHA256
  `63dae8d10748b63c451c27b90b23a4630674d49167aead0f6558de39f59beef6`.
  Head final/full CI dicatat dalam PR. Kasus tambahan mencakup model null/tidak dikenal dan
  Pembetulan0, serta reflow saat pemberitahuan berubah.
- Review lanjutan menemukan bahwa kode dan caption satu masa dapat berbeda.
  Probe RED `41565629114` pada head `21446a9a294036a6876aa2f774ed1299a703fb48`
  membuktikan tiga kegagalan: alias bulanan, alias tahunan dan masa/tahun tidak
  layak. Perbaikan memakai arti masa yang dikenali, tetap mempertahankan sumber,
  dan menolak rentang Masa serta konflik tahun. CI awal `41563209425` juga
  menemukan katalog copy literal belum memuat enam key baru; ekspektasi mandiri
  ditambah untuk perubahan UI yang disengaja, tanpa menghapus pemeriksaan lama.
- GREEN alias/copy pada head `c8831552f1829c3ea5a906179528ac668b5cc46b`, run
  `41566137845` attempt1: seluruh189 kasus lulus, nol gagal/error/skip.
  Artifact `13199276395` diunduh/dibaca ulang, SHA256
  `822100ee0a9d094bb140f1ef85a7fa57bb6003ce109547813339a636c0e8bd60`.
  RED alias artifact `13198641645` berisi9 kasus dengan tepat3 kegagalan yang
  diharapkan, SHA256 `5643ae6f9c5610d21496c6f67542a6e46271bc0c130c9e94aa2125dcf649d942`.
  Satu kasus tambahan pada final memeriksa angka bulan dengan snapshot job sah
  dan penolakan saat tahun belum terikat. Head/run penuh akhir tetap di PR.
- Source/frozen self-test menjalankan checkbox Tk aktual: All, latest,
  kombinasi Potput+PPN, tidak mengirim consent dini, clear, serta mempertahankan
  sorting dan ID literal. Report menambah `selection_shortcuts_control`.
- Probe sementara dihapus sebelum CI PR final. Workflow produksi, dependency,
  coverage, worker allowlist, controller dan worker tidak diubah.

## Review interaksi

PR pendahulu sesi lain #173 menambah bounded owned reference acquisition pada
MPN. Pemilik yang ditinjau adalah `validate_mpn`, observer/capture Accounting,
`AccountingUI._acquire_reference`, `_prepare_header_catalog`, `_bind_header` dan
`detail_pages`, beserta tes failure/cleanup/provenance. Perubahan ini tidak
menyentuhnya. Field GUI selection reply tetap `selected_ids`, dalam urutan
inventaris asli, sehingga filter terbaru tidak menambah izin capture MPN,
reference GET, source/native, PDF, publication atau completion. PR #170 date
clear dan #167 validator/controller/resource juga tetap utuh.

Saat PR dibuka, main bergerak ke `920ca01f5d811064e659d503159f89699408f4a8`
melalui PR #174. Wrapper `coretax_transport.system_ca_manager`, entry/cleanup
CLI dan desktop, resource allowlist53 serta tes native TLS dipelajari sebelum
menggabungkan baseline. Konflik hanya dua paragraf baru AGENTS pada lokasi yang
sama; kedua kontrak dipertahankan. Semua sumber/tes trust dan MPN identik dengan
main baru; CI final menguji kombinasi tersebut. Checkbox tetap hanya GUI dan
tidak mengubah environment trust maupun proses worker.

Semua pytest/import produk/Tk/build/EXE berjalan pada GitHub runner; lokal hanya
source/AST/Git serta inspeksi ZIP/JSON/hash. Bukti sintetis dan paket tidak
membuktikan penerimaan akun Coretax live atau interaksi Excel operator.
