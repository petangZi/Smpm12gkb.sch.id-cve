# Report-3 — "Pembiasaan yang Harus Dibiasakan"

**Target:** `https://pcmgkb.my.id/siswamugeb/` (login: `https://pcmgkb.my.id/siswamugeb/login.php`)
**Subjek:** SISWA MGKB — aplikasi kesiswaan/pembiasaan (PHPRunner, PHP, LiteSpeed, Hostinger)
**Tema:** *"Pembiasaan yang harus dibiasakan"* — aplikasi yang mencatat pembiasaan harian siswa, tetapi belum membiasakan higiene keamanan paling dasar: direktori tidak ditutup, dokumen pribadi siswa tidak dijaga, dan jejak path server dibiarkan terbuka.
**Tanggal:** 17 Oktober 2026
**Klasifikasi:** HIGH

> Catatan metode: pengujian black-box, tanpa autentikasi, non-destruktif. Tidak ada berkas yang diubah/dihapus. Isi dokumen pribadi **tidak** diunduh ke repositori; hanya metadata (status HTTP, tipe, ukuran) yang dicatat, dan nama berkas diredact.

---

## Ringkasan Eksekutif

Aplikasi `SISWA MGKB` menyimpan berkas yang secara alami bersifat pribadi: KTP/KIA siswa, ijazah, kartu NISN, dan foto siswa. Empat hal dasar yang seharusnya menjadi "pembiasaan" dalam mengelola aplikasi sekolah justru belum dilakukan:

| Kode | Tingkat | Temuan |
|------|---------|--------|
| F1 | **HIGH** | Dokumen pribadi siswa (KTP/ijazah/foto/NISN) dapat dienumerasi & diunduh tanpa login — **186 berkas**. |
| F2 | **MEDIUM** | Directory listing (autoindex) aktif pada `include/`, `files/`, `images/`, `styles/` dan subdirektori unggahan. |
| F3 | **MEDIUM** | `include/*.php` dapat diakses langsung → fatal error PHP + **path absolut server** terungkap. |
| F4 | **LOW** | Header keamanan dasar absen (tanpa `X-Frame-Options`, CSP, HSTS, `X-Content-Type-Options`). |

Tema yang menyatukan: **kontrol yang seharusnya otomatis, justru harus dibiasakan.** Server web sudah punya satu saklar untuk mematikan directory listing dan satu baris untuk menutup folder unggahan dari akses langsung. Keduanya belum dinyalakan. Akibatnya dokumen identitas anak-anak sekolah terbuka bagi siapa pun di internet yang menebak satu URL.

---

## F1 — HIGH: Dokumen Pribadi Siswa Terbuka Tanpa Autentikasi

**Endpoint:** `GET https://pcmgkb.my.id/siswamugeb/files/files_ktp/` (dan `files_ijazah/`, `files_fotosiswa/`)
**Autentikasi:** **tidak ada**.

Tiga folder unggahan siswa dapat didaftar dan **seluruh berkasnya diunduh** tanpa cookie/login:

| Direktori | Jumlah berkas | Isi |
|-----------|---------------|-----|
| `files/files_ktp/` | 8 | KTP/KIA siswa, kartu NISN (PDF) |
| `files/files_ijazah/` | 4 | Ijazah (gambar + PDF) |
| `files/files_fotosiswa/` | 174 | Foto siswa, nama lengkap pada nama berkas |
| **Total** | **186** | |

Sampel status (semua `HTTP 200`, terkirim penuh tanpa autentikasi):

```
[200] files/files_ktp/KIA …      image/jpeg       793994 bytes
[200] files/files_ktp/ZF-kartu NISN ….pdf   application/pdf  85790 bytes
[200] files/files_ijazah/ZF-ijazah ….pdf    application/pdf  194481 bytes
[200] files/files_fotosiswa/<Nama Siswa>.JPG  image/jpeg  3489496 bytes
```

**Dampak.** Kebocoran data pribadi (PII) anak di bawah umur: nomor induk, foto wajah, dan dokumen identitas yang lazim dipakai untuk penipuan/pemalsuan identitas. Setiap nama berkas siswa terekspos sekaligus dalam listing.

**Bukti.** `evidence/siswamugeb/poc-pii.txt`, `evidence/siswamugeb/poc-dirlist.txt`.

**Reproduksi.**
```bash
# tanpa cookie apa pun
curl -s https://pcmgkb.my.id/siswamugeb/files/files_ktp/ | grep -oE 'href="[^"]+\.(jpg|pdf)"'
curl -sO https://pcmgkb.my.id/siswamugeb/files/files_ktp/<nama-berkas>
# atau otomatis:
python3 poc/poc_siswamugeb_exposure.py
```

**Perbaikan.**
1. Pindahkan folder `files/` ke luar web root, atau sajikan lewat skrip ber-otorisasi.
2. Blokir akses langsung ke `files/**` (aturan server: `Require all denied` + handler PHP pengunduh).
3. Matikan autoindex (lihat F2).
4. Jika berkas memang publik, acak nama (tanpa nama siswa) — tetapi KTP/ijazah tetap **tidak boleh** publik.

---

## F2 — MEDIUM: Directory Listing (Autoindex) Aktif

**Endpoint:** `GET https://pcmgkb.my.id/siswamugeb/<dir>/`
**Autentikasi:** tidak ada.

Server mengembalikan halaman "Index of …" untuk banyak direktori:

```
GET /siswamugeb/include/               -> 200  title=Index of /siswamugeb/include/  entri=463
GET /siswamugeb/images/                -> 200  title=Index of /siswamugeb/images/   entri=79
GET /siswamugeb/styles/                -> 200  title=Index of /siswamugeb/styles/   entri=13
GET /siswamugeb/files/                 -> 200  title=Index of /siswamugeb/files/    entri=6
GET /siswamugeb/files/files_fotosiswa/ -> 200  title=Index of /siswamugeb/files/files_fotosiswa/  entri=177
```

`include/` membocorkan **463 entri** termasuk 414 berkas `.php`, mengungkap struktur internal aplikasi — antara lain keluarga modul `belum_input_pembiasaan_*` (modul pembiasaan), `blm_input_pembiasaan_smp1..12`, `cv_blm_inpt_pemb_*`, `ciphereraes.php`, `appsettings.php`. Ini menjadi peta bagi penyerang.

**Dampak.** Penyerang memetakan struktur aplikasi & menemukan berkas PII (F1) tanpa perlu menebak URL.

**Bukti.** `evidence/siswamugeb/poc-dirlist.txt`.

**Perbaikan.** Matikan autoindex (Apache/LiteSpeed: `Options -Indexes`; nginx: `autoindex off;`). Tambahkan `index.php`/`index.html` kosong sebagai penutup di tiap direktori.

---

## F3 — MEDIUM: `include/*.php` Diakses Langsung → Path Absolut + Fatal Error

**Endpoint:** `GET https://pcmgkb.my.id/siswamugeb/include/appsettings.php`
**Autentikasi:** tidak ada.

Berkas include dieksekusi langsung dan menampilkan error PHP mentah:

```
<b>Fatal error</b>: Uncaught Error: Call to undefined function getabspath() in
/home2/pcmg***/public_html/siswamugeb/include/appsettings.php:45
```

**Dampak.** `display_errors=On` di produksi + berkas include yang dapat diakses langsung → **kebocoran path absolut server** (akun hosting & struktur direktori). Ini informasi yang dipakai untuk memindahkan serangan ranged (LFI/RFI/upload) menjadi akses berkas nyata. Bukti kedua: `belum_input_pembiasaan_settings.php:2`, `commonfunctions.php:3`.

**Bukti.** `evidence/siswamugeb/poc-pathdisclosure.txt`.

**Perbaikan.**
1. Set `display_errors=Off` dan `log_errors=On` di produksi.
2. Lupakan akses langsung ke `include/*`: pindahkan di luar web root atau tolak lewat aturan server.
3. Aktifkan proteksi berkas sensitif (`.env`, `error_log`, `.git`) — saat ini balasan `403` menandakan berkas-berkas itu memang ada di server.

---

## F4 — LOW: Header Keamanan Absen

**Endpoint:** `GET https://pcmgkb.my.id/siswamugeb/login.php`

```
MISS x-frame-options       MISS content-security-policy
MISS strict-transport-security   MISS x-content-type-options
MISS referrer-policy       MISS permissions-policy
```

**Dampak.** Tidak ada pertahanan clickjacking (`X-Frame-Options`), tidak ada kunci HSTS, tidak ada CSP. Halaman login dapat dibingkai (clickjacking) dan endpoint rentan tebak-tipe.

**Bukti.** `evidence/siswamugeb/poc-headers.txt`.

**Perbaikan.** Kirim header: `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, `Strict-Transport-Security: max-age=31536000; includeSubDomains`, dan CSP minimum.

---

## Catatan Uji (negatif, dicatat jujur)

Agar laporan tidak melebih-lebihkan: **login tidak dapat dibypass.**

- Kredensial default (`admin/admin`, dll.) → `Invalid Login`.
- SQL injection pada `username` (`' OR '1'='1'-- -`, `admin'-- -`, time-based `SLEEP`) → `Invalid Login`, tanpa delay.

Kesimpulan: temuan Report-3 ini berdiri pada **exposure tanpa autentikasi**, bukan pada bypass autentikasi. Bukti: `evidence/siswamugeb/poc-login-negative.txt`.

---

## Struktur Aplikasi (konteks)

- Halaman login `login.php` (PHPRunner, form `username`/`password`/`btnSubmit`).
- Modul utama terdeteksi dari `include/`: `belum_input_pembiasaan_*` → **modul pembiasaan siswa** (inti tema aplikasi), serta modul `admin_*`, `userinfo`, `changepwd`.
- Endpoint modul memerlukan sesi (balasan `302` ke `login.php` saat diakses anonim) — jadi exposure justru terjadi pada **berkas statis & folder**, bukan pada logika halaman.

---

## Metode & Reproduksi

1. Recon pasif (header, `robots.txt`, struktur direktori).
2. Deteksi autoindex & enumerasi berkas (`files/`, `include/`).
3. Verifikasi unduhan PII tanpa cookie (`HEAD`/`GET` — hanya metadata).
4. Uji path disclosure via akses `include/*.php`.
5. Uji autentikasi (default + SQLi) — negatif, dicatat.

Semua langkah otomatis lewat:
```bash
python3 poc/poc_siswamugeb_exposure.py --out evidence/siswamugeb/poc-exposure.txt
```

**Bukti:** `evidence/siswamugeb/` — `poc-exposure.txt`, `poc-dirlist.txt`, `poc-pii.txt`, `poc-pathdisclosure.txt`, `poc-headers.txt`, `poc-login-negative.txt`.
