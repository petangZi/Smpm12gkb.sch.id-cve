# smpm12gkb.sch.id — Security Research

Penetration test findings untuk **https://smpm12gkb.sch.id/** (SMP Muhammadiyah 12 GKB Gresik).

## Laporan

- **[REPORT-1](./REPORT-1.md)** — E-Complaint (custom PHP): Broken Access Control pada API admin (CRITICAL), Stored XSS (HIGH), Unrestricted file upload `.php` (HIGH), PII disclosure (MEDIUM), WP user enum + XML-RPC (MEDIUM). *13 Oktober 2026.*

- **[REPORT-2](./REPORT-2.md)** — *"truncated AI slop"*: Unrestricted file upload → RCE tanpa autentikasi pada E-Complaint (CRITICAL), kebocoran hardcoded `BRIDGE_SECRET_KEY` pada `bridge.php` (CRITICAL). *16 Oktober 2026.*

- **[REPORT-3](./REPORT-3.md)** — *"PedagogiAI is slop"*: Verifikasi kwitansi tanpa autentikasi / IDOR enumerasi (HIGH), webhook pembayaran tanpa auth menulis DB sebelum validasi + bocor skema (MEDIUM), mode debug aktif (MEDIUM), info disclosure + CSP lemah (LOW). Sandbox `/api/execute-code` dicatat informatif (by-design). *16 Oktober 2026.*

## Struktur

```
.
├── REPORT-1.md                  # laporan utama
├── evidence/                    # bukti HTTP mentah per temuan (PII redacted)
│   ├── poc-admin-api.txt
│   ├── poc-admin-get-all.redacted.json
│   ├── poc-admin-page.txt
│   ├── poc-stored-xss.txt
│   ├── poc-upload.txt
│   ├── poc-pathdisclosure.txt
│   ├── poc-wp-enum.txt
│   ├── poc-misc.txt
│   └── report2/                 # bukti recon Report 2 (lihat report2/README.md)
└── poc/
    └── poc-ecomplaint.sh        # script PoC runnable
```

## Metode

Black-box, unauthenticated, non-destruktif. Seluruh tiket uji yang dibuat selama pembuktian sudah dihapus. PII pihak ketiga di-redact di seluruh repository.
