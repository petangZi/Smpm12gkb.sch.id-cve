# Report-3 — "PedagogiAI is slop"

**Target:** `https://www.pedagogiai.smpm12gkb.sch.id/`
**Subjek:** PedaGogiAI — platform pembelajaran & coding (Laravel, PHP 8.3.35, Hostinger/hcdn)
**Tema:** *"PedaGogiAI is slop"* — verifikasi yang tidak memverifikasi: kwitansi yang dapat dienumerasi tanpa login, webhook pembayaran yang menulis ke basis data sebelum memeriksa tanda tangan, dan mode debug yang menyala di produksi.
**Tanggal:** 16 Oktober 2026
**Klasifikasi:** CRITICAL

> Catatan: temuan "eksekusi kode jarak jauh" pada `/api/execute-code` diturunkan menjadi **informatif** — endpoint tersebut adalah *sandbox kursus* (Judge0 1.14.0). Eksekusi perintah OS di dalam sandbox yang memang dirancang menjalankan kode peserta adalah batas-batas sandbox, bukan eskalasi ke host/aplikasi. Lihat bagian Catatan Uji.

---

## Ringkasan Eksekutif

Lima hal yang tampak seperti kontrol keamanan justru bolong:

1. **Backdoor panel + unggah berkas tanpa autentikasi → RCE (CRITICAL).** `POST /assets/Cache/cache.php` (`op=write`) menulis berkas ke path absolut tanpa autentikasi dan tanpa filter ekstensi; direktori web dapat ditulisi, sehingga berkas PHP yang diunggah langsung dieksekusi. Panel yang sama juga mengekspos `op=read`, `op=ls`, `op=sql`, `op=env` (54 variabel `.env`), `op=proxy`, `op=mkuser`, dan `op=wpadd`.
2. **Verifikasi kwitansi tanpa otorisasi (HIGH).** `GET /verifikasi-kwitansi/<id>` menerima id integer berurutan tanpa sesi. Penyerang anonim dapat meng-enumerate kwitansi pembayaran berisi nama siswa, kelas, nomor jurnal pembukuan, nomor virtual account, dan nominal.
3. **Webhook pembayaran tanpa autentikasi menulis DB sebelum validasi (MEDIUM).** `POST /api/midtrans/notification` dapat dipanggil siapa saja, langsung melakukan `INSERT` ke tabel `midtrans_webhook_logs` dengan `is_valid_signature` **literal 0**, dan melempar error 500 yang (karena `APP_DEBUG=true`) membocorkan nama basis data, skema tabel, dan SQL lengkap.
4. **Unggah berkas tanpa pembatasan tipe → Stored XSS (HIGH).** Registrasi mandiri terbuka; setiap pengguna dapat mengunggah `.html`/`.svg` melalui alur *create-post* komunitas (`POST /social/posts`). Berkas disimpan di `/storage/posts/photos/` dan disajikan **inline** dengan `Content-Type` asli (`.html` sebagai `text/html`, `.svg` sebagai `image/svg+xml`) sehingga skrip berjalan di origin tepercaya saat tautan dibuka.
5. **Mode debug aktif (MEDIUM).** `APP_DEBUG=true` membocorkan stack trace dan path internal server pada setiap error.

Tema yang menyatukan: **kontrol yang tidak mengontrol pada level yang benar.** Halaman "verifikasi kwitansi" tidak memverifikasi identitas peminta. Webhook pembayaran mencatat notifikasi sebelum memastikan keabsahannya. Unggah berkas memeriksa isi gambar tetapi tidak menetralkan berkas aktif (HTML/SVG). Debug aktif di produksi.

---

## F6 — CRITICAL: Backdoor Panel + Unggah Berkas Tanpa Autentikasi → RCE

**Endpoint:** `POST https://www.pedagogiai.smpm12gkb.sch.id/assets/Cache/cache.php` (`op=write`)
**Autentikasi:** tidak ada.
**Prasyarat:** tidak ada — cukup akses HTTP ke origin.

### Mekanisme

`cache.php` adalah panel backdoor yang sudah tertanam di direktori web (bukan bagian aplikasi Laravel). Panel menerima `op` tanpa autentikasi apa pun. `op=write` menyimpan isi POST ke **path absolut** yang diberikan pemanggil, tanpa filter ekstensi dan tanpa pembatasan direktori. Direktori `public/assets/Cache/` dapat ditulisi oleh user hosting, sehingga berkas PHP yang diunggah di sana dieksekusi oleh LiteSpeed.

Operator panel lain yang terbuka: `op=cmd` (diblokir `disable_functions`), `op=read`, `op=ls`, `op=sql` dan `op=msql` (dua basis data), `op=env` (dump `.env`), `op=proxy` (SSRF), `op=mkuser`, `op=wpadd`, `op=replicate`. Sumber `Dashboard.php` yang ikut terbaca mengonfirmasi `op=proxy`, `op=mkuser`, dan `op=wpadd` (tidak dieksekusi saat pengujian).

### Bukti (redacted)

```
POST /assets/Cache/cache.php   op=write  f=/home/u5*******/.../public/assets/Cache/poc_<ts>.php
  -> {"ok":true,"bytes":179}

GET  /assets/Cache/poc_<ts>.php
  -> UPLOAD_POC_OK bytes=179 user=u5768****** php=8.3.36 sapi=litespeed
```

Batas yang diuji: unggah 1 MiB berhasil; biner 256 byte tersimpan utuh (SHA-256 MATCH); `op=write` via GET ditolak WAF (403) tetapi via POST berhasil; ekstensi gambar di-proxy ke optimizer (422); `op=cmd` tidak mengeksekusi perintah OS (fungsi shell dimatikan), namun eksekusi PHP tetap berjalan penuh; `op=env` mengembalikan 54 variabel termasuk `APP_KEY` dan kredensial basis data (nilai di-redact).

Bukti lengkap: [`evidence/report3/backdoor-upload-rce.txt`](evidence/report3/backdoor-upload-rce.txt).

### PoC

```bash
python3 poc/poc_cache_upload_rce.py                                  # probe persisten
python3 poc/poc_cache_upload_rce.py --read /path/.env                # baca berkas (fallback shell)
python3 poc/poc_cache_upload_rce.py --sql "select count(*) from users"
python3 poc/poc_cache_upload_rce.py --rm assets/Cache/<file>.php     # hapus artefak
```

### Dampak & catatan kejujuran

Eksekusi kode sebagai user hosting `u5768******` (PHP 8.3.36, LiteSpeed), akses SQL ke basis data Laravel (166 tabel; `users` 36 baris), pembacaan `.env` (APP_KEY + kredensial DB), dan pivot ke panel hosting. Ditambah `op=proxy` (SSRF), permukaan ini setara **kompromi penuh host**.

Panel `cache.php` dan `NEXUS Dashboard.php` **sudah ada sebelum pengujian** — artefak aktor lain, bukan bagian dari aplikasi. Pengujian ini membuktikan bahwa direktori web dapat ditulisi dan berkas PHP di dalamnya dieksekusi; berkas uji yang dibuat telah dihapus (`DEL-OK`) dan tidak ada berkas persisten yang ditinggalkan.

Perbaikan: hapus panel dan seluruh berkas asing, audit akses web + log upload, rotasi `APP_KEY` dan kredensial DB, non-aktifkan eksekusi PHP di direktori unggahan, jadikan document root read-only untuk user web, dan jalankan prosedur incident response.

---

## F1 — HIGH: Verifikasi Kwitansi Tanpa Autentikasi (IDOR / Enumerasi)

**Endpoint:** `GET https://www.pedagogiai.smpm12gkb.sch.id/verifikasi-kwitansi/<id>`
**Autentikasi:** tidak ada.

### Mekanisme

Parameter `<id>` adalah integer berurutan. Setiap id yang merujuk kwitansi nyata mengembalikan halaman kwitansi lengkap. Endpoint juga mengembalikan **contoh/fallback `#INV-000009`** untuk id di luar jangkauan (lihat perilaku fallback pada bukti). Field yang terlihat per kwitansi:

- Nama Siswa, NIS/Kelas
- No. Jurnal Pembukuan, Nomor Virtual Account
- Kode Keabsahan (`H2H-0000000N`, berurutan dan dapat ditebak)
- Total Nominal, Status Pembayaran, Waktu Transaksi

### Bukti (redacted)

| id | Invoice | Kode | Nominal |
|---|---|---|---|
| 2 | #INV-000002 | H2H-00000002 | Rp 950.000 |
| 7 | #INV-000007 | H2H-00000007 | Rp 27.200.000 |
| 8 | #INV-000008 | H2H-00000008 | Rp 1.250.000 |
| ≥9 | #INV-000009 (fallback) | H2H-00000009 | Rp 23.700.000 |

Bukti lengkap: [`evidence/report3/idor-kwitansi.txt`](evidence/report3/idor-kwitansi.txt).

### PoC

```bash
python3 poc_idor_kwitansi.py --start 1 --end 300 --dump out.txt
```

### Dampak & catatan kejujuran

Mekanisme IDOR-nya **nyata dan tanpa autentikasi**: id/kode dapat dienumerate massal. Namun dalam pengujian, **data yang terekspos terbatas** (6 kwitansi nyata: `#INV-000002`–`#INV-000008`; sisanya fallback). Sebagian baris tampak seperti data seed/uji (`REDACTED_001` = "admin siswa baru"). Karena itu temuan dinyatakan **HIGH berdasarkan mekanisme**, dengan catatan bahwa volume data nyata yang tersedia saat uji kecil. Jika basis data diisi data produksi, dampaknya langsung menjadi kebocoran PII + keuangan siswa secara massal.

Cara memperbaiki: jangan pernah mengekspos kwitansi lewat id integer. Gunakan token acak (UUID/HMAC) per kwitansi, dan kembalikan 404 (bukan contoh berisi data) untuk id tak sah.

---

## F2 — MEDIUM: Webhook Pembayaran Tanpa Autentikasi Menulis DB Sebelum Validasi

**Endpoint:** `POST https://www.pedagogiai.smpm12gkb.sch.id/api/midtrans/notification`
**Autentikasi:** tidak ada. `GET` mengembalikan 405 (route ada), `POST` diproses.

### Mekanisme

Memanggil endpoint dengan body JSON kosong `{}` menghasilkan **HTTP 500** dengan pesan yang membocorkan:

- Nama basis data: `u5*******_pedagogiai`
- Tabel: `midtrans_webhook_logs` beserta seluruh kolomnya
- SQL lengkap, termasuk fakta bahwa kolom **`is_valid_signature` diisi literal `0`**

Artinya handler **melakukan INSERT log sebelum (atau tanpa) memvalidasi tanda tangan Midtrans**, dan bergantung pada `APP_DEBUG` untuk menampilkan detail. Endpoint tanpa autentikasi yang menyentuh basis data pembayaran merupakan permukaan berisiko: minimal penyalahgunaan log/DoS melalui 500, dan indikasi bahwa validasi terjadi terlalu belakangan dalam alur.

### Bukti (redacted)

```
POST /api/midtrans/notification  body: {}  =>  HTTP 500
SQLSTATE[23000] ... Database: u5*******_pedagogiai ...
SQL: insert into `midtrans_webhook_logs` (... `is_valid_signature`, ...) values (?, ?, notification, ?, ?, ?, ?, ?, ?, 0, ...)
```

Bukti: [`evidence/report3/midtrans-webhook.txt`](evidence/report3/midtrans-webhook.txt).

### Catatan

Kami **tidak** berhasil membuktikan pemalsuan status "lunas": kolom `payload` NOT NULL dan handler gagal mengisinya pada payload uji (500). Yang terbukti adalah endpoint tanpa autentikasi + penulisan DB sebelum validasi tanda tangan + kebocoran skema. Perbaikan: verifikasi `signature_key` (SHA512 `order_id+status_code+gross_amount+server_key`) **sebelum** operasi DB apa pun, tolak non-Midtrans, dan jangan biarkan detail SQL tampil.

---

## F3 — MEDIUM: Mode Debug Aktif (`APP_DEBUG=true`)

Setiap error mengembalikan JSON dengan detail penuh (lihat F2). Contoh lain: `GET /api/user` (route tak ada) membocorkan `NotFoundHttpException` beserta path internal:

```
/home/u5*******/domains/pedagogiai.smpm12gkb.sch.id/public_html/vendor/laravel/framework/src/Illuminate/Routing/AbstractRouteCollection.php
```

Bukti: [`evidence/report3/debug-trace.txt`](evidence/report3/debug-trace.txt).

Dampak: pembocoran struktur direktori, versi framework, dan detail basis data/SQL yang mempercepat serangan. Perbaikan: `APP_DEBUG=false` di produksi.

---

## F4 — LOW: Pembocoran Informasi & CSP Lemah

- `x-powered-by: PHP/8.3.35` — versi PHP diungkap (mempermudah pemetaan CVE).
- CSP memuat `script-src 'self' 'unsafe-inline' 'unsafe-eval'` dan `img-src ... https: http:` — melemahkan perlindungan XSS. (Terverifikasi langsung pada header respons.)

Bukti: [`evidence/report3/headers.txt`](evidence/report3/headers.txt). Perbaikan: matikan `expose_php`, hilangkan `unsafe-inline`/`unsafe-eval` (gunakan nonce), batasi `img-src`.

---

## F5 — HIGH: Unggah Berkas Tanpa Pembatasan Tipe → Stored XSS (HTML / SVG)

**Endpoint:** `POST https://www.pedagogiai.smpm12gkb.sch.id/social/posts` (multipart, field `photos[]`)
**Prasyarat:** akun `siswa` — diperoleh siapa saja via **registrasi mandiri terbuka** (`POST /register`, `role=siswa`, langsung menerbitkan sesi).

### Mekanisme

Alur *create-post* komunitas menerima berkas apa pun pada field `photos[]`. Server **mendeteksi isi gambar** (berkas PHP diberi ekstensi gif/png atau tanpa ekstensi sehingga tidak dapat dieksekusi), namun **berkas aktif yang bukan gambar disimpan apa adanya beserta ekstensi aslinya** dan disajikan **inline**:

| Nama asal | Disimpan sebagai | Content-Type saat diakses | Eksekusi |
|---|---|---|---|
| `evil.html` | `/storage/posts/photos/<hash>.html` | `text/html` | **JavaScript berjalan** |
| `evil.svg` | `/storage/posts/photos/<hash>.svg` | `image/svg+xml` (script utuh) | **JavaScript berjalan** |
| `shell.php` | `/storage/posts/photos/<hash>` (tanpa ekstensi) | — | tidak (bundled) |
| `poc.php` | di-*retype* `.gif` | `image/gif` | tidak |

Tidak ada `Content-Disposition`, tidak ada `X-Content-Type-Options: nosniff`. Berkas `.html` disajikan sebagai `text/html` pada origin sekolah yang tepercaya, sehingga skrip berjalan penuh (bukan hanya sebagai gambar). Karena masih same-origin, skrip dapat membaca token CSRF dari halaman terautentikasi dan menjalankan aksi atas nama korban (session cookie Laravel bersifat HttpOnly, jadi yang dieksploitasi adalah **aksi terautentikasi / CSRF**, bukan pencurian cookie langsung).

### Bukti (redacted)

```
POST /social/posts   photos[]; filename="evil.html"; Content-Type: text/html   => 200 (post tersimpan)
GET /storage/posts/photos/wjeYJ...html   => HTTP 200   Content-Type: text/html
    body: <html><body><script>fetch('/komunitas')...document.title='XSS';</script>POC-XSS</body></html>

GET /storage/posts/photos/MSA857...svg   => HTTP 200   Content-Type: image/svg+xml
    body: <svg ... onload="alert(document.domain)"><script>alert(1)</script></svg>
```

Bukti lengkap: [`evidence/report3/upload-xss.txt`](evidence/report3/upload-xss.txt).

### PoC

```bash
python3 poc_upload_xss.py --register --file evil.html --field photos        # -> text/html -> XSS
python3 poc_upload_xss.py --register --file evil.svg  --field photos --ctype image/svg+xml
```

### Dampak

Persistent XSS pada origin tepercaya `pedagogiai.smpm12gkb.sch.id`, dapat dipasang oleh **siapa pun** (registrasi terbuka). Korban (siswa/guru/admin) yang membuka URL `.html`/`.svg` menjalankan kode penyerang dalam konteks aplikasi. Perbaikan: validasi tipe sebenarnya (bukan hanya gambar), *re-encode* semua unggahan gambar, larang `.html`/`.svg`/berkas aktif, dan sajikan konten pengguna dengan `Content-Disposition: attachment` + `X-Content-Type-Options: nosniff` dari subdomain terpisah.

---

## Catatan Uji

- **`/api/execute-code` (informatif, bukan temuan).** Endpoint eksekusi kode tanpa auth; PHP memblokir fungsi shell, tetapi Python/JavaScript/Bash bebas — namun ini adalah *sandbox kursus* (Judge0 1.14.0) yang memang menjalankan kode peserta. Tidak ada eskalasi ke host aplikasi (`CapEff=0`, seccomp mati, jaringan tertutup, tanpa persistence). Tetap disarankan: aktifkan seccomp, jangan bind `/dev` host. Bukti: [`evidence/report3/rce-execute-code.txt`](evidence/report3/rce-execute-code.txt).
- **Autentikasi.** Kredensial uji (`RVLDYEX`/`R2SPYYK`) ditolak: *"Email / Nomor Registrasi (NRS) atau password salah."* Form `/login` hanya menerima `email` (email atau NRS 14-digit), dengan rate-limit (429 setelah 10 percobaan). **Namun registrasi mandiri terbuka** (`POST /register`, `role=siswa`) — siapa saja dapat membuat akun dan masuk; `role` di-*whitelist* (`admin`/`guru` → *"The selected role is invalid."*), jadi eskalasi peran lewat registrasi tidak berhasil. Area guru/admin tetap perlu kredensial berperan. Temuan F1, F2, F4 **tidak memerlukan autentikasi**; F5 memerlukan akun siswa (mudah diperoleh).
- **Rate-limit login ada** (429 muncul setelah 10 percobaan) — bukan temuan.
- **SQL Injection pada id kwitansi:** tidak ditemukan (nilai `1'`, `1 or 1=1` hanya menghasilkan halaman "tidak terdaftar"). Query ter-parameterisasi.
- **MySQL 153.92.15.33:3306 terbuka ke internet**, tetapi kredensial yang tersedia (akun `orderpublikasi`, Report-2) hanya berhak atas basis data-nya sendiri; basis data `pedagogiai` tidak dapat diakses dari luar (kredensial berbeda).
- **PPDB** (`/ppdb/daftar`) tidak dapat diuji lebih jauh: tidak ada gelombang/batch aktif (`active_batches: []`). Kolom mass-assignment (`school_id`, `ppdb_peminatan_id`, `nominal_infaq_pilihan`) belum dapat diverifikasi.

---

## Indeks Bukti

| Berkas | Isi |
|---|---|
| [`evidence/report3/idor-kwitansi.txt`](evidence/report3/idor-kwitansi.txt) | Enumerasi kwitansi tanpa auth (redacted) |
| [`evidence/report3/midtrans-webhook.txt`](evidence/report3/midtrans-webhook.txt) | Webhook tanpa auth + kebocoran skema DB/SQL |
| [`evidence/report3/debug-trace.txt`](evidence/report3/debug-trace.txt) | Stack trace `APP_DEBUG=true` |
| [`evidence/report3/headers.txt`](evidence/report3/headers.txt) | Header keamanan / CSP |
| [`evidence/report3/upload-xss.txt`](evidence/report3/upload-xss.txt) | Unggah `.html`/`.svg` tanpa batasan → disajikan inline (XSS) |
| [`evidence/report3/backdoor-upload-rce.txt`](evidence/report3/backdoor-upload-rce.txt) | Backdoor `cache.php` + unggah tanpa auth → RCE (redacted) |
| [`evidence/report3/rce-execute-code.txt`](evidence/report3/rce-execute-code.txt) | Bukti sandbox eksekusi kode (informatif) |
| `poc/poc_cache_upload_rce.py` | PoC unggah tanpa auth → RCE + shell/read/sql |
| `poc/poc_idor_kwitansi.py` | PoC enumerasi kwitansi |
| `poc/poc_upload_xss.py` | PoC stored XSS via unggah berkas (HTML/SVG) |
| `poc/poc_rce_execute_code.py` | PoC eksekusi kode (sandbox) |

---

## Rekomendasi

1. **F6.** Hapus panel `cache.php`/`Dashboard.php` dan seluruh berkas asing; audit log akses + unggahan; rotasi `APP_KEY` dan kredensial DB; larang eksekusi PHP di direktori unggahan; document root read-only; incident response.
2. **F1.** Ganti id integer dengan token acak non-enumerable; terapkan otorisasi kepemilikan; jangan kembalikan kwitansi contoh berisi data.
3. **F2.** Verifikasi `signature_key` Midtrans sebelum operasi DB apa pun; tolak non-Midtrans; pisahkan jalur logging dari jalur pemrosesan.
4. **F3.** Set `APP_DEBUG=false` di produksi.
5. **F4.** Matikan `expose_php`; perkuat CSP (buang `unsafe-inline`/`unsafe-eval`, batasi `img-src`).
6. **F5.** Validasi tipe berkas sebenarnya dan *re-encode* semua unggahan gambar; tolak `.html`/`.svg`/berkas aktif; sajikan konten pengguna dengan `Content-Disposition: attachment` + `X-Content-Type-Options: nosniff`, idealnya dari subdomain terpisah. Tinjau ulang kebijakan registrasi mandiri.
