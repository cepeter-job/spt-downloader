# Penyelesaian prioritas 4 — fixture browser sintetis

Baseline: `e8624a8414a20e3edad8d87c80df8393d77d8f1e`, hasil merge PR #69.
Tujuan: menyelesaikan peluang reuse proses browser yang mengurangi peluncuran
pada dua shard Windows, sambil mempertahankan context baru per kasus dan semua
kontrak capture, identitas, pagination, cancellation, serta paket.

## Cakupan yang diperiksa

| Kelompok | Kasus browser lama | Modul |
| --- | ---: | ---: |
| PPN requested choice, capture readiness, recovery | 18 | 3 |
| PPN DOM context dan layout | 6 | 2 |
| Inventory browser dan listing, termasuk seluruh consumer | 61 | 8 |
| Total | 85 | 13 |

Seluruh modul ini memuat 208 kasus, termasuk kontrol tanpa browser. Fixture
browser tetap non-autouse dan hanya diminta oleh kasus browser. Dua helper
inventory harus dimigrasikan bersama karena dua modul consumer memakai keduanya.

## Langkah dan kontrak penerimaan

1. Pertahankan 208 identitas workload yang ada dan seluruh assertion lama.
   Gunakan browser dari `support_isolated_browser`, dengan context baru yang
   ditutup melalui `finally` untuk setiap pemakaian. Jangan memindahkan state,
   route, monkeypatch, metrics, atau IndexedDB ke scope modul.
2. Pertahankan timezone `Asia/Jakarta` hanya pada helper listing, default context
   pada helper inventory, level route page/context, timeout, semua data fixture,
   dan fungsi data `test_json_inventory.context()`. Daftarkan dependensi fixture
   secara eksplisit pada setiap modul consumer.
3. Ganti satu jeda auxiliary 100 ms dengan event selesai untuk request POST yang
   URL dan payload-nya tepat, dengan batas 5 detik. Pertahankan assertion bahwa
   respons auxiliary tidak mengubah sequence atau binding observer. Tambahkan
   satu regresi khusus isolasi IndexedDB/route antarkedua helper pada proses sama.
4. Jalankan tiga pasangan baseline/kandidat pada Windows dengan lock/runtime dan
   workload yang sama; balik urutan pasangan kedua. Periksa waktu sesi lengkap,
   lifecycle browser, semua fase/JUnit, hash, commit/tree/run/attempt, serta
   artifact. Jalankan regresi isolasi terpisah agar workload tetap sebanding.
5. Hapus alat profiling sementara, dokumentasikan hasil dan batasnya, verifikasi
   seluruh suite serta paket pada head final, merge setelah gate wajib lulus,
   lalu periksa run main dan artifact hasil merge.

Semua eksekusi pytest, browser, produk, self-test, dan build berada di runner
GitHub. Pemeriksaan lokal hanya membaca sumber, AST, metadata, dan artifact.
Perubahan tidak mencakup kode produksi, dependency, kebijakan cache/shard, atau
pengurangan gate CI.

## Keputusan untuk kasus yang dipertahankan

Dua varian browser pada `test_json_capture.py` berada pada shard berbeda; reuse
per modul tidak mengurangi launch pada pipeline dua shard saat ini. Satu kasus
browser pada `test_pr20_residual_contracts.py` tidak mempunyai pasangan untuk
reuse. Pertahankan ketiganya. Seluruh launch browser nyata lainnya sudah memakai
fixture berscope modul atau menguji kepemilikan proses/profil secara sengaja.

Penundaan login, prefill terlambat, polling readiness/cancellation, dan proses
anak sintetis merupakan kontrol perilaku yang diperlukan. Pertahankan semua
kontrol tersebut. Penghematan ditetapkan dari hasil pengukuran, bukan dari
perkiraan jumlah launch atau jumlah milidetik sleep yang dihapus.
