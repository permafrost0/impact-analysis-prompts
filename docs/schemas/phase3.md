# 成果物の形式: フェーズ3 実装計画

共通の項目(meta、根拠、excerpt、question、assumptions、issues)は `common.md` を見てください。
このフェーズの根拠も、**コード(`code:`)** です。手本・書き方・置き場所は、周辺の既存コードから決めます。

## plan.yaml(p3a-plan)

```yaml
meta: {...}
order:
  - order: 1
    feature: F-04
    approach: delete                # delete(既存の削除)/ reuse(既存の流用)/ follow_existing(既存を手本に追加)/ modify_existing(既存の変更)/ new_mechanism(新しい仕組み)/ shared_or_high_risk(共通処理の変更・影響大)
    reason: "既存の項目を外すだけで、他の機能に依存しない"
    depends_on: []                  # 先に終わっている必要がある機能
    chg_ids: [CHG-F04-001, CHG-F04-002]   # この機能で行う修正
    decisions: []                   # 反映するユーザーの判断(DEC ID)
    exception: ""                   # 方針の順番を崩した理由(崩したときだけ)
    question: {...}                 # ユーザーに確認したいとき(任意)
assumptions: []
issues: []
```

**順番の方針**: まず依存関係(先に作らないと動かないもの)を守ります。そのうえで、`delete → reuse → follow_existing → modify_existing → new_mechanism → shared_or_high_risk` の順に並べます(既存をもとにしたものから進め、慎重さが要るものを後ろにする)。共通処理の変更が他の機能の前提になる場合など、方針の順番を崩すときは `exception` に理由を書き、`question` で確認します。

- フェーズ2の全修正(`changes/*.yaml` と `reuse.yaml` の changes)を、ちょうど1つの機能の `chg_ids` に入れます。
- フェーズ2までのユーザーの判断(decisions.yaml)のうち、修正の内容を変えるもの(effect: change)と、方針を決めたもの(共通処理の判断、懸念への方針)を、関係する機能の `decisions` に入れます。

## steps/{F-01}.yaml(p3b-steps、機能ごとに1ファイル)

```yaml
meta: {...}                         # worker: p3b-F01
feature: F-01
goal: "ユーザー登録画面で電話番号を入力・チェック・保存できる。更新画面は従来どおり動く"
prerequisites: [F-04]
fixed_decisions:                    # この機能に関係する確定済みの判断
  - {id: DEC-003, text: "共通チェックは部分修正"}
procedure:
  - no: 1
    file: src/main/resources/db/migration/V20__add_user_tel.sql
    place: "新規ファイル"
    action: "M_USER に TEL VARCHAR(11) NULL を追加する"
    chg_ids: [CHG-F01-006]
    exemplar: "code:src/main/resources/db/migration/V18__add_item_code.sql:1"   # 手本にする既存実装
    exemplar_excerpt: {file: src/main/resources/db/migration/V18__add_item_code.sql, start: 1, end: 3}   # 主な手本だけ(任意)
    note: ""
new_files:                          # 新しく作るもの
  - kind: migration                 # class / migration / template / message_key / config / other
    name: V20__add_user_tel.sql
    place: src/main/resources/db/migration
    basis: "code:src/main/resources/db/migration/V19__add_shop_tel.sql:1"   # 命名・配置の根拠(最新が V19)
conventions:                        # 合わせる書き方(周辺のコードから)
  - aspect: "単項目チェック"
    rule: "Form のアノテーションで行う"
    basis: "code:src/main/java/com/example/user/UserForm.java:18"
keep_behaviors:                     # 守るべき既存の振る舞い
  - behavior: "CommonValidator#validateTel は変更しない"
    reason_ids: [IMP-001, CMN-001]
done_criteria: ["確認方法の F-01 の項目がすべて期待どおり", "既存のテストがすべて通る"]
questions: []                       # ユーザーに確認したいこと(question の形を並べる。任意)
assumptions: []
issues: []
```

- この機能の全修正(plan.yaml の `chg_ids`)を、いずれかの手順の `chg_ids` に入れます。
- 直す行と今のコードは、手順の `chg_ids` から、修正箇所(フェーズ2)の `location`・`excerpt` をスクリプトが実装計画書に差し込みます。書き写しません。
- 手順は、製造担当がこの順に作業できる粒度で書きます。`exemplar` は必ず実在する既存コードにします。

## verification.yaml(p3c-verification)

```yaml
meta: {...}
items:
  - id: TC-001
    feature: F-01
    kind: new                       # new(今回の機能の確認)/ regression(既存機能が変わらないことの確認)
    input: "電話番号を空にして登録ボタンを押す"
    expected: "「電話番号を入力してください」が表示され、登録されない"
    where: "UserFormTest に追加"     # どこで確認するか(テストクラス、または「画面で確認」)
    req_ids: [REQ-S1-001]
    imp_ids: []
    cmn_ids: []
    priority: 高                    # 高 / 中 / 低
assumptions: []
issues: []
```

- 全要件(excluded を除く)に、少なくとも1つの `kind: new` を用意します(用意しないものは `meta.not_covered` に理由)。
- 重大度「高」の全影響に、少なくとも1つの `kind: regression` を用意します。
- 全 CMN について、今回の対象ではない呼び出し元の `kind: regression` を少なくとも1つ用意します。
- `where` は、既存のテストの構成(テストクラスの置き場所と命名)に合わせます。
