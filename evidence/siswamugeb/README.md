# Evidence — Report 3 (Pembiasaan) · SISWA MGKB

Target: `https://pcmgkb.my.id/siswamugeb/`

| Berkas | Temuan | Isi |
|--------|--------|-----|
| `poc-exposure.txt` | F1–F4 | ringkasan keluaran PoC otomatis |
| `poc-dirlist.txt` | F2 | bukti "Index of …" per direktori (tanpa login) |
| `poc-pii.txt` | F1 | daftar direktori PII + status unduhan (nama diredact) |
| `poc-pathdisclosure.txt` | F3 | fatal error PHP + path absolut dari `include/*.php` |
| `poc-headers.txt` | F4 | header keamanan absen pada `login.php` |
| `poc-login-negative.txt` | — | uji negatif: default creds & SQLi gagal (dicatat jujur) |

Semua permintaan **tanpa cookie/autentikasi**. Isi dokumen pribadi **tidak** disimpan di sini — hanya metadata (status HTTP, tipe MIME, ukuran). Nama berkas siswa diredact.

Reproduksi:
```bash
python3 poc/poc_siswamugeb_exposure.py --out evidence/siswamugeb/poc-exposure.txt
```
