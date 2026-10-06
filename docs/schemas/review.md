# 成果物の形式: 点検と振り返り

共通の項目は `common.md` を見てください。

## 点検の種類

| 点検名 | いつ | 何を見るか | ファイル |
|---|---|---|---|
| p1-scope | フェーズ1の途中(p1a の後) | 範囲がユーザーの指示どおりか | review/p1-scope_check.yaml |
| p1 | フェーズ1の最後 | 要件の抽出全体 | review/p1_check.yaml |
| p2-changes | フェーズ2の途中(p2a・p2b の後) | 流用先と修正箇所の根拠・漏れ | review/p2-changes_check.yaml |
| p2 | フェーズ2の最後 | 影響・共通処理・懸念を含む全体 | review/p2_check.yaml |
| p3 | フェーズ3の最後 | 実装計画の全体 | review/p3_check.yaml |

## {点検名}_check.yaml(impact-reviewer)

```yaml
meta:
  run_id: 20261007-usertel
  checkpoint: p1                    # 点検名
  agent: impact-reviewer
  attempt: 1                        # そのフェーズの attempt
  round: 1                          # 同じ attempt の中で点検した回数
  verdict: pass_with_notes          # pass(合格)/ pass_with_notes(条件付き合格)/ fail(不合格)
  self_check:                       # 完了前の自己点検(tools/check_outputs.py --file の結果)
    - {check: "tools/check_outputs.py --file", result: ok, note: ""}
spot_checks:                        # 根拠を実際に開いて確かめた記録
  - id: REQ-S1-001
    evidence: "sheet:機能設計書_ユーザー登録/画面項目定義#L27"
    result: ok                      # ok / ng
    note: ""
findings:
  - id: RVF-p1-001
    severity: major                 # blocker(後の作業を誤らせる)/ major(手戻りが起きやすい)/ minor(直したほうがよい)
    target_worker: p1b-S1           # 直すべき作業者タグ
    description: "REQ-S1-003 の桁が設計書(L29: 6)と違う(5 になっている)"
    evidence: ["sheet:機能設計書_ユーザー登録/画面項目定義#L29"]
    suggestion: "values.桁 を 6 にする"
    status: open                    # open / fixed(再点検で直っていることを確かめたら fixed)
approval_points:                    # フェーズの最後の点検だけ(途中の点検では空)
  - no: 1
    point: "対象の範囲が、指示どおりの行に当たっているか"
    result: ok                      # ok / needs_user(ユーザーの判断が必要)/ ng
    note: ""
    refs: []
questions: []                       # レビュー担当からユーザーに確認したいこと(question の形に about: [関係する機能 ID] を足して並べる)
summary: |                          # フェーズの最後の点検だけ。承認資料の冒頭に載せる要約(3〜5行)
  4つの機能、11件の要件を抽出しました。…
```

**判定の基準**: blocker か major の指摘が1件でもあれば fail。minor の指摘か、needs_user の観点があれば pass_with_notes。どちらもなければ pass。

## フェーズの最後の点検で確かめる承認の観点

`approval_points` には、次の観点を番号どおりにすべて書きます。`policies/review.md` に追加の観点があれば、その後ろに続けます。

**p1(要件の抽出)**
1. 対象の範囲が、指示どおりの行に当たっているか
2. 既存の記述が要件に混ざっていないか(対象の行と見出し行以外を根拠にしていないか)
3. 区分(新規・変更・削除・既存の流用)が正しいか
4. 値(項目名・型・桁・必須・文言など)が設計書どおりに写されているか
5. 機能のまとまりが、利用者から見た機能になっているか
6. 判断に困る表現と仮定が、確認事項に挙がっているか
7. 参照先の設計書の扱い(見出しだけを、必要なときだけ読んだか)

**p2(懸念事項の抽出)**
1. 全要件に、修正箇所か流用先があるか
2. 流用先の特定と、その振る舞いの読み取りは正しいか
3. 修正箇所の「今の振る舞い」が、コードどおりか
4. 影響・懸念の根拠が、すべてコードか
5. 共通処理の呼び出し元に漏れがなく、全体修正か部分修正かの判断が妥当か
6. 重大度・重要度は妥当か
7. 「影響なし」とした修正の調べた範囲は十分か

**p3(実装計画)**
1. 全修正が、いずれかの機能の手順に入っているか
2. 順番が「依存関係 → 既存をもとにしたものから」になっているか
3. 手本の既存実装は実在し、適切か
4. 新しく作るものの名前・置き場所・書き方が、周辺の既存コードに合っているか
5. 確認方法が、全要件・重大度「高」の影響・共通処理を網羅しているか
6. フェーズ2までの判断(decisions.yaml)が反映されているか

## retrospective.yaml(impact-retrospective)

```yaml
meta: {...}                         # phase: retro
read:                               # 読んだもの
  - "decisions.yaml"
  - "review/*_check.yaml"
  - "history/feedback_log.md"
  - "history/questions_log.md"
observations:
  - id: OBS-001
    kind: user_correction           # user_correction / review_finding / interim_fail / rejected_assumption / recurring_question / other
    description: "電話番号の形式が、フェーズ1で確認事項になった"
    refs: [DEC-002, ASM-p1b-S1-001]
    cause: 手順の不足                # 手順の不足 / 設計書の書き方の癖 / 点検の見落とし / 一過性 / その他
    recurring: true                 # history/feedback_log.md・questions_log.md で、過去にも同じ種類があったか
proposals:
  - id: PRP-001
    target_file: policies/phase1.md # policies/common.md / phase1.md / phase2.md / phase3.md / review.md
    for: worker                     # worker(作業エージェント向け)/ reviewer(レビュー担当の点検項目)
    action: add                     # add(追加)/ rewrite(既存の方針の書き直し)/ retire(廃止)
    existing_policy: ""             # rewrite / retire のとき、対象の方針 ID
    text: "電話番号の形式は、記載がなければハイフンなしの数字とする"   # そのまま方針に書ける文
    reason: "3回の調査で、毎回同じ確認事項になっている"
    based_on: [OBS-001]
    decision: pending               # pending / adopted / rejected(オーケストレータが記入)
```

改善案がなければ `proposals: []` にします。方針を足し続けて長くしないよう、既存の方針と重なるときは `rewrite` を提案します。
