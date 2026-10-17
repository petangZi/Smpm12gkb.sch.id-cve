# RECON — Attack Surface · Ekosistem SMP Muhammadiyah 12 GKB
# pcmgkb.my.id · smpm12gkb.sch.id

Tanggal : 17 Oktober 2026
Metode  : Certificate Transparency (crt.sh), DoH enumeration (dns.google), HTTP probing, directory discovery
Sifat   : Recon / pemetaan permukaan serangan (tanpa autentikasi)

---

## 1. Subdomain (live, punya A record)

### pcmgkb.my.id
| Host | IP | Status | Keterangan |
|---|---|---|---|
| pcmgkb.my.id / www | 103.112.245.9 | 302 | placeholder → `mercusuar.uzone.id` |
| cpanel.pcmgkb.my.id | 103.112.245.9 | 200 | **cPanel Login** |
| webmail.pcmgkb.my.id | 103.112.245.9 | 200 | **Webmail Login** |
| frontaccounting.pcmgkb.my.id | 103.112.245.9 | 200 | **FrontAccounting 2.4.14 — Index of / + login** |
| webdisk.pcmgkb.my.id | 103.112.245.9 | 401 | cPanel WebDisk |
| cpcalendars.pcmgkb.my.id | 103.112.245.9 | 401 | cPanel Calendar |
| cpcontacts.pcmgkb.my.id | 103.112.245.9 | 401 | cPanel Contacts |
| mail / autoconfig / autodiscover | 103.112.245.9 | 200/400 | layanan mail |
| car.pcmgkb.my.id | — | CT only | tidak ada A record |
| sdm2gkb.pcmgkb.my.id | — | CT only | tidak ada A record |

### smpm12gkb.sch.id
| Host | Status | Keterangan |
|---|---|---|
| smpm12gkb.sch.id / www | 200 | Situs utama (Spemdalas) |
| ppdb.smpm12gkb.sch.id | 200 | PPDB (SPMB) |
| pedagogiai.smpm12gkb.sch.id | 200 | PedaGogiAI (Laravel) — lihat REPORT-3-pedagogiai |
| virtualclass.smpm12gkb.sch.id | 303 | **Moodle** (virtual class) |
| kartuujian.smpm12gkb.sch.id | 200 | Cek Ruang Ujian STS 2026/2027 |
| pengumumankelas2627.smpm12gkb.sch.id | 200 | Pengumuman Kelas Siswa TA 2026/2027 |
| undangan.smpm12gkb.sch.id | 200 | Undangan Final Moment Spemdalas 23 |
| konsumsi.smpm12gkb.sch.id | 302 | Order Konsumsi Spemdalas |
| mbg.smpm12gkb.sch.id | 302 | Dashboard |
| spemdalas / spemdalasnew / spemdalas.new | 200 | Spemdalas |
| synology.smpm12gkb.sch.id | 200 | **Access via Synology** (NAS) |
| tamanilmu.smpm12gkb.sch.id | 200 | Taman Ilmu Spemdalas |
| tictactoe.smpm12gkb.sch.id | 200 | Tic Tac Toe (demo) |
| perpus.smpm12gkb.sch.id | — | tidak resolve saat tes |

Host pada CT log (belum ada A record / perlu verifikasi): `keuangan`, `katalog`, `indenpublikasi`, `indenmobil`, `ordermobil`, `paket`, `pemanggilan`, `finalmoment`, `finalmomentxxii`, `dtcp`, `wisuda`, `undanganwisuda`, `kelulusan`, `moodle`, `ipv6`, `s`, `azam-lomba-acer`, `konsumsi`.

---

## 2. Path pada `pcmgkb.my.id`

| Path | Status | Keterangan |
|---|---|---|
| `/app/` | 200 | **MENU MGKB-APPS** — membocorkan daftar 28 aplikasi internal |
| `/dashboardmgkb/` | 200 → login.php | app dashboard (PHPRunner) |
| `/siswamugeb/` | 200 | app siswa — PII (REPORT-3) |
| `/cpanel`, `/webmail` | 200 | redirect cPanel |
| `/.git/config` | 403 | ada (diblokir) |

### 28 aplikasi internal (dari `/app/`)
`aset, clean, infaq, ost, pengajian, perangkat, siswamugeb, supervisi, uks, agenda, bk, dhuha, feedback_pelatihan, ismuba, kerja, kontrol, lab, mugebcar, ngaji, perpus, ppdbmugeb, presensi, prestasi, rapat, ruang, sdm, security, dashboardmgkb`

**Setiap app** mengekspos (tanpa autentikasi):
- `/include/` → **directory listing ON** (78–693 entri; membocorkan nama file sumber: `dbcommon.php`, `cv_m_*_events.php`, dll.)
- `/images/`, `/styles/` → directory listing ON
- `/login.php` → halaman login (PHPRunner)
- 10 app punya `/files/`: `clean, ost, pengajian, perangkat, siswamugeb, supervisi, bk, ismuba, ppdbmugeb, sdm`
- `/ngaji/koneksi.php` → 200 (file koneksi DB, body kosong saat include langsung)

---

## 3. Ringkasan temuan recon

| # | Temuan | Sev |
|---|---|---|
| R1 | Menu `/app/` membocorkan 28 aplikasi internal (nama + path) | LOW |
| R2 | Autoindex `/include/` `/images/` `/styles/` pada 28 app → nama file sumber, struktur PHPRunner | MEDIUM |
| R3 | `frontaccounting.pcmgkb.my.id` — FrontAccounting 2.4.14 (versi lama, 2020) + Index of / | MEDIUM |
| R4 | cPanel/Webmail/WebDisk/WHM terekspos pada path & subdomain standar | LOW |
| R5 | `synology.smpm12gkb.sch.id` — NAS Synology terekspos ke internet | LOW |
| R6 | `/ngaji/koneksi.php` dapat diakses langsung (200) | LOW |
| R7 | Arsitektur seragam PHPRunner → satu pola bug berlaku di banyak app | INFO |

---

## 4. Catatan
- Semua data di atas berasal dari CT log publik + HTTP anonim; tanpa kredensial.
- Subdomain yang sudah dilaporkan PII-nya: `siswamugeb` (REPORT-3), `pedagogiai` (REPORT-3-pedagogiai).
- Prioritas tindak lanjut: FrontAccounting (versi lama), relevansi `synology`, dan app dengan `/files/` selain siswamugeb.
