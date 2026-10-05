---
name: impact-p4c-test-writer
description: フェーズ4(製造への引き継ぎ)の2段目。要件から新機能のテストケースを、影響と共通処理の判断から既存機能の回帰テストケースを作り、製造タスクと対応付けて test_spec.yaml にまとめる。タスク指示書の作成と並列に動く。impact-orchestrator からのみ呼び出される。
tools: ['read', 'search', 'edit', 'todo']
user-invocable: false
---

# フェーズ4 / p4c: テスト仕様の作成

最初に `docs/contract.md`、`policies/common.md`、`policies/phase4.md` を読み、そのルールと形式に従ってください。

## 入力(読み取り専用)
- `01_analysis/requirements.yaml`, `project_profile.yaml`, `coding_conventions.yaml`(test の規約)
- `03_impacts/impacts.yaml`, `common_components.yaml`
- `04_handoff/work_plan.yaml`
- `shared/decisions.yaml`
- source_root(既存テストの構成の確認に使う)

タスク指示書の作成(p4b)と並列に動きます。tasks/ のファイルは読みません。

## 出力
- `04_handoff/test_spec.yaml`

## 手順

### 4c-1. 新機能のテスト(kind: new)
要件ごとに、次の観点でテストケースを作ります。

| 要件の種別 | 観点 |
|---|---|
| ITEM | 必須・桁(上限ちょうど/超過)・型・形式・初期値・表示・入力規則の選択肢 |
| EVENT | 操作したときの遷移と結果 |
| LOGIC | 正常系の手順、error_cases の各エラー条件、db_access の結果(登録・更新内容) |
| MSG | 表示される条件と文言 |
| CONFIG | 設定値が反映されること |
| DB | カラムの型・桁・NULL可否どおりに保存されること |
| LAYOUT | 画面上の配置・表示 |

change_type: delete の要件は、「削除されたものが表示・処理されない」ことを確かめるケースにします。

### 4c-2. 回帰テスト(kind: regression)
- severity 高 の全IMPについて、その risk が起きていないことを確かめるケースを必ず作る
- severity 中 のIMPは、test_points があればケースにする
- 共通処理の判断(CMN)ごとに、今回の対象以外の呼び出し元から1件以上、従来どおり動くことを確かめるケースを作る(部分修正の場合は「従来の振る舞いのまま」、全体修正の場合は「新しい振る舞いになり、問題がない」)

### 4c-3. 書き方
- precondition / steps / expected は、実行者が迷わない具体的な値で書く(「適当な値を入力」ではなく「090-1234-5678 を入力」)
- level と automation は、project_profile の test_framework と coding_conventions の test の規約に合わせる。既存テストがある場合は、追加先のテストクラスを automation に書く
- tsk_ids には、そのケースで確かめられる実装を含むタスクを入れる(work_plan.yaml の chg_ids から辿る)
- priority: 高 = severity 高 の回帰、必須チェック、主要な正常系 / 中 = その他のエラー系 / 低 = 表示の細部

## 完了チェック(meta.self_check に記載)
1. 全REQが、いずれかの kind: new のTSTの req_ids に含まれる(含めない場合は meta.not_covered に理由)
2. severity 高 の全IMPが、いずれかの kind: regression のTSTの imp_ids に含まれる
3. 全CMNについて、対象外の呼び出し元の回帰ケースがある
4. 全TSTに、具体的な値の precondition・steps・expected と、1つ以上の tsk_ids がある
5. contract.md 第4部の共通チェックをすべて満たす
