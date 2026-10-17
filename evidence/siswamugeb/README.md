# Evidence — Report 3 (Pembiasaan) · SISWA MGKB

Target: `https://pcmgkb.my.id/siswamugeb/`

| Berkas | Temuan | Isi |
|--------|--------|-----|
| `poc-exposure.txt` | F1–F4 | ringkasan keluaran PoC otomatis |
| `poc-dirlist.txt` | F2 | bukti "Index of …" per direktori (tanpa login) |
| `poc-pii.txt` | F1 | daftar direktori PII + status unduhan (nama diredact) |
| `poc-pathdisclosure.txt` | F3 | fatal error PHP + path absolut dari `include/*.php` |
| `poc-headers.txt` | F4 | header keamanan absen pada `login.php` |
| `poc-f1.txt` / `f1-summary.json` | F1 | run checker: 186 entri, 185 terkirim + magic terverifikasi |
| `poc-f1-exfil.txt` | F1 | manifest exfil nyata (186 berkas, nama disensor + sha256) |
| `poc-f1-exfil-summary.txt` | F1 | ringkasan exfil: 476.41 MiB, bukti JPEG/Exif + PDF |
| `poc-login-negative.txt` | — | uji negatif: default creds & SQLi gagal (dicatat jujur) |

Semua permintaan **tanpa cookie/autentikasi**. Isi dokumen pribadi **tidak** disimpan di sini — hanya metadata (status HTTP, tipe MIME, ukuran). Nama berkas siswa diredact.

Reproduksi:
```bash
python3 poc/poc_siswamugeb_exposure.py --out evidence/siswamugeb/poc-exposure.txt
```
