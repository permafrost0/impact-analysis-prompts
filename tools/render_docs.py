#!/usr/bin/env python3
"""YAML の成果物から、人が読む資料(承認資料)を作る。

使い方:
    python tools/render_docs.py <調査フォルダ> --phase 1 | 2 | 3 | retro

作るもの:
    --phase 1      01_requirements/requirements.md       (フェーズ1の承認資料)
    --phase 2      02_impact/impact_report.md            (フェーズ2の承認資料 = 影響調査報告書)
    --phase 3      03_plan/implementation_plan.md        (フェーズ3の承認資料 = 実装計画書)
    --phase retro  retrospective.md                      (振り返りの資料)
    あわせて review/phase{N}_questions.yaml(確認事項の Q 番号と、元の項目の対応)を作る。

資料の構成: 抽出した内容(機能ごと)→ 確認事項(Q番号)→ 付録。
コードの抜粋は、YAML の excerpt(file / start / end)をもとに、実際のソースから切り出して差し込む。
ソースと設計書は読むだけで、書き込むのは上の資料だけ。同じ入力からは常に同じ資料になる。
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

CATEGORY = {"new": "新規", "change": "変更", "delete": "削除", "reuse": "既存の流用", "mixed": "混在"}
ACTION = {"new": "新規", "modify": "修正", "delete": "削除"}
APPROACH = {"delete": "既存の削除", "reuse": "既存の流用", "follow_existing": "既存を手本に追加",
            "modify_existing": "既存の変更", "new_mechanism": "新しい仕組み", "shared_or_high_risk": "共通処理の変更・影響大"}
MATCH = {"exact": "完全一致", "normalized": "表記ゆれを除いて一致", "partial": "部分一致", "marker": "書式の目印",
         "whole_sheet": "シート全体", "text": "識別文字列", "rows": "行範囲", "inferred": "推定"}
EXCLUDED = {"ambiguous": "判断に困る表現", "existing_description": "既存の説明", "note_only": "注記のみ"}
FIT = {"as_is": "そのまま使える", "partial": "一部合わない", "not_fit": "使えない"}
DECISION = {"global": "全体修正", "partial": "部分修正"}
METHOD = {"new_method": "新メソッドを追加", "overload": "引数違いのメソッドを追加", "parameter": "引数を追加",
          "subclass": "派生クラスを作る", "new_component": "専用の部品を作る"}
VERDICT = {"pass": "合格", "pass_with_notes": "条件付き合格", "fail": "不合格"}
FSEV = {"blocker": "重大", "major": "要修正", "minor": "軽微"}
POINT = {"ok": "問題なし", "needs_user": "要確認", "ng": "問題あり"}
KIND_TC = {"new": "新規", "regression": "回帰"}
NB = {"yes": "必要", "no": "不要", "unknown": "不明", True: "必要", False: "不要"}
LANG = {".java": "java", ".xml": "xml", ".html": "html", ".js": "javascript", ".ts": "typescript", ".sql": "sql",
        ".properties": "properties", ".yml": "yaml", ".yaml": "yaml", ".jsp": "jsp", ".kt": "kotlin", ".css": "css",
        ".py": "python", ".json": "json", ".gradle": "groovy"}
CHECKPOINT_NAME = {"p1-scope": "途中の点検(範囲の特定後)", "p1": "フェーズ末の点検",
                   "p2-changes": "途中の点検(修正箇所の特定後)", "p2": "フェーズ末の点検", "p3": "フェーズ末の点検"}


def esc(v):
    if v is None:
        return ""
    if isinstance(v, list):
        return "<br>".join(esc(x) for x in v)
    return str(v).replace("|", "\\|").replace("\n", "<br>")


def table(header, rows):
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join(esc(c) for c in r) + " |" for r in rows]
    return out


class Doc:
    def __init__(self, run):
        self.run = Path(run)
        self.cache = {}
        self.scope = self.load("scope.yaml") or {}
        root = self.scope.get("source_root")
        self.source_root = Path(str(root)) if root else None
        self.decisions = self.lst(self.load("decisions.yaml"), "items")
        self.questions = []          # [{q, source, feature, text, examples, answered}]
        self.qmap = {}               # 項目 ID → [Q番号]

    def load(self, rel):
        if rel not in self.cache:
            p = self.run / rel
            self.cache[rel] = yaml.safe_load(p.read_text(encoding="utf-8-sig")) if p.exists() else None
        return self.cache[rel]

    def files(self, pattern):
        return sorted(p.relative_to(self.run).as_posix() for p in self.run.glob(pattern))

    @staticmethod
    def lst(d, key):
        v = (d or {}).get(key)
        return v if isinstance(v, list) else []

    # ---------- 表示の整形 ----------
    @staticmethod
    def where(ref):
        if ref in (None, ""):
            return ""
        s = str(ref)
        m = re.match(r"^sheet:([^/]+)/(.+)#(.+)$", s)
        if m:
            return f"{m.group(2)} {m.group(3).replace('-', '〜')}"
        m = re.match(r"^heading:([^/]+)/(.+)#(.+)$", s)
        if m:
            return f"{m.group(1)} / {m.group(2)} {m.group(3)}(見出し)"
        m = re.match(r"^code:(.+?):(\d+(?:-\d+)?)$", s)
        if m:
            return f"`{Path(m.group(1)).name}:{m.group(2)}`"
        return s

    def wheres(self, refs):
        return "<br>".join(self.where(r) for r in (refs or []))

    def excerpt(self, ex, title=None):
        if not isinstance(ex, dict) or not ex.get("file"):
            return []
        try:
            a, b = int(ex["start"]), int(ex["end"])
        except (KeyError, TypeError, ValueError):
            return []
        head = f"`{ex['file']}` {a}〜{b} 行目(今のコード)" if not title else title
        if not self.source_root:
            return [f"{head}: (ソースのルートが分からないため抜粋できません)", ""]
        p = self.source_root / ex["file"]
        try:
            p.resolve().relative_to(self.source_root.resolve())
            raw = p.read_bytes()
        except (ValueError, OSError):
            return [f"{head}: (ファイルが見つからないため抜粋できません)", ""]
        for enc in ("utf-8-sig", "cp932"):
            try:
                text = raw.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        else:
            text = raw.decode("utf-8", errors="replace")
        lines = text.splitlines()[a - 1:min(b, a + 39)]
        width = len(str(a + len(lines)))
        body = [f"{str(a + i).rjust(width)}: {line}" for i, line in enumerate(lines)]
        return [head, "", f"```{LANG.get(p.suffix.lower(), '')}"] + body + ["```", ""]

    # ---------- 確認事項 ----------
    def answered(self, key):
        for d in self.decisions:
            if key in (d.get("about") or []):
                return d
        return None

    def add_q(self, key, q, feature="", marks=()):
        if not isinstance(q, dict) or not q.get("text"):
            return
        dec = self.answered(key)
        entry = {"source": key, "feature": feature or "", "text": q.get("text"),
                 "examples": q.get("answer_examples") or [], "decision": dec}
        self.questions.append(entry)
        entry["marks"] = [key, *marks]

    def number_questions(self, phase):
        n = 0
        for e in self.questions:
            if e["decision"] is None:
                n += 1
                e["q"] = f"Q{n}"
            else:
                e["q"] = f"済{e['decision'].get('id', '')}"
            for m in e["marks"]:
                self.qmap.setdefault(m, []).append(e["q"])
        data = {"phase": phase, "questions": [
            {"q": e["q"], "source": e["source"], "feature": e["feature"], "text": e["text"],
             "answered_by": (e["decision"] or {}).get("id")} for e in self.questions]}
        out = self.run / "review" / f"phase{phase}_questions.yaml"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=1000), encoding="utf-8")

    def qref(self, *keys):
        qs = []
        for k in keys:
            for q in self.qmap.get(k, []):
                if q.startswith("Q") and q not in qs:
                    qs.append(q)
        return ", ".join(sorted(qs, key=lambda x: int(x[1:])))

    def feature_map(self):
        """項目 ID → 機能 ID の対応(確認事項の「機能」欄に使う)"""
        if hasattr(self, "_fmap"):
            return self._fmap
        fm = {}
        rq = self.load("01_requirements/requirements.yaml") or {}
        for it in self.lst(rq, "items"):
            fm[it.get("id")] = [it.get("feature")]
        for f in self.files("02_impact/changes/*.yaml"):
            d = self.load(f) or {}
            for it in self.lst(d, "items"):
                fm[it.get("id")] = [d.get("feature")]
        ru = self.load("02_impact/reuse.yaml") or {}
        for it in self.lst(ru, "items"):
            fm[it.get("id")] = [it.get("feature")]
        for it in self.lst(ru, "changes"):
            fm[it.get("id")] = sorted({x for r in it.get("req_ids") or [] for x in fm.get(r, [])})
        for name in ("impacts", "concerns", "common_components"):
            for it in self.lst(self.load(f"02_impact/{name}.yaml"), "items"):
                fm[it.get("id")] = [it.get("feature")] if it.get("feature") else list(it.get("features") or [])
        self._fmap = fm
        return fm

    def features_of(self, ids):
        fm = self.feature_map()
        return ", ".join(sorted({f for i in ids or [] for f in fm.get(i, []) if f}))

    def collect_asm_iss(self, files):
        asm, iss = [], []
        for f in files:
            d = self.load(f) or {}
            for a in self.lst(d, "assumptions"):
                asm.append(a)
                if a.get("ask_user"):
                    self.add_q(a.get("id"), a.get("question"), self.features_of(a.get("affects")),
                               marks=a.get("affects") or [])
            for i in self.lst(d, "issues"):
                iss.append(i)
                if i.get("ask_user"):
                    self.add_q(i.get("id"), i.get("question"), self.features_of(i.get("related_ids")),
                               marks=i.get("related_ids") or [])
        return asm, iss

    def review_questions(self, checkpoints):
        for cp in checkpoints:
            d = self.load(f"review/{cp}_check.yaml") or {}
            for i, q in enumerate(self.lst(d, "questions"), 1):
                self.add_q(f"review:{cp}:{i}", q, feature=", ".join(q.get("about") or []) if isinstance(q, dict) else "",
                           marks=q.get("about") or [] if isinstance(q, dict) else [])

    def questions_section(self):
        pending = [e for e in self.questions if e["q"].startswith("Q")]
        done = [e for e in self.questions if not e["q"].startswith("Q")]
        out = ["## 2. 確認事項", ""]
        if pending:
            out += ["番号を付けて答えてください(例:「Q1: はい / Q2: ハイフンあり」)。"
                    "**回答しなかった確認事項は、この資料に書かれている内容のまま確定します。**", ""]
            out += table(["No", "機能", "内容", "回答例"],
                         [[e["q"], e["feature"] or "-", e["text"], " / ".join(f"「{x}」" for x in e["examples"])]
                          for e in pending])
        else:
            out += ["確認事項はありません。内容に問題がなければ「承認」と答えてください。"]
        if done:
            out += ["", "### 回答済みの確認事項", ""]
            out += table(["判断", "内容", "決まったこと"],
                         [[e["decision"].get("id"), e["text"], e["decision"].get("decision")] for e in done])
        return out + [""]

    def review_appendix(self, checkpoints):
        out = ["### レビュー担当の点検", ""]
        rows, findings, points = [], [], []
        for cp in checkpoints:
            d = self.load(f"review/{cp}_check.yaml")
            if not d:
                continue
            m = d.get("meta") or {}
            fs = self.lst(d, "findings")
            rows.append([CHECKPOINT_NAME.get(cp, cp), VERDICT.get(m.get("verdict"), m.get("verdict")),
                         f"{len(fs)} 件(未対応 {sum(1 for f in fs if f.get('status') == 'open')} 件)",
                         f"{len(self.lst(d, 'spot_checks'))} 件"])
            findings += [[f.get("id"), FSEV.get(f.get("severity"), f.get("severity")), f.get("description"),
                          "対応済み" if f.get("status") == "fixed" else "未対応"] for f in fs]
            points += [[a.get("no"), a.get("point"), POINT.get(a.get("result"), a.get("result")), a.get("note")]
                       for a in self.lst(d, "approval_points")]
        if not rows:
            return out + ["(点検の結果はまだありません)", ""]
        out += table(["点検", "判定", "指摘", "根拠を開いて確かめた数"], rows) + [""]
        if points:
            out += ["**承認の観点**", ""] + table(["No", "観点", "結果", "メモ"], points) + [""]
        if findings:
            out += ["**指摘**", ""] + table(["ID", "重さ", "内容", "状態"], findings) + [""]
        return out

    def asm_iss_appendix(self, asm, iss):
        out = []
        if asm:
            out += ["### 仮定の一覧", ""] + table(
                ["ID", "仮定", "理由", "関係する項目", "確認"],
                [[a.get("id"), a.get("statement"), a.get("reason"), ", ".join(a.get("affects") or []),
                  self.qref(a.get("id")) or "-"] for a in asm]) + [""]
        if iss:
            out += ["### 課題の一覧", ""] + table(
                ["ID", "内容", "関係する項目", "確認"],
                [[i.get("id"), i.get("description"), ", ".join(i.get("related_ids") or []),
                  self.qref(i.get("id")) or "-"] for i in iss]) + [""]
        return out

    def header(self, title, phase_label, extra=None):
        s = self.scope
        out = [f"# {title}", "",
               f"> 調査: {s.get('title', '')}({s.get('run_id', '')})/ {phase_label}",
               "> この資料は YAML から自動で作られています。直したい点は、オーケストレータに伝えてください。"]
        if extra:
            out += [f"> {extra}"]
        return out + [""]

    def summary(self, cp):
        d = self.load(f"review/{cp}_check.yaml") or {}
        s = d.get("summary")
        return ["## はじめに", "", s.strip(), ""] if s else []

    # ---------- フェーズ1 ----------
    def render_phase1(self):
        rq = self.load("01_requirements/requirements.yaml") or {}
        sr = self.load("01_requirements/scope_resolution.yaml") or {}
        feats, items = self.lst(rq, "features"), {i.get("id"): i for i in self.lst(rq, "items")}
        files = ["01_requirements/scope_resolution.yaml"] + self.files("01_requirements/extract/*.yaml") + \
                ["01_requirements/requirements.yaml"]
        # 確認事項を集める(順番: 範囲 → 要件 → 除外 → 仮定・課題 → レビュー担当)
        for u in self.lst(sr, "unresolved"):
            self.add_q(f"unresolved:{u.get('instruction')}", u.get("question"))
        for o in self.lst(sr, "out_of_scope_refs"):
            self.add_q(f"out_of_scope:{o.get('from')}", o.get("question"))
        for f in feats:
            for r in self.lst(f, "req_ids"):
                it = items.get(r) or {}
                if it.get("question"):
                    self.add_q(r, it["question"], feature=f.get("id"))
        for e in self.lst(rq, "excluded"):
            if e.get("question"):
                self.add_q(f"excluded:{e.get('source')}", e["question"], feature=e.get("feature") or "")
        asm, iss = self.collect_asm_iss(files)
        self.review_questions(["p1-scope", "p1"])
        self.number_questions(1)

        sheets = ", ".join(f"{t.get('sheet')}({t.get('file')})" for t in self.lst(self.scope, "sheet_tags"))
        out = self.header("要件の一覧(フェーズ1 承認資料)", "フェーズ1 要件の抽出", f"読んだシート: {sheets}")
        out += self.summary("p1")
        out += ["## 1. 抽出した要件(機能ごと)", "", "### 機能の一覧", ""]
        out += table(["機能", "区分", "要件の数", "確認事項"],
                     [[f"[{f.get('id')} {f.get('name')}](#{f.get('id', '').lower()})", CATEGORY.get(f.get("category"), ""),
                       len(self.lst(f, "req_ids")),
                       self.qref(*self.lst(f, "req_ids"), *[f"excluded:{e.get('source')}" for e in self.lst(rq, "excluded")
                                                            if e.get("feature") == f.get("id")]) or "-"] for f in feats])
        out += [""]
        for f in feats:
            out += [f"### {f.get('id')}", "", f"**{f.get('name')}**({CATEGORY.get(f.get('category'), '')})", "",
                    f.get("summary", ""), ""]
            rows = []
            for r in self.lst(f, "req_ids"):
                it = items.get(r) or {}
                vals = " / ".join(f"{k}: {v}" for k, v in (it.get("values") or {}).items())
                content = it.get("title", "")
                if it.get("summary"):
                    content += f"<br>{it['summary']}"
                if it.get("category") == "reuse" and it.get("reuse"):
                    ru = it["reuse"]
                    content += f"<br>原文「{ru.get('quote', '')}」<br>手がかり: {', '.join(ru.get('clues') or [])}"
                rows.append([r, CATEGORY.get(it.get("category"), ""), content, vals, self.wheres(it.get("source")),
                             self.qref(r) or "-"])
            out += table(["要件", "区分", "内容", "主な値", "設計書の箇所", "確認"], rows) + [""]
        if self.lst(rq, "excluded"):
            out += ["### 要件にしなかった記述", ""]
            out += table(["設計書の箇所", "記述", "理由", "関係する機能", "確認"],
                         [[self.where(e.get("source")), e.get("quote"), EXCLUDED.get(e.get("reason"), e.get("reason")),
                           e.get("feature") or "-",
                           self.qref(f"excluded:{e.get('source')}") or "-"] for e in self.lst(rq, "excluded")]) + [""]
        out += ["### 範囲の特定(指示 → 設計書の行)", ""]
        instr = {t.get("id"): t for t in self.lst(self.scope, "instructions")}
        tags = {t.get("tag"): t for t in self.lst(self.scope, "sheet_tags")}
        rows = []
        for s in self.lst(sr, "items"):
            t = instr.get(s.get("instruction"), {})
            tg = tags.get(s.get("sheet_tag"), {})
            rows.append([s.get("instruction"), t.get("user_words", ""), tg.get("sheet", s.get("sheet_tag")),
                         ", ".join(f"L{r}" for r in s.get("rows") or []) +
                         (f"<br>図形 {', '.join(map(str, s.get('shapes')))}" if s.get("shapes") else ""),
                         MATCH.get(s.get("match"), s.get("match")), s.get("confidence"), s.get("note", "")])
        for u in self.lst(sr, "unresolved"):
            rows.append([u.get("instruction"), instr.get(u.get("instruction"), {}).get("user_words", ""), "-",
                         "(決められない)", "-", "-", f"{u.get('reason')} {self.qref('unresolved:' + str(u.get('instruction')))}"])
        out += table(["指示", "ユーザーの指示", "シート", "対象の行", "一致", "確信度", "メモ"], rows) + [""]
        if self.lst(sr, "out_of_scope_refs"):
            out += ["**指示されていないシートへの参照**", ""]
            out += table(["参照元", "記述", "確認"],
                         [[self.where(o.get("from")), o.get("quote"), self.qref(f"out_of_scope:{o.get('from')}") or "-"]
                          for o in self.lst(sr, "out_of_scope_refs")]) + [""]
        out += ["### 参照先の設計書(既存)の扱い", ""]
        if self.lst(rq, "reference_reads"):
            out += table(["ファイル", "読んだ見出し", "目的"],
                         [[r.get("file"), r.get("found"), r.get("purpose")] for r in self.lst(rq, "reference_reads")])
            out += ["", "読んだのは見出しの一覧だけで、本文は読んでいません。"]
        else:
            out += ["参照先の設計書は読んでいません。"]
        out += [""]
        if self.lst(rq, "cross_refs"):
            out += ["### 対応する相手が対象範囲にない関係", ""]
            out += table(["要件", "内容"], [[c.get("from"), c.get("note")] for c in self.lst(rq, "cross_refs")]) + [""]
        out += self.questions_section()
        out += ["## 付録", ""] + self.review_appendix(["p1-scope", "p1"]) + self.asm_iss_appendix(asm, iss)
        out += ["### 正本のファイル", "", "- 01_requirements/requirements.yaml(要件と機能)",
                "- 01_requirements/scope_resolution.yaml(範囲の特定)", "- 01_requirements/extract/(シートごとの抽出結果)", ""]
        return "01_requirements/requirements.md", out

    # ---------- フェーズ2 ----------
    def render_phase2(self):
        rq = self.load("01_requirements/requirements.yaml") or {}
        feats = self.lst(rq, "features")
        reqs = {i.get("id"): i for i in self.lst(rq, "items")}
        ru = self.load("02_impact/reuse.yaml") or {}
        imp = self.load("02_impact/impacts.yaml") or {}
        cm = self.load("02_impact/common_components.yaml") or {}
        co = self.load("02_impact/concerns.yaml") or {}
        changes = {f.get("id"): self.load(f"02_impact/changes/{f.get('id')}.yaml") or {} for f in feats}
        reuse_chg = self.lst(ru, "changes")

        def feature_of_change(c):
            for r in c.get("req_ids") or []:
                if r in reqs:
                    return reqs[r].get("feature")
            return None

        cmn_of_chg = {c: m.get("id") for m in self.lst(cm, "items") for c in m.get("chg_ids") or []}
        files = (["02_impact/reuse.yaml"] if ru else []) + [f"02_impact/changes/{f.get('id')}.yaml" for f in feats] + \
                ["02_impact/impacts.yaml", "02_impact/common_components.yaml", "02_impact/concerns.yaml"]
        # 確認事項
        for f in feats:
            fid = f.get("id")
            for n in self.lst(ru, "not_found"):
                if reqs.get(n.get("req_id"), {}).get("feature") == fid:
                    self.add_q(f"not_found:{n.get('req_id')}", n.get("question"), fid, [n.get("req_id")])
            for p in self.lst(changes[fid], "premise_broken"):
                self.add_q(f"premise:{p.get('req_id')}", p.get("question"), fid, [p.get("req_id")])
            for m in self.lst(cm, "items"):
                if (m.get("features") or [None])[0] == fid:
                    self.add_q(m.get("id"), m.get("question"), ", ".join(m.get("features") or []), m.get("chg_ids") or [])
            for c in self.lst(co, "items"):
                if (c.get("features") or [None])[0] == fid and c.get("question"):
                    self.add_q(c.get("id"), c.get("question"), ", ".join(c.get("features") or []))
        asm, iss = self.collect_asm_iss([f for f in files if (self.run / f).exists()])
        self.review_questions(["p2-changes", "p2"])
        self.number_questions(2)

        def sev_count(items):
            c = {"高": 0, "中": 0, "低": 0}
            for x in items:
                c[x.get("severity")] = c.get(x.get("severity"), 0) + 1
            return " / ".join(f"{k} {v}" for k, v in c.items() if v) or "なし"

        out = self.header("影響調査報告書(フェーズ2 承認資料)", "フェーズ2 懸念事項の抽出",
                          "根拠はすべてソースコードです。コードの抜粋は、実際のソースから切り出しています。")
        out += self.summary("p2")
        out += ["## 1. 抽出した内容(機能ごと)", "", "### 機能の一覧", ""]
        rows = []
        for f in feats:
            fid = f.get("id")
            chs = self.lst(changes[fid], "items") + [c for c in reuse_chg if feature_of_change(c) == fid]
            imps = [i for i in self.lst(imp, "items") if i.get("feature") == fid]
            cons = [c for c in self.lst(co, "items") if fid in (c.get("features") or [])]
            nshared = sum(1 for c in chs if c.get("shared"))
            keys = [c.get("id") for c in chs] + [i.get("id") for i in imps] + [c.get("id") for c in cons] + \
                   self.lst(f, "req_ids")
            rows.append([f"[{fid} {f.get('name')}](#{fid.lower()})",
                         f"{len(chs)}" + (f"(うち共通処理 {nshared})" if nshared else ""),
                         sev_count(imps), sev_count(cons), self.qref(*keys) or "-"])
        out += table(["機能", "修正箇所", "既存機能への影響", "懸念", "確認事項"], rows) + [""]

        for f in feats:
            fid = f.get("id")
            ch = changes[fid]
            chs = self.lst(ch, "items") + [c for c in reuse_chg if feature_of_change(c) == fid]
            out += ["---", "", f"### {fid}", "", f"**{f.get('name')}**", "", f.get("summary", ""), ""]
            out += ["#### (1) 今の処理の流れ(コードから)", ""]
            if self.lst(ch, "flow"):
                out += table(["順", "場所", "対象", "今の振る舞い"],
                             [[x.get("order"), self.where(x.get("location")), x.get("symbol"), x.get("behavior")]
                              for x in self.lst(ch, "flow")]) + [""]
            elif not ch:
                out += ["(この機能は既存の流用だけです。流用先の振る舞いは (3) を見てください)", ""]
            else:
                out += ["(処理の流れが記録されていません)", ""]
            out += ["#### (2) 修正箇所", ""]
            if not chs:
                out += ["(修正箇所はありません)", ""]
            for c in chs:
                tag = " 〔共通処理〕" if c.get("shared") else ""
                q = self.qref(c.get("id"), cmn_of_chg.get(c.get("id"), ""))
                out += [f"**{c.get('id')} `{c.get('file')}`({ACTION.get(c.get('action'), '')}){tag}**"
                        + (f" → {q}" if q else ""), ""]
                rows = [["対象", c.get("symbol")], ["場所", self.where(c.get("location")) or "(新しく作る)"],
                        ["今の振る舞い", c.get("before")], ["変更後", c.get("after")]]
                if c.get("detail"):
                    rows.append(["指示", c.get("detail")])
                rows.append(["理由(要件)", ", ".join(c.get("req_ids") or [])])
                if c.get("shared"):
                    rows.append(["共通処理である理由", c.get("shared_reason")])
                if c.get("reference"):
                    rows.append(["手本にする既存実装", self.wheres(c.get("reference"))])
                if c.get("depends_on"):
                    rows.append(["先に必要な修正", ", ".join(c.get("depends_on"))])
                out += table(["項目", "内容"], rows) + [""]
                out += self.excerpt(c.get("excerpt"))
            rus = [x for x in self.lst(ru, "items") if x.get("feature") == fid]
            out += ["#### (3) 流用する既存処理", ""]
            if not (rus or any(reqs.get(r, {}).get("category") == "reuse" for r in self.lst(f, "req_ids"))):
                out += ["(この機能に、既存の流用の要件はありません)", ""]
            else:
                for x in rus:
                    out += [f"**{x.get('id')} {x.get('target')}**", ""]
                    out += table(["項目", "内容"], [
                        ["流用先", self.where(x.get("location"))], ["要件", ", ".join(x.get("req_ids") or [])],
                        ["今の振る舞い", x.get("behavior")], ["そのまま使えるか", FIT.get(x.get("fit"), x.get("fit"))],
                        ["流用のしかた", x.get("how_to_reuse")], ["合わない点", x.get("gap") or "-"],
                        ["探した言葉", ", ".join(x.get("searched") or [])]]) + [""]
                    out += self.excerpt(x.get("excerpt"))
                for n in self.lst(ru, "not_found"):
                    if reqs.get(n.get("req_id"), {}).get("feature") == fid:
                        out += [f"- {n.get('req_id')}: 流用先が見つかりません(探した言葉: {', '.join(n.get('searched') or [])})"
                                f" → {self.qref('not_found:' + str(n.get('req_id')))}", ""]
            imps = [i for i in self.lst(imp, "items") if i.get("feature") == fid]
            out += ["#### (4) 既存機能への影響", ""]
            if not imps:
                out += ["(既存機能への影響は見つかりませんでした。調べた範囲は (6) を見てください)", ""]
            for i in sorted(imps, key=lambda x: "高中低".find(x.get("severity", "低"))):
                q = self.qref(i.get("id"))
                out += [f"**{i.get('id')} {i.get('affected')}(重大度: {i.get('severity')})**" + (f" → {q}" if q else ""), ""]
                out += table(["項目", "内容"], [
                    ["原因の修正", ", ".join(i.get("chg_ids") or [])], ["場所", self.where(i.get("location"))],
                    ["今の使われ方", i.get("current_use")], ["起こりうること", i.get("risk")],
                    ["今回の扱い", i.get("handling") or "-"], ["確認の観点", i.get("test_points") or []]]) + [""]
                out += self.excerpt(i.get("excerpt"))
            cons = [c for c in self.lst(co, "items") if fid in (c.get("features") or [])]
            out += ["#### (5) 実装上の懸念", ""]
            if not cons:
                out += ["(懸念は見つかりませんでした)", ""]
            for c in sorted(cons, key=lambda x: "高中低".find(x.get("severity", "低"))):
                q = self.qref(c.get("id"))
                other = [x for x in c.get("features") or [] if x != fid]
                out += [f"**{c.get('id')} {c.get('title')}(重要度: {c.get('severity')})**" + (f" → {q}" if q else ""), ""]
                rows = [["内容", c.get("description")], ["コードの根拠", self.where(c.get("location")) or "-"],
                        ["推奨する対応", c.get("recommendation")]]
                if other:
                    rows.append(["ほかに関係する機能", ", ".join(other)])
                out += table(["項目", "内容"], rows) + [""]
                out += self.excerpt(c.get("excerpt"))
            my_chg = {c.get("id") for c in chs}
            logs = [s for s in self.lst(imp, "search_log") + self.lst(cm, "search_log") if s.get("chg_id") in my_chg]
            out += ["#### (6) 調べた範囲", ""]
            out += (table(["修正", "調べたこと", "結果"],
                          [[s.get("chg_id"), s.get("searched") or [],
                            {"impact": "影響あり", "none": "影響なし", "shared": "他の機能からも使われている",
                             "not_shared": "この機能だけで使われている"}.get(s.get("result"), s.get("result"))]
                           for s in logs]) if logs else ["(記録なし)"]) + [""]

        out += ["---", "", "### 機能をまたぐ事項", ""]
        cmns = self.lst(cm, "items")
        if not cmns:
            out += ["共通処理への修正はありません。", ""]
        for m in cmns:
            q = self.qref(m.get("id"))
            how = DECISION.get(m.get("decision"), "") + (f"({METHOD.get(m.get('method'), m.get('method'))})"
                                                         if m.get("decision") == "partial" else "")
            out += [f"**{m.get('id')} 共通処理 {m.get('component')}**(関係する機能: {', '.join(m.get('features') or [])})"
                    + (f" → {q}" if q else ""), ""]
            out += table(["呼び出し元", "機能", "今回の対象か", "使われ方", "新しい振る舞いが必要か"],
                         [[self.where(c.get("location")), c.get("feature_name"), "対象" if c.get("is_target") else "対象外",
                           c.get("usage"), NB.get(c.get("needs_new_behavior"), c.get("needs_new_behavior"))]
                          for c in self.lst(m, "callers")]) + [""]
            rows = [["判断", how], ["理由", m.get("rationale")], ["全体修正した場合", m.get("if_global")],
                    ["関係する修正", ", ".join(m.get("chg_ids") or [])]]
            if m.get("precedent"):
                rows.append(["同様の先例", self.where(m.get("precedent"))])
            if m.get("conflicts_with_chg"):
                rows.append(["修正箇所との食い違い", "あり(修正箇所の内容と、この判断が食い違っています)"])
            out += table(["項目", "内容"], rows) + [""]
            out += self.excerpt(m.get("excerpt"))
        multi = [c for c in self.lst(co, "items") if len(c.get("features") or []) > 1]
        if multi:
            out += ["**複数の機能にかかわる懸念**", ""]
            out += table(["懸念", "重要度", "機能", "内容"],
                         [[c.get("id"), c.get("severity"), ", ".join(c.get("features")), c.get("title")] for c in multi]) + [""]

        out += self.questions_section()
        out += ["## 付録", "", "### 回帰テストの観点", ""]
        tps = [[i.get("id"), i.get("affected"), i.get("severity"), i.get("test_points") or []]
               for i in self.lst(imp, "items") if i.get("test_points")]
        out += (table(["影響", "機能", "重大度", "確認すること"], tps) if tps else ["(なし)"]) + [""]
        out += self.review_appendix(["p2-changes", "p2"]) + self.asm_iss_appendix(asm, iss)
        out += ["### 正本のファイル", "", "- 02_impact/ の各 YAML(reuse / changes / impacts / common_components / concerns)", ""]
        return "02_impact/impact_report.md", out

    # ---------- フェーズ3 ----------
    def render_phase3(self):
        rq = self.load("01_requirements/requirements.yaml") or {}
        feats = {f.get("id"): f for f in self.lst(rq, "features")}
        plan = self.load("03_plan/plan.yaml") or {}
        ver = self.load("03_plan/verification.yaml") or {}
        order = self.lst(plan, "order")
        steps = {o.get("feature"): self.load(f"03_plan/steps/{o.get('feature')}.yaml") or {} for o in order}
        # 修正箇所(フェーズ2)の場所と今のコードを、手順に添える
        chg = {c.get("id"): c for f in self.files("02_impact/changes/*.yaml") for c in self.lst(self.load(f), "items")}
        chg.update({c.get("id"): c for c in self.lst(self.load("02_impact/reuse.yaml"), "changes")})
        files = ["03_plan/plan.yaml"] + [f"03_plan/steps/{o.get('feature')}.yaml" for o in order] + \
                ["03_plan/verification.yaml"]
        for o in order:
            if o.get("question"):
                self.add_q(f"plan:{o.get('feature')}", o.get("question"), o.get("feature"), [o.get("feature")])
            for i, q in enumerate(self.lst(steps[o.get("feature")], "questions"), 1):
                self.add_q(f"steps:{o.get('feature')}:{i}", q, o.get("feature"))
        asm, iss = self.collect_asm_iss([f for f in files if (self.run / f).exists()])
        self.review_questions(["p3"])
        self.number_questions(3)

        out = self.header("実装計画書(フェーズ3 承認資料)", "フェーズ3 実装計画",
                          "製造工程の入力です。手本・書き方・置き場所は、周辺の既存コードから決めています。")
        out += self.summary("p3")
        out += ["## 1. 実装計画(機能ごと)", "", "### 実装の順番", "",
                "依存関係を最優先にし、その中で「既存の削除 → 既存の流用 → 既存を手本に追加 → 既存の変更 → "
                "新しい仕組み → 共通処理の変更・影響大」の順に並べています。", ""]
        out += table(["順", "機能", "進め方", "この順にした理由", "前提", "確認"],
                     [[o.get("order"), f"[{o.get('feature')} {feats.get(o.get('feature'), {}).get('name', '')}]"
                                        f"(#{str(o.get('feature')).lower()})",
                       APPROACH.get(o.get("approach"), o.get("approach")),
                       o.get("reason") + (f"<br>(方針と違う順番: {o.get('exception')})" if o.get("exception") else ""),
                       ", ".join(o.get("depends_on") or []) or "-", self.qref(o.get("feature")) or "-"]
                      for o in order]) + [""]
        tcs = self.lst(ver, "items")
        for o in order:
            fid = o.get("feature")
            st = steps[fid]
            out += ["---", "", f"### {fid}", "",
                    f"**{feats.get(fid, {}).get('name', '')}**(順番 {o.get('order')} / {APPROACH.get(o.get('approach'), '')})", ""]
            out += ["#### (1) ゴールと前提", ""]
            out += table(["項目", "内容"], [
                ["ゴール", st.get("goal")], ["前提(先に終わっている機能)", ", ".join(st.get("prerequisites") or []) or "なし"],
                ["確定済みの判断", [f"{d.get('id')}: {d.get('text')}" for d in self.lst(st, "fixed_decisions")] or "なし"]]) + [""]
            out += ["#### (2) 作業手順", ""]
            def at(p):
                locs = [self.where((chg.get(c) or {}).get("location")) for c in p.get("chg_ids") or []]
                locs = [x for x in dict.fromkeys(locs) if x]
                return "<br>".join(locs) if locs else "(新しく作る)"
            out += table(["手順", "ファイル", "場所", "直す行(今のコード)", "やること", "手本にする既存実装", "修正"],
                         [[p.get("no"), p.get("file"), p.get("place"), at(p), p.get("action") +
                           (f"<br>({p.get('note')})" if p.get("note") else ""), self.where(p.get("exemplar")) or "(手本なし)",
                           ", ".join(p.get("chg_ids") or [])] for p in self.lst(st, "procedure")]) + [""]
            for p in self.lst(st, "procedure"):
                cur = [(c, (chg.get(c) or {}).get("excerpt")) for c in p.get("chg_ids") or []]
                cur = [(c, ex) for c, ex in cur if isinstance(ex, dict) and ex.get("file")]
                ex = p.get("exemplar_excerpt")
                if not cur and not ex:
                    continue
                out += [f"**手順{p.get('no')}**", ""]
                seen = set()
                for c, e in cur:
                    k = (e.get("file"), e.get("start"), e.get("end"))
                    if k in seen:
                        continue
                    seen.add(k)
                    out += self.excerpt(e, title=f"直す場所({c}): `{e.get('file')}` {e.get('start')}〜{e.get('end')} 行目(今のコード)")
                if ex:
                    out += self.excerpt(ex, title=f"手本: `{ex.get('file')}` {ex.get('start')}〜{ex.get('end')} 行目(手本のコード)")
            out += ["#### (3) 新しく作るもの", ""]
            out += (table(["種類", "名前", "置き場所", "根拠(既存の命名・配置)"],
                          [[n.get("kind"), n.get("name"), n.get("place"), self.where(n.get("basis"))]
                           for n in self.lst(st, "new_files")]) if self.lst(st, "new_files") else ["(なし)"]) + [""]
            out += ["#### (4) 合わせる書き方(周辺のコードから)", ""]
            out += (table(["観点", "書き方", "根拠"],
                          [[c.get("aspect"), c.get("rule"), self.where(c.get("basis"))] for c in self.lst(st, "conventions")])
                    if self.lst(st, "conventions") else ["(なし)"]) + [""]
            out += ["#### (5) 守るべき既存の振る舞い", ""]
            out += (table(["振る舞い", "理由"],
                          [[k.get("behavior"), ", ".join(k.get("reason_ids") or [])] for k in self.lst(st, "keep_behaviors")])
                    if self.lst(st, "keep_behaviors") else ["(なし)"]) + [""]
            out += ["#### (6) 確認方法", ""]
            mine = [t for t in tcs if t.get("feature") == fid]
            out += (table(["ID", "種類", "入力・操作", "期待する結果", "どこで確認するか", "優先度"],
                          [[t.get("id"), KIND_TC.get(t.get("kind"), t.get("kind")), t.get("input"), t.get("expected"),
                            t.get("where"), t.get("priority")] for t in mine]) if mine else ["(なし)"]) + [""]
            out += ["#### (7) 完了条件", ""] + [f"- {x}" for x in st.get("done_criteria") or []] + [""]
        out += self.questions_section()
        out += ["## 付録", "", "### 修正箇所と手順の対応", ""]
        rows = []
        for o in order:
            st = steps[o.get("feature")]
            for c in o.get("chg_ids") or []:
                nos = [str(p.get("no")) for p in self.lst(st, "procedure") if c in (p.get("chg_ids") or [])]
                rows.append([c, o.get("feature"), ", ".join(nos) or "-"])
        out += table(["修正", "機能", "手順"], rows) + [""]
        out += self.review_appendix(["p3"]) + self.asm_iss_appendix(asm, iss)
        out += ["### 正本のファイル", "", "- 03_plan/plan.yaml / steps/ / verification.yaml",
                "- 影響と懸念の詳細は 02_impact/impact_report.md", ""]
        return "03_plan/implementation_plan.md", out

    # ---------- 振り返り ----------
    def render_retro(self):
        d = self.load("retrospective.yaml") or {}
        out = self.header("振り返り", "調査の締めくくり")
        out += ["## 気づき", ""]
        out += (table(["ID", "種類", "内容", "原因の分類", "過去にもあったか", "関係する項目"],
                      [[o.get("id"), {"user_correction": "ユーザーの修正", "review_finding": "レビュー担当の指摘",
                                      "interim_fail": "途中の点検での不合格", "rejected_assumption": "外れた仮定",
                                      "recurring_question": "繰り返し出た確認事項", "other": "その他"}
                        .get(o.get("kind"), o.get("kind")), o.get("description"), o.get("cause"),
                        "あり" if o.get("recurring") else "-", ", ".join(o.get("refs") or [])]
                       for o in self.lst(d, "observations")]) if self.lst(d, "observations") else ["(なし)"]) + [""]
        out += ["## 改善案", ""]
        st = {"pending": "未定", "adopted": "採用", "rejected": "不採用"}
        props = self.lst(d, "proposals")
        if props:
            out += ["改善案ごとに「P1: 採用 / P2: 不採用」の形で答えてください。"
                    "**答えなかった改善案は採用しません。** 採用したものだけが方針(policies/)に書き込まれ、次の調査から使われます。", ""]
        out += (table(["No", "ID", "対象", "向け", "種類", "文案", "理由", "もとになった気づき", "採否"],
                      [[f"P{n}", p.get("id"), p.get("target_file"), {"worker": "作業エージェント", "reviewer": "レビュー担当"}
                        .get(p.get("for"), p.get("for")),
                        {"add": "追加", "rewrite": "書き直し", "retire": "廃止"}.get(p.get("action"), p.get("action"))
                        + (f"({p.get('existing_policy')})" if p.get("existing_policy") else ""),
                        p.get("text"), p.get("reason"), ", ".join(p.get("based_on") or []),
                        st.get(p.get("decision"), p.get("decision"))] for n, p in enumerate(props, 1)])
                if props else ["今回は改善案はありません。"]) + [""]
        return "retrospective.md", out


def main():
    ap = argparse.ArgumentParser(description="YAML から人が読む資料を作る")
    ap.add_argument("run_dir")
    ap.add_argument("--phase", required=True, choices=["1", "2", "3", "retro"])
    a = ap.parse_args()
    doc = Doc(a.run_dir)
    rel, lines = {"1": doc.render_phase1, "2": doc.render_phase2, "3": doc.render_phase3,
                  "retro": doc.render_retro}[a.phase]()
    out = Path(a.run_dir) / rel
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8", newline="\n")
    pending = sum(1 for e in doc.questions if e.get("q", "").startswith("Q"))
    print(f"作成: {out}" + (f"(確認事項 {pending} 件)" if a.phase != "retro" else ""))


if __name__ == "__main__":
    main()
