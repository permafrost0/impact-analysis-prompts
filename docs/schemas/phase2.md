# 成果物の形式: フェーズ2 懸念事項の抽出

共通の項目(meta、根拠、excerpt、question、assumptions、issues)は `common.md` を見てください。
このフェーズの根拠は、**すべてコード(`code:`)** です。設計書は「何を変えるか」(要件)としてだけ使います。

## reuse.yaml(p2a-reuse)

```yaml
meta: {...}
items:
  - id: RUS-001
    req_ids: [REQ-S3-004]
    feature: F-01
    target: "MemberFormValidator#validate"
    location: "code:src/main/java/com/example/member/MemberFormValidator.java:22"
    excerpt: {file: src/main/java/com/example/member/MemberFormValidator.java, start: 22, end: 30}
    behavior: "電話番号を CommonValidator#validateTel でチェックする。ハイフンありを許容する"   # コードから読み取った今の振る舞い
    fit: partial                    # as_is(そのまま使える)/ partial(一部合わない)/ not_fit(使えない)
    how_to_reuse: "Validator クラスで相関チェックを行う構成を流用する"
    gap: "ハイフンありを許容しているため、ハイフンなしの要件には合わない"   # fit が as_is 以外のとき必須
    searched: ["会員登録", "MemberForm", "Validator"]   # 探した言葉
    confidence: 高
changes: []                         # 流用のために必要な修正(CHG-R-001 の形。形は changes/{F-xx}.yaml の items と同じ)
not_found:                          # 流用先が見つからなかった要件
  - req_id: REQ-S2-005
    clues: [本人確認]
    searched: ["本人確認", "Identity", "Verify"]
    question: {text: "「本人確認」に当たる既存処理が見つかりません。どの機能のことですか?", answer_examples: ["会員登録の本人確認(MemberVerifyService)"]}
assumptions: []
issues: []
```

## changes/{F-01}.yaml(p2b-changes、機能ごとに1ファイル)

```yaml
meta: {...}                         # worker: p2b-F01
feature: F-01
flow:                               # 今の処理の流れ(この機能が通る既存の流れ。コードから。修正が1件でもあれば必須。削除だけの機能でも、削除する項目が通る流れを書く)
  - order: 1
    location: "code:src/main/java/com/example/user/UserController.java:25"
    symbol: "UserController#showRegister"
    behavior: "GET /user/register で user/register.html を表示する"
items:
  - id: CHG-F01-001
    req_ids: [REQ-S1-001]
    file: src/main/resources/templates/user/register.html
    symbol: "入力フォーム(氏名欄の後)"     # クラス#メソッド、要素など
    action: modify                  # new / modify / delete
    layer: view                     # view / controller / form / validator / service / repository / mapper_sql / entity / dto / config / message / migration / js / batch / other
    location: "code:src/main/resources/templates/user/register.html:42"   # modify / delete は必須
    excerpt: {file: src/main/resources/templates/user/register.html, start: 42, end: 48}   # modify / delete は必須
    before: "氏名とメールアドレスの入力欄がある"   # 今の振る舞い(new は「なし」)
    after: "氏名の後に電話番号の入力欄がある。エラー表示は氏名欄と同じ書き方"
    detail: ["th:field は *{tel}", "ラベルは label.user.tel"]
    shared: false                   # 共通処理(他の機能からも使われる箇所)への変更なら true
    shared_reason: ""               # shared: true のとき必須(例: "3か所から呼ばれている")
    reference: ["code:src/main/resources/templates/member/register.html:40"]   # 手本にする既存実装
    depends_on: []                  # 先に必要な修正(CHG ID)
    confidence: 高
premise_broken:                     # 設計書の変更を、コードに当てはめられないもの
  - req_id: REQ-S1-004
    description: "『FAX番号』の項目を削除とあるが、コードに fax の項目がない"
    searched: ["fax", "FAX"]
    question: {text: "FAX番号の項目がコードにありません。削除の要件は不要ですか?", answer_examples: ["不要", "別の項目のこと"]}
assumptions: []
issues: []
```

- この機能の全要件(category が reuse 以外)を、いずれかの修正の `req_ids` に入れます。入れないものは `meta.not_covered` か `premise_broken` に書きます。
- 修正の ID は、機能の番号つき(`CHG-F01-001`)にします。

## impacts.yaml(p2c-impacts)

```yaml
meta: {...}
search_log:                         # 全修正について必須。影響がなくても書く
  - chg_id: CHG-F01-002
    searched: ["UserForm を使うクラス", "tel を参照する箇所"]
    result: impact                  # impact / none
items:
  - id: IMP-001
    chg_ids: [CHG-F01-003]
    feature: F-01                   # 原因の修正が属する機能
    affected: "店舗登録"
    location: "code:src/main/java/com/example/shop/ShopFormValidator.java:31"
    excerpt: {file: src/main/java/com/example/shop/ShopFormValidator.java, start: 28, end: 34}
    current_use: "店舗の電話番号を validateTel でチェックしている"
    risk: "validateTel を変えると、ハイフンありの電話番号がエラーになる"
    severity: 高                    # 高(結果が変わる・エラーになる)/ 中(結果は変わらないが表示・性能などが変わる)/ 低(念のため確認)
    handling: "部分修正にすれば影響しない(CMN-001)"
    test_points: ["店舗登録で 03-1234-5678 が登録できる"]   # 重大度 高 は必須
    confidence: 高
assumptions: []
issues: []
```

影響は「今回の修正によって、**既存の機能**がどう変わるか」です。今回の機能を作るうえでの危うさは concerns.yaml に書きます。

## common_components.yaml(p2d-common)

```yaml
meta: {...}
search_log:
  - chg_id: CHG-F01-003
    searched: ["validateTel の呼び出し元"]
    result: shared                  # shared(他の機能からも使われる)/ not_shared
items:
  - id: CMN-001
    chg_ids: [CHG-F01-003]
    features: [F-01, F-02]
    component: "CommonValidator#validateTel"
    location: "code:src/main/java/com/example/common/CommonValidator.java:30"
    excerpt: {file: src/main/java/com/example/common/CommonValidator.java, start: 30, end: 36}
    callers:                        # 全呼び出し元(1件も省かない)
      - location: "code:src/main/java/com/example/shop/ShopFormValidator.java:31"
        feature_name: 店舗登録
        is_target: false            # 今回の追加機能からの呼び出しか
        usage: "店舗の電話番号の形式チェック"
        needs_new_behavior: "no"    # "yes" / "no" / "unknown"(コードでの使われ方から判断する)
    decision: partial               # global(全体修正)/ partial(部分修正)
    method: new_method              # partial のとき: new_method / overload / parameter / subclass / new_component
    precedent: "code:src/main/java/com/example/common/CommonValidator.java:80"   # 同様の先例(任意)
    rationale: "店舗登録・取引先登録はハイフンありを許容しているため"
    if_global: "店舗登録・取引先登録で、ハイフンありの電話番号がエラーになる"   # 全体修正した場合(partial でも必須)
    conflicts_with_chg: false       # 修正箇所の内容とこの判断が食い違うか
    question: {text: "部分修正(新メソッド追加)でよいですか?", answer_examples: ["部分修正でよい", "全体修正にする"]}   # 必須
    confidence: 中
assumptions: []
issues: []
```

`shared: true` の修正はすべて、いずれかの CMN に入れます。`shared: false` でも、呼び出し元を調べて他の機能から使われていれば CMN にし、issues に記録します。

## concerns.yaml(p2e-concerns)

```yaml
meta: {...}
items:
  - id: CON-001
    features: [F-01]
    category: existing_data         # transaction / existing_data / convention / premise / performance / security / external / exclusive_control / test_difficulty / operation / other
    title: "既存ユーザーの電話番号が空になる"
    description: "M_USER に TEL を追加すると、既存の全ユーザーは電話番号が空になる。設計書では必須"
    location: "code:src/main/java/com/example/user/UserEditController.java:52"
    excerpt: {file: src/main/java/com/example/user/UserEditController.java, start: 50, end: 56}
    severity: 中                    # 高 / 中 / 低
    recommendation: "新規登録と更新でチェックを分ける(groups 指定の既存の仕組みを使う)"
    related_ids: [CHG-F01-002, REQ-S1-001]
    question: {text: "更新時は電話番号を必須にしない方針でよいですか?", answer_examples: ["よい", "更新時も必須"]}   # 方針を決める必要があるとき
    confidence: 高
assumptions: []
issues: []
```

懸念は「今回の機能を**作るうえで**の危うさ」です(トランザクション、既存データ、規約とのずれ、前提が崩れている箇所など)。既存機能への影響は impacts.yaml に書き、重ねて書きません。
