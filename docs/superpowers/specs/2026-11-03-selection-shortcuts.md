# Checkbox pilihan cepat SPT

Permintaan operator: empat checkbox di atas tabel pemilihan, dengan PPh Potput
mencakup PPh Pasal 21/26 dan PPh Unifikasi. Operator menyetujui kombinasi
Pemb. Terakhir dengan PPh Potput dan/atau PPN.

- Awal dialog tetap kosong. All memilih seluruh baris yang terlihat dan
  menghapus mode pembetulan/kategori sebelumnya; melepas All mengosongkan pilihan.
- Pemb. Terakhir tanpa kategori memilih model pembetulan bernomor paling tinggi
  untuk setiap jenis/masa/tahun sumber, atau Normal bila tidak ada pembetulan.
  Dengan kategori, aturan itu diterapkan pada gabungan kategori yang dicentang.
  Melepasnya mengembalikan semua model kategori aktif; tanpa kategori, kosong.
- PPh Potput dan PPN dapat digabung. Memilih kategori setelah All mempersempit
  cakupan ke kategori tersebut. Melepas kategori terakhir mengosongkan pilihan.
- Pemilihan manual tetap tersedia dan menghapus indikator mode pilihan cepat.
  Sorting hanya mengubah tampilan. Perubahan pencarian mengosongkan pilihan dan
  semua checkbox, tanpa mengirim consent atau memilih ulang secara otomatis.
- All/kategori hanya menyentuh baris terlihat. Peringkat pembetulan dihitung dari
  inventaris lengkap sebelum diiriskan dengan hasil pencarian; menyembunyikan
  pembetulan terbaru tidak menjadikan Normal/pembetulan lama sebagai terbaru.

Identitas kelompok memakai caption jenis penuh case-insensitive, masa literal
asli dan tahun metadata literal bila tersedia. Jangan mengelompokkan menurut
caption tampilan `Tahunan`/nama bulan, tanggal penyampaian atau ID. Jangan
menggabungkan alias masa sumber yang berbeda. Model yang dikenali adalah Normal,
Pembetulan N, Pembetulan ke-N dan Amendment N, tanpa penebakan substring.
Nomor dibandingkan berdasarkan panjang/desimal setelah nol awalan untuk
menghindari konversi integer tak terbatas. Seluruh record dengan peringkat
tertinggi yang sama tetap dipilih, termasuk duplikat yang berbeda ID. Kelompok
dengan model tak dikenal atau jenis/masa/tahun tidak layak tetap memerlukan
pilihan manual, dengan pemberitahuan; All tetap dapat memilihnya.

Checkbox tidak mengirim IPC. Konfirmasi tetap tombol Sedot SPT terpilih,
mengirim hanya ID literal terlihat menurut urutan inventaris. Stop, request/job
stale, empty inventory, publication dan MPN tetap memakai gerbang yang ada.
Kontrol harus tetap terbaca pada dialog ringkas dan memakai kontrol Tk native.

Tes perilaku dan source/frozen self-test hanya berjalan pada GitHub runner.
Probe sementara memberi bukti baseline RED dan kandidat GREEN, lalu dihapus
sebelum CI penuh akhir. Workflow produksi, coverage, dependency dan worker
allowlist tetap utuh. Review sebelum merge meliputi PR pendahulu #173: pemilik
MPN reference acquisition/custody dan tesnya tidak diubah oleh pilihan cepat ini.
