# Proyeksi native Induk (Corporate)

Status: usulan, menunggu persetujuan. Menyusul PR #267
(`fix/native-dump-gate`) yang CI-nya merah.

## Masalah

#267 menolak capture native Corporate selama salah satu section masih
memuat tabel dump generik (`JSON path / JSON type / Source value`). Gate itu
benar: tabel dump adalah bukti untuk payload root yang belum diproyeksikan,
bukan proyeksi form, sehingga capture yang masih memuatnya tidak setara
dengan capture DOM.

Akibatnya #267 tidak bisa hijau: fixture sintetis mengikat `Induk` hanya
lewat `paths` (tanpa `projection`), jadi adapter memang mengeluarkan tabel
dump, gate menolak, dan `detail.source` jatuh ke `dom`. Empat shard Windows
gagal (30 kegagalan / 18 test unik), `Windows package` `skipped`.

Jalur produksi juga terpengaruh. Pada live run `82eb0628` (build `6f3f0b2`,
`detail.source = json / native_verified`, COMPLETE, 0 warning), sheet Induk
hanya berisi **1 sel** untuk 74 baris sumber: tidak ada satu pun form
selain L1-D, L3, L7, L11-A, L11-C yang punya proyeksi.

## Bukti live

Diukur dari `jobs/82eb0628…/run.json` dan payload
`json/PPh Badan/0001/6810c29…/response-0001.json` (hanya nama key, tipe,
dan ada/tidak — bukan nilai):

| Section | Tabel dump | `complete` | `unmapped_rows` |
| --- | --- | --- | --- |
| Induk | 1 | false | 74 |
| L2 | 1 | false | 173 |
| L4 | 2 | false | 24 |
| L6 | 1 | false | 10 |
| L9 | 13 | false | 2410 |
| L10-A | 1 | false | 372 |
| L10-B | 1 | false | — |
| L10-C | 1 | false | 3 |
| L10-D | 1 | false | — |
| L11-B | 1 | false | 133 |

10 dari 15 section masih dump. L1-D, L3, L7, L11-A, L11-C sudah terproyeksi.

### Slot Induk yang terbukti

Template `coretax_badan_template._induk` mendeklarasikan 27 slot:
`_INDUK_IDENTITY` (10), `_INDUK_INCOME` (2), `_INDUK_CALCULATIONS` (15).
Pada run DOM pembanding (`0b224de1`, record yang sama), 25 dari 27 slot
terisi; 40 field DOM lain tidak dipetakan. Dari 27 slot deklarasi:

- **10 slot identitas** punya key payload eksplisit di `MainFormData` dan
  nilai DOM-nya identik dengan payload:
  `TaxYear`, `Status`, `AccountingPeriodStart`, `AccountingPeriodEnd`,
  `Tin`, `Name`, `EmailAddress`, `PhoneNumber`, `TinAccountant`,
  `NameAccountant`. Sepuluh ini terisi di DOM.
- **1 slot** (`TaxRate`, "11. Tarif Pajak *") punya key `MainFormData.TaxRate`,
  tetapi payload menyimpan **kode tarif** (mis. `W01`) sedangkan DOM
  menampilkan teks tarif lengkap. Keduanya bukan representasi yang sama,
  jadi tidak boleh diproyeksikan tanpa aturan render baru.
- **16 slot** hanya caption turunan (`name` kosong): 2 di `_INDUK_INCOME`
  dan 14 di `_INDUK_CALCULATIONS`, termasuk "4. Penghasilan Neto Fiskal
  sebelum Fasilitas Pajak", "9. Penghasilan Kena Pajak", "17.a.",
  "Ganti SPT sebelumnya", dst. Di DOM 14 di antaranya terisi oleh render
  frontend; di payload tidak ada key bernama sama. Membuktikan tiap turunan
  butuh pembacaan JS frontend yang hash-terpin.

Konsekuensi: proyeksi Induk yang jujur hanya bisa mengisi 10 dari 25 slot
yang terbukti terisi di DOM (10 dari 27 slot deklarasi).

## Rancangan

### 1. Bukti proyeksi dari observer

`coretax_corporate.observe_forms` menambahkan `projection` pada binding
`Induk`:

```
{'kind': 'corporate-induk-v1',
 'builds': {CIT_SOURCE_URL: digest},
 'route': page.url, 'locale': …, 'timezone': …}
```

`digest` CIT sudah dihitung dan diverifikasi sebagai 64-hex pin di awal
fungsi, jadi proof membawa tepat digest yang sudah diadmit. Tidak ada RPC,
endpoint, pin, preload, timer, atau properti halaman baru.

### 2. Proyeksi

`coretax_corporate_projection.project_induk(main, *, tax_type, locale, timezone_name)`
hanya memancarkan slot yang key-nya ada di `MainFormData` **dan** lolos
pemeriksaan tipe (string atau number token; bool/list/dict/null tidak pernah
dipaksa menjadi nilai identitas). Caption tanpa key payload tidak pernah
ditebak. `_apply_induk` memvalidasi proof (kind, satu digest CIT 64-hex,
`route` vs `event['frame_url']`, locale/timezone), `paths == [['MainFormData']]`,
adanya `primary`, serta lifecycle yang sama dengan cabang lain
(`ReturnSheetStatusCode == 'SUBMITTED'`, `ReturnSheetModel` cocok dengan
`Model SPT`, `source_status == 'SPT Dilaporkan'`).

**Tabel dump tetap disimpan** pada section yang sudah diproyeksikan. Ia
adalah bukti custody mentah (`JSON path / JSON type / Source value`) yang
diuji kontrak lain, bukan worksheet; sheet Induk tetap hanya merender
`fields`. Gate #267 karena itu melewati section yang sudah punya `fields`:
yang ditolak adalah section yang **belum** diproyeksikan.

### 3. Kejujuran kelengkapan

Sheet Induk akan berisi 10 baris, bukan 25 seperti DOM. Supaya audit tidak
mengklaim kelengkapan palsu, proyeksi menandai section sebagai tidak
lengkap dan `_induk` meneruskan sinyal itu ke `_clean_report` lewat
mekanisme `derived_complete`/`derived_reason` yang sudah ada (dipakai
L11-B DER):

- `section['projection_complete'] = False`
- `section['projection_reason'] = 'unprojected_induk_captions'`
- `template_mapping` Induk tetap `complete=False`
- `coretax_exporter` menambah kalimat keterangan untuk reason baru itu di
  kolom Keterangan audit

### 4. Yang TIDAK berubah

- Gate #267 tetap sama: dump table di section mana pun menolak capture.
  Perubahan ini membuat fixture sah menghasilkan `used=json`, bukan
  melonggarkan gate.
- `detail.source`, `coverage`, `provenance`, custody, dan identitas record
  tidak berubah.
- Semua section lain (L2, L4, L6, L9, L10-*, L11-B) tetap dump sampai
  proyeksinya sendiri jadi; masing-masing PR tersendiri.
- Tidak ada nilai pajak di diagnostik.

## Rencana uji

1. RED: `tests/test_corporate_induk_projection.py` — proof salah/`None` →
   `unverified_corporate_induk_binding`; lifecycle belum submit → refusal;
   10 field hadir dengan urutan dan label yang sama seperti deklarasi
   template; slot tanpa key payload tidak ditebak; `tables == []`.
2. RED: test observer — `Induk` binding membawa `corporate-induk-v1` dengan
   builds CIT+MAIN dan `tables: []`.
3. Update ripple: 18 assertion `/MainFormData/…` di
   `tests/test_json_adapter.py`, `test_json_hybrid.py`,
   `test_json_hybrid_native.py`, `test_issue187_real_dom_parity.py`
   berpindah dari tabel dump ke `section['fields']`.
4. `tests/test_corporate_native_dump_gate.py` tetap: dump → tolak,
   section terproyeksi → lolos.
5. `template_mapping` Induk `complete=False` dengan
   `derived_reason='unprojected_induk_captions'`, dan exporter menuliskan
   keterangan itu.
6. GUI self-test/reply inventory tidak tersentuh (tidak ada kontrol baru).

## Risiko yang diketahui

- Sheet Induk turun dari 25 baris (DOM) menjadi 10 baris (native). Ini
  pertukaran sadar: #267 + proyeksi ini memberi `used=json` yang benar,
  sementara 15 baris Induk yang diturunkan frontend baru kembali setelah
  turunannya dibuktikan lewat probe CDP hash-terpin (PR terpisah).
- Sampai turunan terbukti, `template_mapping` Induk tetap PARTIAL, jadi
  audit tidak pernah menyatakan SPT Badan lengkap secara buta.