# Evidence — Report 2 (Recon)

Bukti mentah untuk pengujian lanjutan (Report 2) terhadap `https://smpm12gkb.sch.id/` dan subdomainnya.
Repositori ini **publik**, sehingga seluruh PII pihak ketiga di-redact secara deterministik.

## Skema redaksi

| Data | Bentuk di repo |
|---|---|
| Nama orang (siswa, guru, wali) | `REDACTED_<NNN>` (deterministik per-folder) |
| NIS / username siswa | Prefix + bintang, mis. `3725` → `3***` |
| Password | Pola saja, mis. `Smp<NIS>!` → `Smp<REDACTED>!` |
| Nomor WhatsApp | `62*********` |
| Link grup WhatsApp | `https://chat.whatsapp.com/<REDACTED>` |
| QR code penerima | `*********` |
| Google Drive file ID | `/d/<REDACTED>` |
| Cookie / token sesi, CSRF, request-id | `<REDACTED>` |

Nilai asli (unredacted) hanya tersimpan lokal, tidak masuk repository.

## Isi

### Temuan 1 — Unauthenticated RCE (`pedagogiai`)
- `execute-code-langs.redacted.txt` — output eksekusi python/js/php
- `execute-code-headers.redacted.txt` — header respons (CORS `*`, rate limit, PHP 8.3.35)
- `execute-code-test.redacted.txt` — tes awal

### Temuan 2 — Kebocoran kredensial siswa (Apps Script pengumuman)
- `pengumuman-3725.redacted.json`, `pengumuman-3726.redacted.json`

### Temuan 3 — Dump nilai tryout (Apps Script)
- `tryout-dump.redacted.json` — 262 record (NIS/nama ter-redact; kelas + nilai utuh)

### Temuan 4 — Guest area MBG tanpa login
- `mbg-ajax-dashboard.redacted.json`
- `mbg-riwayat.redacted.html`, `mbg-dashboard.redacted.html`, `mbg-dashboard2.redacted.html`

### Temuan 5 — Spam judi di WordPress
- `wp-search-casino.json` — 7 post kasino (via WP REST search)
- `spam-casino.html` — salinan halaman spam
- `post-sitemap.xml` — spam terindeks sitemap

### Temuan 6 — API terbuka (pedagogiai + WP)
- `pedagogiai-api-courses-full.redacted.json`, `pedagogiai-api-course-5.redacted.json`, `pedagogiai-api-courses.redacted.json`
- `wp-users.redacted.json` — 2 user WP terenumerasi
- `social-posts-405.excerpt.txt` — respons 405 (MethodNotAllowed)

### Temuan 7 — kartuujian
- `kartuujian-3725.redacted.json`, `kartuujian-3726.redacted.json`

### Artefak recon
- `recon-subdomains.txt` — 72 kandidat → 21 DNS hidup
- `recon-dns.txt` — hasil resolve DoH
- `recon-http-probe.txt` — probe HTTP
- `recon-robots.txt` — robots.txt 12 host
- `recon-wayback-cdx.txt` — 1582 URL Wayback CDX

## Catatan
- Bukti besar hanya lokal (tidak di-commit): `undangan.html` (152 MB), `spemdalas.html` (12.5 MB), dump penuh `wp-posts.json` (369 post).
- Pengujian black-box, unauthenticated, non-destruktif.
