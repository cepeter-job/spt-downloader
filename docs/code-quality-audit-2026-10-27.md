# Catatan audit kualitas kode dan test graveyard

Dibuat: 2026-10-27
Branch: `chore/code-quality-gate-improvements`
Base: `origin/main` (`3e46baec`)

## Ringkasan sinkronisasi
- Workspace lokal disinkronkan ke commit terbaru `origin/main` (`3e46baec`).
- Branch kerja dibuat dari `origin/main`.

## Temuan regression test graveyard
- 10 file test berisi skip/xfail.
- Sebagian besar adalah `@pytest.mark.skipif(sys.platform != 'win32', ...)`
  atau `pytest.skip(...)` karena runtime tidak tersedia.
- Tidak ada test yang di-skip tanpa alasan.

## Temuan kualitas kode
- `ruff` F821/F822/F823: lolos.
- Ekspansi seleksi ruff ke B/SIM/C4/UP/RET/RUF/PERF menghasilkan **254 pelanggaran** di 31 kode.
- Autofix menyentuh 77 file (~496 baris) — terlalu berisiko untuk satu PR.
- Aturan dipertahankan minimal: F821/F822/F823 + E9/W6.

## Rencana tindak lanjut (disarankan)
1. PR ini: tambahkan `pyproject.toml` dan pertahankan gate ruff minimum. ✅ (PR #131)
2. PR `fix/broad-exception-handling`:persempit handler `except Exception`, ganti `error=exc` dengan `error_type`, tambahkan policy comment. ✅ Selesai (f473aa7 + 45757ee + 45c9366; driver probes tetap Exception defensif per 45757ee).
3. PR `chore/ruff-bugbear`: perbaiki B007/B008/B023 (12 masalah, semua bug potensial).
3. PR `chore/ruff-simplifications`: perbaiki SIM102/SIM105/SIM117/SIM300.
4. PR `chore/ruff-pyupgrade`: ganti `datetime.timezone.utc` -> `UTC`, format string, dsb.
5. PR `chore/ruff-comprehensions`: C401/C408/C414/C416/C420.
6. PR `chore/ruff-return`: RET501/502/503/505.
7. PR `chore/ruff-ruf`: RUF005/RUF012/RUF015/RUF021/RUF100.
8. Pertimbangkan menambahkan `mypy` setelah gate di atas bersih.
9. Pertimbangkan pre-commit hooks setelah gate stabil.

## File hasil audit
- `C:\Users\kpp096\AppData\Local\hermes\cache\scratch\code_quality_report.md`
- `C:\Users\kpp096\AppData\Local\hermes\cache\scratch\ruff_autofix_diff.patch`
