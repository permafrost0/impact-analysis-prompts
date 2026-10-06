# 影響調査報告書(フェーズ2 承認資料)

> 調査: ユーザー登録への電話番号認証の追加(20261007-usertel)/ フェーズ2 懸念事項の抽出
> この資料は YAML から自動で作られています。直したい点は、オーケストレータに伝えてください。
> 根拠はすべてソースコードです。コードの抜粋は、実際のソースから切り出しています。

## はじめに

15か所の修正(うち共通処理1)を特定しました。既存機能への影響は2件(高1・中1)、懸念は2件(高1・中1)です。
共通処理 CommonValidator は部分修正(新メソッド追加)と判断しています。

## 1. 抽出した内容(機能ごと)

### 機能の一覧

| 機能 | 修正箇所 | 既存機能への影響 | 懸念 | 確認事項 |
|---|---|---|---|---|
| [F-01 電話番号の入力](#f-01) | 8(うち共通処理 1) | 高 1 / 中 1 | 中 1 | Q1 |
| [F-02 電話番号の認証](#f-02) | 3 | なし | 高 1 | Q2 |
| [F-03 FAX番号の廃止](#f-03) | 3 | なし | 中 1 | - |

---

### F-01

**電話番号の入力**

ユーザー登録画面に電話番号の入力項目を追加し、既存の会員登録と同じ入力チェックで確かめる

#### (1) 今の処理の流れ(コードから)

| 順 | 場所 | 対象 | 今の振る舞い |
|---|---|---|---|
| 1 | `UserController.java:18` | UserController#showRegister | GET /user/register で user/register.html を表示する |
| 2 | `UserController.java:23` | UserController#register | @Validated UserForm でチェックし、エラーなら画面に戻す |
| 3 | `UserService.java:15` | UserService#register | @Transactional。UserForm を User に詰め替えて insert する |
| 4 | `UserMapper.xml:3` | UserMapper.insert | INSERT 文。列は明示で列挙している |

#### (2) 修正箇所

**CHG-F01-001 `src/main/resources/templates/user/register.html`(修正)**

| 項目 | 内容 |
|---|---|
| 対象 | 入力フォーム(メールアドレス欄の後) |
| 場所 | `register.html:10` |
| 今の振る舞い | 氏名・メールアドレス・FAX番号の入力欄がある |
| 変更後 | メールアドレス欄の後に電話番号の入力欄がある |
| 指示 | th:field は *{tel}<br>ラベルは label.user.tel |
| 理由(要件) | REQ-S1-001 |
| 手本にする既存実装 | `register.html:10` |
| 先に必要な修正 | CHG-F01-002 |

`src/main/resources/templates/user/register.html` 10〜13 行目(今のコード)

```html
10:   <div class="form-group">
11:     <label for="mail" th:text="#{label.user.mail}">メールアドレス</label>
12:     <input type="text" id="mail" th:field="*{mail}" class="form-control">
13:   </div>
```

**CHG-F01-002 `src/main/java/com/example/user/UserForm.java`(修正)**

| 項目 | 内容 |
|---|---|
| 対象 | UserForm(フィールド) |
| 場所 | `UserForm.java:16` |
| 今の振る舞い | name・mail・fax がある |
| 変更後 | tel(@NotBlank、@Size(max = 11))を追加する |
| 理由(要件) | REQ-S1-001 |
| 手本にする既存実装 | `UserForm.java:12` |

`src/main/java/com/example/user/UserForm.java` 10〜16 行目(今のコード)

```java
10:     @NotBlank
11:     @Size(max = 50)
12:     private String name;
13: 
14:     @NotBlank
15:     @Email
16:     private String mail;
```

**CHG-F01-003 `src/main/java/com/example/common/CommonValidator.java`(修正) 〔共通処理〕** → Q1

| 項目 | 内容 |
|---|---|
| 対象 | CommonValidator#validateTelStrict |
| 場所 | `CommonValidator.java:9` |
| 今の振る舞い | validateTel はハイフンありもなしも許容する |
| 変更後 | ハイフンなし11桁を判定する validateTelStrict を追加する(validateTel は変えない) |
| 理由(要件) | REQ-S3-002 |
| 共通処理である理由 | CommonValidator は会員登録・店舗登録から使われている |
| 手本にする既存実装 | `CommonValidator.java:17` |

`src/main/java/com/example/common/CommonValidator.java` 8〜14 行目(今のコード)

```java
 8:     /** 電話番号の形式チェック(ハイフンあり・なしの両方を許容) */
 9:     public boolean validateTel(String tel) {
10:         if (tel == null || tel.isEmpty()) {
11:             return true;
12:         }
13:         return tel.matches("^[0-9-]{10,13}$");
14:     }
```

**CHG-F01-004 `src/main/java/com/example/user/UserService.java`(修正)**

| 項目 | 内容 |
|---|---|
| 対象 | UserService#register |
| 場所 | `UserService.java:15` |
| 今の振る舞い | name・mail・fax を詰め替えて登録する |
| 変更後 | tel も詰め替えて登録する |
| 理由(要件) | REQ-S1-001 |
| 先に必要な修正 | CHG-F01-005 |

`src/main/java/com/example/user/UserService.java` 14〜21 行目(今のコード)

```java
14:     @Transactional
15:     public void register(UserForm form) {
16:         User user = new User();
17:         user.setName(form.getName());
18:         user.setMail(form.getMail());
19:         user.setFax(form.getFax());
20:         userMapper.insert(user);
21:     }
```

**CHG-F01-005 `src/main/resources/mapper/UserMapper.xml`(修正)**

| 項目 | 内容 |
|---|---|
| 対象 | UserMapper.insert |
| 場所 | `UserMapper.xml:3` |
| 今の振る舞い | NAME・MAIL・FAX を INSERT する |
| 変更後 | TEL を INSERT 列に追加する |
| 理由(要件) | REQ-S1-001 |
| 先に必要な修正 | CHG-F01-007 |

`src/main/resources/mapper/UserMapper.xml` 3〜6 行目(今のコード)

```xml
3:   <insert id="insert">
4:     INSERT INTO M_USER (NAME, MAIL, FAX)
5:     VALUES (#{name}, #{mail}, #{fax})
6:   </insert>
```

**CHG-F01-006 `src/main/resources/messages.properties`(修正)**

| 項目 | 内容 |
|---|---|
| 対象 | error.tel.format.strict |
| 場所 | `messages.properties:4` |
| 今の振る舞い | error.tel.format がある |
| 変更後 | error.tel.format.strict=電話番号の形式が正しくありません を追加する |
| 理由(要件) | REQ-S4-001 |

`src/main/resources/messages.properties` 1〜4 行目(今のコード)

```properties
1: label.user.name=氏名
2: label.user.mail=メールアドレス
3: label.user.fax=FAX番号
4: error.tel.format=電話番号の形式が正しくありません
```

**CHG-F01-007 `src/main/resources/db/migration/V19__add_user_tel.sql`(新規)**

| 項目 | 内容 |
|---|---|
| 対象 | M_USER.TEL |
| 場所 | (新しく作る) |
| 今の振る舞い | なし |
| 変更後 | M_USER に TEL VARCHAR(11) NULL を追加する |
| 理由(要件) | REQ-S1-001 |
| 手本にする既存実装 | `V18__add_item_code.sql:1` |

**CHG-R-001 `src/main/java/com/example/user/UserFormValidator.java`(新規)**

| 項目 | 内容 |
|---|---|
| 対象 | UserFormValidator#validate |
| 場所 | (新しく作る) |
| 今の振る舞い | なし |
| 変更後 | 電話番号を validateTelStrict でチェックし、NG なら error.tel.format.strict |
| 指示 | MemberFormValidator と同じ構成にする |
| 理由(要件) | REQ-S3-002 |
| 手本にする既存実装 | `MemberFormValidator.java:22` |
| 先に必要な修正 | CHG-F01-003 |

#### (3) 流用する既存処理

**RUS-001 MemberFormValidator#validate**

| 項目 | 内容 |
|---|---|
| 流用先 | `MemberFormValidator.java:22` |
| 要件 | REQ-S3-002 |
| 今の振る舞い | 電話番号を CommonValidator#validateTel でチェックする。ハイフンありも許容する |
| そのまま使えるか | 一部合わない |
| 流用のしかた | Validator クラスで形式チェックを行う構成を流用し、ユーザー登録用の Validator を作る |
| 合わない点 | ハイフンありを許容しているため、ハイフンなし(DEC-003)には合わない |
| 探した言葉 | 会員登録, MemberForm, Validator |

`src/main/java/com/example/member/MemberFormValidator.java` 21〜28 行目(今のコード)

```java
21:     @Override
22:     public void validate(Object target, Errors errors) {
23:         MemberForm form = (MemberForm) target;
24:         if (!commonValidator.validateTel(form.getTel())) {
25:             errors.rejectValue("tel", "error.tel.format");
26:         }
27:     }
28: }
```

#### (4) 既存機能への影響

**IMP-001 店舗登録(重大度: 高)**

| 項目 | 内容 |
|---|---|
| 原因の修正 | CHG-F01-003 |
| 場所 | `ShopFormValidator.java:24` |
| 今の使われ方 | 店舗の電話番号を validateTel でチェックしている |
| 起こりうること | validateTel 自体を変えると、ハイフンありの電話番号がエラーになる |
| 今回の扱い | 部分修正(新メソッド追加)にすれば影響しない(CMN-001) |
| 確認の観点 | 店舗登録で 03-1234-5678 が登録できる |

`src/main/java/com/example/shop/ShopFormValidator.java` 22〜26 行目(今のコード)

```java
22:     public void validate(Object target, Errors errors) {
23:         ShopForm form = (ShopForm) target;
24:         if (!commonValidator.validateTel(form.getTel())) {
25:             errors.rejectValue("tel", "error.tel.format");
26:         }
```

**IMP-002 ユーザー一覧のCSV出力(重大度: 中)**

| 項目 | 内容 |
|---|---|
| 原因の修正 | CHG-F01-007 |
| 場所 | `UserMapper.xml:8` |
| 今の使われ方 | SELECT * で全列を取得している |
| 起こりうること | TEL 列が増え、CSV の列が増える可能性がある |
| 今回の扱い | - |
| 確認の観点 | CSV の列が変わらないこと |

#### (5) 実装上の懸念

**CON-002 FAX 列の既存データ(重要度: 中)**

| 項目 | 内容 |
|---|---|
| 内容 | 画面と Form から FAX をなくしても、M_USER.FAX 列と既存データは残る |
| コードの根拠 | `UserMapper.xml:4` |
| 推奨する対応 | 今回は列を残し、後で削除するかを決める |
| ほかに関係する機能 | F-03 |

#### (6) 調べた範囲

| 修正 | 調べたこと | 結果 |
|---|---|---|
| CHG-R-001 | 呼び出し元<br>同じファイルを使う画面 | 影響なし |
| CHG-F01-001 | 呼び出し元<br>同じファイルを使う画面 | 影響なし |
| CHG-F01-002 | 呼び出し元<br>同じファイルを使う画面 | 影響なし |
| CHG-F01-003 | 呼び出し元<br>同じファイルを使う画面 | 影響あり |
| CHG-F01-004 | 呼び出し元<br>同じファイルを使う画面 | 影響なし |
| CHG-F01-005 | 呼び出し元<br>同じファイルを使う画面 | 影響なし |
| CHG-F01-006 | 呼び出し元<br>同じファイルを使う画面 | 影響なし |
| CHG-F01-007 | 呼び出し元<br>同じファイルを使う画面 | 影響あり |
| CHG-F01-003 | validateTel の呼び出し元 | 他の機能からも使われている |

---

### F-02

**電話番号の認証**

認証ボタンでSMSに認証コードを送り、入力されたコードで確かめる

#### (1) 今の処理の流れ(コードから)

| 順 | 場所 | 対象 | 今の振る舞い |
|---|---|---|---|
| 1 | `UserController.java:18` | UserController#showRegister | 登録画面を表示する |

#### (2) 修正箇所

**CHG-F02-001 `src/main/resources/templates/user/register.html`(修正)**

| 項目 | 内容 |
|---|---|
| 対象 | 電話番号欄の後 |
| 場所 | `register.html:10` |
| 今の振る舞い | 認証ボタン・認証コード欄はない |
| 変更後 | 電話番号認証ボタンと認証コードの入力欄を追加する。認証済みならボタンを非活性 |
| 理由(要件) | REQ-S2-001, REQ-S1-002 |
| 先に必要な修正 | CHG-F02-002 |

`src/main/resources/templates/user/register.html` 10〜13 行目(今のコード)

```html
10:   <div class="form-group">
11:     <label for="mail" th:text="#{label.user.mail}">メールアドレス</label>
12:     <input type="text" id="mail" th:field="*{mail}" class="form-control">
13:   </div>
```

**CHG-F02-002 `src/main/java/com/example/user/UserController.java`(修正)**

| 項目 | 内容 |
|---|---|
| 対象 | UserController#sendAuthCode |
| 場所 | `UserController.java:23` |
| 今の振る舞い | 認証用のハンドラはない |
| 変更後 | POST /user/auth-code を追加し、SmsAuthService を呼ぶ |
| 理由(要件) | REQ-S2-001 |
| 手本にする既存実装 | `UserController.java:22` |
| 先に必要な修正 | CHG-F02-003 |

`src/main/java/com/example/user/UserController.java` 22〜29 行目(今のコード)

```java
22:     @PostMapping("/user/register")
23:     public String register(@Validated UserForm form, BindingResult result) {
24:         if (result.hasErrors()) {
25:             return "user/register";
26:         }
27:         userService.register(form);
28:         return "redirect:/user/complete";
29:     }
```

**CHG-F02-003 `src/main/java/com/example/user/SmsAuthService.java`(新規)**

| 項目 | 内容 |
|---|---|
| 対象 | SmsAuthService#send |
| 場所 | (新しく作る) |
| 今の振る舞い | なし |
| 変更後 | 6桁の認証コードを作り、SMS で送信する |
| 理由(要件) | REQ-S3-001 |

#### (3) 流用する既存処理

(この機能に、既存の流用の要件はありません)

#### (4) 既存機能への影響

(既存機能への影響は見つかりませんでした。調べた範囲は (6) を見てください)

#### (5) 実装上の懸念

**CON-001 SMS 送信とトランザクション(重要度: 高)** → Q2

| 項目 | 内容 |
|---|---|
| 内容 | 登録処理は @Transactional。同じトランザクションで SMS を送ると、送信失敗で登録も取り消され、逆に登録失敗でも SMS が送られている |
| コードの根拠 | `UserService.java:14` |
| 推奨する対応 | SMS 送信は登録とは別の処理(認証ボタン押下時)で行い、登録のトランザクションに含めない |

`src/main/java/com/example/user/UserService.java` 14〜21 行目(今のコード)

```java
14:     @Transactional
15:     public void register(UserForm form) {
16:         User user = new User();
17:         user.setName(form.getName());
18:         user.setMail(form.getMail());
19:         user.setFax(form.getFax());
20:         userMapper.insert(user);
21:     }
```

#### (6) 調べた範囲

| 修正 | 調べたこと | 結果 |
|---|---|---|
| CHG-F02-001 | 呼び出し元<br>同じファイルを使う画面 | 影響なし |
| CHG-F02-002 | 呼び出し元<br>同じファイルを使う画面 | 影響なし |
| CHG-F02-003 | 呼び出し元<br>同じファイルを使う画面 | 影響なし |

---

### F-03

**FAX番号の廃止**

FAX番号の入力項目をなくす

#### (1) 今の処理の流れ(コードから)

| 順 | 場所 | 対象 | 今の振る舞い |
|---|---|---|---|
| 1 | `UserController.java:23` | UserController#register | UserForm(fax を含む)を受け取り、チェック後に UserService#register を呼ぶ |
| 2 | `UserService.java:15` | UserService#register | form.getFax() を User に詰め替えて insert する |
| 3 | `UserMapper.xml:3` | UserMapper.insert | FAX 列に #{fax} を INSERT する |

#### (2) 修正箇所

**CHG-F03-001 `src/main/resources/templates/user/register.html`(削除)**

| 項目 | 内容 |
|---|---|
| 対象 | FAX番号の入力欄 |
| 場所 | `register.html:14` |
| 今の振る舞い | FAX番号の入力欄がある |
| 変更後 | なくす |
| 理由(要件) | REQ-S1-003 |

`src/main/resources/templates/user/register.html` 14〜17 行目(今のコード)

```html
14:   <div class="form-group">
15:     <label for="fax" th:text="#{label.user.fax}">FAX番号</label>
16:     <input type="text" id="fax" th:field="*{fax}" class="form-control">
17:   </div>
```

**CHG-F03-002 `src/main/java/com/example/user/UserForm.java`(削除)**

| 項目 | 内容 |
|---|---|
| 対象 | UserForm.fax |
| 場所 | `UserForm.java:19` |
| 今の振る舞い | fax がある |
| 変更後 | なくす |
| 理由(要件) | REQ-S1-003 |
| 先に必要な修正 | CHG-F03-003 |

`src/main/java/com/example/user/UserForm.java` 18〜19 行目(今のコード)

```java
18:     @Size(max = 11)
19:     private String fax;
```

**CHG-F03-003 `src/main/java/com/example/user/UserService.java`(修正)**

| 項目 | 内容 |
|---|---|
| 対象 | UserService#register |
| 場所 | `UserService.java:19` |
| 今の振る舞い | fax を詰め替える |
| 変更後 | fax の詰め替えをなくす |
| 理由(要件) | REQ-S1-003 |

`src/main/java/com/example/user/UserService.java` 19〜19 行目(今のコード)

```java
19:         user.setFax(form.getFax());
```

#### (3) 流用する既存処理

(この機能に、既存の流用の要件はありません)

#### (4) 既存機能への影響

(既存機能への影響は見つかりませんでした。調べた範囲は (6) を見てください)

#### (5) 実装上の懸念

**CON-002 FAX 列の既存データ(重要度: 中)**

| 項目 | 内容 |
|---|---|
| 内容 | 画面と Form から FAX をなくしても、M_USER.FAX 列と既存データは残る |
| コードの根拠 | `UserMapper.xml:4` |
| 推奨する対応 | 今回は列を残し、後で削除するかを決める |
| ほかに関係する機能 | F-01 |

#### (6) 調べた範囲

| 修正 | 調べたこと | 結果 |
|---|---|---|
| CHG-F03-001 | 呼び出し元<br>同じファイルを使う画面 | 影響なし |
| CHG-F03-002 | 呼び出し元<br>同じファイルを使う画面 | 影響なし |
| CHG-F03-003 | 呼び出し元<br>同じファイルを使う画面 | 影響なし |

---

### 機能をまたぐ事項

**CMN-001 共通処理 CommonValidator#validateTel**(関係する機能: F-01) → Q1

| 呼び出し元 | 機能 | 今回の対象か | 使われ方 | 新しい振る舞いが必要か |
|---|---|---|---|---|
| `MemberFormValidator.java:24` | 会員登録 | 対象外 | 会員の電話番号の形式チェック | 不要 |
| `ShopFormValidator.java:24` | 店舗登録 | 対象外 | 店舗の電話番号の形式チェック | 不要 |

| 項目 | 内容 |
|---|---|
| 判断 | 部分修正(新メソッドを追加) |
| 理由 | 会員登録・店舗登録はハイフンありを許容しているため |
| 全体修正した場合 | 会員登録・店舗登録で、ハイフンありの電話番号がエラーになる |
| 関係する修正 | CHG-F01-003 |
| 同様の先例 | `CommonValidator.java:17` |

`src/main/java/com/example/common/CommonValidator.java` 8〜14 行目(今のコード)

```java
 8:     /** 電話番号の形式チェック(ハイフンあり・なしの両方を許容) */
 9:     public boolean validateTel(String tel) {
10:         if (tel == null || tel.isEmpty()) {
11:             return true;
12:         }
13:         return tel.matches("^[0-9-]{10,13}$");
14:     }
```

**複数の機能にかかわる懸念**

| 懸念 | 重要度 | 機能 | 内容 |
|---|---|---|---|
| CON-002 | 中 | F-03, F-01 | FAX 列の既存データ |

## 2. 確認事項

番号を付けて答えてください(例:「Q1: はい / Q2: ハイフンあり」)。**回答しなかった確認事項は、この資料に書かれている内容のまま確定します。**

| No | 機能 | 内容 | 回答例 |
|---|---|---|---|
| Q1 | F-01 | 共通チェックは部分修正(新メソッド validateTelStrict を追加)でよいですか? | 「部分修正でよい」 / 「全体修正にする」 |
| Q2 | F-02 | SMS 送信は登録とは別の処理で行う方針でよいですか? | 「よい」 / 「登録と同時に送る」 |

## 付録

### 回帰テストの観点

| 影響 | 機能 | 重大度 | 確認すること |
|---|---|---|---|
| IMP-001 | 店舗登録 | 高 | 店舗登録で 03-1234-5678 が登録できる |
| IMP-002 | ユーザー一覧のCSV出力 | 中 | CSV の列が変わらないこと |

### レビュー担当の点検

| 点検 | 判定 | 指摘 | 根拠を開いて確かめた数 |
|---|---|---|---|
| 途中の点検(修正箇所の特定後) | 合格 | 0 件(未対応 0 件) | 1 件 |
| フェーズ末の点検 | 条件付き合格 | 0 件(未対応 0 件) | 1 件 |

**承認の観点**

| No | 観点 | 結果 | メモ |
|---|---|---|---|
| 1 | 全要件に、修正箇所か流用先があるか | 問題なし |  |
| 2 | 流用先の特定と振る舞いの読み取り | 問題なし |  |
| 3 | 修正箇所の今の振る舞いがコードどおりか | 問題なし |  |
| 4 | 影響・懸念の根拠がすべてコードか | 問題なし |  |
| 5 | 共通処理の呼び出し元と判断 | 要確認 |  |
| 6 | 重大度・重要度 | 問題なし |  |
| 7 | 影響なしとした修正の調べた範囲 | 問題なし |  |

### 仮定の一覧

| ID | 仮定 | 理由 | 関係する項目 | 確認 |
|---|---|---|---|---|
| ASM-p2b-F02-001 | SMS 送信は外部 API を新規に使う | 既存に SMS 送信の実装がない | CHG-F02-003 | - |

### 正本のファイル

- 02_impact/ の各 YAML(reuse / changes / impacts / common_components / concerns)
