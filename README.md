# smpm12gkb.sch.id — Security Research

Penetration test findings untuk **https://smpm12gkb.sch.id/** (SMP Muhammadiyah 12 GKB Gresik).

## Laporan

- **[REPORT-1](./REPORT-1.md)** — E-Complaint (custom PHP): Broken Access Control pada API admin (CRITICAL), Stored XSS (HIGH), Unrestricted file upload `.php` (HIGH), PII disclosure (MEDIUM), WP user enum + XML-RPC (MEDIUM). *13 Oktober 2026.*

- **[REPORT-2](./REPORT-2.md)** — *"truncated AI slop"*: Unrestricted file upload → RCE tanpa autentikasi pada E-Complaint (CRITICAL), kebocoran hardcoded `BRIDGE_SECRET_KEY` pada `bridge.php` (CRITICAL). *16 Oktober 2026.*

- **[REPORT-3](./REPORT-3.md)** — *"Pembiasaan yang Harus Dibiasakan"*: SISWA MGKB (`https://pcmgkb.my.id/siswamugeb/`) — dokumen pribadi siswa (KTP/ijazah/foto/NISN, **186 berkas**) dapat diunduh tanpa autentikasi (HIGH), directory listing aktif (MEDIUM), path disclosure via `include/*.php` (MEDIUM), header keamanan absen (LOW). *17 Oktober 2026.*

- **[REPORT-3 (PedagogiAI)](./REPORT-3-pedagogiai.md)** — *"PedagogiAI is slop"*: Verifikasi kwitansi tanpa autentikasi / IDOR enumerasi (HIGH), webhook pembayaran tanpa auth menulis DB sebelum validasi + bocor skema (MEDIUM), mode debug aktif (MEDIUM), info disclosure + CSP lemah (LOW). Sandbox `/api/execute-code` dicatat informatif (by-design). *16 Oktober 2026.*

- **[RECON — Attack Surface](./RECON-attack-surface.md)** — pemetaan subdomain + path: 28 aplikasi internal di `pcmgkb.my.id/app/`, semua dengan autoindex `include/`+`images/`+`styles/` dan `login.php`; subdomain `frontaccounting` (FrontAccounting 2.4.14), `cpanel`/`webmail`/`webdisk`, `synology`, `virtualclass` (Moodle), `kartuujian`, `ppdb`, `pedagogiai`, dll. *17 Oktober 2026.*

## Struktur

```
.
├── REPORT-1.md                  # laporan utama
├── REPORT-2.md
├── REPORT-3.md                  # SISWA MGKB (pcmgkb.my.id/siswamugeb)
├── REPORT-3-pedagogiai.md       # PedagogiAI (laporan ke-3 sebelumnya)
├── RECON-attack-surface.md      # pemetaan subdomain + path
├── evidence/                    # bukti HTTP mentah per temuan (PII redacted)
│   ├── poc-admin-api.txt
│   ├── poc-admin-get-all.redacted.json
│   ├── poc-admin-page.txt
│   ├── poc-stored-xss.txt
│   ├── poc-upload.txt
│   ├── poc-pathdisclosure.txt
│   ├── poc-wp-enum.txt
│   ├── poc-misc.txt
│   ├── report2/                 # bukti recon Report 2 (lihat report2/README.md)
│   ├── report3/                 # bukti Report 3 (PedagogiAI)
│   ├── recon/                   # subdomains.txt, paths-apps.txt
│   └── siswamugeb/              # bukti Report 3 (Pembiasaan / SISWA MGKB)
└── poc/
    ├── poc-ecomplaint.sh
    └── poc_siswamugeb_exposure.py   # PoC runnable Report 3 (Pembiasaan)
```

## Metode

Black-box, unauthenticated, non-destruktif. Seluruh tiket uji yang dibuat selama pembuktian sudah dihapus. PII pihak ketiga di-redact di seluruh repository.
