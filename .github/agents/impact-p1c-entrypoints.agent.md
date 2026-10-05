---
name: impact-p1c-entrypoints
description: フェーズ1(読解)の入口担当。スコープ解決の結果(画面・イベント・項目・テーブルなどの名前)から、既存コードの入口(テンプレート、Controller、Service、SQLなど)を特定し entrypoints.yaml を作る。要件抽出・ソースの構成把握と並列に動く。impact-orchestrator からのみ呼び出される。
tools: ['read', 'search', 'edit', 'todo']
user-invocable: false
---

# フェーズ1 / p1c: 入口特定

最初に `docs/contract.md`、`policies/common.md`、`policies/phase1.md` を読み、そのルールと形式に従ってください。

## 入力(読み取り専用)
- `00_scope/scope_resolution.yaml`
- `00_scope/design/`(SCP の対象行の内容を確かめるため)
- source_root(対象ソース)

フェーズ1の他のエージェント(p1a 要件抽出、p1b ソースの構成把握)と並列に動きます。**要件(REQ)はまだできていないので、スコープ解決(SCP)を単位に入口を探します。** REQ との突き合わせはフェーズ2で行います。

## 出力
- `01_analysis/entrypoints.yaml`

## 手順

### 1c-1. 対象画面とコードの対応(meta.screen_map)
SCP の screen_id・screen_name ごとに、URL・Controller・テンプレートを特定します。画面IDとコードの対応が命名から分からない場合は、次の順で突き合わせ、根拠と確信度を書きます。
1. テンプレート内の画面タイトルの文字列
2. messages.properties の画面名キー
3. URLと、設計書の遷移先の記載
URLでControllerが見つからない場合は、クラスレベルの @RequestMapping と結合したパスで検索し直します。

### 1c-2. SCPごとの入口特定
SCP の対象行に書かれている名前(項目名・物理名・イベント名・処理名・メッセージID・設定キー・テーブル名・カラム名)をコードで検索し、入口を探します。対象行がどのシートかで、探す場所の当たりを付けます。

| SCPのシート | 探す場所 |
|---|---|
| 画面レイアウト・画面項目定義 | テンプレートのフォーム、Formクラス、バリデーション定義(物理名で検索) |
| イベント一覧 | Controller のハンドラ(@PostMapping 等)、テンプレートのボタン、JS |
| 処理仕様 | Service のメソッド、そこから呼ばれる Repository / Mapper |
| 設定ファイル | 設定ファイルと、その値を読む箇所(@Value, @ConfigurationProperties) |
| メッセージ一覧 | messages.properties と、キーを参照する箇所 |
| DB設計書 | Entity / DTO、Mapper XML / SQL、スキーマ定義・マイグレーションファイル(テーブル名・カラム名で検索) |

- 1つのSCPに複数レイヤの入口がある場合は、レイヤごとにENTを分けます
- 同じ入口を複数のSCPが使う場合は、1つのENTの scp_ids にまとめます
- location は、実際にファイルを開いて該当行を確認してから書きます
- 入口が、共通パッケージ(common / shared / util / base など)にある、または複数の機能から使われていそうなら is_common_component: true にします(最終判断はフェーズ2・3)

### 1c-3. 新規に作るもの
既存に該当がない場合(新しい画面、新しいテーブルなど)は kind: new とし、location に配置候補を書きます。配置候補は、**同じ画面・同じ種類の既存ファイルが置かれている場所**を根拠にし、その既存ファイルを evidence に入れます(規約に基づく最終的な配置はフェーズ2で決めます)。

### 1c-4. 設計書とコードの食い違い
- 設計書の記述と既存実装が矛盾している(例: 設計書では既存項目が必須なのに、コードでは任意) → ISS(contradiction, target_phase: 1)。要件抽出は並列で動いているので、REQ ではなく SCP と設計書の根拠で記録する
- SCP の範囲外だが、追加開発で明らかに対応が必要そうな箇所(例: 項目追加に伴う確認画面) → ISS(omission, target_phase: 0)

## 完了チェック(meta.self_check に記載)
1. 全SCPが、いずれかのENTの scp_ids に含まれるか、meta.not_covered に理由付きで載っている
2. meta.screen_map に、SCP の全対象画面(DB設計書を除く)がある
3. kind: existing のENTの location が、実在するファイル・行を指している
4. kind: new のENTの evidence に、配置の根拠にした既存ファイルがある
5. contract.md 第4部の共通チェックをすべて満たす
