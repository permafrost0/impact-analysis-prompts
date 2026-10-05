# 取り決め(共通ルール+成果物スキーマ)

オーケストレータと全エージェントが従う唯一の取り決めです。
フェーズ間・エージェント間の受け渡しはすべてこのファイルの形式で行います。形式を変えるときは、このファイルだけを変えます。

- 第1部 共通ルール
- 第2部 フェーズとエージェントの構成
- 第3部 成果物スキーマ
- 第4部 全エージェント共通の完了チェック
- 第5部 完了報告・レビュー・承認の観点

---

## 第1部 共通ルール

### 立場
- あなたは追加機能の影響調査チームの一員です。**調査対象のソースコードは一切変更しません。**
- 書き込んでよいのは `work/runs/{run_id}/` 配下の、自分の担当の成果物だけです(オーケストレータは `policies/` と state.yaml、shared/ の status も更新します)。
- ユーザーとやり取りするのはオーケストレータだけです。エージェントはユーザーに質問できないので、曖昧な点は仮定を置いて記録します。

### 作業開始時に必ず読むもの
1. このファイル
2. `policies/common.md` と、担当フェーズの `policies/phase{N}.md`
3. `work/runs/{run_id}/state.yaml` の担当フェーズの feedback(差し戻し中なら、その内容を最優先で反映)
4. `work/runs/{run_id}/shared/` の仮定・課題・決定事項
5. 前回のレビューで指摘を受けて再実行する場合は、`review/phase{N}_check.yaml` の自分宛ての指摘

### 方針ファイル(policies/)の扱い
- 方針ファイルは、ユーザーとのやり取りで決まった「今後の進め方」です。エージェント定義の手順と食い違う場合は、**方針ファイルを優先**します。
- エージェントは方針ファイルを書き換えません。手順や方針に改善の余地があると気づいたら、完了報告の「方針への提案」に書きます。

### 他の成果物の扱い
- 自分の担当以外の成果物は**読み取り専用**です(例外: impact-p4d-handoff-packager は、work_plan.yaml の tst_ids と、タスク指示書の「関連テスト」節だけを更新します)。誤りや漏れに気づいたら、直さずに課題(issues.yaml)に記録します(target_phase に問題のあるフェーズ番号)。
- 他の成果物のIDを参照するときは、実在するIDだけを使います。
- 仮定(ASM)を確定扱いにしてはいけません。仮定に依存する項目は assumptions に ASM ID を付けます。
- ユーザーが決めたこと(decisions.yaml)は確定事項として扱い、必ず反映します。
- 同じフェーズで並列に動いている他のエージェントの成果物は、まだ存在しないか途中の可能性があるので読みません。

### 設計書の扱い
- 設計書(Excel)の変換は、必ず `tools/design_to_json.py` で行います。同じ設計書からは毎回まったく同じ出力が得られ、根拠の行番号がずれません。エージェントが独自に変換スクリプトを書いたり、変換結果を手で直したりしてはいけません。
- 変換結果のうち、`{シート名}.json` が正本、`{シート名}.md` が閲覧用です。値を転記するときは JSON の値をそのまま使います。
- 変換結果には、セルの値に加えて、図形・テキストボックスの文字、コメント、書式の目印(取り消し線・文字色・背景色)、数式、表示形式、入力規則、画像ファイルが含まれます。**要件の手がかりはセルの値だけでなく、これらすべてです。**
- 取り消し線は「削除された記載」、赤字などの文字色は「変更された記載」の目印であることが多いですが、設計書の書き方によります。意味の解釈に迷う場合は仮定(ASM)を立てます。方針ファイルに設計書の書き方の決まりがあれば、それに従います。
- `index.json` の not_captured に載っている情報(画像の中身、埋め込みオブジェクトなど)は変換されていません。調査に必要そうな場合は課題(ISS, kind: not_investigated)に記録します。
- 名前や書式の目印から設計書の箇所を探すときは、`tools/find_in_design.py` を使います。

### 根拠と確信度
- すべての項目に根拠を付けます。
  - 設計書のセル: `00_scope/design/{ブック名}/{シート名}.md#L{行}`(行番号は元のExcelの行番号で、.json と共通)
  - 設計書の図形: `00_scope/design/{ブック名}/{シート名}.md#S{番号}`
  - ソース: `{source_root からの相対パス}:{行}`
- 確信度
  - 高: 根拠となる記述・コードを実際に読んで確認した
  - 中: 根拠はあるが、解釈や追跡の一部が推測
  - 低: 命名や構成からの推測で、直接の根拠がない

### 仮定・課題・決定事項
- 仮定(assumptions.yaml): 設計書やコードからは決めきれず、ある解釈を採用したもの。エージェントが追加する
- 課題(issues.yaml): 他フェーズの誤り・漏れ、設計書の矛盾、調査できなかった範囲。エージェントが追加する
- 決定事項(decisions.yaml): ユーザーが判断したこと。オーケストレータだけが追加する
- IDは既存の最大番号の続きから振ります。並列で動くエージェント同士が同じIDを振らないよう、仮定と課題のIDには担当エージェントの略号を付けます(例: `ASM-p1a-001`、`ISS-p1c-002`)。既存の項目は書き換えません(status はオーケストレータだけが更新します)。

### 差し戻しとレビュー指摘への対応
- feedback(ユーザーの差し戻し)とレビュー指摘(review/phase{N}_check.yaml)は、すべて対応し、対応内容を meta.feedback_response に書きます。
- 対応できない指摘は、その理由を書きます。黙って無視してはいけません。

### 共通処理の扱い(全フェーズ共通の方針)
共通処理(複数の機能・画面から呼ばれる処理、共通パッケージや基底クラスにある処理)に手を入れる場合は、**必ず他の呼び出し元を確認し、全体的な修正か部分的な修正かを判断します**。
- フェーズ1は、共通部品を洗い出します(project_profile.yaml の common_components)。
- フェーズ2は、変更対象が共通処理かどうかを判定して印を付けます(shared_component)。
- フェーズ3は、印の付いた変更について全呼び出し元を洗い出し、全体修正か部分修正かを判断します(common_components.yaml)。
- フェーズ4は、その判断(ユーザー承認済み)に従って製造タスクを作ります。

### 現行ソースの書き方の尊重
製造で書かれるコードは、現行ソースの書き方・設計方針に合わせます。そのためフェーズ1でコーディング規約と設計方針を読み取り(coding_conventions.yaml)、フェーズ2の変更内容とフェーズ4の製造タスクは、該当する規約(CNV)を必ず参照します。

---

## 第2部 フェーズとエージェントの構成

承認はフェーズ単位です。各フェーズは「作業エージェント → レビュー担当(impact-reviewer)→ ユーザー承認」の順に進みます。
レビュー担当は作業に関わっていない立場で成果物を点検し、問題がなければユーザーへの承認依頼に進みます(製造フェーズで想定している「エージェント内で承認してから利用者に承認を求める」流れと同じ型です)。

| フェーズ | 段 | エージェント | 主な成果物 | 並列 |
|---|---|---|---|---|
| 0 スコープ確定 | 1 | impact-p0a-design-converter | 00_scope/design/ | |
| | 2 | impact-p0b-scope-resolver | 00_scope/scope_resolution.yaml | |
| 1 読解 | 1 | impact-p1a-requirements | 01_analysis/requirements.yaml | 3つ並列 |
| | 1 | impact-p1b-codebase-profiler | 01_analysis/project_profile.yaml, coding_conventions.yaml | 〃 |
| | 1 | impact-p1c-entrypoints | 01_analysis/entrypoints.yaml | 〃 |
| 2 変更箇所特定 | 1 | impact-p2-changes | 02_changes/changes.yaml | |
| 3 影響範囲 | 1 | impact-p3a-impacts | 03_impacts/impacts.yaml | 2つ並列 |
| | 1 | impact-p3b-common-components | 03_impacts/common_components.yaml | 〃 |
| 4 製造への引き継ぎ | 1 | impact-p4a-work-planner | 04_handoff/work_plan.yaml | |
| | 2 | impact-p4b-task-writer(タスクを分けて複数) | 04_handoff/tasks/TSK-xxx.md | p4c と並列 |
| | 2 | impact-p4c-test-writer | 04_handoff/test_spec.yaml | p4b と並列 |
| | 3 | impact-p4d-handoff-packager | 04_handoff/README.md, coding_guide.md, handoff_check.yaml | |
| 全フェーズ | 最後 | impact-reviewer | review/phase{N}.md, review/phase{N}_check.yaml | |

同じ「段」のエージェントは互いの成果物を使わないので、同時に動かせます。並列にできるのは、どれも前の段・前のフェーズの成果物だけを入力にしているためです。特にフェーズ1は、フェーズ0で作るスコープ解決(SCP)を共通の入力にし、要件(REQ)と入口(ENT)の双方に SCP の ID を持たせることで、フェーズ2で両者を突き合わせられるようにしています。

---

## 第3部 成果物スキーマ

### リポジトリのディレクトリ

```
input/                              ユーザーが設計書(Excel)を置く場所
policies/                           フェーズごとの方針(オーケストレータが更新)
tools/
├─ design_to_json.py                設計書の決定論的な変換(Excel → JSON / Markdown)
└─ find_in_design.py                変換済み設計書から名前・書式の目印で箇所を探す
work/runs/{run_id}/
├─ state.yaml                       オーケストレータ専用
├─ scope.yaml                       ユーザーの指示を記録したもの(オーケストレータが作る)
├─ 00_scope/
│  ├─ original/                     input/ からコピーした設計書(調査時点の版)
│  ├─ design/{ブック名}/
│  │  ├─ index.json / index.md      シート一覧、元ファイルの SHA-256、取り込めなかった情報
│  │  ├─ {シート}.json              シートの正本データ
│  │  ├─ {シート}.md                閲覧用(行番号 L{行}、図形番号 S{番号} 付き)
│  │  └─ images/                    シートに貼られた画像
│  ├─ conversion_log.yaml
│  └─ scope_resolution.yaml
├─ 01_analysis/
│  ├─ requirements.yaml
│  ├─ project_profile.yaml
│  ├─ coding_conventions.yaml
│  └─ entrypoints.yaml
├─ 02_changes/changes.yaml
├─ 03_impacts/
│  ├─ impacts.yaml
│  └─ common_components.yaml
├─ 04_handoff/                      製造フェーズへの引き継ぎ一式
│  ├─ README.md                     製造フェーズの入口(推奨する製造・承認の流れを含む)
│  ├─ coding_guide.md               製造向けのコーディングガイド(規約と手本)
│  ├─ work_plan.yaml                製造タスク・製造順・進捗欄
│  ├─ tasks/TSK-001.md …            タスクごとの指示書
│  ├─ test_spec.yaml                テスト仕様(新機能・回帰)
│  └─ handoff_check.yaml            引き継ぎの整合確認
├─ shared/
│  ├─ assumptions.yaml
│  ├─ issues.yaml
│  └─ decisions.yaml
└─ review/
   ├─ phase{N}.md                   レビュー資料(承認の観点を含む)
   └─ phase{N}_check.yaml           レビュー担当の点検結果
```

成果物のYAMLはすべて `meta` と `items` を持ちます。YAMLが正本で、Markdown は YAML から作る要約・展開です。

### ID体系

| 接頭辞 | 意味 | 採番するエージェント |
|---|---|---|
| SCP-001 | スコープ解決 | p0b |
| REQ-001 | 要件 | p1a |
| CNV-001 | コーディング規約・設計方針 | p1b |
| ENT-001 | 入口 | p1c |
| CHG-001 | 変更箇所 | p2 |
| IMP-001 | 影響 | p3a |
| CMN-001 | 共通処理の判断 | p3b |
| TSK-001 | 製造タスク | p4a |
| TST-001 | テストケース | p4c |
| RVF-p{N}-001 | レビュー指摘 | reviewer |
| ASM-{略号}-001 | 仮定 | 全エージェント(略号はエージェント名の p0a, p1b など) |
| ISS-{略号}-001 | 課題 | 全エージェント |
| DEC-001 | 決定事項 | オーケストレータ |

3桁ゼロ埋め。一度振ったIDは再利用しません(差し戻しで項目を消しても欠番にする)。

### 共通の meta

```yaml
meta:
  run_id: 20261005-usertel
  phase: 1
  agent: impact-p1a-requirements
  attempt: 1                      # フェーズの差し戻しで再実行するたびに+1
  feedback_response:              # 差し戻し・レビュー指摘への対応(該当するときは必須)
    - feedback: "RVF-p1-003: REQ-004の粒度が粗い"
      response: "REQ-004をREQ-004〜REQ-007に分割"
  not_covered:                    # 入力のIDのうち、この成果物で扱わなかったもの(理由必須)
    - id: SCP-010
      reason: "メッセージ文言のみの変更で、コード上の入口が不要"
  self_check:
    - check: "全SCPがREQまたはnot_coveredに含まれる"
      result: ok                  # ok / ng
      note: ""
```

### scope.yaml(オーケストレータが作る)

ユーザーは、追加開発になった部分を**シート名・イベント名・項目名などの名前で**指示します。書式の目印(例: 赤字の行)で指示することもできます。オーケストレータはその指示を、解釈を加えずにここへ記録します。

```yaml
source_root: C:\work\app
design_docs:                      # input/ からコピーするファイル
  - file: 機能設計書_ユーザー登録.xlsx
    kind: function                # function(機能設計書)/ db(DB設計書)
  - file: DB設計書.xlsx
    kind: db
targets:
  - id: T-01
    file: 機能設計書_ユーザー登録.xlsx
    screen: ユーザー登録画面      # 画面名または画面ID(分かれば)
    sheet: イベント一覧
    by: event                     # 下表の指定方法
    names: ["電話番号認証ボタン押下"]
    change_type_hint: add         # add / modify / delete / 不明なら空
    user_words: "イベント一覧の『電話番号認証ボタン押下』を追加"   # ユーザーの指示の原文
  - id: T-02
    file: 機能設計書_ユーザー登録.xlsx
    sheet: 画面項目定義
    by: format
    format: {font_color: FFFF0000}
    user_words: "画面項目定義の赤字の行が今回の変更"
notes: ""
```

| by | 意味 | 指定するもの |
|---|---|---|
| sheet | シート全体 | (なし) |
| item | 画面項目 | names: 項目名 |
| event | イベント | names: イベント名 |
| process | 処理仕様の節・処理 | names: 処理名・節の見出し |
| message | メッセージ | names: メッセージIDまたは文言の一部 |
| config | 設定 | names: 設定キー |
| table | テーブル全体 | names: テーブル名 |
| column | カラム | names: カラム名 |
| text | 任意の識別文字列 | names: 例 "2026/10"(変更履歴列の値など) |
| format | 書式の目印 | format: {font_color / fill_color / strike} |
| rows | 行範囲(最終手段) | names: 例 "25-31" |

### scope_resolution.yaml(p0b)

```yaml
items:
  - id: SCP-001
    target_id: T-01
    file: 機能設計書_ユーザー登録.xlsx
    sheet: イベント一覧
    matched_name: "電話番号認証ボタン押下"
    rows: [12]                    # 対象行
    block_rows: [12, 13]          # 1つの定義が複数行にまたがる場合の範囲
    shapes: []                    # 対象に含まれる図形(S番号)
    screen_id: SCR-010            # 解決できた画面ID(なければ null)
    screen_name: ユーザー登録画面
    referenced_rows:              # 対象行が参照している既存行(文脈として読む。要件化はしない)
      - "00_scope/design/機能設計書_ユーザー登録/処理仕様.md#L40-L58"
    match_type: exact             # exact / partial / inferred / format
    evidence: ["00_scope/design/機能設計書_ユーザー登録/イベント一覧.md#L12"]
    confidence: 高
meta:
  search_commands:                # 実行した tools/find_in_design.py のコマンドと件数
    - command: "python tools/find_in_design.py … --name 電話番号認証ボタン押下 --sheet イベント一覧"
      hits: 1
  unresolved:                     # 見つからなかった・複数該当した指示
    - target_id: T-03
      name: "確認ボタン"
      reason: "イベント一覧に『確認ボタン押下』が2行ある(L8, L21)"
      candidates: ["…#L8", "…#L21"]
  design_notes:                   # 対象範囲にある、後続が注意すべき情報
    - "SCP-003 の範囲に取り消し線の行(L30)がある"
    - "画面レイアウトに図形 S2 があり、対象画面の注記と思われる"
```

### requirements.yaml(p1a)

```yaml
items:
  - id: REQ-001
    type: ITEM                    # ITEM / EVENT / LOGIC / CONFIG / MSG / DB / LAYOUT
    change_type: add              # add / modify / delete
    scp_ids: [SCP-002]
    screen: SCR-010
    title: 電話番号項目の追加
    detail: {}                    # type別。下表のキーをすべて持つ
    source: ["00_scope/design/機能設計書_ユーザー登録/画面項目定義.md#L27"]
    related: [REQ-005]
    related_note: ""              # スコープ外の既存行との関係
    assumptions: []
    confidence: 高
```

`detail` の必須キー(設計書に記載がなければ値を null にし、ASMを立てる):

| type | 必須キー |
|---|---|
| ITEM | name, physical_name, io(入力/出力/入出力), data_type, length, required, initial_value, validations |
| EVENT | trigger(対象項目と操作), handler_spec(処理仕様の参照先), transition(遷移先) |
| LOGIC | steps(手順の配列), db_access(テーブルと操作の配列), error_cases(エラー条件の配列) |
| CONFIG | file, key, value, purpose |
| MSG | message_id, text, kind(エラー/警告/情報/確認), used_by(参照するREQ) |
| DB | table, column, operation(add_column / modify_column / add_table / add_index など), definition |
| LAYOUT | element(画面上の要素), position(配置), note |

任意キー: `detail.common_hint`(設計書にある「共通処理」等の記載)、`detail.design_marks`(要件の根拠となった書式の目印・コメント・図形の要約)

### project_profile.yaml(p1b)

```yaml
items:
  - key: stack
    value: "Spring Boot 3.2 / Java 17 / Thymeleaf / MyBatis / Maven"
    evidence: ["pom.xml:12", "pom.xml:40"]
    confidence: 高
```

必須キー: stack, build_and_run, package_layout, layering, view_tech, data_access, config_files, message_source, exception_handling, transaction, test_framework, common_components, existing_docs, screen_map

- `build_and_run` の value: `{build, test, run, static_checks}`(コマンド。見つからなければ null)
- `common_components` の value: `[{name, location, kind(共通Service/ユーティリティ/基底クラス/共通JS/共通fragment等), used_by_count, count_method, evidence}]`
- `existing_docs` の value: リポジトリにある規約・設計の資料と設定(README, CONTRIBUTING, docs/, .editorconfig, checkstyle, spotbugs, formatter 設定など)の一覧
- `screen_map` の value: `[{screen_id, screen_name, url, controller, template, evidence}]`(プロジェクト全体の画面のうち分かるもの)

### coding_conventions.yaml(p1b)

現行ソースの書き方と設計方針です。製造フェーズで、既存コードと同じ書き方にするための正本になります。

```yaml
items:
  - id: CNV-001
    kind: coding                  # coding(書き方)/ design(設計方針)
    category: validation          # 下表
    rule: "単項目チェックは Form の Bean Validation、相関チェックは Validator クラスで行う"
    detail: "Validator は org.springframework.validation.Validator を実装し、Controller の @InitBinder で登録する"
    exemplars:                    # 手本(ファイル:行 と、何の手本か)
      - {location: "src/main/java/com/example/item/ItemFormValidator.java:15", what: "相関チェックの実装"}
    strength: consistent          # enforced(ツール設定で強制)/ consistent(全体で一貫)/ majority(多数派)/ mixed(混在)
    counter_examples: []          # 規約に反する既存箇所(mixed / majority のとき)
    evidence: ["…ItemFormValidator.java:15", "…UserFormValidator.java:12", "…ItemController.java:30"]
    confidence: 高
```

| category | 主な観点 |
|---|---|
| naming | クラス・メソッド・変数・定数・URL・テンプレート・メッセージキー・テーブルの命名 |
| formatting | インデント、改行、import の順、ファイルの文字コード |
| structure | パッケージの切り方、クラスの責務分割、1クラスの大きさ |
| controller | ハンドラの書き方、画面遷移、リダイレクト、モデルへの詰め方 |
| service | トランザクション境界、業務ロジックの置き場所、戻り値の型 |
| data_access | Mapper/Repository の書き方、SQL の書き方(動的SQL、resultMap)、楽観ロック |
| validation | 単項目・相関チェックの置き場所と書き方 |
| view | テンプレートの共通化、フォームの書き方、エラー表示 |
| javascript | JS の置き場所、ライブラリ、書き方 |
| exception | 例外クラスの使い分け、エラー画面、業務エラーの返し方 |
| logging | ロガーの取得方法、ログレベルの使い分け、出力内容 |
| messages | メッセージキーの付け方、プレースホルダ |
| null_handling | null・Optional の扱い |
| object_mapping | Form・DTO・Entity の詰め替え方法 |
| annotations | Lombok などのアノテーションの使い方 |
| comments | Javadoc・コメントの有無と言語 |
| test | テストの書き方、命名、置き場所、使うモック |
| security | 認証・認可・入力の無害化 |
| layer_responsibility | (design)各層の責務と、層をまたぐ呼び出しの決まり |
| other | 上記以外 |

### entrypoints.yaml(p1c)

フェーズ1で要件抽出と並列に作るため、要件(REQ)ではなくスコープ解決(SCP)を単位にします。REQ との突き合わせはフェーズ2で行います。

```yaml
meta:
  screen_map:                     # 今回の対象画面とコードの対応
    - screen_id: SCR-010
      screen_name: ユーザー登録画面
      url: /user/register
      controller: src/main/java/com/example/user/UserController.java
      template: src/main/resources/templates/user/register.html
      evidence: ["…UserController.java:25", "…register.html:3"]
      confidence: 高
items:
  - id: ENT-001
    scp_ids: [SCP-001, SCP-002]
    kind: existing                # existing(既存コードに入口がある)/ new(新規に作る必要がある)
    layer: view                   # view / controller / form / service / repository / mapper_sql / entity / config / message / js / migration / other
    location: src/main/resources/templates/user/register.html:55   # new の場合は配置候補(隣接する既存ファイルを根拠に)
    symbol: "form#userForm"
    description: 入力フォーム本体。電話番号項目の追加先
    is_common_component: false    # project_profile の共通部品に当たりそうなら true(判断はフェーズ2・3)
    evidence: ["src/main/resources/templates/user/register.html:55"]
    assumptions: []
    confidence: 高
```

### changes.yaml(p2)

```yaml
meta:
  req_ent_map:                    # REQ と ENT の突き合わせ結果(SCP を介して対応付け、コードで確認)
    - req_id: REQ-001
      ent_ids: [ENT-001, ENT-004]
  trace_log:
    - "ENT-001: register.html:55 → UserController#register:40 → UserService#register:22 → UserMapper.xml:15"
items:
  - id: CHG-001
    req_ids: [REQ-001]
    ent_ids: [ENT-003]
    layer: service
    file: src/main/java/com/example/user/UserService.java
    target: UserService#register
    action: modify                # new / modify / delete
    shared_component: false       # 共通処理への変更なら true
    shared_reason: ""             # true の理由(例: "CommonValidator は 12 画面から呼ばれている")
    before: "入力値をそのまま登録する"
    after: "登録前に電話番号の重複チェックを行い、重複時は DuplicateException を送出する"
    detail:
      - "UserMapper に countByTel(String tel) を追加して呼ぶ(CHG-004)"
      - "例外メッセージキーは MSG-E021(REQ-012)"
    conventions: [CNV-004, CNV-011]   # この変更で従う規約・設計方針
    reference: ["src/main/java/com/example/item/ItemService.java:88"]
    depends_on: [CHG-004]
    assumptions: []
    confidence: 中
```

### impacts.yaml(p3a)

```yaml
meta:
  search_log:                     # 全CHGについて必須。影響なしでも記録
    - chg_id: CHG-001
      searched: ["UserService#register の呼び出し元を全検索", "users テーブルを参照するSQLを全検索"]
      result: impact              # impact / none
items:
  - id: IMP-001
    chg_ids: [CHG-001]
    impact_type: caller           # caller / shared_data / common_component / view / config / message / transaction / batch / external / other
    affected: "一括取込(BatchImportService#execute)"
    evidence: ["src/main/java/com/example/batch/BatchImportService.java:130"]
    risk: "一括取込でも重複チェックが走り、従来成功していたデータがエラーになる"
    severity: 高                  # 高 / 中 / 低
    test_points: ["一括取込で重複電話番号を含むデータを流す"]
    assumptions: []
    confidence: 高
```

### common_components.yaml(p3b)

```yaml
items:
  - id: CMN-001
    chg_ids: [CHG-007]
    component: "CommonValidator#validateTel"
    location: src/main/java/com/example/common/CommonValidator.java:30
    callers:                      # 全呼び出し元(1件も省略しない)
      - location: src/main/java/com/example/user/UserForm.java:22
        feature: ユーザー登録(今回の対象)
        is_target: true
        wants_new_behavior: yes   # yes / no / unknown
        evidence: ["…UserForm.java:22"]
      - location: src/main/java/com/example/shop/ShopForm.java:40
        feature: 店舗登録
        is_target: false
        wants_new_behavior: no
        evidence: ["…ShopForm.java:40"]
    decision: partial             # global(全体修正)/ partial(部分修正)
    partial_method: new_method    # partial の場合: new_method / overload / parameter / subclass / new_component
    precedent: "src/main/java/com/example/common/CommonValidator.java:80(validateZipStrict を別メソッドで追加した先例)"
    rationale: "店舗登録は従来の形式を許容する必要があり、全体修正すると既存データが不正になる"
    global_impact: "全体修正した場合、店舗登録・取引先登録の2機能で入力チェック結果が変わる"
    conflicts_with_chg: true      # CHGの内容とこの判断が食い違うか
    assumptions: []
    confidence: 中
```

### work_plan.yaml(p4a)

```yaml
meta:
  verification:                   # 製造時の確認コマンド(project_profile の build_and_run から)
    build: "mvn -q compile"
    test: "mvn -q test"
    static_checks: "mvn -q checkstyle:check"
  open_items:                     # 製造開始時点で未決の事項(open な ASM / ISS)
    - id: ASM-p1a-002
      affects: [TSK-004]
items:
  - id: TSK-001
    title: M_USER に TEL / TEL_VERIFIED カラムを追加
    chg_ids: [CHG-001]
    cmn_ids: []
    dec_ids: []
    files: [src/main/resources/db/migration/V20__add_tel.sql]
    order: 1                      # 製造順
    depends_on: []
    size: S                       # S / M / L(L は分割を検討)
    done_criteria: ["マイグレーション適用後、M_USER に2カラムが存在する"]
    tst_ids: [TST-003]            # p4d が埋める
    risk_level: 低                # 関係する IMP の最大 severity(なければ 低)
    status: todo                  # 製造フェーズが更新する: todo / in_progress / self_checked / internal_approved / user_approved / done / blocked
    note: ""                      # DECでCHGの内容を変えた場合などの補足
```

### tasks/TSK-xxx.md(p4b)

製造担当がこの1ファイルと coding_guide.md だけで作業し、自分で確かめ、内部レビューを通せるように書きます。

```markdown
# TSK-001 {タイトル}

## 目的
## 対象ファイルと変更内容      (CHGごとに: ファイル / 対象 / 変更前 / 変更後 / 指示 / シグネチャ)
## 使う値                      (項目定義・メッセージ文言・設定値を、設計書を見なくて済むよう転記)
## 従う書き方                  (関係する CNV の rule と手本。coding_guide.md の該当節)
## 守るべき既存の振る舞い      (IMP・CMN から)
## 参考実装
## 確定済みの判断              (DEC・確定したASM・CMNの判断)
## 未決事項                    (open な ASM / ISS と、それぞれの現在の仮定。なければ「なし」)
## 前提タスク
## 完了条件                    (観察可能な条件)
## 検証手順                    (実行するコマンドと、確かめる関連テスト)
## 関連テスト                  (TST ID と一行要約。p4d が埋める)
## セルフレビュー観点          (製造担当が提出前に自分で確かめること)
## 内部レビューの合格基準      (製造フェーズのレビュー役が合否を判断する基準)
## 利用者承認の観点            (内部レビュー合格後、利用者が見るべき点)
## 作業を止めて確認する条件    (エスカレーション条件)
## トレース                    (REQ / ENT / CHG / IMP / CMN / CNV / DEC の ID)
```

### test_spec.yaml(p4c)

```yaml
items:
  - id: TST-001
    kind: new                     # new(新機能の確認)/ regression(既存機能の回帰)
    title: 電話番号が未入力の場合は登録できない
    req_ids: [REQ-001]
    imp_ids: []
    cmn_ids: []
    tsk_ids: [TSK-003]
    level: unit                   # unit / integration / screen
    precondition: "ユーザー登録画面を表示している"
    steps: ["電話番号を空欄のまま登録ボタンを押す"]
    expected: "MSG-E020『電話番号を入力してください』が表示され、登録されない"
    priority: 高                  # 高 / 中 / 低
    automation: "UserFormTest に追加(既存のテスト構成に合わせる)"   # 自動テストにする場合の置き場所。手動なら manual
```

### handoff_check.yaml(p4d)

```yaml
items:
  - check: "全CHGがいずれかのTSKに含まれる"
    result: ok                    # ok / ng
    detail: ""
meta:
  verdict: ready                  # ready(引き継ぎ可)/ ready_with_open_items / not_ready
  open_items: [ASM-p1a-002]
```

### review/phase{N}_check.yaml(reviewer)

```yaml
meta:
  run_id: 20261005-usertel
  phase: 1
  agent: impact-reviewer
  review_round: 1                 # 同じ attempt の中でレビューした回数
  verdict: pass_with_notes        # pass / pass_with_notes / fail
findings:
  - id: RVF-p1-001
    severity: major               # blocker / major / minor
    target_agent: impact-p1a-requirements
    description: "SCP-004 の対象行 L33 の取り消し線が、REQ に反映されていない"
    evidence: ["00_scope/design/…/画面項目定義.md#L33"]
    suggestion: "削除の要件(change_type: delete)として扱うか、仮定を立てる"
approval_points:                  # 第5部のフェーズ別の承認観点ごとの確認結果
  - point: "指示ごとの要件の件数と粒度は妥当か"
    status: needs_user_judgement  # ok / needs_user_judgement / ng
    note: "T-03 から要件が7件出ている。細かすぎないか確認してほしい"
    refs: [REQ-010, REQ-016]
```

### shared/assumptions.yaml

```yaml
items:
  - id: ASM-p1a-001
    phase: 1
    statement: "電話番号はハイフンなしで保存する"
    reason: "画面項目定義に形式の記載がない"
    affects: [REQ-001]
    status: open                  # open / confirmed / rejected(更新はオーケストレータのみ)
```

### shared/issues.yaml

```yaml
items:
  - id: ISS-p2-001
    raised_phase: 2
    target_phase: 1               # 問題があるフェーズ(raised_phase 以下)
    kind: omission                # error / omission / contradiction / not_investigated / conflict
    description: "処理仕様にある監査ログ出力が要件化されていない"
    evidence: ["00_scope/design/機能設計書_ユーザー登録/処理仕様.md#L52"]
    related_ids: [REQ-006]
    status: open                  # open / resolved / deferred(更新はオーケストレータのみ)
    resolution: ""                # 対応した DEC ID など
```

### shared/decisions.yaml(オーケストレータのみ)

```yaml
items:
  - id: DEC-001
    phase: 3
    about: [CMN-001, ISS-p3b-001]
    decision: "CommonValidator は部分修正(新メソッド追加)とする。CHG-007 の内容よりこちらを優先する"
    user_words: "店舗登録には影響させたくないので部分修正で"
    decided_at: 2026-10-05T21:30:00+09:00
```

---

## 第4部 全エージェント共通の完了チェック

各作業エージェントは終了前に、レビュー担当はフェーズの点検で、次を確認します。

1. 成果物のYAMLが読める形式で、meta と items がある
2. 全項目の id が形式どおりで、重複がない
3. 第3部で必須とされている項目がすべて埋まっている(null を許すのは detail の値だけで、その場合は対応するASMがある)
4. 選択肢が決まっている項目(type, action, confidence など)が許可された値だけを使っている
5. 参照しているIDがすべて実在する
6. 入力のIDがすべて、この成果物のどこかで参照されているか、meta.not_covered に理由付きで載っている
7. 差し戻し・レビュー指摘があった場合、meta.feedback_response がある
8. issues.yaml の target_phase が raised_phase を超えていない
9. decisions.yaml の決定事項が、関係する項目に反映されている

---

## 第5部 完了報告・レビュー・承認の観点

### 完了報告(作業エージェントの最後の応答)
サブエージェントは最後の応答だけがオーケストレータに渡るので、次の形式で必要なことをすべて書きます。

```
## {エージェント名} 完了報告(フェーズN / attempt n)
- 成果物: {作成・更新したファイルのパス}
- 件数: {種別ごとの件数}
- 確信度「低」: {件数と ID}
- 新しい仮定: {ASM ID と一行要約}
- 新しい課題: {ISS ID、target_phase、一行要約}
- self_check で ng: {項目と理由。なければ「なし」}
- 差し戻し・レビュー指摘への対応: {該当するとき、指摘ごとの対応の要約}
- 方針への提案: {手順や方針の改善案。なければ「なし」}
```

### レビュー担当の報告(impact-reviewer の最後の応答)

```
## impact-reviewer 点検報告(フェーズN / attempt n / review_round r)
- 判定: pass / pass_with_notes / fail
- 差し戻し先: {blocker・major の指摘があるエージェントと、指摘ID}
- ユーザーの判断が必要な観点: {件数と要約}
- レビュー資料: review/phase{N}.md
```

### レビュー資料(review/phase{N}.md)
レビュー担当がフェーズ全体について書きます。YAMLの全文を貼らず、承認の判断に必要なことだけを書きます。

```markdown
# フェーズN {フェーズ名} レビュー資料(attempt {n})

## 承認の観点                  (下記のフェーズ別の観点ごとに: 確認結果 / ユーザーに判断してほしいこと / 参照ID)
## サマリ                      (件数と、確信度の内訳)
## 特に確認してほしい項目      (確信度「低」、フェーズ3では severity「高」と共通処理の判断、フェーズ4では未決事項)
## レビュー担当の指摘          (minor を含む全指摘と、作業エージェントの対応状況)
## 差し戻しへの対応
## 入力から引き継がなかった項目
## このフェーズで立てた仮定 / 見つけた課題   (前のフェーズへの差し戻し候補は目立つように分ける)
## 一覧
## トレーサビリティ            (フェーズ2以降。指示 → 要件 → 入口 → 変更 → 影響 → タスク → テスト のうち、そのフェーズまで)
## 完了チェックの結果
```

### フェーズ別の承認の観点
レビュー担当は、次の観点ごとに確認結果を approval_points に書き、レビュー資料の冒頭に載せます。オーケストレータは承認依頼のときに、この観点をユーザーに示します。

**フェーズ0 スコープ確定**
1. 指示したすべての箇所が、設計書の正しいシート・行(図形)に当たっているか
2. 見つからなかった指示・複数の候補がある指示はどれか
3. 指示に含まれていないが、対になっていて対象に加えるべき箇所はないか(指示の漏れの可能性)
4. 対象範囲に、取り消し線・文字色・コメント・図形など、セルの値以外の手がかりがあるか。その扱いはよいか
5. 取り込めなかった情報(画像の中身・埋め込みオブジェクトなど)に、要件にかかわるものがないか

**フェーズ1 読解**
1. 指示ごとの要件の件数と粒度は妥当か。漏れや過剰はないか
2. 立てた仮定(設計書に記載のない値の解釈)は正しいか
3. 対象画面とコード(URL・Controller・テンプレート)の対応は正しいか
4. 読み取ったコーディング規約・設計方針は、実際のチームの書き方と合っているか(特に strength が majority / mixed のもの)
5. 入口の位置は正しいか。新規に作るものの配置候補は妥当か

**フェーズ2 変更箇所特定**
1. 変更内容は要件を満たしているか(要件ごとに変更が揃っているか)
2. 新規作成と既存修正の切り分けは妥当か
3. 共通処理への変更の判定(shared_component)に漏れはないか
4. 変更内容が規約・設計方針(CNV)に沿っているか
5. 製造順(依存関係)は妥当か

**フェーズ3 影響範囲**
1. 共通処理ごとの、全体修正か部分修正かの判断は妥当か(ユーザーの決定が必要)
2. severity「高」の影響と、その回帰テスト観点は妥当か
3. 「影響なし」とした変更の検索範囲は十分か
4. フェーズ2の変更内容と食い違う判断がある場合、どちらで解消するか

**フェーズ4 製造への引き継ぎ**
1. 引き継ぎの判定(ready / ready_with_open_items / not_ready)と、その理由
2. 未決事項を残したまま製造に進んでよいか
3. タスクの粒度と製造順は妥当か
4. テスト仕様で、要件と severity「高」の影響が網羅されているか
5. 製造フェーズの承認フローで使う観点(セルフレビュー観点・内部レビューの合格基準・利用者承認の観点)は妥当か
