# GitHub Copilot → Claude Code 移植プロンプト

GitHub Copilot（VS Code）用に作ったエージェント一式を、Claude Code 用に移植するときに使うプロンプトです。
移植元の作りはさまざまなので、このプロンプトは特定の仕組み（進行役、ゲート、状態ファイル、フックなど）を前提にしていません。**移植元にあるものだけを変換し、無いものは作りません**（「1. 必須事項」で求めるものを除く）。

---

## 0. 使い方

1. 移植先のフォルダ（移植元の一式を置いたフォルダ）で Claude Code を起動する
2. 次のように依頼する

```
docs/Copilot→ClaudeCode移植プロンプト.md を読んで、その手順どおりに
<Copilot 版のフォルダ（例：.github/ を含むこのフォルダ）> を Claude Code 用に移植してください。
対象PJ名は <PJ名>、SVN の URL は <URL> です。
```

### Claude への指示（ここから下は Claude が従う）
- あなたは移植担当です。「1. 必須事項」を必ず満たし、「3. 手順」の順に進めます
- **各段階の最後で、人に結果を見せて確認を取ってから次へ進みます**。決まらない点は推測で埋めず、質問します
- 移植元に無い仕組みを、良かれと思って追加しません（必須事項で求めるものを除く）
- 移植元のエージェントの役割・判断基準・出力形式は変えません。変えるのは、Claude Code で動かすために必要な部分だけです
- 移植元のファイルは、「M5 旧版の削除」で人が了承するまで消しません

---

## 1. 必須事項（移植元に関係なく、必ず満たす）

### M1. SVN コミット用フォルダ
- 開発対象のソースは、パッケージの中の **`source/<PJ名>/`** に置く。ここは対象PJの **SVN 作業コピー**そのもの（人が `svn checkout <URL> source/<PJ名>`）。複数の PJ を並べてよい
- Claude Code には、`.claude/settings.local.json`（個人の設定。コミットしない）でソースを読ませる
  ```json
  {
    "permissions": {
      "additionalDirectories": ["source/<PJ名>"]
    }
  }
  ```
  ひな形を `templates/settings.local.json` として用意する
- 移植元がソースを別の場所から参照していた場合（VS Code のマルチルートのワークスペース、設定ファイルに書いた絶対パスなど）は、`source/<PJ名>` に置き換える。スクリプトがその場所を読んでいれば、読み先も変える
- パッケージ自体も SVN で管理する。`svn:ignore` で除外するもの：`source/` の中身、個人の設定（`.claude/settings.local.json`）、作業成果物や業務資料のフォルダ（移植元で除外していたもの）、`__pycache__` など
- 調査の対象外の設定があれば、`.svn` を加える。無ければ、エージェントの指示に「`.svn` フォルダは見ない」と書く
- **SVN 操作（checkout、update、switch、commit）は人が行う**。文書には次を書く
  - 実装の単位ごとに、人が確認・ビルドしてから `svn commit` する
  - AI が実装している間は `svn update`／`svn switch` をしない（AI が見ている内容と、差分の基準がずれるため）

### M2. 製造のゴールは `mvn compile`
- AI が実装・修正したときのゴールは、**`mvn compile` が通ること**。`mvn clean install`、テスト、Tomcat での動作確認は人が Eclipse で行う
- 実装を担うエージェント（移植元で「実装」「製造」「コード修正」を担当するもの）の手順に、次を加える
  1. 変更が終わったら、Bash ツールで `mvn -B -q -f source/<PJ名>/pom.xml compile` を実行する（`cd` はしない。初回は依存の取得で時間がかかるので、Bash の timeout を 600000 にする）
  2. 失敗したら、エラーの出た箇所だけを直して、もう一度実行する（直すのは、そのエージェントが変更してよい範囲の中だけ）
  3. 3回やっても通らなければ、直すのをやめて、エラーの内容と質問を残して止まる
  4. 報告には compile の結果（成功／失敗）を必ず書く
- 禁止事項に「`install`／`package`／`deploy`／`test`、サーバーの起動は実行しない（人が行う）」を加える
- レビュー役のエージェントがいれば、「compile が通っていない実装は NG」を判定の観点に加える（自分では compile を実行せず、実装役の報告とその記録で確かめる）
- 人の install・動作確認で失敗したら、人がエラー全文を渡して AI に直させる流れを文書に書く（直した後も compile を通す）
- Maven の CLI が必要（Eclipse 内蔵の Maven は使わない）。Git Bash から `mvn -v` が動くようにし、JDK はプロジェクトに合わせる（`JAVA_HOME`）
- compile のコマンドだけを、確認なしで実行できるようにする（`.claude/settings.local.json` の `permissions.allow` に `"Bash(mvn -B -q -f source/<PJ名>/pom.xml compile)"`）

### M3. 人の作業は AI にさせない
- 承認・差し戻し（移植元にあれば）、SVN 操作、install・デプロイ・サーバーの起動は、AI にさせない
- 二重に止める
  1. エージェントの指示に「しない」と書く
  2. `.claude/settings.json` の `permissions.deny` で止める
     ```json
     "deny": [
       "Bash(svn:*)",
       "Bash(mvn install:*)", "Bash(mvn clean:*)", "Bash(mvn package:*)", "Bash(mvn deploy:*)", "Bash(mvn test:*)",
       "Bash(mvn -B install:*)", "Bash(mvn -B clean:*)", "Bash(mvn -B package:*)", "Bash(mvn -B deploy:*)", "Bash(mvn -B test:*)"
     ]
     ```
     移植元に人だけが実行するコマンド（承認用のスクリプトなど）があれば、それも deny に入れる
- deny は、複合コマンド（`&&`、`;`、`|` など）を部分ごとに判定し、`timeout` などの包み込みも外して判定する。それでも、`/usr/bin/svn` のような絶対パスや別名など、書き方を変えたコマンドはすり抜けうる（公式にも「Bash permission patterns that try to constrain command arguments are fragile」とある）。確実に止めたい場合は、コマンド文字列を見て止める PreToolUse フックを足す（移植元にフックがあれば、その制限も必ず移植する）

### M4. 既存成果物の流用
Copilot 版を使ってすでに作られた成果物（後続のフェーズへの資料）は、作り直さずに引き継ぎます。
- 棚卸しで洗い出すもの
  - エージェントの出力先フォルダの中身（調査結果、要件一覧、計画、レビュー結果など）
  - ナレッジや用語集など、使うほど追記されるファイル
  - 使ううちに追記されたレビュー観点・チェックリスト（`.github/` の中にあることが多い）
  - 進み具合を記録するファイル（あれば）
- 引き継ぎ方
  - その場所のまま残す。**消さない、作り直さない、書式を変えない**
  - `.github/` の中にあるもの（追記されたチェックリストなど）は、移植先の対応する場所へ**内容ごと**移す（移植元の初期版で上書きしない）
  - 成果物の中のパス参照が `.github/` などの旧パスを指していれば、新しいパスに置き換える
  - ソースの行番号の参照（`ファイル:行` など）は、**Copilot 版で使っていたのと同じリビジョンを `source/<PJ名>/` に checkout** すれば有効なまま。違うリビジョンになる場合は人に伝える
  - 作業の途中のもの（実行中のまま止まったもの、実装の途中のもの）があれば、移植の前に人に区切りを付けてもらう（完了させるか、やり直す扱いにする）

### M5. 旧版の削除
- 検証が終わり、人が了承してから、Copilot 用のファイル（`.github/` の Copilot 用の部分、`.vscode/` の Copilot 用の設定、ワークスペースファイル）を削除する
- 削除の前に、移植先から旧版への参照が残っていないことを確かめる（V2）

---

## 2. 変換規則（移植元にあるものだけ変換する）

### 2-0. 仕組みの違い（公式ドキュメント準拠・2026-10-15 時点）
2-1 以降の変換規則の根拠です。製品の更新で変わることがあるので、移植の前に末尾の出典で確かめてください。

| 項目 | Copilot（VS Code） | Claude Code | 移植での扱い |
|---|---|---|---|
| 全体の指示 | `.github/copilot-instructions.md`。`AGENTS.md`、`CLAUDE.md` も読める | `CLAUDE.md`／`.claude/CLAUDE.md`。`AGENTS.md` は、`CLAUDE.md` が無いときだけ読む | `CLAUDE.md` にする |
| ファイル別の指示 | `.github/instructions/*.instructions.md`（`applyTo` で対象を指定） | `.claude/rules/*.md`（`paths` で対象を指定）。サブフォルダの `CLAUDE.md` は、そのフォルダを扱うときに読み込まれる | `applyTo`→`paths` |
| エージェント | `*.agent.md`（旧 `*.chatmode.md`）。`tools` は `read/readFile` のような ID の配列。`model` は配列で書ける（使える最初のもの）。`agents`、`handoffs`、`user-invocable`、`disable-model-invocation`、`target`、`mcp-servers` がある | `.claude/agents/*.md`。`tools` は Claude Code のツール名。`model` は1つ（`sonnet`／`opus`／`haiku`／`inherit` など）。知らない項目はエラーにならず無視される | 2-2 で変換する |
| サブエージェント | `agent/runSubagent` で呼ぶ。入れ子は既定で無効（設定 `chat.subagents.allowInvocationsFromSubagents` で有効にでき、深さは最大5）。呼び出しごとに状態を持たない | `Agent` ツール（旧名 Task）で呼ぶ。入れ子は既定で有効（メインの会話から3階層まで。`CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` で変更）。呼ばれた側は会話の履歴を引き継がない | 進行役は、人の確認をメインの会話で取るためにスキルにする（公式の制約が理由ではない） |
| プロンプト／スキル | `.github/prompts/*.prompt.md`（引数は `${input:名前}`）。`.github/skills/` の `SKILL.md` もある（`context: fork` は試験的な機能） | `.claude/skills/<名前>/SKILL.md`（旧 `.claude/commands/` も動く）。引数は `$ARGUMENTS`、`$0`、`$1`…、`arguments` に書いた名前 `$名前`。`context: fork` は既定でバックグラウンドで動き、会話の履歴を見ない | 2-2 で変換する |
| フックの置き場所と書き方 | `.github/hooks/*.json`、エージェントの frontmatter（プレビュー）。コマンドの項目は `command`、`windows`／`linux`／`osx`、`cwd`、`env`、`timeout`（既定で 30 秒）。matcher は無い（Claude Code の形式で書いても無視され、そのイベントのフックはすべて動く） | `.claude/settings.json` の `hooks`、エージェント・スキルの frontmatter。`matcher` で対象のツールを絞れる（省略すると全部）。`command` の `timeout` は既定で 600 | 2-2・2-4 を参照 |
| フックの入出力 | 標準入力：`timestamp`、`cwd`、`session_id`、`hook_event_name`、`transcript_path`、ツールのイベントでは `tool_name`、`tool_input`、`tool_use_id`。終了コード：0＝成功（標準出力の JSON を読む）、2＝止める（標準エラーをモデルに渡す）、その他＝警告して続ける。`permissionDecision` は `allow`／`deny`／`ask` | 標準入力に `timestamp` は無く、`permission_mode` などが加わる。終了コードの意味は同じ。`permissionDecision` には `defer` もある。フックが `allow` を返しても、`permissions.deny` に当たれば止まる | ツール名と `tool_input` の形は製品ごとに違う（Copilot の公式にも「Tool names and arguments differ between harnesses」とある）→ 2-4 |
| コマンドの自動承認 | `chat.tools.terminal.autoApprove`。キーはコマンド名か `/正規表現/`、値は `true`（自動承認）／`false`（承認を求める。**止めはしない**）。複合コマンドは部分ごとに判定し、`false` が優先 | `.claude/settings.json` の `permissions` の `allow`／`ask`／`deny`。`Bash(x *)` と `Bash(x:*)` は同じ意味。判定は deny→ask→allow の順。複合コマンド（`&&`、`;`、`|` など）は部分ごとに判定する | `true`→allow、`false`→ask（deny ではない）。正規表現はワイルドカードの形に書き直す |
| MCP | `.vscode/mcp.json`（`servers`、`inputs`、`${input:…}`、`${workspaceFolder}` などの変数）。ルートの `.mcp.json`（`mcpServers`）も読める | `.mcp.json`（`mcpServers`）。展開できるのは環境変数 `${VAR}`／`${VAR:-既定値}` だけ。プロジェクトの MCP サーバーは、初めて使うときに承認を求められる | `inputs` と VS Code の変数は、環境変数に置き換える |
| シェル | VS Code のターミナル | Windows では Git Bash（Git for Windows が無ければ PowerShell）。Bash のタイムアウトは既定で2分、最大10分。時間切れになったコマンドはバックグラウンドに回る | 2-3・5 を参照 |
| 共存 | VS Code は `.claude/agents`、`.claude/skills`、`.claude/rules`、`CLAUDE.md`、`.mcp.json` も読める（Claude Code の形式のフックは、設定 `chat.useClaudeHooks` を有効にしたときだけ） | ― | 移行の期間中は、移植先のファイルを Copilot からも使える。ただし動きが同じになるとは限らない（Copilot の公式にも「This file compatibility does not make their behavior identical」とある） |

**出典**
- Copilot（VS Code）
  - https://code.visualstudio.com/docs/copilot/customization/custom-agents
  - https://code.visualstudio.com/docs/copilot/customization/prompt-files
  - https://code.visualstudio.com/docs/copilot/customization/agent-skills
  - https://code.visualstudio.com/docs/copilot/customization/custom-instructions
  - https://code.visualstudio.com/docs/copilot/customization/hooks
  - https://code.visualstudio.com/docs/agents/reference/hooks-reference
  - https://code.visualstudio.com/docs/copilot/agents/subagents
  - https://code.visualstudio.com/docs/agents/reference/tools-reference
  - https://code.visualstudio.com/docs/agents/run/approvals
  - https://code.visualstudio.com/docs/copilot/customization/mcp-servers
- Claude Code
  - https://code.claude.com/docs/en/memory
  - https://code.claude.com/docs/en/sub-agents
  - https://code.claude.com/docs/en/skills
  - https://code.claude.com/docs/en/hooks
  - https://code.claude.com/docs/en/permissions
  - https://code.claude.com/docs/en/settings
  - https://code.claude.com/docs/en/mcp
  - https://code.claude.com/docs/en/tools-reference
  - https://code.claude.com/docs/en/setup

### 2-1. ファイルの対応
| 移植元（あれば） | Claude Code | 要点 |
|---|---|---|
| `.github/agents/*.agent.md`、`.github/chatmodes/*.chatmode.md` | `.claude/agents/<名前>.md` | 1ファイル＝1エージェント。本文はそのまま使い、2-3 の規則で書き換える |
| `.github/prompts/*.prompt.md` | `.claude/skills/<名前>/SKILL.md` | `/<名前>` で呼べる。2-2 を参照 |
| `.github/skills/<名前>/SKILL.md` | `.claude/skills/<名前>/SKILL.md` | 形式は同じなので、ほぼそのまま移す。本文は 2-3 で書き換える |
| 他のエージェントを呼び出すエージェント（進行役など） | メインの会話で動くスキル | 人の確認をメインの会話で取るため、進行役の手順をスキルの本文にし、Agent ツール（`subagent_type` にエージェント名）で各エージェントを呼ぶ（Claude Code でもサブエージェントの入れ子はできるが、この形にそろえる。2-0） |
| `.github/copilot-instructions.md` | `CLAUDE.md` | 全体の原則。パス表記を置き換える |
| `AGENTS.md` | `CLAUDE.md` | 内容を `CLAUDE.md` に移すか、`CLAUDE.md` に `@AGENTS.md` と書いて読み込む（`CLAUDE.md` があると `AGENTS.md` は読まれない。2-0） |
| `.github/instructions/*.instructions.md`（`applyTo` 付き） | `.claude/rules/<名前>.md` | `applyTo` を `paths`（glob の配列）にする。全体に効くもの（`applyTo: "**"`）は `CLAUDE.md` の節にしてもよい |
| `.github/hooks/*.json`（全体のフック） | `.claude/settings.json` の `hooks` | 2-2 を参照 |
| `.vscode/settings.json` の `chat.tools.terminal.autoApprove` | `.claude/settings.json` の `permissions` | `true` のコマンドを `allow` に、`false` のコマンドを `ask` に（`false` は止める設定ではないので `deny` にしない）。`/正規表現/` のキーは `Bash(コマンド *)` の形に書き直す。その他の `chat.*`・`github.copilot.*` 設定は不要 |
| `.vscode/mcp.json` | `.mcp.json` | キーは `servers` → `mcpServers`。`inputs`・`${input:…}`・`${workspaceFolder}` などの VS Code の変数は使えないので、環境変数 `${VAR}` に置き換える |
| マルチルートのワークスペースファイル | `source/<PJ名>` と `additionalDirectories` | M1 を参照 |
| 補助スクリプト（`tools/` など） | そのまま使う | 2-4 の互換性を確認する |

### 2-2. frontmatter の変換
**エージェント（`.claude/agents/<名前>.md`）**
| 移植元の項目 | Claude Code | 変換 |
|---|---|---|
| `name` | `name` | そのまま |
| `description` | `description` | そのまま（どんなときに使うかが分かる文にする。進行役から呼ぶ専用なら「〜専用」と書く） |
| `tools` | `tools` | `read`・`read/readFile` など→`Read`、`search`・`search/*`→`Grep, Glob`、`edit`・`edit/*`→`Write, Edit`、`execute/runInTerminal`（旧 `runCommands` など）→`Bash`、`web/fetch`（旧 `fetch`）→`WebFetch`、`todos`→不要、`agent`・`agent/runSubagent`→不要（進行役はスキルにする）、MCP のツール（`<サーバー>/*` など）→`mcp__<サーバー>__<ツール>`。Copilot の古い ID が書かれていることもあるので、役割から判断する |
| `model` | `model` | `sonnet`／`opus`／`haiku`／`inherit` などに置き換えるか、削除（呼び出し元に合わせる）。配列で書かれていれば1つにする |
| `hooks` | `hooks` | 形を変える（下の例）。`Stop` は、サブエージェントとして動くときは SubagentStop として扱われる（両製品とも同じ） |
| `agents`（呼び出せるエージェントの一覧） | 不要 | 進行役のスキルの本文に、呼び出すエージェントを書く |
| `user-invocable`、`disable-model-invocation`、`infer` | 不要 | Claude Code のサブエージェントには無い項目。進行役から呼ぶ専用なら、description に「〜専用」と書く |
| `mcp-servers` | `mcpServers` | そのエージェントだけで使う MCP サーバー |
| `argument-hint`、`handoffs`、`target` | 不要 | 引数の書き方や次の手順は、本文に書く |

フックの書き方（移植元 → Claude Code）：
```yaml
# 移植元（Copilot）
hooks:
  PreToolUse:
    - type: command
      command: "python tools/guard.py --role <エージェント名>"
# Claude Code
hooks:
  PreToolUse:
    - matcher: "Write|Edit|NotebookEdit|Bash|PowerShell"
      hooks:
        - type: command
          command: 'python "$CLAUDE_PROJECT_DIR/tools/guard.py" --role <エージェント名>'
          timeout: 30
```
- Copilot のフックには matcher が無く、そのイベントのすべてのツールで動く。同じ動きにするなら matcher を省略する。絞る場合は、スクリプトがツール名で判定していた範囲に合わせる
- `windows`／`linux`／`osx`／`cwd`／`env` は Claude Code のフックには無い。Windows 用の `command` を採り、作業フォルダや環境変数はコマンドの中で指定する
- `timeout` の既定値が違う（Copilot は 30 秒、Claude Code の `command` は 600）。移植元で省略していれば `timeout: 30` を書く

**スキル（`.claude/skills/<名前>/SKILL.md`）**
| 移植元の項目 | Claude Code | 変換 |
|---|---|---|
| `name`、`description`、`argument-hint` | 同じ名前 | そのまま |
| `agent`（特定のエージェントで動かす） | `context: fork` ＋ `agent: <名前>` | 別のコンテキストで、そのエージェントとして動く（「New Chat で実行」の運用は不要になる）。会話の履歴は渡らないので、必要な情報は本文と引数で渡す。既定ではバックグラウンドで動くため、結果を待ってから次へ進む作りなら `background: false` を付ける |
| `agent` なし | （指定しない） | メインの会話で動く |
| `tools` | `allowed-tools` | Copilot は「使えるツール」、Claude Code は「確認なしで使えるツール」の指定で、意味が少し違う |
| `model` | `model` | エージェントと同じ |
| 本文中の引数（`${input:名前}` など） | `$ARGUMENTS`、`$0`・`$1`…、または `arguments` ＋ `$名前` | 引数が1つなら `$ARGUMENTS`。複数なら `arguments: [名前, …]` を書いて `$名前` で参照する |
| `${selection}`、`${file}` などの VS Code の変数 | なし | 対象は引数で受け取るように本文を書き換える |
| `.github/skills/` の `user-invocable`、`disable-model-invocation`、`context` | 同じ名前 | そのまま |
| （追加） | `disable-model-invocation: true` | 人がコマンドで呼ぶ専用にする場合（AI に勝手に起動させない） |

### 2-3. 本文の書き換え
| 移植元の表現 | 書き換え |
|---|---|
| 「ターミナルで実行」 | 「Bash ツールで実行」。`cd` を使わない（作業フォルダはパッケージのまま。別のフォルダが要るときは `-f` などでパスを渡す） |
| 「編集ツールで変更」「ファイルを作成」 | 既存ファイルの変更は Edit、新しいファイルの作成は Write |
| 「読み取りツール・検索ツール」 | Read・Grep・Glob |
| 「ワークスペースに追加したフォルダ」 | `source/<PJ名>`（M1） |
| `.github/…` へのリンク | 移植先のパスに。Markdown のリンクはパス表記（`` `…` ``）でよい |
| 「コマンドごとに New Chat で実行」 | 削除（fork のスキルは別コンテキストで動く） |
| 「サブエージェントとして呼ぶ」 | 「Agent ツールで呼ぶ」 |
| 「ビルドしない」（移植元がそうなら） | M2 に合わせて「compile まで行い、install と動作確認は人」に |

### 2-4. 補助スクリプトの互換性（移植元にあれば）
- フックから呼ばれるスクリプトは、標準入力の JSON（`tool_name`、`tool_input`、`cwd`）を読み、止めるときは**終了コード 2**で終わり、理由を標準エラーに出す。Copilot と同じ形なので、多くはそのまま動く（2-0）
- 標準入力の `timestamp` は Claude Code には無い。使っていれば、スクリプトの中で時刻を取るように直す
- ツール名で判定している場合は、Claude Code のツール名（`Write`、`Edit`、`NotebookEdit`、`Bash`、`PowerShell`、`Read`、`Grep`、`Glob`）で正しく判定できるかを確かめる
- `tool_input` の中身（ファイルのパスやコマンドが入る項目の名前）も製品ごとに違う。Claude Code では `Write`・`Edit` は `file_path`、`Bash` は `command`。パスやコマンドを取り出す部分を確かめる
- フックが `allow` を返しても、`permissions.deny` に当たるコマンドは止まる。逆に、deny に無いものを止めたいならフックで止める
- スクリプトの中の `.github/…`・ワークスペースファイル・VS Code 固有の参照を洗い出し、移植先のパスに置き換える
- スクリプトの呼び出しは `python "$CLAUDE_PROJECT_DIR/tools/…"` の形にする（どこから呼ばれても動くように）

---

## 3. 手順（各段階の最後に人の確認を取る）

| 段階 | すること | 人に見せて確認すること |
|---|---|---|
| 1. 棚卸し | 移植元のファイル一覧（エージェント、プロンプト、指示、フック、スクリプト、VS Code 設定、MCP 設定）。エージェントごとの役割と呼び出し関係（どれが進行役か、どれが実装役か、どれがレビュー役か）。M4 の既存成果物。`.github`・ワークスペース・VS Code 固有の表記を参照している箇所（grep） | 一覧、役割の分類、引き継ぐ成果物、作業途中のものの有無 |
| 2. 変換方針 | ファイルごとの対応表（2-1・2-2）。M1〜M3 をどのエージェント・どの設定に入れるか。決まらない点の質問 | 対応表、必須事項の組み込み先、質問への回答 |
| 3. スクリプトの修正 | 補助スクリプトのパス参照などを直す（2-4）。**フックを有効にする前に行う**（フックが書き込みを止める作りの場合、有効にした瞬間から同じセッションでも止められる） | 変更点の要約 |
| 4. 生成 | エージェント・スキルを、変換用のスクリプトで機械的に生成する（手作業の写し間違いを防ぐ）。生成後に旧パスが残っていないことをスクリプトで確かめる | 生成したファイルの一覧、代表1件の中身 |
| 5. 必須事項の組み込み | M1（`source/`、`templates/settings.local.json`、svn:ignore の手順）、M2（実装役・レビュー役の手順、allow）、M3（deny、フック）、`CLAUDE.md` | 組み込んだ箇所 |
| 6. 既存成果物の引き継ぎ | M4。移す前に、成果物の一覧とハッシュを記録しておく（V7 で比べる） | 移したもの、書き換えたパス参照 |
| 7. 文書の更新 | README・使い方を「Claude Code ＋ SVN ＋ compile は AI、install と動作確認は人」の前提に書き換える | 書き換えた文書 |
| 8. 検証 | 「4. 検証」をすべて行う | 結果（失敗したものは、その出力も） |
| 9. 旧版の削除 | M5 | 削除してよいかの了承 |

---

## 4. 検証（移植したファイルを読んで確かめる）

| No | 確認すること | 確かめ方 | 期待結果 |
|---|---|---|---|
| V1 | 定義の形式 | 下の「V1 のスクリプト」 | 全ファイルが読め、エラーが出ない |
| V2 | 旧参照の残り | `grep -rn -e "\.github" -e "copilot" -e "code-workspace" -e "\.vscode" CLAUDE.md .claude docs README.md tools` | このプロンプト以外は0件 |
| V3 | Claude Code での読み込み | Claude Code を起動し直して `/agents`、`/hooks`、入力欄で `/` | エージェント・スキル・フックの数が、棚卸しの対応表と一致する |
| V4 | ソースの参照・compile の許可 | `templates/settings.local.json` を読む | `additionalDirectories` に `source/<PJ名>`、`permissions.allow` に M2 の compile のコマンドがある |
| V5 | 人の作業の禁止 | `.claude/settings.json` とエージェントの指示を読む | `permissions.deny` に M3 の一覧（移植元の人だけが実行するコマンドを含む）があり、エージェントの指示にも「しない」と書いてある |
| V6 | フック（移植元にあれば） | 移植元のフックと、移植先の `hooks`（`.claude/settings.json`、エージェントの frontmatter）を突き合わせる | 移植元のフックがすべて移植されていて、スクリプトの呼び出しが `python "$CLAUDE_PROJECT_DIR/tools/…"` の形になっている |
| V7 | 既存成果物の引き継ぎ | 段階6で記録した一覧とハッシュを、移植後と比べる。ソースの行番号の参照を数件開く | 欠落・意図しない変更がない。行番号の内容が一致する |

コマンドを実行して動きを確かめる確認（`mvn`・`svn` の実行、フックの試験、移植したエージェント・スキルを動かして作業を進めることなど）は、移植の範囲に含めない（移植後に人が使いながら確かめる）。

**V1 のスクリプト**（例：`python check_frontmatter.py`）
```python
import glob, yaml
files = glob.glob(".claude/agents/*.md") + glob.glob(".claude/skills/*/SKILL.md")
for f in files:
    text = open(f, encoding="utf-8").read()
    assert text.startswith("---\n"), f
    meta = yaml.safe_load(text.split("---")[1])
    assert meta.get("name") and meta.get("description"), f
print(f"OK: {len(files)} files")
```

---

## 5. 落とし穴（実際に移植したときに起きたこと）
- **フックは保存した直後から、同じセッションでも効く**：Claude Code は設定ファイルを監視していて、`hooks` や `permissions` の変更を実行中のセッションにも反映する。スクリプトや保護対象のファイルの修正は、フックを有効にする前に済ませる
- **コマンド文字列を見て止めるフックは、ヒアドキュメントの中身にも反応する**：一括変換などは、スクリプトをファイルに書いてから実行する
- **進行役はメインの会話で動くスキルにする**：Claude Code でもサブエージェントの入れ子はできる（2-0）が、進行役をサブエージェントにすると、人の確認がメインの会話で取れない
- **Windows では、Claude Code の Bash は Git Bash**：`python`・`mvn` が Git Bash から動くこと。日本語を含むパスは引用符で囲む
- **Bash ツールのタイムアウトは既定で2分、最大10分**：初回の compile は依存の取得で長くかかる。時間切れになったコマンドは止まらずにバックグラウンドに回る
- **Maven の CLI が入っていない環境が多い**：Eclipse だけでは `mvn` コマンドが無い。事前に Apache Maven を入れる
- **文字コード**：Windows の既定は MS932。Spring Boot の SQL スクリプトは `spring.sql.init.encoding=UTF-8` が無いと文字化けする
- **Eclipse**：`source/<PJ名>` は「既存 Maven プロジェクト」としてインポートしないと、サーバー（Tomcat）に追加できない。Spring Boot 3 系は Tomcat 10.1（Tomcat 9 以前は不可）

---

## 6. 付録：移植の例（次期ATTA）
このパッケージは、このプロンプトの元になった移植の結果です。**移植元に同じ仕組みが無ければ、真似して作らないでください。**

| 内容 | 例 |
|---|---|
| フック付きのエージェント | `.claude/agents/implementer.md` |
| 別コンテキストで動くスキル | `.claude/skills/spec-extract/SKILL.md` |
| 進行役をスキルにした例 | `.claude/skills/proceed/SKILL.md` |
| 全体のフックと permissions | `.claude/settings.json` |
| ソースルートを `settings.local.json` から読むスクリプト | `tools/_common.py` の `source_root()` |

注：次期ATTA は「ビルドはすべて人」の時点で作った版で、M2（compile まで AI）はまだ組み込んでいません。
