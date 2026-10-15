# smpm12gkb.sch.id — Security Research

Penetration test findings untuk **https://smpm12gkb.sch.id/** (SMP Muhammadiyah 12 GKB Gresik).

## Laporan

- **[REPORT-1](./REPORT-1.md)** — E-Complaint (custom PHP): Broken Access Control pada API admin (CRITICAL), Stored XSS (HIGH), Unrestricted file upload `.php` (HIGH), PII disclosure (MEDIUM), WP user enum + XML-RPC (MEDIUM). *13 Oktober 2026.*

**[REPORT-2](./evidence/report2/) (recon)** — inventaris subdomain/endpoint + bukti. Laporan penuh menyusul.

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
