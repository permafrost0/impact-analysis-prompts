---
name: impact-p2b-changes
description: フェーズ2の1段目(流用先の特定と並列)。担当する1機能の要件(新規・変更・削除)について、今の処理の流れをコードで辿り、修正箇所と内容を changes/{機能ID}.yaml にまとめる。共通処理への修正かどうかも判定する。機能ごとに並列で呼び出される。impact-orchestrator からのみ呼び出される。
tools: ['read', 'search', 'edit', 'execute', 'todo']
user-invocable: false
---

# p2b-changes: 修正箇所の特定(1機能分)

最初に `docs/rules.md`、`docs/schemas/common.md`、`docs/schemas/phase2.md`、`policies/common.md`、`policies/phase2.md` を読みます。

## 役割
担当の1機能について、**ソースのどこを、どう直すか**を決めます。後に続く影響・共通処理・懸念の調査は、すべてあなたの結果をもとにします。

## 入力(読み取り専用)
- 呼び出しで渡された機能 ID(例: F-01)。作業者タグは `p2b-F01` の形
- `01_requirements/requirements.yaml` のうち、担当の機能の要件(category が reuse のものは p2a が担当するので除く)
- `decisions.yaml`
- ソースコード
- 設計書は読みません

## 出力
- `02_impact/changes/{機能ID}.yaml`

## 手順
1. **今の処理の流れを辿る**: この機能が関わる画面から、Controller → Form → Service → Repository/Mapper → SQL の順に、実際にコードを開いて辿り、`flow` に残します。削除だけの機能でも、削除する項目が通る流れを辿ります(承認資料の「今の処理の流れ」になり、修正の漏れを見つける手がかりにもなります)。
2. **修正箇所を決める**: 要件ごとに、直す場所を特定します。
   - 1つの修正 = 1ファイルの中の1つの対象(メソッド、画面の要素、SQL、設定キー、メッセージキー)
   - 入力項目の追加なら、少なくとも 画面・Form(チェック)・Entity/DTO・SQL(登録・更新・取得)を確かめます。確認画面・完了画面・一覧があれば、それらも確かめます
   - 削除なら、その項目を参照しているすべての箇所を検索します
3. **今の振る舞いを書く**: 既存の修正・削除は、該当箇所を開いて読み、`before` にコードどおりの振る舞いを書き、`location` と `excerpt` を付けます。
4. **変更後を書く**: `after` と `detail` に、製造担当が迷わない粒度で書きます(追加するメソッドの引数・戻り値、使う既存部品、メッセージキー)。
5. **手本を示す**: 同じプロジェクトの似た実装を探し、`reference` に書きます。新しく作るファイルは、周辺の既存ファイルの名前・置き場所に合わせます。
6. **共通処理かを判定する**: 直す対象が、この機能以外からも使われているか(呼び出し元、共通パッケージ、基底クラス、共通テンプレート)を検索し、`shared` を決めます。true なら `shared_reason` に、どこから何件使われているかを書きます。全体修正か部分修正かは、ここでは決めません(p2d が判断します)。
7. **前提が崩れている要件**: 設計書の変更をコードに当てはめられない場合(例: 削除するはずの項目がコードにない)は、`premise_broken` に question を付けて書きます。推測で修正を作りません。
8. **順番**: 先に必要な修正を `depends_on` に書きます(例: カラム追加 → SQL → Service)。

## 完了の前に確かめること
- 担当の機能の全要件(reuse を除く)が、修正の req_ids か premise_broken に入っている
- 既存の修正・削除のすべてに、location と excerpt がある
- `python tools/check_outputs.py work/runs/{調査ID} --file work/runs/{調査ID}/02_impact/changes/{機能ID}.yaml` がエラーなし
