# Pilot sumber detail JSON-hybrid untuk SPT Badan dan Masa

**Status:** desain percakapan hybrid disetujui; scope diperluas oleh pengguna ke SPT Masa. Dokumen ini diajukan untuk review spesifikasi sebelum rencana implementasi dan kode produk. PR pilot baru diizinkan, tanpa merge. Branch `feat/spt-badan-json-first` dipertahankan namanya tetapi scope PR mencakup hybrid lintas SPT.

**Basis:** `main` pada `be67f5153a07ce100048d67191a02ca1d0fca1db`. PR #8 sudah digabung secara eksternal, termasuk perbaikan retry PDF dan resume Badan lama pada `9a5fa3a6bb7dfb992948c1bbccf655747147c47b`. PR pilot mengarah langsung ke `main`, bukan lagi branch PR #8 yang telah dihapus. Tidak ada perubahan CI, akses portal, atau eksekusi produk lokal untuk penulisan spesifikasi ini.

## 1. Hasil yang diminta dan batas dukungan

Tujuan: menawarkan sumber detail JSON-first dengan verifikasi/navigasi DOM dan fallback yang terlihat dalam audit, tanpa mengganti exporter atau mengurangi bukti kelengkapan. Pengguna meminta alternatif selain DOM, kemudian menyetujui hybrid dan meminta pola yang sama untuk SPT Masa. Default lama tetap DOM; memperluas mode hybrid bukan bukti bahwa semua format native JSON telah diketahui.

| Kelompok SPT terpilih | Mode `json-first` pada pilot | Bukti format saat ini |
|---|---|---|
| PPh Badan | JSON menjadi sumber primer hanya untuk format teramati yang didukung dan terbukti lengkap; selain itu fallback DOM yang aman | Envelope corporate dengan `Payload.CurrentFormData` dan grid terpisah sudah teramati |
| PPh Masa 21/26 | Capture respons yang aman, verifikasi DOM, dan fallback DOM dengan alasan format belum didukung | Belum ada sampel respons detail Masa untuk membuat decoder primer |
| PPh Masa Unifikasi | Kontrak hybrid dan fallback yang sama | Format detail belum teramati |
| PPN Masa | Kontrak hybrid dan fallback yang sama | Format detail belum teramati |
| Jenis lain dalam scope terpilih | Tetap dapat memakai jalur DOM; hybrid tidak mengarang decoder atau form baru | Dukungan JSON primer tidak diklaim |

Capture JSON Masa dengan fallback merupakan fungsi hybrid yang nyata, bukan janji JSON primer untuk Masa. Decoder primer Masa hanya ditambahkan setelah ada respons teramati yang berizin, pemetaan form yang dapat diverifikasi, dan kontrak sintetis. Tidak meniru struktur Badan untuk Masa.

CLI mempertahankan nilai `--detail-source dom` dan menambah pilihan `--detail-source json-first`. GUI menampilkan pilihan `DOM` dan `JSON-hybrid (pilot)` dalam Pengaturan, menyimpan preferensi nonrahasia, serta meneruskan pilihan hanya ke pekerjaan ekspor. Preferensi lama atau nilai tersimpan yang tidak dikenal kembali ke DOM; nilai baru yang tidak valid ditolak sebelum worker dimulai. Cek Kredensial tidak berubah. `--from-json` tetap membaca canonical `run.json`, bukan arbitrary envelope API.

## 2. Batas capture, privasi, dan lifecycle

Boundary integrasi adalah `collect_details` pada `coretax_browser.py`, setelah selected row/metadata diverifikasi dan **sebelum** `open_return_readonly`. Listener dipasang pada context milik pekerjaan sehingga initial prefill pada same-page maupun popup tidak hilang. Epoch capture terikat pada satu aksi View, selected record, scope, source row, dan halaman/popup milik aksi tersebut. Respons tab lain, frame yang tidak dapat diatribusikan, inventory yang terlambat, atau attempt sebelumnya tidak menjadi bukti detail ini.

Observer hanya mengamati request yang dihasilkan navigasi baca browser. Tidak melakukan replay request, menebak endpoint, submit/save/cancel, atau membuat dokumen remote. Browser-generated POST bukan otomatis aksi edit; format corporate yang teramati berasal dari prefill. Untuk format lain, nama endpoint atau metode saja bukan bukti bahwa payload dapat dijadikan sumber primer.

Simpan body asli yang aman, URL sumber yang bebas secret, metode, status HTTP, sequence/attempt, halaman/form/grid/pagination yang teramati, ukuran dan hash dalam checkpoint privat. Manifest membedakan atribusi navigasi dari identitas payload yang benar-benar tervalidasi. Jangan menyimpan headers, cookies, Authorization, login POST, seluruh cabang identityprovider, auth/token responses, atau secret di URL/body/JSON yang terenkode di dalam string. Secret-bearing response ditolak seluruhnya, bukan disensor lalu dianggap body asli. Log GUI dan audit publik hanya memuat kode alasan/count/status, tanpa nilai pajak atau secret.

Callback cukup merekam metadata dan completion event; pembacaan body dilakukan untuk request yang telah selesai agar tidak menunggu download tanpa batas dalam callback. Batas pilot: body 32 MiB, total body aman per attempt 128 MiB, 1.024 respons, dan drain respons selesai maksimal 20 detik. Periksa declared size sebelum membaca bila tersedia dan actual size setelahnya; ini bukan jaminan hard cap RAM driver/browser. Proses satu body pada satu waktu, tulis incremental, dan jangan menahan seluruh body dalam daftar memori. Respons pending/over-limit/budget-exhausted tidak dihitung lengkap. Batas ini tidak memperbesar batas pagination DOM atau PDF yang sudah ada.

Stop diperiksa sebelum navigasi, pemrosesan body, adapter, fallback, checkpoint, dan publikasi. Stop tidak memulai fallback atau resume baru. Listener dilepas dan hanya popup/context milik pekerjaan ditutup di semua jalur. Batas forced owned-tree cleanup desktop yang sudah ada tetap berlaku; tidak mengklaim setiap driver call dapat dibatalkan secara sinkron.

## 3. Adapter kecil dan bukti kelengkapan

Pisahkan format/konversi murni dari akses Playwright. Gunakan modul kecil `coretax_json.py` untuk decoder/adaptasi/provenance dan `coretax_json_capture.py` untuk observer/capture privat. Kedua modul worker ditambahkan eksplisit ke `WORKER_FILES`; tidak ada registry plugin, framework scraper baru, atau dependency baru. Jalur DOM yang sudah ada tetap menjadi implementasi default dan fallback satu record penuh.

Format corporate pertama memakai HTTP sukses **dan** `IsSuccessful=true`; `ErrorCode=0` tidak mengesahkan response gagal. Decode `Payload.CurrentFormData` sebagai JSON terpisah. Dukungan mengenali struktur teramati `MainFormData`, identifier record/aggregate, group form yang dikenal, dan grid `Payload.Data`/`TotalRecords`/`Index`; tidak memakai asumsi `MainForm` atau endpoint detail rekaan. Nilai/count sampel tidak ditanam sebagai kriteria produksi.

`ReturnSheetRecordIdentifier` harus cocok dengan identifier yang tervalidasi dari selected inventory row. Bila identifier inventory memakai aggregate, pasangan record/aggregate harus diperoleh dari evidence source row yang sebenarnya, bukan menyamakan dua jenis identifier. Verifikasi aggregate bila tersedia sebagai binding teramati; binding primer yang tidak dapat dibuktikan membuat JSON tidak eligible. Metadata NPWP, tahun/basis, masa, pembetulan, source status, dan provenance URL tetap tunduk pada kontrak lama. Outer `IsDraft` tidak menimpa status dari inventory; konflik antar-lapisan disimpan sebagai observasi dan direkonsiliasi, bukan dipilih diam-diam.

Pertahankan required canonical `record_id`, `meta`, `scope`, `detail_url`, `sections`, `capture_complete`, dan `attachments`. Section memakai jalur form yang benar-benar teramati di UI; payload group bukan izin membuat worksheet untuk form/tax type yang tidak terlihat atau tidak dipilih. Pemetaan yang tidak dapat dibuktikan tidak eligible untuk JSON primer. Label UI dipakai bila pemetaannya terverifikasi; literal key/path JSON tetap disimpan sebagai provenance, bukan nama/arti pajak yang dikarang.

Angka JSON dipreservasi sebagai lexeme teks persis untuk canonical cell; pertahankan perbedaan number/string/bool/null pada provenance dan body asli. Gunakan Decimal hanya internal bila perlu perbandingan angka, jangan mengirim Decimal ke validator Excel atau memakai `default=str` sebagai konversi skema terselubung. Teks terlalu panjang/karakter yang tidak dapat diekspor tepat tidak dipotong; JSON primer tidak eligible, raw yang aman tetap privat. Urutan serta duplicate rows dipertahankan. L1-D `Data/Children` mempertahankan path/hierarki; jangan menjumlahkan parent dan descendant sebagai baris independen.

Untuk JSON COMPLETE, semua form/field/grid yang didukung dan teramati harus terpetakan serta direkonsiliasi. Gunakan tab, accordion, reset/pagination baca yang telah diinspeksi untuk memperoleh response berikutnya; tidak menggunakan page-load payload sebagai bukti exhaustiveness. Cocokkan `TotalRecords`, received rows, page/index, group/filter/context, dan count UI yang tersedia. `Data=null` dengan total nol tetap raw null dan hanya membuktikan empty grid yang terikat, bukan seluruh SPT. Contoh 10/60 tetap JSON incomplete. Repeated events tidak dibuang karena URL/body hash sama; derived page coverage hanya boleh menghitung ulang page yang identitas/context/content-nya terbukti sama, bukan menghapus duplicate rows yang sah. Context group/page yang ambigu atau data yang berubah selama traversal menolak JSON COMPLETE.

## 4. Fallback, checkpoint, workbook, dan PDF

| Keadaan | Tindakan dan status |
|---|---|
| JSON didukung, terikat, dan seluruh coverage terbukti | Pakai section JSON sebagai satu sumber record; `capture_complete` tetap menunggu seluruh kontrak termasuk PDF yang diwajibkan |
| Tidak ada JSON, format Masa/bentuk lain belum didukung, atau JSON kurang coverage tanpa pelanggaran identitas/otorisasi | Verifikasi ulang selected detail, capture satu record penuh lewat DOM, dan catat requested=`json-first`, used=`dom-fallback`, alasan aman; tidak menggabungkan section JSON parsial ke section DOM |
| Identitas/origin/provenance bertentangan, challenge/otorisasi detail tidak sah, atau source berubah | Tolak hasil record, PARTIAL/BLOCKED sesuai kontrak lama; fallback tidak boleh menutupi kegagalan safety |
| Stop atau failure DOM/PDF | Tidak ada fallback setelah Stop; record/run tetap tidak COMPLETE; checkpoint dan cancellation lifecycle dipertahankan |
| Lookup ancillary gagal, misalnya HTTP 400 dengan ErrorCode nol | Simpan observasi aman tanpa mengatribusi identifier yang tidak teramati; hanya dependency yang benar-benar diwajibkan coverage membuatnya blocking |

Audit menyebut requested/actual source dan alasan fallback secara eksplisit. JSON incomplete tetap incomplete dalam provenance walaupun hasil DOM yang terverifikasi dapat COMPLETE. Fallback informasional bukan `run.errors` palsu yang selalu memaksa PARTIAL; kegagalan nyata tetap error. `run.complete` masih mensyaratkan inventory lengkap, tidak ada error blocking, dan seluruh selected record lengkap.

Checkpoint menyimpan descriptor sumber opsional dan reference ke manifest attempt privat di bawah `returns/json/<ordinal>/<attempt>/`. Nama lokal tidak berasal dari identifier taxpayer; reference harus relative, tetap di dalam job, dan bebas traversal/link escape. Resume hybrid membutuhkan scope/record/source/mode/version yang sama serta manifest/hash yang tervalidasi. Checkpoint DOM lama tidak dianggap bukti JSON hybrid: capture ulang dengan mode baru. Dalam mode DOM, compatibility checkpoint lama dan perbaikan resume Badan tanpa lampiran dari `main` tetap berlaku. Ekspor offline lama tetap kompatibel. Attempt lama dipertahankan, tidak ditimpa atau dicampur sebagai response attempt baru.

Tidak menulis ulang renderer Excel. `resume.xlsx`, workbook per masa literal, sheet form/amendment, nilai sumber, duplicate rows, hyperlink relatif, collision checks, selection dan overwrite consent tetap sama. Raw JSON privat tidak ikut folder publik Downloads atau artifact GitHub. Sumber yang berubah tidak menimpa bukti record lama sebagai COMPLETE.

PDF keuangan/auditan Badan tetap ditemukan dari inspected link pada Induk yang telah diverifikasi. Adapter boleh membaca metadata dokumen tetapi tidak menggantinya menjadi PDF COMPLETE. Jalur Induk/read-only yang sama tetap menjalankan downloader dan publication declaration/custody/hash/size/deadline/Stop. Pertahankan perbaikan `main`: retry hanya menerima existing PDF yang persis sama dengan byte GET terbaru melalui reader terkunci; file berbeda tidak ditimpa. Masa tidak memperoleh attachment PDF rekaan dari metadata Badan.

## 5. Verifikasi dan publikasi

Semua pytest, product imports, Edge/Tk/native fixtures, source/frozen self-tests, build dan EXE execution hanya di GitHub runner. Local hanya source/AST, diff check, metadata/hash artifact dan operasi Git yang diizinkan. Fixture selalu sintetis; capture pengguna tidak disalin ke repo, subagent, artifact atau jaringan.

| Kelompok kontrak | Bukti acceptance yang harus dijalankan |
|---|---|
| Mode dan compatibility | Default DOM, preferensi lama/invalid, CLI→controller→worker→collect_details, login-check terpisah, `--from-json` tidak berubah |
| Observer dan privacy | Listener sebelum same-page/popup View, foreign tab/frame/attempt ditolak, auth/secret termasuk embedded JSON dikecualikan, body/manifest hash dan budget, listener cleanup/Stop |
| Adapter dan completeness | Embedded JSON, angka presisi/lexeme, null/bool/0, hierarchy/duplicate rows, group/page context, missing 50 of 60, identity conflict, empty grid, outer/inner status |
| Fallback dan checkpoint | Masa unknown-format benar-benar mengamati JSON dan mengekspor DOM dengan audit, JSON unsupported/partial fallback satu record penuh, unsafe/Stop tidak fallback, mode/manifest/hash mismatch, old offline/live resume/PDF retries |
| Output dan distribusi | Tulis lalu reopen XLSX sintetis per scope/form/amendment/masa; nilai/link/count/COMPLETE cocok; raw privat tidak ikut publikasi; source/frozen GUI pilihan baru dan resource allowlist benar-benar diuji |

Publikasi awal PR hanya spesifikasi ini; bukan implementasi atau bukti fitur berfungsi. Setelah pengguna menyetujui spesifikasi tertulis, buat rencana implementasi tertulis dan minta pilihan metode eksekusi sebelum kode produk. Slice berikutnya mengikuti reviewed synthetic tests → exact-head GitHub RED → reviewed minimal source → exact-head full GREEN. Periksa actual working-tree diff sebelum publish, baca kembali remote head/PR/files/body dan artifact ID/hash/tree. Jangan author CI, merge/auto-merge, atau menyebut fixture sebagai penerimaan portal live. PR mengarah ke `main`, sehingga workflow existing dapat dipicu otomatis; workflow_dispatch existing hanya alternatif tanpa perubahan CI.
