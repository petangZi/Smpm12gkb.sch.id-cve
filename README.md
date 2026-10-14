# Smpm12gkb.sch.id — Security Assessment

Kumpulan laporan keamanan (non-destruktif) untuk `https://smpm12gkb.sch.id/`.

| Report | Fokus | Severity tertinggi | Tanggal |
|--------|-------|--------------------|---------|
| [REPORT-1](REPORT-1.md) | WordPress stack + aplikasi custom E-Complaint | KRITIS (CVSS 9.8) | 13 Okt 2026 |

## Ringkas REPORT-1

- WordPress 7.1.3 + seluruh plugin **ter-patch penuh** (tidak ada CVE exploitable).
- Temuan kritis ada di aplikasi custom `/app/page/E-Complaint/`:
  - **F1** Admin API tanpa autentikasi (dump/hapus/ubah seluruh tiket) — KRITIS
  - **F2** Stored XSS dieksekusi di panel admin — TINGGI
  - **F3** Unrestricted file upload (`.php` dipertahankan) — TINGGI
  - **F4** Kebocoran PII via pencarian tanpa verifikasi — SEDANG
  - **F5** Permukaan brute-force WordPress — SEDANG
  - **F6** Path disclosure — RENDAH
  - **F7** wp-cron / dalas stats / AISA sanitasi lemah — RENDAH

PoC lengkap: direktori [`poc/`](poc/).
