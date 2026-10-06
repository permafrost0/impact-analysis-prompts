#!/usr/bin/env python3
"""既存のソースと設計書が変更されていないことを確かめる(読み取り専用の確認)。

使い方:
    調査の開始時に、基準を記録する:
        python tools/guard.py record <調査フォルダ> --path input/source/<フォルダ名> --path input/target --path input/reference
    各フェーズの終わりに、基準と照合する:
        python tools/guard.py verify <調査フォルダ>

    記録先: <調査フォルダ>/guard/baseline.json
    照合の結果: 変更・追加・削除されたファイルがあれば一覧を表示し、終了コード 1 を返す。なければ 0。

    既定で照合から外すもの(調査とは関係なく、IDE やビルド、Excel が自動で作るもの):
      - フォルダ: .git .svn .settings .idea .vscode .gradle node_modules
      - pom.xml / build.gradle などがあるフォルダの直下の target build bin out
      - ファイル: ~$ で始まるもの(Excel を開いている間の一時ファイル)、.classpath .project .factorypath
                  Thumbs.db desktop.ini .DS_Store
    --exclude で、照合から外すフォルダ名を追加できる。
このスクリプトは、記録先以外には何も書き込まない。
"""
import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

# Windows のコンソール(cp932)で表せない文字があっても止まらないようにする
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(errors="replace")
    except (AttributeError, ValueError):
        pass

DEFAULT_EXCLUDE = {".git", ".svn", ".settings", ".idea", ".vscode", ".gradle", "node_modules"}
BUILD_MARKERS = {"pom.xml", "build.gradle", "build.gradle.kts", "settings.gradle", ".project"}
BUILD_OUTPUT = {"target", "build", "bin", "out"}
IGNORED_FILES = {".classpath", ".project", ".factorypath", "Thumbs.db", "desktop.ini", ".DS_Store"}


def ignored_file(name):
    return name.startswith("~$") or name in IGNORED_FILES


def file_hash(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def scan(root, exclude, extra_skip=()):
    """ファイルの一覧(相対パス → [サイズ, SHA-256])と、照合から外したフォルダ(相対パス)を返す"""
    files, skipped = {}, set()
    root = Path(root)
    extra_skip = set(extra_skip)
    for dirpath, dirnames, filenames in os.walk(root):
        skip = set(exclude) | (BUILD_OUTPUT if BUILD_MARKERS & set(filenames) else set())
        rel_dir = Path(dirpath).relative_to(root)
        keep = []
        for d in sorted(dirnames):
            rel = (rel_dir / d).as_posix()
            if d in skip or rel in extra_skip:
                skipped.add(rel)
            else:
                keep.append(d)
        dirnames[:] = keep
        for name in sorted(filenames):
            if ignored_file(name):
                continue
            p = Path(dirpath) / name
            try:
                st = p.stat()
                files[p.relative_to(root).as_posix()] = [st.st_size, file_hash(p)]
            except OSError as e:
                files[p.relative_to(root).as_posix()] = [-1, f"読めません: {e}"]
    return files, skipped


def under(path, dirs):
    return any(path == d or path.startswith(d + "/") for d in dirs)


def main():
    ap = argparse.ArgumentParser(description="ソースと設計書が変わっていないかを確かめる")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("record")
    r.add_argument("run_dir")
    r.add_argument("--path", action="append", required=True)
    r.add_argument("--exclude", action="append", default=[])
    v = sub.add_parser("verify")
    v.add_argument("run_dir")
    a = ap.parse_args()

    base = Path(a.run_dir) / "guard" / "baseline.json"
    if a.cmd == "record":
        exclude = sorted(DEFAULT_EXCLUDE | set(a.exclude))
        data = {"exclude": exclude, "roots": {}, "skipped": {}}
        for p in a.path:
            if not Path(p).exists():
                sys.exit(f"見つかりません: {p}")
            files, skipped = scan(p, set(exclude))
            data["roots"][str(Path(p).resolve())] = files
            data["skipped"][str(Path(p).resolve())] = sorted(skipped)
        base.parent.mkdir(parents=True, exist_ok=True)
        base.write_text(json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        n = sum(len(f) for f in data["roots"].values())
        print(f"基準を記録しました: {len(data['roots'])} か所 / {n} ファイル → {base}")
        return

    if not base.exists():
        sys.exit(f"基準がありません。先に record を実行してください: {base}")
    data = json.loads(base.read_text(encoding="utf-8"))
    problems = []
    for root, old in data["roots"].items():
        rec_skip = set((data.get("skipped") or {}).get(root, []))
        new, now_skip = scan(root, set(data["exclude"]), rec_skip) if Path(root).exists() else ({}, set())
        # 記録した後に IDE がビルド用の設定を作った場合などに、外したフォルダの中身を「削除」と誤って出さない
        old = {k: v for k, v in old.items() if not under(k, now_skip)}
        for path in sorted(set(old) | set(new)):
            if path not in new:
                problems.append(("削除", root, path))
            elif path not in old:
                problems.append(("追加", root, path))
            elif old[path] != new[path]:
                problems.append(("変更", root, path))
    if not problems:
        print("OK: ソースと設計書に変更はありません")
        return
    print(f"NG: {len(problems)} 件の変更があります(既存のソースと設計書は読むだけの約束です)")
    for kind, root, path in problems[:50]:
        print(f"  {kind}: {root}/{path}")
    if len(problems) > 50:
        print(f"  ほか {len(problems) - 50} 件")
    sys.exit(1)


if __name__ == "__main__":
    main()
