# Evidence — REPORT-1

Bukti HTTP mentah per temuan. Semua data pribadi (PII) pihak ketiga telah di-redact.

| File | Temuan | Isi |
|---|---|---|
| `poc-admin-api.txt` | F1 | `admin_update_status` + verifikasi via endpoint publik + `admin_delete` (tid fiktif) + cleanup tiket uji |
| `poc-admin-get-all.redacted.json` | F1 | Respons `admin_get_all` final (9 record, field PII → `[REDACTED]`) |
| `poc-admin-get-all.snapshot-23.redacted.txt` | F1 | Snapshot tengah pengujian (23 record ter-dump tanpa auth, contoh record + daftar field) |
| `poc-admin-page.txt` | F1/F2 | Timeline `admin.php`: HTTP 200 tanpa auth (capture #1) → HTTP 302 ke `guard.php` (capture #2) + source sink XSS |
| `poc-stored-xss.txt` | F2 | Submit payload → refleksi mentah di `get_status` → PII via `search_status` |
| `poc-upload.txt` | F3 | Upload `.php` → filename `complaint_*.php` tersimpan di database |
| `poc-pathdisclosure.txt` | F6 | Warning PHP dengan path filesystem lengkap |
| `poc-wp-enum.txt` | F5 | REST user enumeration + methods XML-RPC (`system.multicall`) |
| `poc-misc.txt` | F7 | `wp-cron.php`, `dalas/v1/stats`, MCP endpoint, fingerprint subdomain |

Catatan: seluruh tiket uji yang dibuat selama pembuktian telah dihapus dari sistem target setelah bukti terekam.
