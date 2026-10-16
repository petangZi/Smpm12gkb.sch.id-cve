# Report-3 — "PedagogiAI is slop"

**Target:** `https://www.pedagogiai.smpm12gkb.sch.id/`
**Subjek:** PedaGogiAI — platform pembelajaran & coding (Laravel, PHP 8.3.35, Hostinger/hcdn)
**Tema:** *"PedaGogiAI is slop"* — keamanan yang tampak ada tetapi kosong: filter blacklist per-bahasa, endpoint eksekusi kode tanpa autentikasi, dan IDOR kwitansi.
**Tanggal:** 16 Oktober 2026
**Klasifikasi:** CRITICAL (kombinasi)

---

## Ringkasan Eksekutif

PedaGogiAI adalah platform Laravel yang mempromosikan "Demo & Clean Architecture". Di baliknya, tiga kontrol keamanan dasar absen sekaligus:

1. **Eksekusi kode jarak jauh tanpa autentikasi (CRITICAL).** Endpoint publik `POST /api/execute-code` menjalankan kode pengguna di worker Judge0 1.14.0 (`zag-srv02-ce-execution-worker`). "Perlindungan" yang ada hanyalah **blacklist fungsi shell per-bahasa**: untuk PHP, fungsi eksekusi shell diblokir; tetapi **Python, JavaScript, dan Bash** mengeksekusi perintah OS bebas. Hasilnya: shell penuh tanpa login.
2. **IDOR kwitansi pembayaran tanpa autentikasi (HIGH).** `GET /verifikasi-kwitansi/<id>` menerima id integer dan mengembalikan kwitansi pembayaran asli berisi PII siswa: nama, NIS/kelas, nomor jurnal pembukuan, nomor virtual account, dan nominal. Id dapat di-enumerate.
3. **Mode debug aktif (MEDIUM).** `APP_DEBUG=true` membocorkan stack trace lengkap dan path internal server pada setiap error.

Pola yang menghubungkan ketiganya adalah pola yang sama: kontrol keamanan yang **terlihat** ada (filter "Keamanan: Fungsi eksekusi shell dinonaktifkan", halaman verifikasi kwitansi, error handler) tetapi **tidak menyelesaikan masalah pada level yang benar**. Filter keyword per-bahasa bukan sandbox. Verifikasi kwitansi tanpa otorisasi bukan verifikasi. Debug aktif bukan konfigurasi produksi.

---

## F1 — CRITICAL: Eksekusi Kode Jarak Jauh Tanpa Autentikasi

**Endpoint:** `POST https://www.pedagogiai.smpm12gkb.sch.id/api/execute-code`
**Autentikasi:** tidak ada (publik).

### Mekanisme

Endpoint menerima JSON `{ "language": "...", "code": "..." }` dan meneruskan kode ke worker Judge0. Uji kontrol:

| Bahasa | Perintah | Hasil |
|---|---|---|
| PHP | `shell_exec(...)` | DIBLOKIR — pesan: *"Keamanan: Fungsi eksekusi shell dinonaktifkan di sandbox."* |
| Bash | `id; uname -a` | **BERJALAN** |
| Python | `import os; os.popen("id").read()` | **BERJALAN** |
| JavaScript | `require("child_process").execSync("id")` | **BERJALAN** |

Pembuat platform menerapkan filter hanya pada fungsi shell PHP (`shell_exec`, `system`, `exec`, dan sejenisnya). Bahasa lain **tidak difilter sama sekali**. Ini klasik blacklist hasil pembuatan cepat: menutup satu pintu, meninggalkan tiga pintu lain terbuka.

### Bukti eksekusi (redacted)

Perintah `id; hostname; uname -a; cat /etc/passwd; env | grep JUDGE0` mengembalikan:

- `uid=1427**** gid=1427****` (uid ephemeral per-request)
- `zag-srv02-ce-execution-worker`
- kernel host `6.8.0-146-generic`
- isi `/etc/passwd` lengkap (`root:x:0:0:root:/root:/bin/bash`, dst.)
- environment worker: `JUDGE0_VERSION=1.14.0`, `PWD=/box`, `HOME=/tmp`

Lihat [`evidence/report3/rce-execute-code.txt`](evidence/report3/rce-execute-code.txt).

### PoC

```bash
python3 poc_rce_execute_code.py --cmd 'id'
python3 poc_rce_execute_code.py --read /etc/passwd
python3 poc_rce_execute_code.py --lang python --code 'import os;print(os.popen("id").read())'
```

### Dampak

- Eksekusi perintah OS oleh penyerang anonim.
- Pembacaan berkas di dalam worker.
- Konsumsi sumber daya bebas (komputasi, kripto-mining) atas biaya sekolah.
- Titik pijak bila isolasi container ditemukan lemah (lihat F4).

---

## F2 — HIGH: IDOR / Enumerasi Kwitansi Pembayaran Tanpa Autentikasi

**Endpoint:** `GET https://www.pedagogiai.smpm12gkb.sch.id/verifikasi-kwitansi/<id>`
**Autentikasi:** tidak ada.

### Mekanisme

Parameter `<id>` adalah integer berurutan tanpa pemeriksaan kepemilikan maupun sesi. Setiap id yang valid mengembalikan kwitansi asli. Endpoint juga mengembalikan sebuah kwitansi contoh (`#INV-000009`) untuk id di luar jangkauan, tetapi id yang valid membocorkan data nyata.

### Bukti (redacted)

| id | Invoice | Nama | VA | Nominal |
|---|---|---|---|---|
| 2 | #INV-000002 | REDACTED_002 | \<REDACTED\> | Rp 950.000 |
| 4 | #INV-000004 | REDACTED_002 | \<REDACTED\> | Rp 950.000 |
| 7 | #INV-000007 | REDACTED_002 | \<REDACTED\> | Rp 27.200.000 |
| 1 | #INV-000009 | REDACTED_001 | \<REDACTED\> | Rp 23.700.000 |

Field yang bocor per kwitansi: **Nama Siswa, NIS/Kelas, No. Jurnal Pembukuan, Nomor Virtual Account, Total Nominal, Status Pembayaran, Waktu Transaksi**. Bukti lengkap (redacted): [`evidence/report3/idor-kwitansi.txt`](evidence/report3/idor-kwitansi.txt).

### PoC

```bash
python3 poc_idor_kwitansi.py --start 1 --end 200 --dump out.txt
```

### Dampak

Kebocoran data pribadi siswa (nama, NIS, kelas) dan data keuangan (virtual account, nominal, nomor jurnal). Virtual account + nominal memungkinkan penyerang menghubungkan siswa dengan tagihan spesifik — permukaan untuk penipuan bertarget. Tanpa autentikasi, dan id berurutan membuat enumerasi massal sepele.

---

## F3 — MEDIUM: Mode Debug Aktif (`APP_DEBUG=true`)

Setiap error mengembalikan JSON stack trace lengkap. Contoh: `GET /api/user` (route tidak ada) mengembalikan `NotFoundHttpException` beserta seluruh jejak framework, path internal server, dan struktur direktori:

```
/home/u5*******/domains/pedagogiai.smpm12gkb.sch.id/public_html/vendor/laravel/framework/src/Illuminate/Routing/AbstractRouteCollection.php
```

Lihat [`evidence/report3/debug-trace.txt`](evidence/report3/debug-trace.txt).

Dampak: pembocoran struktur direktori internal, versi framework, dan permukaan serangan tambahan. Pada lingkungan produksi, `APP_DEBUG` seharusnya `false`.

---

## F4 — MEDIUM: Pembocoran Informasi Worker Eksekusi

Dari F1, worker mengungkap:

- Kernel host: `Linux 6.8.0-146-generic` (Ubuntu 24.04).
- **Tabel mount host bocor** — berisi path `/var/lib/docker/overlay2/...` (ID layer container host). Ini mengonfirmasi worker berjalan di atas Docker host yang sama dan membocorkan struktur penyimpanan host.
- `/dev` container adalah `/dev` host (node device terlihat: `btrfs-control`, `cpu`, dst.).
- `Seccomp: 0` pada proses eksekusi — seccomp **tidak aktif**, sehingga syscall tidak terfilter.
- Kapabilitas proses: `CapEff: 0000000000000000` (kosong) — jadi eskalasi ke host tidak berhasil dalam uji ini, tetapi lemahnya isolasi (seccomp mati, `/dev` host, mount bocor) menjadikannya permukaan yang layak ditinjau.

Endpoint eksekusi juga membuka `/files/gson-2.11.0.jar` (read-only), menandakan konfigurasi worker yang tidak dikeraskan.

---

## Catatan Uji

- Autentikasi: kredensial yang diberikan (`RVLDYEX` / `R2SPYYK`) **tidak berhasil** untuk form `/login` (form meminta `email` atau NRS 14-digit; `RVLDYEX` bukan keduanya). Area terautentikasi (`/profile`, `/tickets`, `/admin`, `/api/notifications`) tetap tertutup. Seluruh temuan di atas **tidak membutuhkan autentikasi**.
- Tidak ada egress jaringan dari worker (`Network is unreachable`) dan tidak ada pivot ke jaringan internal Docker — jadi RCE terkurung di worker, bukan di host aplikasi.
- Tidak ada persistence: proses latar (`sleep`) mati antar-request.

---

## Rekomendasi

1. **F1.** Hapus endpoint eksekusi publik atau wajibkan autentikasi + otorisasi. Ganti blacklist keyword dengan isolasi nyata (Judge0 `isolate` dengan seccomp aktif, tanpa `/dev` host). Jangan pernah memercayai daftar hitam fungsi per-bahasa.
2. **F2.** Tambahkan otorisasi kepemilikan pada `/verifikasi-kwitansi`. Gunakan token acak non-enumerable (UUID/HMAC) sebagai pengganti id integer. Jangan ever return kwitansi contoh berisi data asli.
3. **F3.** Set `APP_DEBUG=false` di produksi.
4. **F4.** Keraskan worker: aktifkan seccomp, jangan bind `/dev` host, batasi akses `CapBnd`, dan sembunyikan tabel mount.

---

## Indeks Bukti

| Berkas | Isi |
|---|---|
| [`evidence/report3/rce-execute-code.txt`](evidence/report3/rce-execute-code.txt) | Bukti RCE tanpa auth (redacted) |
| [`evidence/report3/idor-kwitansi.txt`](evidence/report3/idor-kwitansi.txt) | Enumerasi kwitansi + PII (redacted) |
| [`evidence/report3/debug-trace.txt`](evidence/report3/debug-trace.txt) | Stack trace `APP_DEBUG=true` |
| `poc/poc_rce_execute_code.py` | PoC RCE |
| `poc/poc_idor_kwitansi.py` | PoC IDOR kwitansi |
