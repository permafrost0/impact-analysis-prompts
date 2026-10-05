# 追加機能 影響調査プロンプト(GitHub Copilot / VS Code用)

追加開発の設計書(Excel)を入力に、既存ソースのどこをどう直すか、既存機能にどう影響するかを段階的に調査し、製造フェーズへの引き継ぎ資料(製造タスク・テスト仕様・コーディングガイド)までを作るためのプロンプト一式です。

- ユーザーが対話するのはオーケストレータだけです。オーケストレータが承認フローに沿って、各フェーズのエージェントを呼び出します。
- 各フェーズの最後に、作業に関わっていないレビュー担当が点検し、合格したものだけがユーザーの承認に進みます。承認の観点もフェーズごとに示されます。
- 追加開発の部分は、シート名・イベント名・項目名などの名前、または「赤字の行」のような書式の目印で指示します。
- 設計書は同梱のスクリプトで決定論的に変換します。セルの値だけでなく、図形・テキストボックスの文字、コメント、取り消し線・文字色、数式、画像も取り込みます。
- 共通処理に手が入る場合は、他の呼び出し元をすべて確認し、全体修正か部分修正かを判断します。
- 現行ソースのコーディング規約と設計方針を手本付きで読み取り、製造フェーズに引き継ぎます。
- やり取りの中で決まった進め方は、方針として `policies/` に蓄積され、以降の調査に適用されます。

## 使い方
1. このリポジトリと対象ソースを、1つの VS Code ワークスペースに入れる(Python が必要です)
2. 設計書(Excel)を `input/` に置く
3. Copilot Chat で `impact-orchestrator` を選び、「新しい調査を始めたい」と伝える

詳しくは [docs/usage.md](docs/usage.md) を参照してください。

## 全体の構造

```mermaid
flowchart LR
    U[ユーザー<br/>指示と承認] <--> O[オーケストレータ<br/>承認フローを管理]
    O -->|方針を記録| P[(policies/<br/>方針)]
    O -->|呼び出し| W[作業エージェント<br/>12個]
    W -->|完了報告| O
    O -->|点検を依頼| R[レビュー担当]
    R -->|判定と承認の観点| O
    I[(input/<br/>設計書)] --> T[tools/<br/>変換・検索]
    T --> W
    P -.->|作業前に読む| W
    W <--> S[(shared/<br/>仮定・課題・決定)]
    W --> H[04_handoff/<br/>製造への引き継ぎ]
    H -.-> M[製造フェーズ<br/>今後作成]
```

## フェーズの流れ

承認はフェーズ単位です。同じ段のエージェントは並列に動き、フェーズの最後にレビュー担当が点検してから、ユーザーが承認します。

```mermaid
flowchart TD
    S0[ユーザーが名前・書式の目印で<br/>追加開発の部分を指示] --> P0a

    subgraph F0[フェーズ0 スコープ確定]
        P0a[p0a 設計書の変換<br/>tools/design_to_json.py] --> P0b[p0b 指示を行・図形に解決<br/>tools/find_in_design.py]
    end
    P0b --> R0[レビュー担当] --> A0{ユーザー承認}

    subgraph F1[フェーズ1 読解 ― 3つ並列]
        P1a[p1a 要件抽出]
        P1b[p1b ソースの構成と<br/>規約・設計方針]
        P1c[p1c 入口特定]
    end
    A0 --> P1a & P1b & P1c
    P1a & P1b & P1c --> R1[レビュー担当] --> A1{ユーザー承認}

    subgraph F2[フェーズ2 変更箇所特定]
        P2[p2 要件と入口の突き合わせ<br/>変更内容・共通処理の判定]
    end
    A1 --> P2 --> R2[レビュー担当] --> A2{ユーザー承認}

    subgraph F3[フェーズ3 影響範囲 ― 2つ並列]
        P3a[p3a 影響の検索]
        P3b[p3b 共通処理の<br/>全体/部分修正の判断]
    end
    A2 --> P3a & P3b
    P3a & P3b --> R3[レビュー担当] --> A3{ユーザー承認<br/>共通処理の判断を含む}

    subgraph F4[フェーズ4 製造への引き継ぎ]
        P4a[p4a 製造計画] --> P4b[p4b タスク指示書<br/>複数並列] & P4c[p4c テスト仕様]
        P4b & P4c --> P4d[p4d コーディングガイド<br/>入口資料・整合確認]
    end
    A3 --> P4a
    P4d --> R4[レビュー担当] --> A4{ユーザー承認}
    A4 --> M[製造フェーズへ<br/>04_handoff/README.md]
```

- レビュー担当の判定が fail のときは、指摘を作業エージェントに戻して直させ、再び点検します(最大2回)。
- ユーザーが差し戻すと、そのフェーズの該当エージェントを再実行し、後ろのフェーズは再実行待ちになります。

## フェーズとエージェント

| フェーズ | エージェント | 内容 |
|---|---|---|
| 0 スコープ確定 | impact-p0a-design-converter | 設計書をコピーし、変換スクリプトで JSON と Markdown に変換 |
| | impact-p0b-scope-resolver | 検索スクリプトで候補を出し、指示を設計書の行・図形に解決 |
| 1 読解 | impact-p1a-requirements | 設計書から要件を抽出(書式の目印・コメント・図形も読む) |
| | impact-p1b-codebase-profiler | 技術スタック・構成・共通部品、コーディング規約と設計方針(手本付き) |
| | impact-p1c-entrypoints | 指示の対象から既存コードの入口を特定 |
| 2 変更箇所特定 | impact-p2-changes | 要件と入口を突き合わせ、変更内容・共通処理の判定・従う規約を決める |
| 3 影響範囲 | impact-p3a-impacts | 既存機能への影響を網羅的に検索 |
| | impact-p3b-common-components | 共通処理の全体修正/部分修正を判断 |
| 4 製造への引き継ぎ | impact-p4a-work-planner | 製造タスクへの分割、製造順、完了条件、確認コマンド |
| | impact-p4b-task-writer | タスクごとの指示書(自己確認・内部レビュー・利用者承認の観点を含む) |
| | impact-p4c-test-writer | テスト仕様(新機能・回帰) |
| | impact-p4d-handoff-packager | コーディングガイド、製造フェーズの入口資料、整合確認 |
| 全フェーズ | impact-reviewer | 作業に関わっていない立場での点検、承認の観点、レビュー資料 |

## ディレクトリ構造

```
impact-analysis-prompts/
├─ README.md
├─ .github/
│  ├─ copilot-instructions.md               リポジトリ全体の指示(全チャットに自動適用)
│  └─ agents/
│     ├─ impact-orchestrator.agent.md       オーケストレータ(ユーザーが選ぶのはこれだけ)
│     ├─ impact-reviewer.agent.md           レビュー担当
│     ├─ impact-p0a-design-converter.agent.md
│     ├─ impact-p0b-scope-resolver.agent.md
│     ├─ impact-p1a-requirements.agent.md
│     ├─ impact-p1b-codebase-profiler.agent.md
│     ├─ impact-p1c-entrypoints.agent.md
│     ├─ impact-p2-changes.agent.md
│     ├─ impact-p3a-impacts.agent.md
│     ├─ impact-p3b-common-components.agent.md
│     ├─ impact-p4a-work-planner.agent.md
│     ├─ impact-p4b-task-writer.agent.md
│     ├─ impact-p4c-test-writer.agent.md
│     └─ impact-p4d-handoff-packager.agent.md
├─ docs/
│  ├─ contract.md                           取り決め(共通ルール・成果物の形式・承認の観点)
│  └─ usage.md                              使い方ガイド
├─ tools/
│  ├─ design_to_json.py                     設計書の決定論的な変換(Excel → JSON / Markdown)
│  └─ find_in_design.py                     変換済み設計書から名前・書式の目印で箇所を探す
├─ policies/                                フェーズごとの方針(やり取りの中で育つ)
│  ├─ common.md
│  ├─ phase0.md 〜 phase4.md
│  └─ CHANGELOG.md
├─ input/                                   設計書(Excel)を置く場所
└─ work/runs/{run_id}/                      調査ごとの成果物(調査を始めると作られる)
   ├─ state.yaml / scope.yaml
   ├─ 00_scope/                             設計書のコピー、変換結果、指示の解決結果
   ├─ 01_analysis/                          要件、ソースの構成、規約・設計方針、入口
   ├─ 02_changes/                           変更箇所
   ├─ 03_impacts/                           影響、共通処理の判断
   ├─ 04_handoff/                           製造への引き継ぎ一式
   │  ├─ README.md                          製造フェーズの入口(推奨する製造・承認の流れ)
   │  ├─ coding_guide.md                    コーディングガイド(規約と手本)
   │  ├─ work_plan.yaml                     製造タスク・製造順・進捗欄
   │  ├─ tasks/TSK-xxx.md                   タスクごとの指示書
   │  ├─ test_spec.yaml                     テスト仕様
   │  └─ handoff_check.yaml                 整合確認
   ├─ shared/                               仮定・課題・決定事項の台帳
   └─ review/                               フェーズごとのレビュー資料と点検結果
```

## 製造フェーズとのつなぎ方

製造フェーズ(今後作成)では、エージェント自身の承認フローを経てから利用者に承認を求める流れを想定しています。引き継ぎ資料は、その流れに沿って次を含みます。

| 製造フェーズの段階 | 引き継ぎ資料の対応箇所 |
|---|---|
| 実装 | タスク指示書の「対象ファイルと変更内容」「使う値」「従う書き方」、coding_guide.md |
| 自己確認 | タスク指示書の「完了条件」「検証手順」「セルフレビュー観点」、work_plan.yaml の確認コマンド |
| 内部レビュー | タスク指示書の「内部レビューの合格基準」「守るべき既存の振る舞い」、test_spec.yaml |
| 利用者承認 | タスク指示書の「利用者承認の観点」、work_plan.yaml の risk_level |
| 途中での確認 | タスク指示書の「作業を止めて確認する条件」「未決事項」 |
| 進捗の記録 | work_plan.yaml の status 欄 |

この調査自体も、各フェーズで「作業エージェント → レビュー担当 → ユーザー承認」と同じ型で進みます。

## 注意
各エージェントの `tools` 欄のツール名(`read`, `search`, `edit`, `execute` など)は、VS Code の更新で変わることがあります。エージェントファイルを開いてツール名に警告が出たら、「ツールの構成」から選び直してください。
