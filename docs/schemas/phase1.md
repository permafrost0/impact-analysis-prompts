# 成果物の形式: フェーズ1 要件の抽出

共通の項目(meta、根拠、question、assumptions、issues)は `common.md` を見てください。

## scope.yaml(オーケストレータが作る)

```yaml
run_id: 20261007-usertel
title: ユーザー登録への電話番号認証の追加
source_root: C:/work/app            # 調査対象のソースのルート
design_docs:                        # input/target/ に置かれた、追加開発の設計書
  - file: 機能設計書_ユーザー登録.xlsx
    sheets: [画面項目定義, イベント一覧, 処理仕様, メッセージ一覧]   # 指示されたシート("*" は全シート)
sheet_tags:                         # 対象シートごとのタグ(p1b の作業者タグになる)
  - {tag: S1, file: 機能設計書_ユーザー登録.xlsx, sheet: 画面項目定義}
  - {tag: S2, file: 機能設計書_ユーザー登録.xlsx, sheet: イベント一覧}
instructions:                       # ユーザーの指示を、解釈を加えずに記録したもの
  - id: T-01
    sheets: [S1, S2, S3, S4]        # 対象のシートタグ
    how: marker                     # marker(書式の目印)/ name(名前)/ whole_sheet(シート全体)/ text(識別文字列)/ rows(行範囲)
    marker: "変更は赤字、削除は取り消し線"   # how: marker のとき(ユーザーの言葉のまま)
    names: []                       # how: name のとき
    text: ""                        # how: text のとき(例: "2026/10")
    rows: ""                        # how: rows のとき(例: "25-31")
    change_hint: ""                 # add / modify / delete / 空
    user_words: "4シートが対象。変更箇所は赤字、削除は取り消し線"   # 原文。見分け方を方針で代用したときは「(見分け方は POL-common-001 による)」
reference_docs: [会員管理設計書.xlsx]   # input/reference/ に置かれたファイル(中身は読まない)
notes: ""
```

## scope_resolution.yaml(p1a-scope)

```yaml
meta: {...}
items:
  - id: SCP-001
    instruction: T-01
    sheet_tag: S1
    rows: [27, 28]                  # 対象の行(続きの行も含める)
    header_rows: [3]                # 列の意味が分かる見出し行
    shapes: []                      # 対象に含まれる図形(S番号)
    match: marker                   # exact / normalized / partial / marker / whole_sheet / text / rows / inferred
    evidence: ["sheet:機能設計書_ユーザー登録/画面項目定義#L27-L28"]
    note: "L27・L28 が赤字"
    confidence: 高
unresolved:                         # 範囲を決められなかった指示(フェーズの途中でユーザーに確認する)
  - instruction: T-02
    reason: "『認証コード』という項目名がない"
    candidates: ["sheet:機能設計書_ユーザー登録/画面項目定義#L28"]
    question: {text: "L28『認証コード入力』を対象にしてよいですか?", answer_examples: ["はい", "対象外"]}
out_of_scope_refs:                  # 対象の行が、指示されていないシートを指しているもの(フェーズの途中でユーザーに確認する)
  - from: "sheet:機能設計書_ユーザー登録/処理仕様#L55"
    quote: "外部IF定義シート参照"
    question: {text: "「外部IF定義」シートは指示に含まれていません。対象に加えますか?", answer_examples: ["加える", "加えない"]}
assumptions: []
issues: []
```

- 指示された全シートのうち、対象の行がないシートは SCP を作らず、`meta.not_covered` に「シートタグ: 理由」を書きます(id には シートタグを書く)。
- 対象の行が範囲に入っていない書式の目印(例: 指示は赤字だが、取り消し線の行もある)は、`issues`(kind: omission、ask_user: true)にします。

## extract/{シートタグ}.yaml(p1b-extract、シートごとに1ファイル)

```yaml
meta: {...}                         # worker: p1b-S1
sheet: {tag: S1, file: 機能設計書_ユーザー登録.xlsx, sheet: 画面項目定義}
items:
  - id: REQ-S1-001
    category: new                   # new(新規)/ change(変更)/ delete(削除)/ reuse(既存の流用)
    type: ITEM                      # ITEM / EVENT / LOGIC / MSG / CONFIG / DB / LAYOUT / OTHER
    title: 電話番号の入力項目
    summary: "ユーザー登録画面に電話番号の入力項目を追加する"
    values:                         # 設計書の値を、見出し行の言葉をキーにしてそのまま写す
      項目名: 電話番号
      物理名: tel
      型: 文字列
      桁: "11"
      必須: ○
    scp_ids: [SCP-001]
    source: ["sheet:機能設計書_ユーザー登録/画面項目定義#L27"]
    category_basis: "赤字(指示の目印)"   # 区分の根拠
    confidence: 高
  - id: REQ-S3-004
    category: reuse
    type: LOGIC
    title: 電話番号の入力チェック
    summary: "既存の会員登録の入力チェックを流用する"
    values: {}
    scp_ids: [SCP-007]
    source: ["sheet:機能設計書_ユーザー登録/処理仕様#L47"]
    category_basis: "「既存設計を参照」の記述"
    reuse:                          # category: reuse のとき必須
      quote: "入力チェックは既存設計(会員管理設計書 4.2)を参照"   # 原文
      clues: [会員登録, 入力チェック]    # 既存機能を探す手がかり
      identified_by: heading         # text(対象の行の言葉だけで特定)/ heading(参照先の見出しで特定)/ none(特定できない)
      heading_refs: ["heading:会員管理設計書/処理仕様#L30"]   # identified_by: heading のとき
    question: {text: "参照先の見出し「4.2 会員登録 入力チェック」から、流用先を「会員登録の入力チェック」と特定しました。正しいですか?", answer_examples: ["はい"]}
    confidence: 中
excluded:                           # 対象の行のうち、要件にしなかった記述(reason: ambiguous は1箇所に1件。同じ箇所に判断に困る表現が複数あれば、1件にまとめて quote に並べる)
  - source: "sheet:機能設計書_ユーザー登録/処理仕様#L52"
    quote: "必要に応じて認証コードを再送信できること"
    reason: ambiguous               # ambiguous(判断に困る表現)/ existing_description(既存の説明)/ note_only(注記のみ)
    question: {text: "「必要に応じて再送信できること」は、今は要件にしていません。要件にしますか?", answer_examples: ["要件にする", "対象外"]}   # ambiguous のとき必須
reference_reads:                    # 参照先の見出しを読んだ記録(読んだときだけ)
  - file: 会員管理設計書.xlsx
    command: "python tools/list_headings.py input/reference/会員管理設計書.xlsx --grep 入力チェック"
    found: "処理仕様 L30: 4.2 会員登録 入力チェック"
    purpose: "REQ-S3-004 の流用先の機能名を特定するため"
assumptions: []
issues: []
```

- `values` には、設計書のセルの値を**そのまま**写します(言い換え・全角半角の統一をしない)。数値も文字列として写します。
- 要件ごとに、`scp_ids` の SCP の行だけを根拠にします。見出し行以外の既存の行は読みません。
- `values` に null は入れません。設計書に書かれていない値は、キーごと省き、必要なら仮定(assumptions)を立てます。

## requirements.yaml(p1c-integrate、要件の正本)

```yaml
meta:
  ...
  changes:                          # extract から内容を変えた項目(理由必須。値は変えない)
    - {id: REQ-S2-003, field: title, from: "...", to: "...", reason: "..."}
features:
  - id: F-01
    name: 電話番号の入力
    category: new                   # new / change / delete / reuse / mixed
    summary: "ユーザー登録画面に電話番号の入力項目を追加し、チェックして保存する"
    req_ids: [REQ-S1-001, REQ-S3-004, REQ-S4-001]
items:                              # extract の全要件を写し、feature と related を足したもの
  - id: REQ-S1-001
    feature: F-01
    related: [REQ-S3-004]           # 関係する要件(シートをまたいでよい)
    # 以下は extract と同じ項目(category, type, title, summary, values, scp_ids, source, category_basis, reuse, question, confidence)
excluded: []                        # 全 extract の excluded を写したもの。関係する機能が分かるものには feature: F-01 を足す(なければ省く)
reference_reads: []                 # 全 extract の reference_reads を写したもの
cross_refs:                         # 対応する相手が、指示されたシートにない関係
  - from: REQ-S2-001
    note: "処理仕様 3.2 を呼ぶが、処理仕様 3.2 の行は対象範囲にない"
assumptions: []
issues: []
```

- extract の要件は、**すべて** items に写します(重複をまとめる場合は、残さない側を `meta.not_covered` に理由付きで書く)。
- `values` と `source` は extract から変えません。title・summary・category を変えるときは `meta.changes` に記録します。
- ユーザーの判断で要件を追加するときだけ、`REQ-I-001` の形で新しく作ります。
- 全要件が、いずれかの機能の `req_ids` に入ります。機能は、利用者から見た機能のまとまり(例:「電話番号の入力」「電話番号の認証」)で分けます。層(画面・DB)で分けません。
