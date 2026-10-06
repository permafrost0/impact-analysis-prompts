#!/usr/bin/env python3
"""成果物(YAML)を機械的に点検する。形式は docs/schemas/ が正本で、このスクリプトはそれに対応する。

使い方:
    1ファイルの点検(各エージェントが完了前に実行する):
        python tools/check_outputs.py <調査フォルダ> --file <YAMLのパス>
    まとめて点検(オーケストレータがレビュー担当を呼ぶ前に実行する):
        python tools/check_outputs.py <調査フォルダ> --checkpoint p1-scope | p1 | p2-changes | p2 | p3 | retro

結果: [ERROR] があれば終了コード 1。[WARN] は終了コードに影響しない。
このスクリプトは読むだけで、何も書き込まない。
"""
import argparse
import re
import sys
from pathlib import Path

# Windows のコンソール(cp932)で表せない文字があっても止まらないようにする
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(errors="replace")
    except (AttributeError, ValueError):
        pass

try:
    import yaml
except ImportError:
    sys.exit("PyYAML がありません。pip install pyyaml を実行してください。")

CONF = {"高", "中", "低"}
SEV = {"高", "中", "低"}
REQ_CATEGORY = {"new", "change", "delete", "reuse"}
FEATURE_CATEGORY = REQ_CATEGORY | {"mixed"}
REQ_TYPE = {"ITEM", "EVENT", "LOGIC", "MSG", "CONFIG", "DB", "LAYOUT", "OTHER"}
MATCH = {"exact", "normalized", "partial", "marker", "whole_sheet", "text", "rows", "inferred"}
EXCLUDED_REASON = {"ambiguous", "existing_description", "note_only"}
IDENTIFIED_BY = {"text", "heading", "none"}
ISSUE_KIND = {"omission", "contradiction", "not_found", "premise_broken", "not_investigated", "error"}
FIT = {"as_is", "partial", "not_fit"}
ACTION = {"new", "modify", "delete"}
LAYER = {"view", "controller", "form", "validator", "service", "repository", "mapper_sql", "entity", "dto",
         "config", "message", "migration", "js", "batch", "other"}
DECISION = {"global", "partial"}
METHOD = {"new_method", "overload", "parameter", "subclass", "new_component"}
CON_CATEGORY = {"transaction", "existing_data", "convention", "premise", "performance", "security", "external",
                "exclusive_control", "test_difficulty", "operation", "other"}
APPROACH = ["delete", "reuse", "follow_existing", "modify_existing", "new_mechanism", "shared_or_high_risk"]
NEW_FILE_KIND = {"class", "migration", "template", "message_key", "config", "other"}
TC_KIND = {"new", "regression"}
CHECKPOINTS = ["p1-scope", "p1", "p2-changes", "p2", "p3", "retro"]
PHASE_END = {"p1": 7, "p2": 7, "p3": 6}   # 承認の観点の数(docs/schemas/review.md)
VERDICT = {"pass", "pass_with_notes", "fail"}
FINDING_SEV = {"blocker", "major", "minor"}
OBS_KIND = {"user_correction", "review_finding", "interim_fail", "rejected_assumption", "recurring_question", "other"}
CAUSE = {"手順の不足", "設計書の書き方の癖", "点検の見落とし", "一過性", "その他"}
PROPOSAL_TARGET = {"policies/common.md", "policies/phase1.md", "policies/phase2.md", "policies/phase3.md",
                   "policies/review.md"}

SHEET_REF = re.compile(r"^sheet:([^/]+)/(.+)#(?:L(\d+)(?:-L(\d+))?|S(\d+))$")
CODE_REF = re.compile(r"^code:(.+?):(\d+)(?:-(\d+))?$")
HEADING_REF = re.compile(r"^heading:([^/]+)/(.+)#L(\d+)$")


def safe_name(name):
    return re.sub(r'[\\/:*?"<>|]', "_", name).strip() or "sheet"



def resolve_source_root(value):
    """scope.yaml の source_root(例: input/source/myapp)を実際のフォルダにする。
    相対パスは、今いるフォルダ → このリポジトリのフォルダ(tools/ の1つ上)の順に探す。"""
    if not value:
        return None
    p = Path(str(value))
    if p.is_absolute():
        return p
    for base in (Path.cwd(), Path(__file__).resolve().parent.parent):
        if (base / p).exists():
            return base / p
    return Path.cwd() / p

class Checker:
    def __init__(self, run):
        self.run = Path(run)
        self.errors, self.warnings = [], []
        self.cache = {}
        self.sheet_cache = {}
        self.code_cache = {}
        self.scope = self.load("scope.yaml", required=False) or {}
        self.source_root = resolve_source_root(self.scope.get("source_root"))
        self.source_warned = False

    # ---------- 出力 ----------
    def err(self, where, msg):
        self.errors.append(f"[ERROR] {where}: {msg}")

    def warn(self, where, msg):
        self.warnings.append(f"[WARN]  {where}: {msg}")

    # ---------- 読み込み ----------
    def load(self, rel, required=True):
        if rel in self.cache:
            return self.cache[rel]
        p = self.run / rel
        data = None
        if not p.exists():
            if required:
                self.err(rel, "ファイルがありません")
        else:
            try:
                data = yaml.safe_load(p.read_text(encoding="utf-8-sig"))
                if data is None:
                    data = {}
                if not isinstance(data, dict):
                    self.err(rel, "YAML の一番外側が辞書(キー: 値)になっていません")
                    data = None
            except yaml.YAMLError as e:
                self.err(rel, f"YAML として読めません: {e}")
        self.cache[rel] = data
        return data

    def files(self, pattern):
        return sorted(p.relative_to(self.run).as_posix() for p in self.run.glob(pattern))

    def lst(self, d, key):
        v = (d or {}).get(key)
        return v if isinstance(v, list) else []

    # ---------- 全体の ID 一覧 ----------
    def build_index(self):
        idx = {}

        def add(i, kind, where, obj):
            if isinstance(i, str) and i:
                idx.setdefault(i, (kind, where, obj))

        sr = self.load("01_requirements/scope_resolution.yaml", required=False) or {}
        for it in self.lst(sr, "items"):
            add(it.get("id"), "SCP", "scope_resolution", it)
        for f in self.files("01_requirements/extract/*.yaml"):
            for it in self.lst(self.load(f, False), "items"):
                add(it.get("id"), "REQ_EXTRACT", f, it)
        rq = self.load("01_requirements/requirements.yaml", required=False) or {}
        for it in self.lst(rq, "items"):
            idx[it.get("id")] = ("REQ", "requirements", it) if isinstance(it.get("id"), str) else None
        for ft in self.lst(rq, "features"):
            add(ft.get("id"), "F", "requirements", ft)
        ru = self.load("02_impact/reuse.yaml", required=False) or {}
        for it in self.lst(ru, "items"):
            add(it.get("id"), "RUS", "reuse", it)
        for it in self.lst(ru, "changes"):
            add(it.get("id"), "CHG", "reuse", it)
        for f in self.files("02_impact/changes/*.yaml"):
            for it in self.lst(self.load(f, False), "items"):
                add(it.get("id"), "CHG", f, it)
        for name, kind in (("impacts", "IMP"), ("common_components", "CMN"), ("concerns", "CON")):
            for it in self.lst(self.load(f"02_impact/{name}.yaml", False), "items"):
                add(it.get("id"), kind, name, it)
        for it in self.lst(self.load("03_plan/verification.yaml", False), "items"):
            add(it.get("id"), "TC", "verification", it)
        for it in self.lst(self.load("decisions.yaml", False), "items"):
            add(it.get("id"), "DEC", "decisions", it)
        # 仮定・課題
        for f in self.files("**/*.yaml"):
            d = self.load(f, False)
            if not isinstance(d, dict):
                continue
            for key, kind in (("assumptions", "ASM"), ("issues", "ISS")):
                for it in self.lst(d, key):
                    if isinstance(it, dict):
                        add(it.get("id"), kind, f, it)
        idx.pop(None, None)
        self.index = {k: v for k, v in idx.items() if v}
        return self.index

    def ids_of(self, kind):
        return {k for k, v in self.index.items() if v[0] == kind}

    def exists(self, where, ref, kinds=None):
        if ref not in self.index:
            self.err(where, f"{ref} は存在しない ID です")
            return False
        if kinds and self.index[ref][0] not in kinds:
            self.err(where, f"{ref} は {'/'.join(kinds)} の ID ではありません")
            return False
        return True

    # ---------- 根拠 ----------
    def sheet_rows(self, book, sheet):
        key = (book, sheet)
        if key not in self.sheet_cache:
            p = self.run / "01_requirements" / "sheets" / safe_name(book) / f"{safe_name(sheet)}.md"
            rows, shapes, ok = set(), set(), p.exists()
            if ok:
                section = None
                for line in p.read_text(encoding="utf-8-sig").splitlines():
                    if line.startswith("## "):
                        section = line[3:].strip()
                        continue
                    m = re.match(r"^L(\d+)", line)
                    if section == "セル" and m:
                        rows.add(int(m.group(1)))
                    m = re.match(r"^S(\d+)\s", line)
                    if section and section.startswith("図形") and m:
                        shapes.add(int(m.group(1)))
            self.sheet_cache[key] = (ok, rows, shapes)
        return self.sheet_cache[key]

    def check_sheet_ref(self, where, ref, allowed_rows=None):
        m = SHEET_REF.match(str(ref))
        if not m:
            self.err(where, f"設計書の根拠の形が違います: {ref}(例: sheet:ブック/シート#L27)")
            return None
        book, sheet, a, b, s = m.groups()
        ok, rows, shapes = self.sheet_rows(book, sheet)
        if not ok:
            self.err(where, f"変換済みのシートがありません: {book}/{sheet}(指示外のシートは読みません)")
            return None
        if s:
            if int(s) not in shapes:
                self.err(where, f"図形 S{s} はシート {sheet} にありません")
            return set()
        a = int(a)
        b = int(b) if b else a
        in_range = {r for r in rows if a <= r <= b}
        if a not in rows or b not in rows:
            self.err(where, f"行 L{a}{'-L' + str(b) if b != a else ''} が {sheet} の変換結果にありません")
        if allowed_rows is not None:
            outside = sorted(r for r in (in_range | {a, b}) if r not in allowed_rows)
            if outside:
                self.err(where, f"対象の範囲外の行を根拠にしています: L{', L'.join(map(str, outside))}"
                                f"(既存の行は要件の根拠にしません)")
        return in_range

    def code_lines(self, rel):
        if rel not in self.code_cache:
            n = None
            if self.source_root and self.source_root.exists():
                p = (self.source_root / rel)
                try:
                    p.resolve().relative_to(self.source_root.resolve())
                    if p.is_file():
                        with open(p, "rb") as f:
                            n = sum(1 for _ in f)
                except (ValueError, OSError):
                    n = None
            self.code_cache[rel] = n
        return self.code_cache[rel]

    def source_available(self, where):
        if self.source_root and self.source_root.exists():
            return True
        if not self.source_warned:
            self.warn("scope.yaml", f"ソースのルートが見つからないため、コードの根拠の実在を確かめられません: {self.source_root}")
            self.source_warned = True
        return False

    def check_code_ref(self, where, ref):
        m = CODE_REF.match(str(ref))
        if not m:
            self.err(where, f"コードの根拠の形が違います: {ref}(例: code:src/main/java/.../X.java:22)")
            return
        path, a, b = m.group(1), int(m.group(2)), int(m.group(3) or m.group(2))
        if not self.source_available(where):
            return
        n = self.code_lines(path)
        if n is None:
            self.err(where, f"ソースにファイルがありません: {path}")
        elif not (1 <= a <= b <= max(n, 1)):
            self.err(where, f"行番号が範囲外です: {path}:{a}-{b}(ファイルは {n} 行)")

    def check_excerpt(self, where, ex, required=False):
        if ex in (None, {}, ""):
            if required:
                self.err(where, "excerpt(コードの抜粋の範囲)がありません")
            return
        if not isinstance(ex, dict) or not all(k in ex for k in ("file", "start", "end")):
            self.err(where, "excerpt は file / start / end の形で書きます")
            return
        try:
            a, b = int(ex["start"]), int(ex["end"])
        except (TypeError, ValueError):
            self.err(where, "excerpt の start / end が数字ではありません")
            return
        if b < a or b - a >= 40:
            self.err(where, f"excerpt の範囲が不正です(start {a} / end {b}、最大40行)")
        self.check_code_ref(where, f"code:{ex['file']}:{a}-{b}")

    # ---------- 共通の項目 ----------
    def need(self, where, obj, keys):
        for k in keys:
            v = obj.get(k) if isinstance(obj, dict) else None
            if v is None or v == "" or v == []:
                self.err(where, f"必須の項目 {k} がありません")

    def enum(self, where, obj, key, allowed, required=True):
        v = obj.get(key)
        if v is None and not required:
            return
        if v not in allowed:
            self.err(where, f"{key}={v!r} は使えない値です(使える値: {', '.join(sorted(map(str, allowed)))})")

    def check_question(self, where, q):
        if not isinstance(q, dict) or not q.get("text") or not isinstance(q.get("answer_examples"), list) \
                or not q.get("answer_examples"):
            self.err(where, "question は text と answer_examples(1つ以上)が必要です")

    def check_meta(self, rel, d, phase, agent, worker):
        m = d.get("meta")
        if not isinstance(m, dict):
            self.err(rel, "meta がありません")
            return
        self.need(rel + " meta", m, ["run_id", "agent", "worker", "attempt"])
        if str(m.get("phase")) != str(phase):
            self.err(rel, f"meta.phase は {phase} です")
        if agent and m.get("agent") != agent:
            self.err(rel, f"meta.agent は {agent} です")
        if worker and m.get("worker") != worker:
            self.err(rel, f"meta.worker は {worker} です")
        if self.scope.get("run_id") and m.get("run_id") != self.scope.get("run_id"):
            self.err(rel, f"meta.run_id が scope.yaml({self.scope.get('run_id')})と違います")
        att = m.get("attempt")
        if not isinstance(att, int) or att < 1:
            self.err(rel, "meta.attempt は 1 以上の数字です")
        elif att >= 2 and not m.get("feedback_response"):
            self.err(rel, "attempt が 2 以上なのに meta.feedback_response がありません")
        for n in self.lst(m, "not_covered"):
            if not isinstance(n, dict) or not n.get("id") or not n.get("reason"):
                self.err(rel, "meta.not_covered は id と reason が必要です")
        if not isinstance(m.get("self_check"), list):
            self.err(rel, "meta.self_check がありません")

    def check_asm_iss(self, rel, d, worker):
        for key, prefix in (("assumptions", "ASM"), ("issues", "ISS")):
            v = d.get(key)
            if v is None:
                continue
            if not isinstance(v, list):
                self.err(rel, f"{key} は配列です")
                continue
            for it in v:
                w = f"{rel} {key} {it.get('id') if isinstance(it, dict) else ''}"
                if not isinstance(it, dict):
                    self.err(w, "要素が辞書ではありません")
                    continue
                if not re.fullmatch(rf"{prefix}-{re.escape(str(worker))}-\d{{3}}", str(it.get("id", ""))):
                    self.err(w, f"ID は {prefix}-{worker}-001 の形です")
                if key == "assumptions":
                    self.need(w, it, ["statement", "reason"])
                else:
                    self.need(w, it, ["kind", "target", "description"])
                    self.enum(w, it, "kind", ISSUE_KIND)
                if not isinstance(it.get("ask_user"), bool):
                    self.err(w, "ask_user は true / false です")
                elif it.get("ask_user"):
                    self.check_question(w, it.get("question"))

    def check_items_ids(self, rel, items, pattern):
        seen = set()
        for it in items:
            i = it.get("id") if isinstance(it, dict) else None
            if not isinstance(i, str) or not re.fullmatch(pattern, i):
                self.err(rel, f"ID の形が違います: {i!r}(形: {pattern})")
            if i in seen:
                self.err(rel, f"ID が重複しています: {i}")
            seen.add(i)

    def worker_of(self, d):
        return (d.get("meta") or {}).get("worker", "")

    # ---------- フェーズ1 ----------
    def tags(self):
        return {t.get("tag"): t for t in self.lst(self.scope, "sheet_tags") if isinstance(t, dict)}

    def check_scope_resolution(self, rel):
        d = self.load(rel)
        if d is None:
            return
        self.check_meta(rel, d, 1, "impact-p1a-scope", "p1a")
        items = self.lst(d, "items")
        self.check_items_ids(rel, items, r"SCP-\d{3}")
        instr = {t.get("id") for t in self.lst(self.scope, "instructions")}
        tags = self.tags()
        for it in items:
            w = f"{rel} {it.get('id')}"
            self.need(w, it, ["instruction", "sheet_tag", "rows", "match", "evidence", "confidence"])
            if it.get("instruction") not in instr:
                self.err(w, f"instruction {it.get('instruction')} は scope.yaml にありません")
            tag = tags.get(it.get("sheet_tag"))
            if not tag:
                self.err(w, f"sheet_tag {it.get('sheet_tag')} は scope.yaml にありません")
                continue
            book = Path(tag["file"]).stem
            ok, rows, shapes = self.sheet_rows(book, tag["sheet"])
            if not ok:
                self.err(w, f"変換済みのシートがありません: {book}/{tag['sheet']}")
                continue
            for r in self.lst(it, "rows") + self.lst(it, "header_rows"):
                if r not in rows:
                    self.err(w, f"行 L{r} が変換結果にありません")
            for s in self.lst(it, "shapes"):
                if int(str(s).lstrip("S") or 0) not in shapes:
                    self.err(w, f"図形 {s} がありません")
            self.enum(w, it, "match", MATCH)
            self.enum(w, it, "confidence", CONF)
            own = set(self.lst(it, "rows")) | set(self.lst(it, "header_rows"))
            for e in self.lst(it, "evidence"):
                m = SHEET_REF.match(str(e))
                if m and (m.group(1), m.group(2)) != (book, tag["sheet"]):
                    self.err(w, f"根拠 {e} が、sheet_tag {it.get('sheet_tag')}({book}/{tag['sheet']})と別のシートを指しています")
                    continue
                self.check_sheet_ref(w, e, allowed_rows=own if m and not m.group(5) else None)
        for u in self.lst(d, "unresolved"):
            w = f"{rel} unresolved {u.get('instruction')}"
            self.need(w, u, ["instruction", "reason"])
            self.check_question(w, u.get("question"))
        for o in self.lst(d, "out_of_scope_refs"):
            w = f"{rel} out_of_scope_refs"
            self.need(w, o, ["from", "quote"])
            self.check_question(w, o.get("question"))
        self.check_asm_iss(rel, d, "p1a")

    def allowed_rows_for(self, scp_ids):
        sr = self.load("01_requirements/scope_resolution.yaml", required=False) or {}
        by = {s.get("id"): s for s in self.lst(sr, "items")}
        rows, headers = set(), set()
        for i in scp_ids:
            s = by.get(i)
            if s:
                rows |= set(self.lst(s, "rows"))
                headers |= set(self.lst(s, "header_rows"))
        return rows, headers

    def check_req_item(self, w, it, extract_tag=None):
        self.need(w, it, ["category", "type", "title", "summary", "scp_ids", "source", "category_basis", "confidence"])
        self.enum(w, it, "category", REQ_CATEGORY)
        self.enum(w, it, "type", REQ_TYPE)
        self.enum(w, it, "confidence", CONF)
        vals = it.get("values")
        if not isinstance(vals, dict):
            self.err(w, "values は辞書です(値がなければ {})")
        else:
            for k, v in vals.items():
                if v is None or isinstance(v, (dict, list)):
                    self.err(w, f"values.{k} は文字列で写します(null や入れ子は使いません)")
        sr = self.load("01_requirements/scope_resolution.yaml", required=False) or {}
        scp = {s.get("id"): s for s in self.lst(sr, "items")}
        for s in self.lst(it, "scp_ids"):
            if s not in scp:
                self.err(w, f"scp_ids の {s} は存在しません")
            elif extract_tag and scp[s].get("sheet_tag") != extract_tag:
                self.err(w, f"{s} は別のシート({scp[s].get('sheet_tag')})の範囲です")
        rows, _ = self.allowed_rows_for(self.lst(it, "scp_ids"))
        for src in self.lst(it, "source"):
            self.check_sheet_ref(w, src, allowed_rows=rows if not str(src).split("#")[-1].startswith("S") else None)
        if it.get("category") == "reuse":
            r = it.get("reuse")
            if not isinstance(r, dict):
                self.err(w, "category が reuse のときは reuse(quote / clues / identified_by)が必要です")
            else:
                self.need(w + " reuse", r, ["quote", "clues", "identified_by"])
                self.enum(w + " reuse", r, "identified_by", IDENTIFIED_BY)
                if r.get("identified_by") == "heading" and not r.get("heading_refs"):
                    self.err(w, "identified_by が heading のときは heading_refs が必要です")
                for h in self.lst(r, "heading_refs"):
                    if not HEADING_REF.match(str(h)):
                        self.err(w, f"heading_refs の形が違います: {h}")
                if r.get("identified_by") == "none" and not it.get("question"):
                    self.err(w, "流用先を特定できない(identified_by: none)ときは question が必要です")
        if it.get("question") is not None:
            self.check_question(w, it.get("question"))

    def check_excluded(self, rel, d, scp_rows=None):
        seen = set()
        for e in self.lst(d, "excluded"):
            w = f"{rel} excluded {e.get('source')}"
            if e.get("reason") == "ambiguous":
                if e.get("source") in seen:
                    self.err(w, "同じ箇所の判断に困る表現(ambiguous)が複数あります。1件にまとめ、quote に並べます")
                seen.add(e.get("source"))
            self.need(w, e, ["source", "quote", "reason"])
            self.enum(w, e, "reason", EXCLUDED_REASON)
            if e.get("source"):
                self.check_sheet_ref(w, e["source"], allowed_rows=scp_rows)
            if e.get("reason") == "ambiguous":
                self.check_question(w, e.get("question"))

    def check_reference_reads(self, rel, d):
        ref_dir = Path("input/reference")
        for r in self.lst(d, "reference_reads"):
            w = f"{rel} reference_reads"
            self.need(w, r, ["file", "command", "found", "purpose"])
            if "list_headings.py" not in str(r.get("command", "")):
                self.err(w, "参照先は tools/list_headings.py で見出しだけを読みます")
            if r.get("file") and ref_dir.exists() and not (ref_dir / r["file"]).exists():
                self.err(w, f"input/reference/{r['file']} がありません")

    def check_extract(self, rel):
        d = self.load(rel)
        if d is None:
            return
        tag = Path(rel).stem
        self.check_meta(rel, d, 1, "impact-p1b-extract", f"p1b-{tag}")
        sh = d.get("sheet") or {}
        if sh.get("tag") != tag:
            self.err(rel, f"sheet.tag はファイル名と同じ {tag} です")
        items = self.lst(d, "items")
        self.check_items_ids(rel, items, rf"REQ-{re.escape(tag)}-\d{{3}}")
        for it in items:
            self.check_req_item(f"{rel} {it.get('id')}", it, extract_tag=tag)
        sr = self.load("01_requirements/scope_resolution.yaml", required=False) or {}
        my_scp = [s.get("id") for s in self.lst(sr, "items") if s.get("sheet_tag") == tag]
        rows, _ = self.allowed_rows_for(my_scp)
        self.check_excluded(rel, d, rows)
        self.check_reference_reads(rel, d)
        if any((it.get("reuse") or {}).get("identified_by") == "heading" for it in items) \
                and not d.get("reference_reads"):
            self.err(rel, "見出しで特定した要件があるのに reference_reads がありません")
        self.check_asm_iss(rel, d, f"p1b-{tag}")

    def check_requirements(self, rel):
        d = self.load(rel)
        if d is None:
            return
        self.check_meta(rel, d, 1, "impact-p1c-integrate", "p1c")
        feats = self.lst(d, "features")
        self.check_items_ids(rel, feats, r"F-\d{2}")
        items = self.lst(d, "items")
        self.check_items_ids(rel, items, r"REQ-(?:S\d+|I)-\d{3}")
        by_id = {it.get("id"): it for it in items}
        fid = {f.get("id") for f in feats}
        member = {}
        for f in feats:
            w = f"{rel} {f.get('id')}"
            self.need(w, f, ["name", "category", "summary", "req_ids"])
            self.enum(w, f, "category", FEATURE_CATEGORY)
            for r in self.lst(f, "req_ids"):
                if r not in by_id:
                    self.err(w, f"req_ids の {r} が items にありません")
                member.setdefault(r, []).append(f.get("id"))
        changes = {(c.get("id"), c.get("field")) for c in self.lst(d.get("meta") or {}, "changes")}
        extracts = {}
        for f in self.files("01_requirements/extract/*.yaml"):
            for it in self.lst(self.load(f, False), "items"):
                extracts[it.get("id")] = it
        merged_away = {n.get("id") for n in self.lst(d.get("meta") or {}, "not_covered")}
        for i, ex in extracts.items():
            if i not in by_id and i not in merged_away:
                self.err(rel, f"抽出した要件 {i} が items にありません(まとめた場合は meta.not_covered に理由)")
        for it in items:
            w = f"{rel} {it.get('id')}"
            self.check_req_item(w, it)
            if it.get("feature") not in fid:
                self.err(w, f"feature {it.get('feature')} が features にありません")
            if member.get(it.get("id")) != [it.get("feature")]:
                self.err(w, "要件は、ちょうど1つの機能の req_ids に入ります(feature と一致させる)")
            for r in self.lst(it, "related"):
                if r not in by_id:
                    self.err(w, f"related の {r} が items にありません")
            ex = extracts.get(it.get("id"))
            if ex is None:
                if not str(it.get("id", "")).startswith("REQ-I-"):
                    self.err(w, "抽出結果(extract)にない要件です")
                continue
            for k in ("values", "source", "scp_ids"):
                if ex.get(k) != it.get(k):
                    self.err(w, f"{k} が抽出結果と違います(値・根拠は写すだけで変えません)")
            for k in ("category", "title", "summary", "type"):
                if ex.get(k) != it.get(k) and (it.get("id"), k) not in changes:
                    self.err(w, f"{k} が抽出結果と違います(変えるときは meta.changes に理由を記録)")
        ex_sources = {e.get("source") for f in self.files("01_requirements/extract/*.yaml")
                      for e in self.lst(self.load(f, False), "excluded")}
        my_sources = {e.get("source") for e in self.lst(d, "excluded")}
        # ユーザーの判断(effect: change)で要件にした記述は、excluded から外してよい
        changed = {a[len("excluded:"):] for x in self.lst(self.load("decisions.yaml", False), "items")
                   if x.get("effect") == "change" for a in self.lst(x, "about") if str(a).startswith("excluded:")}
        for s in sorted(ex_sources - my_sources - changed):
            self.err(rel, f"抽出結果の excluded({s})が写されていません")
        self.check_excluded(rel, d)
        fids = {f.get("id") for f in self.lst(d, "features")}
        for e in self.lst(d, "excluded"):
            if e.get("feature") and e.get("feature") not in fids:
                self.err(f"{rel} excluded {e.get('source')}", f"feature({e.get('feature')})が features にありません")
        self.check_reference_reads(rel, d)
        for c in self.lst(d, "cross_refs"):
            if c.get("from") not in by_id:
                self.err(rel, f"cross_refs の from {c.get('from')} が items にありません")
        self.check_asm_iss(rel, d, "p1c")

    # ---------- フェーズ2 ----------
    def req_items(self):
        rq = self.load("01_requirements/requirements.yaml", required=False) or {}
        return {it.get("id"): it for it in self.lst(rq, "items")}

    def features(self):
        rq = self.load("01_requirements/requirements.yaml", required=False) or {}
        return {f.get("id"): f for f in self.lst(rq, "features")}

    def check_change_item(self, w, it, feature=None):
        self.need(w, it, ["req_ids", "file", "symbol", "action", "layer", "before", "after", "confidence"])
        self.enum(w, it, "action", ACTION)
        self.enum(w, it, "layer", LAYER)
        self.enum(w, it, "confidence", CONF)
        reqs = self.req_items()
        for r in self.lst(it, "req_ids"):
            if r not in reqs:
                self.err(w, f"req_ids の {r} は要件にありません")
            elif feature and reqs[r].get("feature") != feature:
                self.err(w, f"{r} は機能 {reqs[r].get('feature')} の要件です(このファイルは {feature})")
        if it.get("action") in ("modify", "delete"):
            if not it.get("location"):
                self.err(w, "既存の修正・削除には location(code:)が必要です")
            else:
                self.check_code_ref(w, it["location"])
            self.check_excerpt(w, it.get("excerpt"), required=True)
        else:
            self.check_excerpt(w, it.get("excerpt"))
            if it.get("location"):
                self.check_code_ref(w, it["location"])
        if not isinstance(it.get("shared"), bool):
            self.err(w, "shared は true / false です")
        elif it.get("shared") and not it.get("shared_reason"):
            self.err(w, "shared が true のときは shared_reason が必要です")
        for r in self.lst(it, "reference"):
            self.check_code_ref(w, r)
        if not isinstance(it.get("detail", []), list):
            self.err(w, "detail は配列です")

    def check_reuse(self, rel):
        d = self.load(rel)
        if d is None:
            return
        self.check_meta(rel, d, 2, "impact-p2a-reuse", "p2a")
        reqs, feats = self.req_items(), self.features()
        items = self.lst(d, "items")
        self.check_items_ids(rel, items, r"RUS-\d{3}")
        for it in items:
            w = f"{rel} {it.get('id')}"
            self.need(w, it, ["req_ids", "feature", "target", "location", "behavior", "fit", "how_to_reuse",
                              "searched", "confidence"])
            for r in self.lst(it, "req_ids"):
                if r not in reqs:
                    self.err(w, f"{r} は要件にありません")
                elif reqs[r].get("category") != "reuse":
                    self.err(w, f"{r} は「既存の流用」の要件ではありません")
            if it.get("feature") not in feats:
                self.err(w, f"feature {it.get('feature')} がありません")
            self.enum(w, it, "fit", FIT)
            self.enum(w, it, "confidence", CONF)
            if it.get("fit") in ("partial", "not_fit") and not it.get("gap"):
                self.err(w, "fit が as_is 以外のときは gap が必要です")
            if it.get("location"):
                self.check_code_ref(w, it["location"])
            self.check_excerpt(w, it.get("excerpt"))
        ch = self.lst(d, "changes")
        self.check_items_ids(rel + " changes", ch, r"CHG-R-\d{3}")
        for it in ch:
            self.check_change_item(f"{rel} {it.get('id')}", it)
        for n in self.lst(d, "not_found"):
            w = f"{rel} not_found {n.get('req_id')}"
            self.need(w, n, ["req_id", "clues", "searched"])
            self.check_question(w, n.get("question"))
        self.check_asm_iss(rel, d, "p2a")

    def check_changes(self, rel):
        d = self.load(rel)
        if d is None:
            return
        fid = Path(rel).stem
        num = fid.replace("F-", "F")
        self.check_meta(rel, d, 2, "impact-p2b-changes", f"p2b-{num}")
        if d.get("feature") != fid:
            self.err(rel, f"feature はファイル名と同じ {fid} です")
        if fid not in self.features():
            self.err(rel, f"機能 {fid} が requirements.yaml にありません")
        for fl in self.lst(d, "flow"):
            w = f"{rel} flow {fl.get('order')}"
            self.need(w, fl, ["order", "location", "symbol", "behavior"])
            if fl.get("location"):
                self.check_code_ref(w, fl["location"])
        items = self.lst(d, "items")
        if items and not self.lst(d, "flow"):
            self.err(rel, "flow(今の処理の流れ)がありません。修正箇所の前に、この機能が通る処理をコードで辿って記録します")
        self.check_items_ids(rel, items, rf"CHG-{num}-\d{{3}}")
        for it in items:
            self.check_change_item(f"{rel} {it.get('id')}", it, feature=fid)
        for p in self.lst(d, "premise_broken"):
            w = f"{rel} premise_broken {p.get('req_id')}"
            self.need(w, p, ["req_id", "description", "searched"])
            self.check_question(w, p.get("question"))
        self.check_asm_iss(rel, d, f"p2b-{num}")

    def all_changes(self):
        out = {}
        for it in self.lst(self.load("02_impact/reuse.yaml", False), "changes"):
            out[it.get("id")] = it
        for f in self.files("02_impact/changes/*.yaml"):
            for it in self.lst(self.load(f, False), "items"):
                out[it.get("id")] = it
        return out

    def check_impacts(self, rel):
        d = self.load(rel)
        if d is None:
            return
        self.check_meta(rel, d, 2, "impact-p2c-impacts", "p2c")
        chg, feats = self.all_changes(), self.features()
        logged = set()
        for s in self.lst(d, "search_log"):
            w = f"{rel} search_log {s.get('chg_id')}"
            self.need(w, s, ["chg_id", "searched", "result"])
            self.enum(w, s, "result", {"impact", "none"})
            logged.add(s.get("chg_id"))
        for c in sorted(set(chg) - logged):
            self.err(rel, f"修正 {c} の search_log がありません(影響がなくても書きます)")
        items = self.lst(d, "items")
        self.check_items_ids(rel, items, r"IMP-\d{3}")
        for it in items:
            w = f"{rel} {it.get('id')}"
            self.need(w, it, ["chg_ids", "feature", "affected", "location", "current_use", "risk", "severity",
                              "confidence"])
            for c in self.lst(it, "chg_ids"):
                if c not in chg:
                    self.err(w, f"chg_ids の {c} は修正にありません")
            if it.get("feature") not in feats:
                self.err(w, f"feature {it.get('feature')} がありません")
            self.enum(w, it, "severity", SEV)
            self.enum(w, it, "confidence", CONF)
            if it.get("location"):
                self.check_code_ref(w, it["location"])
            self.check_excerpt(w, it.get("excerpt"))
            if it.get("severity") == "高" and not it.get("test_points"):
                self.err(w, "重大度 高 の影響には test_points が必要です")
        self.check_asm_iss(rel, d, "p2c")

    def check_common(self, rel):
        d = self.load(rel)
        if d is None:
            return
        self.check_meta(rel, d, 2, "impact-p2d-common", "p2d")
        chg, feats = self.all_changes(), self.features()
        items = self.lst(d, "items")
        self.check_items_ids(rel, items, r"CMN-\d{3}")
        for it in items:
            w = f"{rel} {it.get('id')}"
            self.need(w, it, ["chg_ids", "features", "component", "location", "callers", "decision", "rationale",
                              "if_global", "confidence"])
            for c in self.lst(it, "chg_ids"):
                if c not in chg:
                    self.err(w, f"chg_ids の {c} は修正にありません")
            for f in self.lst(it, "features"):
                if f not in feats:
                    self.err(w, f"features の {f} がありません")
            if it.get("location"):
                self.check_code_ref(w, it["location"])
            self.check_excerpt(w, it.get("excerpt"))
            for cl in self.lst(it, "callers"):
                cw = f"{w} caller {cl.get('location')}"
                self.need(cw, cl, ["location", "feature_name", "usage"])
                if cl.get("location"):
                    self.check_code_ref(cw, cl["location"])
                if not isinstance(cl.get("is_target"), bool):
                    self.err(cw, "is_target は true / false です")
                nb = cl.get("needs_new_behavior")
                nb = {True: "yes", False: "no"}.get(nb, nb)
                if nb not in ("yes", "no", "unknown"):
                    self.err(cw, "needs_new_behavior は yes / no / unknown です")
            self.enum(w, it, "decision", DECISION)
            if it.get("decision") == "partial":
                self.enum(w, it, "method", METHOD)
            if not isinstance(it.get("conflicts_with_chg"), bool):
                self.err(w, "conflicts_with_chg は true / false です")
            self.check_question(w, it.get("question"))
            self.enum(w, it, "confidence", CONF)
        self.check_asm_iss(rel, d, "p2d")

    def check_concerns(self, rel):
        d = self.load(rel)
        if d is None:
            return
        self.check_meta(rel, d, 2, "impact-p2e-concerns", "p2e")
        feats = self.features()
        items = self.lst(d, "items")
        self.check_items_ids(rel, items, r"CON-\d{3}")
        for it in items:
            w = f"{rel} {it.get('id')}"
            self.need(w, it, ["features", "category", "title", "description", "severity", "recommendation",
                              "confidence"])
            for f in self.lst(it, "features"):
                if f not in feats:
                    self.err(w, f"features の {f} がありません")
            self.enum(w, it, "category", CON_CATEGORY)
            self.enum(w, it, "severity", SEV)
            self.enum(w, it, "confidence", CONF)
            if it.get("location"):
                self.check_code_ref(w, it["location"])
            else:
                self.warn(w, "location(code:)がありません。コードに根拠がある懸念は場所を書きます")
            self.check_excerpt(w, it.get("excerpt"))
            if it.get("question") is not None:
                self.check_question(w, it.get("question"))
        self.check_asm_iss(rel, d, "p2e")

    # ---------- フェーズ3 ----------
    def check_plan(self, rel):
        d = self.load(rel)
        if d is None:
            return
        self.check_meta(rel, d, 3, "impact-p3a-plan", "p3a")
        feats, chg = self.features(), self.all_changes()
        decs = {x.get("id") for x in self.lst(self.load("decisions.yaml", False), "items")}
        order = self.lst(d, "order")
        nums = [o.get("order") for o in order]
        if nums != list(range(1, len(order) + 1)):
            self.err(rel, "order は 1 から順に振ります")
        pos = {}
        assigned = {}
        for o in order:
            w = f"{rel} order {o.get('order')} {o.get('feature')}"
            self.need(w, o, ["order", "feature", "approach", "reason"])
            self.enum(w, o, "approach", set(APPROACH))
            if o.get("feature") not in feats:
                self.err(w, f"機能 {o.get('feature')} がありません")
            if o.get("feature") in pos:
                self.err(w, "同じ機能が2回出てきます")
            pos[o.get("feature")] = o.get("order")
            for c in self.lst(o, "chg_ids"):
                if c not in chg:
                    self.err(w, f"chg_ids の {c} は修正にありません")
                assigned.setdefault(c, []).append(o.get("feature"))
            for x in self.lst(o, "decisions"):
                if x not in decs:
                    self.err(w, f"decisions の {x} は decisions.yaml にありません")
            if o.get("question") is not None:
                self.check_question(w, o.get("question"))
        for o in order:
            for dep in self.lst(o, "depends_on"):
                if dep not in pos:
                    self.err(rel, f"{o.get('feature')} の depends_on {dep} が order にありません")
                elif pos[dep] >= o.get("order", 0):
                    self.err(rel, f"{o.get('feature')} は {dep} に依存するので、{dep} より後ろに置きます")
        for f in sorted(set(feats) - set(pos)):
            self.err(rel, f"機能 {f} が order にありません")
        for c in sorted(chg):
            if c not in assigned:
                self.err(rel, f"修正 {c} が、どの機能の chg_ids にも入っていません")
            elif len(assigned[c]) > 1:
                self.err(rel, f"修正 {c} が複数の機能に入っています: {', '.join(assigned[c])}")
        # 方針の順番(既存をもとにしたものから)を崩していないか
        rank = {a: i for i, a in enumerate(APPROACH)}
        deps_all = {o.get("feature"): set(self.lst(o, "depends_on")) for o in order}
        for i, a in enumerate(order):
            for b in order[i + 1:]:
                if rank.get(a.get("approach"), 0) > rank.get(b.get("approach"), 0) \
                        and a.get("feature") not in deps_all.get(b.get("feature"), set()) \
                        and not (a.get("exception") or b.get("exception")):
                    self.warn(rel, f"{a.get('feature')}({a.get('approach')})が {b.get('feature')}"
                                   f"({b.get('approach')})より前にあります。方針と違う順番なら exception に理由を書きます")
        self.check_asm_iss(rel, d, "p3a")

    def check_steps(self, rel):
        d = self.load(rel)
        if d is None:
            return
        fid = Path(rel).stem
        num = fid.replace("F-", "F")
        self.check_meta(rel, d, 3, "impact-p3b-steps", f"p3b-{num}")
        if d.get("feature") != fid:
            self.err(rel, f"feature はファイル名と同じ {fid} です")
        self.need(rel, d, ["goal", "procedure", "done_criteria"])
        plan = self.load("03_plan/plan.yaml", required=False) or {}
        mine = next((o for o in self.lst(plan, "order") if o.get("feature") == fid), None)
        if mine is None:
            self.err(rel, f"機能 {fid} が plan.yaml にありません")
        feats = self.features()
        for p in self.lst(d, "prerequisites"):
            if p not in feats:
                self.err(rel, f"prerequisites の {p} がありません")
        decs = {x.get("id") for x in self.lst(self.load("decisions.yaml", False), "items")}
        for fd in self.lst(d, "fixed_decisions"):
            if fd.get("id") not in decs:
                self.err(rel, f"fixed_decisions の {fd.get('id')} は decisions.yaml にありません")
        covered = set()
        nos = []
        for p in self.lst(d, "procedure"):
            w = f"{rel} 手順 {p.get('no')}"
            nos.append(p.get("no"))
            self.need(w, p, ["no", "file", "place", "action"])
            covered |= set(self.lst(p, "chg_ids"))
            if p.get("exemplar"):
                self.check_code_ref(w, p["exemplar"])
            else:
                self.warn(w, "exemplar(手本にする既存実装)がありません")
            self.check_excerpt(w, p.get("exemplar_excerpt"))
        if nos != list(range(1, len(nos) + 1)):
            self.err(rel, "手順の no は 1 から順に振ります")
        if mine is not None:
            want = set(self.lst(mine, "chg_ids"))
            for c in sorted(want - covered):
                self.err(rel, f"修正 {c} が、どの手順にも入っていません")
            for c in sorted(covered - want):
                self.err(rel, f"修正 {c} は、plan.yaml でこの機能に割り当てられていません")
        for nf in self.lst(d, "new_files"):
            w = f"{rel} new_files {nf.get('name')}"
            self.need(w, nf, ["kind", "name", "place", "basis"])
            self.enum(w, nf, "kind", NEW_FILE_KIND)
            if nf.get("basis"):
                self.check_code_ref(w, nf["basis"])
        for cv in self.lst(d, "conventions"):
            w = f"{rel} conventions {cv.get('aspect')}"
            self.need(w, cv, ["aspect", "rule", "basis"])
            if cv.get("basis"):
                self.check_code_ref(w, cv["basis"])
        for kb in self.lst(d, "keep_behaviors"):
            self.need(f"{rel} keep_behaviors", kb, ["behavior"])
        for q in self.lst(d, "questions"):
            self.check_question(f"{rel} questions", q)
        self.check_asm_iss(rel, d, f"p3b-{num}")

    def check_verification(self, rel):
        d = self.load(rel)
        if d is None:
            return
        self.check_meta(rel, d, 3, "impact-p3c-verification", "p3c")
        items = self.lst(d, "items")
        self.check_items_ids(rel, items, r"TC-\d{3}")
        feats, reqs = self.features(), self.req_items()
        imps = {it.get("id"): it for it in self.lst(self.load("02_impact/impacts.yaml", False), "items")}
        cmns = {it.get("id") for it in self.lst(self.load("02_impact/common_components.yaml", False), "items")}
        for it in items:
            w = f"{rel} {it.get('id')}"
            self.need(w, it, ["feature", "kind", "input", "expected", "where", "priority"])
            if it.get("feature") not in feats:
                self.err(w, f"feature {it.get('feature')} がありません")
            self.enum(w, it, "kind", TC_KIND)
            self.enum(w, it, "priority", SEV)
            for r in self.lst(it, "req_ids"):
                if r not in reqs:
                    self.err(w, f"req_ids の {r} は要件にありません")
            for r in self.lst(it, "imp_ids"):
                if r not in imps:
                    self.err(w, f"imp_ids の {r} は影響にありません")
            for r in self.lst(it, "cmn_ids"):
                if r not in cmns:
                    self.err(w, f"cmn_ids の {r} は共通処理の判断にありません")
        nc = {n.get("id") for n in self.lst(d.get("meta") or {}, "not_covered")}
        new_req = {r for it in items if it.get("kind") == "new" for r in self.lst(it, "req_ids")}
        for r in sorted(set(reqs) - new_req - nc):
            self.err(rel, f"要件 {r} の確認方法(kind: new)がありません")
        reg_imp = {r for it in items if it.get("kind") == "regression" for r in self.lst(it, "imp_ids")}
        for i, imp in imps.items():
            if imp.get("severity") == "高" and i not in reg_imp and i not in nc:
                self.err(rel, f"重大度 高 の影響 {i} の回帰の確認(kind: regression)がありません")
        reg_cmn = {r for it in items if it.get("kind") == "regression" for r in self.lst(it, "cmn_ids")}
        for c in sorted(cmns - reg_cmn - nc):
            self.err(rel, f"共通処理 {c} の回帰の確認(kind: regression)がありません")
        self.check_asm_iss(rel, d, "p3c")

    # ---------- 点検と振り返り ----------
    def check_review(self, rel):
        d = self.load(rel)
        if d is None:
            return
        cp = Path(rel).stem.replace("_check", "")
        m = d.get("meta") or {}
        self.need(rel + " meta", m, ["run_id", "checkpoint", "agent", "attempt", "round", "verdict"])
        if m.get("checkpoint") != cp:
            self.err(rel, f"meta.checkpoint はファイル名と同じ {cp} です")
        self.enum(rel, m, "verdict", VERDICT)
        findings = self.lst(d, "findings")
        self.check_items_ids(rel, findings, rf"RVF-{re.escape(cp)}-\d{{3}}")
        open_heavy = open_minor = False
        for f in findings:
            w = f"{rel} {f.get('id')}"
            self.need(w, f, ["severity", "target_worker", "description", "status"])
            self.enum(w, f, "severity", FINDING_SEV)
            self.enum(w, f, "status", {"open", "fixed"})
            if f.get("status") == "open":
                open_heavy |= f.get("severity") in ("blocker", "major")
                open_minor |= f.get("severity") == "minor"
        if not isinstance(m.get("self_check"), list):
            self.err(rel, "meta.self_check がありません")
        if not self.lst(d, "spot_checks"):
            self.err(rel, "spot_checks(根拠を実際に開いて確かめた記録)がありません")
        aps = self.lst(d, "approval_points")
        needs_user = any(a.get("result") == "needs_user" for a in aps)
        if cp in PHASE_END:
            if [a.get("no") for a in aps][:PHASE_END[cp]] != list(range(1, PHASE_END[cp] + 1)):
                self.err(rel, f"approval_points に、承認の観点 1〜{PHASE_END[cp]} を番号どおりに書きます")
            for a in aps:
                self.enum(f"{rel} 観点{a.get('no')}", a, "result", {"ok", "needs_user", "ng"})
            if not d.get("summary"):
                self.err(rel, "フェーズの最後の点検には summary(承認資料の冒頭の要約)が必要です")
        for q in self.lst(d, "questions"):
            self.check_question(rel + " questions", q)
        expect = "fail" if open_heavy else ("pass_with_notes" if (open_minor or needs_user) else "pass")
        if m.get("verdict") in VERDICT and m.get("verdict") != expect:
            self.err(rel, f"判定が基準と合いません(指摘と観点からは {expect})")

    def check_retro(self, rel):
        d = self.load(rel)
        if d is None:
            return
        self.check_meta(rel, d, "retro", "impact-retrospective", "retro")
        obs = self.lst(d, "observations")
        self.check_items_ids(rel, obs, r"OBS-\d{3}")
        for o in obs:
            w = f"{rel} {o.get('id')}"
            self.need(w, o, ["kind", "description", "cause"])
            self.enum(w, o, "kind", OBS_KIND)
            self.enum(w, o, "cause", CAUSE)
        props = self.lst(d, "proposals")
        self.check_items_ids(rel, props, r"PRP-\d{3}")
        oid = {o.get("id") for o in obs}
        for p in props:
            w = f"{rel} {p.get('id')}"
            self.need(w, p, ["target_file", "for", "action", "text", "reason", "based_on", "decision"])
            self.enum(w, p, "target_file", PROPOSAL_TARGET)
            self.enum(w, p, "for", {"worker", "reviewer"})
            self.enum(w, p, "action", {"add", "rewrite", "retire"})
            self.enum(w, p, "decision", {"pending", "adopted", "rejected"})
            if p.get("action") in ("rewrite", "retire") and not p.get("existing_policy"):
                self.err(w, "rewrite / retire のときは existing_policy が必要です")
            for b in self.lst(p, "based_on"):
                if b not in oid:
                    self.err(w, f"based_on の {b} が observations にありません")

    def check_decisions(self):
        d = self.load("decisions.yaml", required=False)
        if not d:
            return
        for it in self.lst(d, "items"):
            w = f"decisions.yaml {it.get('id')}"
            if not re.fullmatch(r"DEC-\d{3}", str(it.get("id", ""))):
                self.err(w, "ID は DEC-001 の形です")
            self.need(w, it, ["phase", "about", "decision", "effect"])
            self.enum(w, it, "effect", {"confirm", "change"})
            for a in self.lst(it, "about"):
                # ID を持たない確認事項は、review/phase{N}_questions.yaml の source の形(unresolved:T-02 など)で書く
                if re.match(r"^(unresolved|out_of_scope|excluded|not_found|premise|plan|steps|review):", str(a)):
                    continue
                if a not in self.index:
                    self.err(w, f"about の {a} が見つかりません")

    # ---------- 振り分け ----------
    def check_file(self, rel):
        rel = Path(rel).as_posix()
        if rel.startswith(self.run.as_posix() + "/"):
            rel = rel[len(self.run.as_posix()) + 1:]
        table = [
            (r"^01_requirements/scope_resolution\.yaml$", self.check_scope_resolution),
            (r"^01_requirements/extract/S\d+\.yaml$", self.check_extract),
            (r"^01_requirements/requirements\.yaml$", self.check_requirements),
            (r"^02_impact/reuse\.yaml$", self.check_reuse),
            (r"^02_impact/changes/F-\d{2}\.yaml$", self.check_changes),
            (r"^02_impact/impacts\.yaml$", self.check_impacts),
            (r"^02_impact/common_components\.yaml$", self.check_common),
            (r"^02_impact/concerns\.yaml$", self.check_concerns),
            (r"^03_plan/plan\.yaml$", self.check_plan),
            (r"^03_plan/steps/F-\d{2}\.yaml$", self.check_steps),
            (r"^03_plan/verification\.yaml$", self.check_verification),
            (r"^review/[a-z0-9-]+_check\.yaml$", self.check_review),
            (r"^retrospective\.yaml$", self.check_retro),
            (r"^decisions\.yaml$", lambda _rel: self.check_decisions()),
        ]
        for pat, fn in table:
            if re.match(pat, rel):
                fn(rel)
                return
        self.err(rel, "点検の対象ではないファイル名です(docs/schemas/common.md の置き場所と名前を確認)")

    def check_unique_ids(self, files):
        seen = {}
        for f in files:
            d = self.load(f, False)
            if not isinstance(d, dict):
                continue
            for key in ("items", "changes", "features", "assumptions", "issues"):
                for it in self.lst(d, key):
                    i = it.get("id") if isinstance(it, dict) else None
                    if not i:
                        continue
                    if f.endswith("requirements.yaml") and key == "items":
                        continue   # requirements は extract の写し
                    if i in seen and seen[i] != f:
                        self.err(f, f"ID {i} が {seen[i]} と重複しています")
                    seen.setdefault(i, f)

    def check_scope_source(self):
        v = str(self.scope.get("source_root") or "").replace("\\", "/").rstrip("/")
        if not re.fullmatch(r"input/source/[^/]+", v):
            self.err("scope.yaml", f"source_root は input/source/{{フォルダ名}} の形で書きます(今: {v or '空'})。"
                                   f"ソースは input/source/ の下に置く決まりです")
        elif not (self.source_root and self.source_root.is_dir()):
            self.err("scope.yaml", f"ソースのフォルダがありません: {v}")

    def checkpoint(self, cp):
        self.build_index()
        self.check_scope_source()
        self.check_decisions()
        if cp == "p1-scope":
            self.check_scope_resolution("01_requirements/scope_resolution.yaml")
            sr = self.load("01_requirements/scope_resolution.yaml", False) or {}
            got = {s.get("instruction") for s in self.lst(sr, "items")} | \
                  {u.get("instruction") for u in self.lst(sr, "unresolved")}
            for t in self.lst(self.scope, "instructions"):
                if t.get("id") not in got:
                    self.err("scope_resolution.yaml", f"指示 {t.get('id')} に当たる範囲も、決められない理由もありません")
            covered_tags = {s.get("sheet_tag") for s in self.lst(sr, "items")} | \
                           {n.get("id") for n in self.lst(sr.get("meta") or {}, "not_covered")}
            for t in self.lst(self.scope, "sheet_tags"):
                if t.get("tag") not in covered_tags:
                    self.err("scope_resolution.yaml", f"シート {t.get('tag')}({t.get('sheet')})に範囲がありません"
                                                      f"(ない場合は meta.not_covered に理由)")
        elif cp == "p1":
            files = ["01_requirements/scope_resolution.yaml"] + self.files("01_requirements/extract/*.yaml") + \
                    ["01_requirements/requirements.yaml"]
            for f in files:
                self.check_file(f)
            sr = self.load("01_requirements/scope_resolution.yaml", False) or {}
            tags_with_scp = sorted({s.get("sheet_tag") for s in self.lst(sr, "items")})
            for t in tags_with_scp:
                if f"01_requirements/extract/{t}.yaml" not in files:
                    self.err("01_requirements/extract", f"シート {t} の抽出結果がありません")
            used = set()
            for f in self.files("01_requirements/extract/*.yaml"):
                d = self.load(f, False) or {}
                for it in self.lst(d, "items"):
                    used |= set(self.lst(it, "scp_ids"))
                for e in self.lst(d, "excluded"):
                    m = SHEET_REF.match(str(e.get("source", "")))
                    if m and m.group(3):
                        for s in self.lst(sr, "items"):
                            if int(m.group(3)) in self.lst(s, "rows"):
                                used.add(s.get("id"))
                used |= {n.get("id") for n in self.lst(d.get("meta") or {}, "not_covered")}
            for s in self.lst(sr, "items"):
                if s.get("id") not in used:
                    self.err("01_requirements/extract", f"範囲 {s.get('id')} から要件も除外の記録も作られていません")
            self.check_unique_ids(files)
        elif cp == "p2-changes":
            files = (["02_impact/reuse.yaml"] if (self.run / "02_impact/reuse.yaml").exists() else []) + \
                    self.files("02_impact/changes/*.yaml")
            for f in files:
                self.check_file(f)
            reqs, feats = self.req_items(), self.features()
            ru = self.load("02_impact/reuse.yaml", False) or {}
            handled = {r for it in self.lst(ru, "items") for r in self.lst(it, "req_ids")} | \
                      {n.get("req_id") for n in self.lst(ru, "not_found")} | \
                      {n.get("id") for n in self.lst(ru.get("meta") or {}, "not_covered")}
            for r, it in reqs.items():
                if it.get("category") == "reuse" and r not in handled:
                    self.err("02_impact/reuse.yaml", f"流用の要件 {r} の流用先がありません(見つからなければ not_found)")
            if any(it.get("category") == "reuse" for it in reqs.values()) and not ru:
                self.err("02_impact/reuse.yaml", "流用の要件があるのに reuse.yaml がありません")
            for fid, f in feats.items():
                non_reuse = [r for r in self.lst(f, "req_ids") if reqs.get(r, {}).get("category") != "reuse"]
                path = f"02_impact/changes/{fid}.yaml"
                if non_reuse and path not in files:
                    self.err(path, f"機能 {fid} の修正箇所のファイルがありません")
                    continue
                d = self.load(path, False) or {}
                done = {r for it in self.lst(d, "items") for r in self.lst(it, "req_ids")} | \
                       {p.get("req_id") for p in self.lst(d, "premise_broken")} | \
                       {n.get("id") for n in self.lst(d.get("meta") or {}, "not_covered")}
                for r in non_reuse:
                    if r not in done:
                        self.err(path, f"要件 {r} の修正箇所がありません(当てはめられなければ premise_broken)")
            self.check_cycles()
            self.check_unique_ids(files)
        elif cp == "p2":
            self.checkpoint_inner_p2()
        elif cp == "p3":
            files = ["03_plan/plan.yaml"] + self.files("03_plan/steps/*.yaml") + ["03_plan/verification.yaml"]
            for f in files:
                self.check_file(f)
            plan = self.load("03_plan/plan.yaml", False) or {}
            for o in self.lst(plan, "order"):
                p = f"03_plan/steps/{o.get('feature')}.yaml"
                if p not in files:
                    self.err(p, f"機能 {o.get('feature')} の手順のファイルがありません")
            self.check_unique_ids(files)
        elif cp == "retro":
            self.check_file("retrospective.yaml")
        # 点検結果のファイル(あれば)
        for f in self.files(f"review/{cp}_check.yaml"):
            self.check_review(f)

    def checkpoint_inner_p2(self):
        files = ["02_impact/impacts.yaml", "02_impact/common_components.yaml", "02_impact/concerns.yaml"]
        for f in files:
            self.check_file(f)
        self.checkpoint("p2-changes")
        cm = self.load("02_impact/common_components.yaml", False) or {}
        in_cmn = {c for it in self.lst(cm, "items") for c in self.lst(it, "chg_ids")}
        for cid, ch in self.all_changes().items():
            if ch.get("shared") and cid not in in_cmn:
                self.err("02_impact/common_components.yaml", f"共通処理への修正 {cid} の判断(CMN)がありません")
        self.check_unique_ids(files + self.files("02_impact/changes/*.yaml") +
                              (["02_impact/reuse.yaml"] if (self.run / "02_impact/reuse.yaml").exists() else []))

    def check_cycles(self):
        graph = {k: self.lst(v, "depends_on") for k, v in self.all_changes().items()}
        for k, deps in graph.items():
            for dep in deps:
                if dep not in graph:
                    self.err("02_impact", f"{k} の depends_on {dep} は修正にありません")
        state = {}

        def visit(n, path):
            if state.get(n) == 1:
                self.err("02_impact", "depends_on が循環しています: " + " → ".join(path + [n]))
                return
            if state.get(n) == 2:
                return
            state[n] = 1
            for m in graph.get(n, []):
                if m in graph:
                    visit(m, path + [n])
            state[n] = 2

        for n in sorted(graph):
            visit(n, [])


def main():
    ap = argparse.ArgumentParser(description="成果物を機械的に点検する")
    ap.add_argument("run_dir")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--file")
    g.add_argument("--checkpoint", choices=CHECKPOINTS)
    a = ap.parse_args()
    c = Checker(a.run_dir)
    if a.file:
        c.build_index()
        c.check_file(a.file)
    else:
        c.checkpoint(a.checkpoint)
    for line in dict.fromkeys(c.errors + c.warnings):
        print(line)
    print(f"\n結果: エラー {len(set(c.errors))} 件 / 警告 {len(set(c.warnings))} 件")
    sys.exit(1 if c.errors else 0)


if __name__ == "__main__":
    main()
