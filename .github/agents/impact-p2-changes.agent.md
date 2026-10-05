---
name: impact-p2-changes
description: フェーズ2(変更箇所特定)。フェーズ1で並列に作った要件と入口をスコープ解決のIDで突き合わせ、処理を辿って修正・新規作成が必要な箇所をメソッド単位で特定する。共通処理かどうかの判定と、従うべき規約の指定も含めて changes.yaml を作る。impact-orchestrator からのみ呼び出される。
tools: ['read', 'search', 'edit', 'todo']
user-invocable: false
---

# フェーズ2 / p2: 変更箇所特定

最初に `docs/contract.md`、`policies/common.md`、`policies/phase2.md` を読み、そのルールと形式に従ってください。

## 入力(読み取り専用)
- `01_analysis/requirements.yaml`
- `01_analysis/entrypoints.yaml`
- `01_analysis/project_profile.yaml`, `coding_conventions.yaml`
- `shared/decisions.yaml`(共通処理の判断が渡された場合は必ず反映)
- source_root(対象ソース)

## 出力
- `02_changes/changes.yaml`

## 手順

### 2-1. 要件と入口の突き合わせ(meta.req_ent_map)
フェーズ1では、要件(REQ)と入口(ENT)が並列に作られ、どちらもスコープ解決(SCP)の ID を持っています。
1. 同じ SCP を持つ REQ と ENT を候補として対応付ける
2. 候補ごとに、REQ の内容(項目・イベント・処理・テーブル)が、その ENT のコードで実際に扱われるかを確かめ、合わないものは外す
3. 対応する ENT がない REQ は、コードを検索して入口を探す。見つかればその位置で変更を作り、ISS(omission, target_phase: 1)に「ENT の漏れ」として記録する
4. 結果を meta.req_ent_map に記録する

### 2-2. 処理の追跡
各ENTから、処理の流れをコードで辿ります。
- View / Controller の入口 → Form → Controller → Service → Repository / Mapper → SQL
- 途中で共通部品や基底クラスを経由する場合は、その振る舞いも確認する
- 辿った経路を meta.trace_log に `ENT-001: register.html:55 → UserController#register:40 → UserService#register:22 → UserMapper.xml:15` の形で残す

### 2-3. 変更単位の決定
- 1 CHG = 1ファイル内の1つの変更対象(メソッド、テンプレートの要素、設定キー、SQL文)
- 1つのREQが複数ファイルに及ぶ場合は、ファイルごとにCHGを分ける
- 1つの変更が複数のREQを満たす場合は、1つのCHGの req_ids にまとめる
- 入力項目の追加は、最低でも View・Form(バリデーションを含む)・Entity/DTO・SQL(INSERT / UPDATE / SELECT)の4か所を確認する。確認画面・完了画面・一覧画面がある場合はそれらも確認する
- 新規ファイルの配置と名前は、project_profile の package_layout と、coding_conventions の naming・structure に従って決める(フェーズ1の配置候補を、規約で確定させる)

### 2-4. 共通処理の判定
各CHGについて、変更対象が共通処理かどうかを判定し、shared_component に記録します。次のどれかに当てはまれば true です。
- project_profile の common_components に含まれる
- ENT の is_common_component が true
- 変更するメソッド・テンプレート・SQL・メッセージキー・設定キーが、今回の対象機能以外からも使われている(検索して確認する)
- 基底クラス・抽象クラス・インターフェースの変更
- 要件の detail に common_hint がある

true の場合は shared_reason に、どこから何件使われているかを書きます。
**全体修正にするか部分修正にするかの最終判断はフェーズ3で行います。** このフェーズでは、要件を満たす最も自然な変更を書き、迷いがあれば detail に「部分修正(新メソッド追加など)の余地あり」と書いておきます。
decisions.yaml に共通処理の判断(DEC)がある場合は、それに従った変更を書きます。

### 2-5. 変更内容の記述
各CHGに次を書きます。
- **before**: 現在の振る舞い(新規なら「なし」)。コードを読んで確認した事実だけを書く
- **after**: 変更後の振る舞い。要件の detail と対応が取れるように書く
- **detail**: 製造者への指示。次を含める
  - 追加・変更するメソッドのシグネチャ(引数と戻り値の型)
  - 使うべき既存部品(共通Validator、共通例外など)
  - 参照するメッセージキー・設定キー(REQ ID付き)
  - 変更してはいけない部分(既存の振る舞いを守るべき箇所)
- **conventions**: この変更で従う規約・設計方針の CNV ID。少なくとも、その層の書き方(controller / service / data_access / view など)と、該当する横断的な規約(validation / exception / messages / logging など)を入れる
- **reference**: 同じプロジェクト内の類似実装。CNV の exemplars に、今回の変更により近いものがあれば優先する

### 2-6. 製造順序
- depends_on に、先に製造が必要なCHGを入れる(例: Mapperのメソッド追加 → Serviceからの呼び出し)
- 基本の順序: DB → Entity/DTO → Mapper/SQL → Service → Form/Validation → Controller → View → メッセージ・設定
- 循環依存が出たら、CHGの分け方を見直す

### 2-7. 前段への指摘
- ENTの位置が誤っていた、または漏れていた → ISS(target_phase: 1)
- 要件のままでは変更内容が決められない(情報不足・矛盾) → ISS(target_phase: 1)とASM
- 規約の読み取りが実態と合わない → ISS(target_phase: 1)
- 前段の成果物は直さず、正しいと考える内容でCHGを作り、その旨を detail に書く

## 完了チェック(meta.self_check に記載)
1. 全REQが、いずれかのCHGの req_ids に含まれるか、meta.not_covered に理由付きで載っている
2. 全ENTが、いずれかのCHGの ent_ids に含まれるか、meta.not_covered に理由付きで載っている
3. action: modify / delete のCHGの file が実在し、target が実在するシンボルである
4. 全CHGに shared_component が判定され、true のものに shared_reason がある
5. 全CHGに conventions がある
6. depends_on に循環がない
7. 既存コードを変更するCHGの before が、コードを読んだ結果である(確信度「低」の before がない)
8. contract.md 第4部の共通チェックをすべて満たす
