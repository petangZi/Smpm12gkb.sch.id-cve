# Report-4 — "Undian tanpa pintu"

**Target:** `https://spinner.smpm12gkb.sch.id/`
**Subjek:** Aplikasi undian "Neobrutalism Lucky Draw" (Laravel, PHP 8.4.27, Hostinger/LiteSpeed)
**Tema:** Panel pengelola undian dan seluruh API status berjalan **tanpa autentikasi sama sekali** — bukan kontrol yang lemah, tetapi tidak ada kontrol.
**Tanggal:** 28 Oktober 2026
**Klasifikasi:** CRITICAL

---

## Ringkasan Eksekutif

Aplikasi ini tidak memasang middleware autentikasi pada satu pun route (`routes/web.php`). Tidak ada halaman login; tidak ada pemeriksaan sesi. Siapa pun yang mengetahui URL dapat:

1. **Mereset seluruh undian (CRITICAL).** `POST /api/lottery/reset-all` mengembalikan semua peserta ke status `available` dan **menghapus seluruh batch/riwayat pemenang** — satu request, tanpa login.
2. **Membaca data peserta dan mengekspor PII (HIGH).** `GET /kelola-peserta` menampilkan 897 peserta dalam 45 halaman (nama, kategori, kelas, ID); `GET /riwayat/export-csv` mengunduh CSV 25 pemenang beserta NIS/NIP.
3. **Menambah peserta tanpa batas (MEDIUM).** `POST /kelola-peserta/import-quick` menerima tempelan teks dan memanggil `Participant::create()` per baris — tanpa batas jumlah, tanpa rate limit, tanpa login.
4. **Satu host, semua aplikasi (MEDIUM).** Aplikasi berbagi user hosting dengan PedagogiAI; backdoor `cache.php` di PedagogiAI dapat membaca `.env` spinner (24 variabel, SQLite).

Tidak ada endpoint unggah berkas pada aplikasi ini. Jalur tulis massal satu-satunya adalah import teks.

---

## F1 — CRITICAL: Tanpa Autentikasi + Reset Undian Destruktif

**Endpoint:** `POST /api/lottery/reset-all`
**Autentikasi:** tidak ada.

### Mekanisme

`routes/web.php` tidak memakai `->middleware('auth')` pada route mana pun. `LotteryController::resetAll()` langsung menjalankan:

```php
Participant::query()->update(['status' => 'available', 'draw_batch_id' => null, 'drawn_at' => null]);
DrawBatch::query()->delete();
```

Tidak ada konfirmasi, token khusus, atau otorisasi peran. Request biasa (dengan `_token` CSRF yang dapat diambil dari halaman mana pun karena halaman juga terbuka) menghapus riwayat undian secara permanen. Route status lain — `spin`, `mark-absent`, `respin-shortfall`, `commit-batch` — juga terbuka, sehingga hasil undian dapat dimanipulasi (menandai hadir/absen, menetapkan pemenang batch).

### Bukti (redacted)

```
POST /api/lottery/reset-all   (tanpa cookie login)
  -> Participant::update(status=available, draw_batch_id=null, drawn_at=null)
  -> DrawBatch::delete()
```

Tidak dieksekusi saat pengujian karena bersifat merusak. Bukti source: `app/Http/Controllers/LotteryController.php` baris 343–357.

Dampak: kehilangan permanen riwayat pemenang dan batch undian; undian dapat diulang/diubah oleh pihak luar kapan saja. Perbaikan: pasang autentikasi + otorisasi admin, pisahkan route publik dan route pengelola, tambahkan konfirmasi eksplisit untuk reset, dan audit log.

---

## F2 — HIGH: PII Peserta dan Pemenang Tanpa Autentikasi

**Endpoint:** `GET /kelola-peserta`, `GET /riwayat/export-csv`
**Autentikasi:** tidak ada.

### Mekanisme

`LotteryController::manage()` memaginasi seluruh tabel `participants` (20 baris/halaman). Halaman menampilkan nama lengkap, kategori, kelas, dan nomor identitas. `exportWinnersCsv()` mengalirkan CSV pemenang dengan kolom `Nama Lengkap`, `Kategori`, `No. Identitas/NIP/NIS`, status, dan waktu undi.

### Bukti (redacted)

```
GET /api/lottery/stats
{"total_participants":897,"total_winners":25,"total_batches":2,...}

GET /kelola-peserta  -> 45 halaman; 897 baris
Kolom: No | Nama Lengkap | Kategori | No. Identitas | Status
881 | [REDACTED] | Siswa Kelas 9 | 9 Cordoba (ID: [REDACTED]) | Siap Diundi

GET /riwayat/export-csv -> 200, text/csv, 25 baris
1,"Batch 1","[REDACTED]","Siswa Kelas 7","[REDACTED]","Pemenang Sah (Hadir)","<ts>"
```

Aplikasi mengklaim data "dummy realistis", tetapi entri yang terlihat mencakup nama siswa dan kelas yang konsisten dengan struktur sekolah, serta nomor identitas berformat NIS. Karena subjeknya sebagian besar anak, paparan ini tetap dinilai HIGH sampai status data dibuktikan sebaliknya.

Perbaikan: autentikasi untuk kedua endpoint, otorisasi per peran, dan redaksi nomor identitas pada tampilan/ekspor.

---

## F3 — MEDIUM: Import Peserta Tanpa Batas (Integritas & Ketersediaan)

**Endpoint:** `POST /kelola-peserta/import-quick`
**Autentikasi:** tidak ada (hanya CSRF token).

### Mekanisme

`importQuick()` memvalidasi `category` dan `names_text`, memecah input per baris, lalu `Participant::create()` untuk setiap baris tanpa batas jumlah, deduplikasi, atau rate limit. Sesi anonim dapat memperoleh `_token` dari `/kelola-peserta` yang juga terbuka.

### Bukti (redacted)

```
POST /kelola-peserta/import-quick  (sesi anonim, names_text kosong)
  -> 302 /kelola-peserta  (handler dieksekusi; validasi gagal)
POST tanpa _token -> 419  (CSRF aktif, bukan autentikasi)
```

Tidak ada baris uji yang dimasukkan saat pengujian agar tidak mencemari data produksi. Dampak: penambahan ribuan baris palsu (penggelembungan kuota/DB, daftar undian rusak) dan penyisipan nama penyerang ke dalam undian. Perbaikan: autentikasi, batas jumlah baris per request, rate limit, dan deduplikasi.

---

## F4 — MEDIUM: Berbagi User Hosting — Satu Aplikasi, Semua Aplikasi

**Subjek:** `spinner` dan `pedagogiai` berjalan pada user hosting yang sama (`u5768******`).

### Mekanisme

Backdoor `cache.php` di PedagogiAI (lihat Report-3 F6) dapat membaca berkas di luar document root miliknya. Berkas `.env` spinner terbaca dari jalur `domains/spinner.smpm12gkb.sch.id/public_html/.env` (24 variabel; `APP_ENV=production`, `DB_CONNECTION=sqlite`, `APP_DEBUG=false`).

### Bukti (redacted)

```
--read /home/u5*******/domains/spinner.smpm12gkb.sch.id/public_html/.env
keys: 24
APP_ENV=production
APP_DEBUG=false
DB_CONNECTION=sqlite
```

Dampak: kompromi satu aplikasi otomatis membuka aplikasi lain pada akun yang sama (kredensial, basis data SQLite, kode sumber). Perbaikan: pisahkan user/shell per aplikasi (atau container), rotasi kredensial, dan hapus backdoor.

---

## F5 — INFO: Klaim "Import Excel/SQL" Tidak Punya Endpoint

`manage.blade.php` (baris 161–162) menampilkan catatan bahwa berkas Excel/SQL "dapat langsung di-import atau dieksekusi ke database ini". Teks itu **tidak didukung kode**:

- `routes/web.php` hanya memiliki `POST /kelola-peserta/import-quick` — teks biasa, satu nama per baris. `routes/api.php` tidak ada, dan tidak ada endpoint `.sql`/`.xlsx`/adminer (semua 404).
- `LotteryController` tidak memakai `DB::raw`, `whereRaw`, `statement`, atau query mentah; seluruh akses data lewat Eloquent (ter-parameterisasi) dan `DB::transaction`.
- View memakai `{{ }}` dan JS memakai `escapeHtml()`; nama berisi `<script>` akan tampil sebagai teks, bukan HTML.
- `database/database.sqlite` ada di disk tetapi tidak dapat diakses lewat HTTP (404).

Kesimpulan: **deface via SQL tidak mungkin dari aplikasi ini** karena tidak ada sink SQL yang dapat dikendalikan. Yang nyata adalah deface lewat penulisan berkas di filesystem — dan itu berasal dari backdoor lintas-aplikasi (F4), bukan dari fitur SQL. Uji benign: satu berkas HTML penanda ditulis ke `public/`, diakses (200, `text/html`), lalu dihapus (`DEL-OK`; akses ulang 404).

---

## Catatan Uji

- **Tidak ada endpoint unggah berkas di spinner.** Permukaan tulis hanya import teks; tidak ditemukan jalur upload/eksekusi seperti pada PedagogiAI.
- **CSRF aktif** untuk POST (`_token` wajib, 419 tanpa token) — tetapi CSRF bukan autentikasi; token tersedia di halaman publik.
- **Tidak ada halaman login** (`/login` → 404) dan tidak ada middleware auth pada route mana pun.
- **Data berlabel "dummy realistis".** Pengujian tidak mengubah data; hanya GET dan satu POST kosong (validasi) yang dijalankan.
- **`.env`, `.git`, `artisan`, `.htaccess`** ditolak 403 oleh aturan server; `/public/index.php` merespons 200.
- Tidak ada artefak yang ditinggalkan pada target.

---

## Indeks Bukti

| Berkas | Isi |
|---|---|
| [`evidence/report4-spinner-unauth.txt`](evidence/report4-spinner-unauth.txt) | Route tanpa auth, stats 897 peserta, CSV pemenang, handler import/reset, lintas-aplikasi `.env` |
| `poc/poc_spinner_unauth.py` | PoC: stats, manage, wheel, export CSV, import, reset |

---

## Rekomendasi

1. **F1.** Pasang autentikasi + otorisasi admin pada seluruh route `api/lottery/*`, `/kelola-peserta`, dan `/riwayat`; pisahkan route publik (papan undian) dari route pengelola; wajibkan konfirmasi eksplisit + audit log untuk `reset-all`.
2. **F2.** Batasi akses data peserta/pemenang ke peran berwenang; redaksi nomor identitas pada tampilan dan ekspor; terapkan rate limit pada ekspor.
3. **F3.** Autentikasi import, batasi jumlah baris per request, deduplikasi nama, dan rate limit.
4. **F4.** Pisahkan user hosting per aplikasi, rotasi kredensial, dan hapus backdoor `cache.php`/`Dashboard.php` (Report-3 F6).
