#!/usr/bin/env python3
"""変換済みの設計書 JSON から、名前や書式の目印に一致する箇所を決定論的に探す。

使い方:
    python tools/find_in_design.py <design_dir> --name "電話番号認証ボタン押下" [--name ...]
    python tools/find_in_design.py <design_dir> --font-color FFFF0000 --sheet 画面項目定義
    python tools/find_in_design.py <design_dir> --strike

    design_dir: work/runs/{run_id}/00_scope/design

    絞り込み:  --book ブック名 / --sheet シート名 / --column 列記号
    名前:      --name(複数可)。省略した場合は書式の条件だけで探す
    書式:      --strike(取り消し線)/ --font-color 色 / --fill-color 色
               色は変換結果に出てくる表記(例: FFFF0000、theme:5)。セル内の一部だけの書式も対象
    対象:      セルの値に加え、図形の文字(S{番号})とセルのコメントも探す(--cells-only でセルだけ)

出力(標準出力に JSON):
    名前ごと(名前を省略した場合は書式条件1件)に、一致した箇所を
    exact(完全一致)→ normalized(表記ゆれを除いて一致)→ partial(部分一致)→ format(書式のみ)の順で返す。
    同じ入力なら常に同じ結果・同じ順序になる。

表記ゆれの正規化(normalized / partial の判定に使う):
    - Unicode NFKC 正規化(全角英数字・半角カナなどを統一)
    - 空白(全角・半角・改行)をすべて除去
    - 英字を小文字に統一
    - 「」『』"" '' 【】() などの括弧・引用符を除去
"""
import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

QUOTES = "「」『』\"'“”‘’【】()()"
ORDER = {"exact": 0, "normalized": 1, "partial": 2, "format": 3}


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    s = re.sub(r"\s+", "", s)
    s = s.translate({ord(c): None for c in QUOTES})
    return s.lower()


def col_key(c: str):
    return (len(c), c)


def match_kind(value: str, name):
    if name is None:
        return "format"
    if value == name:
        return "exact"
    nv, nn = norm(value), norm(name)
    if nv == nn:
        return "normalized"
    if nn and nn in nv:
        return "partial"
    return None


def has_format(a: dict, args) -> bool:
    if not (args.strike or args.font_color or args.fill_color):
        return True
    runs = a.get("runs", [])
    if args.strike and not (a.get("strike") or any(r.get("strike") for r in runs)):
        return False
    if args.font_color and not (a.get("font_color") == args.font_color
                                or any(r.get("font_color") == args.font_color for r in runs)):
        return False
    if args.fill_color and a.get("fill_color") != args.fill_color:
        return False
    return True


def load_sheets(base: Path, args):
    sheets = []
    for idx_path in sorted(base.glob("*/index.json")):
        book_dir = idx_path.parent
        if args.book and book_dir.name != args.book:
            continue
        index = json.loads(idx_path.read_text(encoding="utf-8"))
        for s in index["sheets"]:
            if args.sheet and args.sheet not in (s["sheet"], s["file_stem"]):
                continue
            data = json.loads((book_dir / f"{s['file_stem']}.json").read_text(encoding="utf-8"))
            sheets.append((book_dir.name, s["file_stem"], data))
    return sheets


def search(sheets, name, args):
    hits = []
    fmt_filter = bool(args.strike or args.font_color or args.fill_color)
    for book, stem, data in sheets:
        base_ev = f"00_scope/design/{book}/{stem}.md"
        for row in data["rows"]:
            attrs = row.get("attrs", {})
            for col in sorted(set(row["cells"]) | set(attrs), key=col_key):
                if args.column and col != args.column:
                    continue
                if col in row.get("merged_from", {}):
                    continue
                a = attrs.get(col, {})
                if not has_format(a, args):
                    continue
                v = row["cells"].get(col)
                v = "" if v is None else (v if isinstance(v, str) else str(v))
                kind = match_kind(v, name)
                if kind is None:
                    continue
                hits.append({"match": kind, "source": "cell", "book": book, "sheet": data["source"]["sheet"],
                             "row": row["row"], "column": col, "ref": f"{col}{row['row']}", "value": v,
                             "evidence": f"{base_ev}#L{row['row']}"})
            if args.cells_only or name is None:
                continue
            for col in sorted(attrs, key=col_key):
                c = attrs[col].get("comment")
                if c and (k := match_kind(c, name)):
                    hits.append({"match": k, "source": "comment", "book": book, "sheet": data["source"]["sheet"],
                                 "row": row["row"], "column": col, "ref": f"{col}{row['row']}", "value": c,
                                 "evidence": f"{base_ev}#L{row['row']}"})
        if args.cells_only or name is None or fmt_filter or args.column:
            continue
        for d in data.get("drawings", []):
            t = d.get("text")
            if t and (k := match_kind(t, name)):
                m = re.match(r"([A-Z]+)(\d+)", d["from"] or "")
                hits.append({"match": k, "source": "shape", "book": book, "sheet": data["source"]["sheet"],
                             "row": int(m.group(2)) if m else 0, "column": m.group(1) if m else "",
                             "ref": d["id"], "value": t, "evidence": f"{base_ev}#{d['id']}"})
    src_order = {"cell": 0, "comment": 1, "shape": 2}
    hits.sort(key=lambda h: (ORDER[h["match"]], h["book"], h["sheet"], h["row"], col_key(h["column"]),
                             src_order[h["source"]], h["ref"]))
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("design_dir")
    ap.add_argument("--name", action="append")
    ap.add_argument("--book")
    ap.add_argument("--sheet")
    ap.add_argument("--column")
    ap.add_argument("--strike", action="store_true")
    ap.add_argument("--font-color")
    ap.add_argument("--fill-color")
    ap.add_argument("--cells-only", action="store_true")
    ap.add_argument("--limit", type=int, default=50, help="名前ごとの最大件数(既定50)")
    a = ap.parse_args()
    if not a.name and not (a.strike or a.font_color or a.fill_color):
        ap.error("--name か、書式の条件(--strike / --font-color / --fill-color)のどちらかが必要です")

    sheets = load_sheets(Path(a.design_dir), a)
    result = []
    for name in (a.name or [None]):
        hits = search(sheets, name, a)
        result.append({"name": name, "total": len(hits), "hits": hits[: a.limit]})
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2, sort_keys=True)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
