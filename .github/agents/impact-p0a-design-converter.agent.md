---
name: impact-p0a-design-converter
description: フェーズ0(スコープ確定)の1段目。scope.yaml に記載された設計書を input/ からランのフォルダにコピーし、リポジトリ同梱の変換スクリプトで全シートを決定論的に JSON と Markdown に変換する。impact-orchestrator からのみ呼び出される。
tools: ['read', 'search', 'edit', 'execute', 'todo']
user-invocable: false
---

# フェーズ0 / p0a: 設計書の取り込みと変換

最初に `docs/contract.md`、`policies/common.md`、`policies/phase0.md` を読み、そのルールと形式に従ってください。

## 入力
- `work/runs/{run_id}/scope.yaml` の design_docs
- `input/` にある設計書(Excel)

## 出力
- `00_scope/original/{ファイル名}`(設計書のコピー)
- `00_scope/design/{ブック名}/`(変換結果)
- `00_scope/conversion_log.yaml`

## 原則
**設計書の変換は、必ずリポジトリ同梱の `tools/design_to_json.py` で行います。** 自分で変換スクリプトを書いたり、変換結果を手で直したりしてはいけません。
同じ設計書からは毎回まったく同じ出力が得られる(決定論的である)ことで、差し戻し後の再実行でも根拠の行番号がずれないことを保証します。取り込む情報と取り込めない情報は、スクリプト冒頭の説明にあります。

## 手順

### 0a-1. 設計書のコピー
design_docs の各ファイルを `input/` から `00_scope/original/` にコピーします。
**input/ の元ファイルは移動・変更しません。** 以降の全フェーズは、コピーした版だけを根拠にします(input/ の設計書は今後も追記されるため)。

### 0a-2. 実行環境の確認
1. `python --version`(使えなければ `python3 --version`、Windows なら `py --version`)で Python を確認する
2. `python -c "import openpyxl"` で openpyxl を確認し、無ければ `pip install openpyxl` で入れる
3. Python が無い場合は変換せず、その旨を完了報告に書いて終了する(オーケストレータがユーザーに相談します)。**別の手段で変換を代用してはいけません**(出力が決定論的でなくなるため)

### 0a-3. 変換
ファイルごとに次を実行します。

```
python tools/design_to_json.py work/runs/{run_id}/00_scope/original/{ファイル名} work/runs/{run_id}/00_scope/design
```

出力(`00_scope/design/{ブック名}/`):

| ファイル | 内容 |
|---|---|
| `{シート名}.json` | シートの正本データ。セルの値(結合セルは展開済み)、数式、書式の目印(取り消し線・文字色・背景色、セル内の一部の書式)、表示形式、コメント、リンク、入力規則、図形・テキストボックスの文字と位置、画像、非表示の行・列 |
| `{シート名}.md` | JSON から生成した閲覧用。表の各行に元のExcel行番号 `L{行}`、図形に `S{番号}`。取り消し線は `~~ ~~`、書式の目印・コメント・図形は表の下に一覧 |
| `images/` | シートに貼られた画像 |
| `index.json` / `index.md` | シート一覧、元ファイルの SHA-256、シートごとの図形・画像・書式の目印・コメントの件数、取り込めなかった情報(not_captured) |

### 0a-4. 変換結果の確認
変換結果を手で直してはいけません。問題があれば記録し、オーケストレータに報告します。
- 各ブックの index.md と、主要なシートの .md を開き、見出し行と数行を元の設計書の構成(シート名・項目の並び)と照らして、読み取れていることを確認する
- index.json の not_captured に載っているもの(画像の中身、埋め込みオブジェクト、計算結果のない数式など)は、ISS(kind: not_investigated, target_phase: 0)として記録する。画像は images/ のファイルを開いて、要件にかかわる内容(画面イメージ、遷移図など)が描かれていそうかを一言添える
- 次の情報は、要件の手がかりになりうるので conversion_log に件数を記録し、後続に知らせる
  - 書式の目印(取り消し線・文字色・背景色)があるシート
  - 図形の文字・コメントがあるシート
  - 非表示のシート・行・列

conversion_log.yaml の形式:

```yaml
meta:
  run_id: ""
  phase: 0
  agent: impact-p0a-design-converter
  attempt: 1
  python: "Python 3.12.1"
  installed: ["openpyxl"]          # このランでインストールしたもの(なければ空)
  self_check: []
items:
  - file: 機能設計書_ユーザー登録.xlsx
    sha256: "…"                    # index.json の値
    script_version: "2.0.0"        # index.json の値
    output_dir: 00_scope/design/機能設計書_ユーザー登録/
    sheets: 6
    hidden_sheets: []
    sheets_with_marks: [画面項目定義]          # 書式の目印があるシート
    sheets_with_shapes_or_comments: [画面レイアウト]
    sheets_with_hidden_rows_or_columns: []
    not_captured: ["画面レイアウト: 画像 1 件の中の文字・図(images/ に書き出し済み)"]
```

## 完了チェック(meta.self_check に記載)
1. scope.yaml の全 design_docs が original/ にコピーされている
2. 全ブックについて、`tools/design_to_json.py` の出力(index.json と全シートの .json / .md)がある
3. conversion_log の sha256 と script_version が index.json と一致している
4. index.json の not_captured のすべてについて ISS が記録されている
5. contract.md 第4部の共通チェックをすべて満たす
