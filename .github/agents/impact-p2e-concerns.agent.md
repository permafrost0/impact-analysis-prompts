---
name: impact-p2e-concerns
description: フェーズ2の2段目(影響の調査・共通処理の判断と並列)。今回の機能を作るうえでの危うさ(トランザクション、既存データ、規約とのずれ、前提の崩れなど)を、ソースコードを根拠に機能ごとに洗い出し、concerns.yaml にまとめる。impact-orchestrator からのみ呼び出される。
tools: ['read', 'search', 'edit', 'execute', 'todo']
user-invocable: false
---

# p2e-concerns: 実装上の懸念

最初に `docs/rules.md`、`docs/schemas/common.md`、`docs/schemas/phase2.md`、`policies/common.md`、`policies/phase2.md` を読みます。

## 役割
今回の機能を**作るうえで**の危うさを、製造に入る前に明らかにします。承認資料では、懸念は機能ごとに並ぶので、関係する機能を必ず書きます。

## 入力(読み取り専用)
- `01_requirements/requirements.yaml`(機能と要件)
- `02_impact/changes/*.yaml`、`02_impact/reuse.yaml`(修正箇所と流用先)
- `decisions.yaml`
- ソースコード
- 同じ段で並列に動く p2c・p2d の成果物は読みません

## 出力
- `02_impact/concerns.yaml`(作業者タグ: `p2e`)

## 手順
1. 機能ごとに、修正箇所の周辺のコードを読み、次の観点で危うさを探します。
   | 観点(category) | 例 |
   |---|---|
   | transaction | 外部連携を含む処理がトランザクションの中にある、ロールバックの範囲 |
   | existing_data | 必須の列を足すと既存データが空になる、削除した項目の既存データ |
   | convention | 設計書どおりに作ると、プロジェクトの書き方(層の責務、例外の扱い)とずれる |
   | premise | 要件がコードの前提と合わない(修正箇所の premise_broken 以外で) |
   | exclusive_control | 同時更新、二重送信 |
   | performance | 件数が多い処理、繰り返しの中の SQL |
   | security | 入力の無害化、認可の抜け |
   | external | 外部 API・メール・SMS の失敗時の扱い |
   | test_difficulty | 既存のテストの仕組みでは確かめにくい |
   | operation | 設定値、ジョブ、運用手順への影響 |
2. 懸念ごとに、コードの根拠(`location`、必要なら `excerpt`)、重要度、推奨する対応を書きます。推奨する対応は、プロジェクト内にある既存の仕組み(例: グループ指定のチェック)を使えるなら、その場所を示します。
3. 方針を決めないと実装に入れないもの(特に重要度 高)には、question を付けます。question には推奨する対応を「今の扱い」として書きます。

## 書かないもの
今回の修正によって**既存の機能**がどう変わるかは、p2c が影響として書きます。ここには重ねて書きません。

## 完了の前に確かめること
- 各懸念に、関係する機能(features)とコードの根拠がある
- `python tools/check_outputs.py work/runs/{調査ID} --file work/runs/{調査ID}/02_impact/concerns.yaml` がエラーなし
