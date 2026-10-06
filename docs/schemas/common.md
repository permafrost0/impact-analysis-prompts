# 成果物の形式: 全フェーズ共通

全エージェントが読みます。フェーズごとの形式は `phase1.md`〜`phase3.md`、点検と振り返りは `review.md` にあります。
形式を変えるときは、このフォルダの文書と `tools/check_outputs.py`・`tools/render_docs.py` を同時に直します。

## 1. 調査フォルダ

```
work/runs/{調査ID}/
├─ state.yaml                     進行の記録(オーケストレータだけが書く)
├─ scope.yaml                     ユーザーの指示の記録(オーケストレータだけが書く)
├─ decisions.yaml                 ユーザーの判断の記録(オーケストレータだけが書く)
├─ guard/baseline.json            読み取り専用の確認の基準(tools/guard.py)
├─ 01_requirements/
│  ├─ sheets/{ブック}/{シート}.md  指示したシートの変換結果(tools/convert_sheets.py)
│  ├─ scope_resolution.yaml       範囲の特定(p1a)
│  ├─ extract/{S1}.yaml           シートごとの要件(p1b。シートごとに1ファイル)
│  ├─ requirements.yaml           要件の正本(p1c)
│  └─ requirements.md             フェーズ1の承認資料(tools/render_docs.py)
├─ 02_impact/
│  ├─ reuse.yaml                  流用先(p2a)
│  ├─ changes/{F-01}.yaml         機能ごとの修正箇所(p2b。機能ごとに1ファイル)
│  ├─ impacts.yaml                既存機能への影響(p2c)
│  ├─ common_components.yaml      共通処理の判断(p2d)
│  ├─ concerns.yaml               実装上の懸念(p2e)
│  └─ impact_report.md            フェーズ2の承認資料 = 影響調査報告書(tools/render_docs.py)
├─ 03_plan/
│  ├─ plan.yaml                   機能の順番(p3a)
│  ├─ steps/{F-01}.yaml           機能ごとの手順(p3b。機能ごとに1ファイル)
│  ├─ verification.yaml           確認方法(p3c)
│  └─ implementation_plan.md      フェーズ3の承認資料 = 実装計画書(tools/render_docs.py)
├─ review/
│  ├─ {点検名}_check.yaml          レビュー担当の点検結果(p1-scope / p1 / p2-changes / p2 / p3)
│  └─ phase{N}_questions.yaml     承認資料の確認事項(Q番号と元の項目の対応。tools/render_docs.py)
├─ retrospective.yaml             振り返り(impact-retrospective)
└─ retrospective.md               振り返りの資料(tools/render_docs.py)
```

YAML がエージェント同士のやり取りの正本です。`.md` はスクリプトが YAML から作るもので、手で直しません。

## 2. 作業者タグ

同じエージェントが並列に複数動くとき、互いの ID が重ならないよう、オーケストレータが作業者タグを渡します。

| エージェント | 作業者タグ | 例 |
|---|---|---|
| 1つだけ動くもの | エージェントの略号 | `p1a`、`p2c` |
| p1b-extract | `p1b-{シートタグ}` | `p1b-S1` |
| p2b-changes | `p2b-{機能ID からハイフンを除いたもの}` | `p2b-F01` |
| p3b-steps | `p3b-{機能ID からハイフンを除いたもの}` | `p3b-F01` |

## 3. ID

| 接頭辞 | 意味 | 付ける人 | 形 |
|---|---|---|---|
| T | ユーザーの指示 | オーケストレータ | `T-01` |
| S | 対象シート | オーケストレータ | `S1` |
| SCP | 範囲の特定 | p1a | `SCP-001` |
| REQ | 要件 | p1b(シートタグつき)/ p1c(判断で追加したもの) | `REQ-S1-001` / `REQ-I-001` |
| F | 機能 | p1c | `F-01` |
| RUS | 流用先 | p2a | `RUS-001` |
| CHG | 修正箇所 | p2b(機能つき)/ p2a(流用のための修正) | `CHG-F01-001` / `CHG-R-001` |
| IMP | 既存機能への影響 | p2c | `IMP-001` |
| CMN | 共通処理の判断 | p2d | `CMN-001` |
| CON | 実装上の懸念 | p2e | `CON-001` |
| TC | 確認方法 | p3c | `TC-001` |
| ASM | 仮定 | 全員(作業者タグつき) | `ASM-p1b-S1-001` |
| ISS | 課題 | 全員(作業者タグつき) | `ISS-p2c-001` |
| RVF | レビュー担当の指摘 | レビュー担当(点検名つき) | `RVF-p1-001` |
| DEC | ユーザーの判断 | オーケストレータ | `DEC-001` |
| OBS / PRP | 振り返りの気づき / 改善案 | impact-retrospective | `OBS-001` / `PRP-001` |

番号は3桁(F は2桁)。一度振った ID は使い回しません。

## 4. 根拠の書き方

| 種類 | 書き方 | 例 |
|---|---|---|
| 設計書のセル | `sheet:{ブック}/{シート}#L{行}` または `#L{行}-L{行}` | `sheet:機能設計書_ユーザー登録/画面項目定義#L27` |
| 設計書の図形 | `sheet:{ブック}/{シート}#S{番号}` | `sheet:機能設計書_ユーザー登録/画面レイアウト#S2` |
| 参照先の見出し | `heading:{ブック}/{シート}#L{行}` | `heading:会員管理設計書/処理仕様#L30` |
| コード | `code:{ソースのフォルダ(source_root)からの相対パス}:{行}` または `:{行}-{行}` | `code:src/main/java/com/example/user/UserService.java:22` |

{ブック}は拡張子なしのファイル名です。**既存の振る舞い・修正箇所・影響の根拠は、必ず `code:` です。**

## 5. コードの抜粋(excerpt)

承認資料にコードを載せたい箇所は、抜粋の範囲だけを書きます。中身はスクリプトが実際のソースから切り出します(書き写さないでください)。

```yaml
excerpt:
  file: src/main/java/com/example/user/UserForm.java   # ソースのフォルダ(source_root)からの相対パス
  start: 18
  end: 24        # start から最大40行まで
```

## 6. 共通の項目

### meta(すべての YAML に必須)

```yaml
meta:
  run_id: 20261007-usertel
  phase: 1                 # 1 / 2 / 3 / retro
  agent: impact-p1b-extract
  worker: p1b-S1           # 作業者タグ
  attempt: 1               # やり直すたびに +1
  feedback_response:       # attempt が 2 以上のときは必須。受け取った指摘・判断への対応
    - feedback: "RVF-p1-002: REQ-S1-004 の値が設計書と違う"
      response: "L31 の値に直した"
  not_covered:             # 前段の項目のうち、扱わなかったもの(理由必須)
    - id: SCP-004
      reason: "見出し行だけで、要件にする記述がない"
  self_check:              # 完了前の自己点検(tools/check_outputs.py の結果も含める)
    - check: "tools/check_outputs.py --file"
      result: ok           # ok / ng
      note: ""
```

### 確信度

`高`(根拠を実際に読んで確かめた)/ `中`(根拠はあるが一部は解釈)/ `低`(直接の根拠がない推測)

### question(ユーザーに判断してほしいとき)

```yaml
question:
  text: "電話番号の形式を「ハイフンなしの数字11桁」と仮定しました。正しいですか?"
  answer_examples: ["正しい", "ハイフンありが正しい"]
```

ユーザーが答えなかった確認事項は、**資料に書かれている内容のまま確定**します。そのため、text には「今どう扱っているか」を必ず書きます。

### assumptions / issues(すべての YAML に置ける)

```yaml
assumptions:               # 決めきれず、ある解釈を採用したもの
  - id: ASM-p1b-S1-001
    statement: "電話番号はハイフンなしの数字11桁"
    reason: "画面項目定義に形式の記載がない"
    affects: [REQ-S1-001]
    ask_user: true         # ユーザーに確認するか
    question: {text: "...", answer_examples: ["..."]}   # ask_user: true のとき必須
issues:                    # 他の成果物の誤り・漏れ、調べられなかったことなど
  - id: ISS-p2b-F01-001
    kind: omission         # omission / contradiction / not_found / premise_broken / not_investigated / error
    target: p1c            # 問題がある作業者タグ。外部の問題なら none
    description: "..."
    evidence: ["code:..."]
    related_ids: [REQ-S1-002]
    ask_user: false
    question: {...}        # ask_user: true のとき必須
```

並列で動くエージェントが同じファイルに書き込まないよう、仮定と課題は**自分の成果物の中に**書きます。共有の台帳はありません。

## 7. decisions.yaml(オーケストレータだけが書く)

```yaml
items:
  - id: DEC-001
    phase: 1
    q: Q2                    # 承認資料の確認事項の番号(なければ空)
    about: [ASM-p1b-S1-001]  # 対象の ID
    decision: "電話番号はハイフンなしの数字11桁で確定"
    effect: confirm          # confirm(資料のまま確定)/ change(内容を変える)
    user_words: "Q2: 正しい"
```

`about` には、`review/phase{N}_questions.yaml` の `source` をそのまま書きます。ID を持たない確認事項は、`unresolved:T-02`、`out_of_scope:{参照元}`、`excluded:{設計書の箇所}`、`not_found:REQ-…`、`premise:REQ-…`、`plan:F-01`、`steps:F-01:{番号}`、`review:{点検名}:{番号}` の形になります。

`effect: change` の判断は、関係するエージェントに渡してやり直させます。

## 8. 蓄積の記録(history/、オーケストレータだけが書く。各自の PC の中だけで使う)

振り返りの係が、過去の調査と比べて「繰り返し起きていること」を見つけるために読みます。作業エージェントは読みません。

`history/runs.md`(調査ごとに1行):

```
| 調査ID | 機能名 | 完了日 | 機能の数 | 差し戻し | 採用した改善案 |
```

`history/feedback_log.md`(ユーザーの差し戻し・修正、レビュー担当の不合格を、起きるたびに1行追記):

```
| 日付 | 調査ID | フェーズ | 種類 | 内容 | 原因の分類 | 対応 |
```

原因の分類: `手順の不足` / `設計書の書き方の癖` / `点検の見落とし` / `一過性` / `その他`

`history/questions_log.md`(承認のたびに、確認事項を答えなかったものも含めて1行ずつ追記):

```
| 日付 | 調査ID | フェーズ | Q | 確認の種類 | 内容(要約) | 回答 | 結果 |
```

確認の種類: `範囲` / `仮定` / `判断に困る表現` / `流用先` / `前提` / `共通処理` / `懸念` / `順番` / `手順` / `レビュー担当` / `課題`
結果: `資料のまま`(effect: confirm)/ `変更`(effect: change)
