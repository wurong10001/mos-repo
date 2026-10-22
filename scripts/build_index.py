#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_index.py — 扫描 mos-repo 的 uploads/ 目录，生成 index.json 与 index.tsv。

用法:
    python3 scripts/build_index.py [--root 仓库根目录] [--repo OWNER/NAME]

约定:
  * uploads/<一级子目录名>/ 即分类 category（如 wallpaper / mosapp）；
    uploads/ 根下的散落文件归入 misc。
  * 每个文件记录: path/name/category/ext/type/size/sha256/updated_at/url/cdn。
  * type 由扩展名映射: image|archive|wasm|apk|deb|text|data|file。
  * updated_at 取该文件最后一次提交的 committer 时间（无 git 时退回 mtime）。
  * generated_at 取 HEAD 提交时间，保证文件无变化时重复生成字节一致，
    避免 Actions 每次运行都产生空提交；--stamp now 可强制为当前 UTC 时间。
  * 输出按 path 排序，保持稳定。

仅依赖 Python 标准库，可在 GitHub Actions (ubuntu-latest) 直接运行。
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from urllib.parse import quote

DEFAULT_REPO = "wurong10001/mos-repo"

TYPE_BY_EXT = {
    "png": "image", "jpg": "image", "jpeg": "image", "gif": "image",
    "webp": "image", "bmp": "image", "svg": "image", "heic": "image",
    "zip": "archive", "tar": "archive", "gz": "archive", "tgz": "archive",
    "xz": "archive", "7z": "archive", "rar": "archive",
    "wasm": "wasm", "apk": "apk", "deb": "deb",
    "txt": "text", "md": "text", "json": "data", "tsv": "data",
}

SKIP_NAMES = {".gitkeep", ".ds_store", "thumbs.db"}


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_output(root, args):
    try:
        out = subprocess.run(["git", "-C", root] + args, capture_output=True,
                             text=True, timeout=30)
        if out.returncode == 0:
            return out.stdout.strip()
    except Exception:
        pass
    return None


def file_updated_at(root, rel_path):
    iso = git_output(root, ["log", "-1", "--format=%cI", "--", rel_path])
    if iso:
        return iso
    mt = os.stat(os.path.join(root, rel_path)).st_mtime
    return datetime.fromtimestamp(mt, timezone.utc).isoformat()


def collect(root, uploads="uploads"):
    updir = os.path.join(root, uploads)
    if not os.path.isdir(updir):
        return []
    items = []
    for dirpath, dirnames, filenames in os.walk(updir):
        dirnames.sort()
        rel_dir = os.path.relpath(dirpath, root).replace(os.sep, "/")
        category = rel_dir[len(uploads) + 1:].split("/")[0] if rel_dir != uploads else "misc"
        for name in sorted(filenames):
            if name.lower() in SKIP_NAMES or name.startswith("."):
                continue
            rel = rel_dir + "/" + name
            full = os.path.join(root, rel)
            if "\t" in rel or "\n" in rel:
                print("跳过含制表符/换行的文件名: %s" % rel, file=sys.stderr)
                continue
            ext = os.path.splitext(name)[1].lstrip(".").lower()
            items.append({
                "path": rel,
                "name": name,
                "category": category,
                "ext": ext,
                "type": TYPE_BY_EXT.get(ext, "file"),
                "size": os.path.getsize(full),
                "sha256": sha256_file(full),
                "updated_at": file_updated_at(root, rel),
            })
    items.sort(key=lambda it: it["path"])
    return items


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=None, help="仓库根目录（默认为脚本所在目录的上一级）")
    ap.add_argument("--repo", default=DEFAULT_REPO, help="OWNER/NAME，用于拼接 URL")
    ap.add_argument("--stamp", default="commit", choices=["commit", "now"],
                    help="generated_at 取 HEAD 提交时间或当前时间")
    args = ap.parse_args()

    root = args.root or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    raw_base = "https://raw.githubusercontent.com/%s/main" % args.repo
    cdn_base = "https://cdn.jsdelivr.net/gh/%s@main" % args.repo

    files = collect(root)
    for it in files:
        u = quote(it["path"])
        it["url"] = raw_base + "/" + u
        it["cdn"] = cdn_base + "/" + u

    if args.stamp == "now":
        generated = datetime.now(timezone.utc).isoformat()
    else:
        generated = git_output(root, ["log", "-1", "--format=%cI"]) or \
            datetime.now(timezone.utc).isoformat()

    index = {
        "version": 1,
        "repo": args.repo,
        "generated_at": generated,
        "base_url": raw_base,
        "cdn_url": cdn_base,
        "count": len(files),
        "files": files,
    }

    with open(os.path.join(root, "index.json"), "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2, sort_keys=False)
        f.write("\n")

    header = ("# mos-repo index.tsv  自动生成，请勿手改  列: "
              "category\tname\tpath\tsize\tsha256\text\turl\n")
    with open(os.path.join(root, "index.tsv"), "w", encoding="utf-8") as f:
        f.write(header)
        for it in files:
            f.write("\t".join([it["category"], it["name"], it["path"],
                               str(it["size"]), it["sha256"], it["ext"],
                               it["url"]]) + "\n")

    print("index 生成完成: %d 个文件 -> index.json / index.tsv" % len(files))


if __name__ == "__main__":
    main()
