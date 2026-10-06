# 実装計画書(フェーズ3 承認資料)

> 調査: ユーザー登録への電話番号認証の追加(20261007-usertel)/ フェーズ3 実装計画
> この資料は YAML から自動で作られています。直したい点は、オーケストレータに伝えてください。
> 製造工程の入力です。手本・書き方・置き場所は、周辺の既存コードから決めています。

## はじめに

3つの機能を「FAX番号の廃止 → 電話番号の入力 → 電話番号の認証」の順に実装します。
SMS 送信だけは手本にできる既存実装がなく、確認事項にしています。

## 1. 実装計画(機能ごと)

### 実装の順番

依存関係を最優先にし、その中で「既存の削除 → 既存の流用 → 既存を手本に追加 → 既存の変更 → 新しい仕組み → 共通処理の変更・影響大」の順に並べています。

| 順 | 機能 | 進め方 | この順にした理由 | 前提 | 確認 |
|---|---|---|---|---|---|
| 1 | [F-03 FAX番号の廃止](#f-03) | 既存の削除 | 既存の項目を外すだけで、他の機能に依存しない | - | - |
| 2 | [F-01 電話番号の入力](#f-01) | 既存を手本に追加 | 会員登録の入力項目・Validator と同じ作りで追加できる。F-02 の前提になる | - | - |
| 3 | [F-02 電話番号の認証](#f-02) | 新しい仕組み | 外部 SMS 連携が新規で、懸念(高)があるため最後 | F-01 | Q1 |

---

### F-03

**FAX番号の廃止**(順番 1 / 既存の削除)

#### (1) ゴールと前提

| 項目 | 内容 |
|---|---|
| ゴール | FAX番号の入力項目がなくなり、登録は従来どおりできる |
| 前提(先に終わっている機能) | なし |
| 確定済みの判断 | なし |

#### (2) 作業手順

| 手順 | ファイル | 場所 | 直す行(今のコード) | やること | 手本にする既存実装 | 修正 |
|---|---|---|---|---|---|---|
| 1 | src/main/resources/templates/user/register.html | FAX番号の入力欄 | `register.html:14` | 入力欄を削除する | `register.html:15` | CHG-F03-001 |
| 2 | src/main/java/com/example/user/UserService.java | register | `UserService.java:19` | setFax をなくす | `UserService.java:19` | CHG-F03-003 |
| 3 | src/main/java/com/example/user/UserForm.java | fax | `UserForm.java:19` | fax を削除する | `UserForm.java:19` | CHG-F03-002 |

**手順1**

直す場所(CHG-F03-001): `src/main/resources/templates/user/register.html` 14〜17 行目(今のコード)

```html
14:   <div class="form-group">
15:     <label for="fax" th:text="#{label.user.fax}">FAX番号</label>
16:     <input type="text" id="fax" th:field="*{fax}" class="form-control">
17:   </div>
```

**手順2**

直す場所(CHG-F03-003): `src/main/java/com/example/user/UserService.java` 19〜19 行目(今のコード)

```java
19:         user.setFax(form.getFax());
```

**手順3**

直す場所(CHG-F03-002): `src/main/java/com/example/user/UserForm.java` 18〜19 行目(今のコード)

```java
18:     @Size(max = 11)
19:     private String fax;
```

#### (3) 新しく作るもの

(なし)

#### (4) 合わせる書き方(周辺のコードから)

(なし)

#### (5) 守るべき既存の振る舞い

| 振る舞い | 理由 |
|---|---|
| M_USER.FAX 列は残す | CON-002 |

#### (6) 確認方法

| ID | 種類 | 入力・操作 | 期待する結果 | どこで確認するか | 優先度 |
|---|---|---|---|---|---|
| TC-005 | 新規 | 登録画面を表示 | FAX番号の入力欄がない | 画面で確認 | 中 |

#### (7) 完了条件

- 登録画面に FAX 番号が表示されない
- 既存のテストがすべて通る

---

### F-01

**電話番号の入力**(順番 2 / 既存を手本に追加)

#### (1) ゴールと前提

| 項目 | 内容 |
|---|---|
| ゴール | ユーザー登録画面で電話番号を入力・チェック・保存できる。会員登録・店舗登録のチェックは従来どおり |
| 前提(先に終わっている機能) | F-03 |
| 確定済みの判断 | DEC-004: 共通チェックは部分修正(validateTelStrict を追加)<br>DEC-003: 電話番号はハイフンなしの数字11桁 |

#### (2) 作業手順

| 手順 | ファイル | 場所 | 直す行(今のコード) | やること | 手本にする既存実装 | 修正 |
|---|---|---|---|---|---|---|
| 1 | src/main/resources/db/migration/V19__add_user_tel.sql | 新規ファイル | (新しく作る) | M_USER に TEL VARCHAR(11) NULL を追加する | `V18__add_item_code.sql:1` | CHG-F01-007 |
| 2 | src/main/resources/mapper/UserMapper.xml | insert | `UserMapper.xml:3` | TEL を INSERT 列に追加する | `UserMapper.xml:4` | CHG-F01-005 |
| 3 | src/main/java/com/example/user/UserService.java | register | `UserService.java:15` | tel を詰め替える | `UserService.java:18` | CHG-F01-004 |
| 4 | src/main/java/com/example/common/CommonValidator.java | validateZipStrict の後 | `CommonValidator.java:9` | validateTelStrict(ハイフンなし11桁)を追加する。validateTel は変えない | `CommonValidator.java:17` | CHG-F01-003 |
| 5 | src/main/java/com/example/user/UserForm.java | mail の後 | `UserForm.java:16` | tel を追加する(@NotBlank、@Size(max = 11)) | `UserForm.java:12` | CHG-F01-002 |
| 6 | src/main/java/com/example/user/UserFormValidator.java | 新規ファイル | (新しく作る) | validateTelStrict で形式チェックする Validator を作る<br>(Controller の @InitBinder で登録する) | `MemberFormValidator.java:22` | CHG-R-001 |
| 7 | src/main/resources/templates/user/register.html | メールアドレス欄の後 | `register.html:10` | 電話番号の入力欄を追加する | `register.html:11` | CHG-F01-001 |
| 8 | src/main/resources/messages.properties | error.tel.format の後 | `messages.properties:4` | error.tel.format.strict と label.user.tel を追加する(文字コードは既存に合わせる)<br>(既存ファイルは Shift_JIS) | `messages.properties:4` | CHG-F01-006 |

**手順1**

手本: `src/main/resources/db/migration/V18__add_item_code.sql` 1〜2 行目(手本のコード)

```sql
1: ALTER TABLE M_ITEM
2:   ADD COLUMN ITEM_CODE VARCHAR(10) NULL;
```

**手順2**

直す場所(CHG-F01-005): `src/main/resources/mapper/UserMapper.xml` 3〜6 行目(今のコード)

```xml
3:   <insert id="insert">
4:     INSERT INTO M_USER (NAME, MAIL, FAX)
5:     VALUES (#{name}, #{mail}, #{fax})
6:   </insert>
```

**手順3**

直す場所(CHG-F01-004): `src/main/java/com/example/user/UserService.java` 14〜21 行目(今のコード)

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

**手順4**

直す場所(CHG-F01-003): `src/main/java/com/example/common/CommonValidator.java` 8〜14 行目(今のコード)

```java
 8:     /** 電話番号の形式チェック(ハイフンあり・なしの両方を許容) */
 9:     public boolean validateTel(String tel) {
10:         if (tel == null || tel.isEmpty()) {
11:             return true;
12:         }
13:         return tel.matches("^[0-9-]{10,13}$");
14:     }
```

手本: `src/main/java/com/example/common/CommonValidator.java` 16〜22 行目(手本のコード)

```java
16:     /** 郵便番号(ハイフンなし7桁)の厳密チェック。会員登録用に追加 */
17:     public boolean validateZipStrict(String zip) {
18:         if (zip == null) {
19:             return true;
20:         }
21:         return zip.matches("^[0-9]{7}$");
22:     }
```

**手順5**

直す場所(CHG-F01-002): `src/main/java/com/example/user/UserForm.java` 10〜16 行目(今のコード)

```java
10:     @NotBlank
11:     @Size(max = 50)
12:     private String name;
13: 
14:     @NotBlank
15:     @Email
16:     private String mail;
```

**手順6**

手本: `src/main/java/com/example/member/MemberFormValidator.java` 21〜28 行目(手本のコード)

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

**手順7**

直す場所(CHG-F01-001): `src/main/resources/templates/user/register.html` 10〜13 行目(今のコード)

```html
10:   <div class="form-group">
11:     <label for="mail" th:text="#{label.user.mail}">メールアドレス</label>
12:     <input type="text" id="mail" th:field="*{mail}" class="form-control">
13:   </div>
```

**手順8**

直す場所(CHG-F01-006): `src/main/resources/messages.properties` 1〜4 行目(今のコード)

```properties
1: label.user.name=氏名
2: label.user.mail=メールアドレス
3: label.user.fax=FAX番号
4: error.tel.format=電話番号の形式が正しくありません
```

#### (3) 新しく作るもの

| 種類 | 名前 | 置き場所 | 根拠(既存の命名・配置) |
|---|---|---|---|
| migration | V19__add_user_tel.sql | src/main/resources/db/migration | `V18__add_item_code.sql:1` |
| class | UserFormValidator | com.example.user | `MemberFormValidator.java:1` |

#### (4) 合わせる書き方(周辺のコードから)

| 観点 | 書き方 | 根拠 |
|---|---|---|
| 単項目チェック | Form のアノテーションで行う | `UserForm.java:10` |
| 形式チェック | Validator クラスを作り、CommonValidator を呼ぶ | `MemberFormValidator.java:22` |

#### (5) 守るべき既存の振る舞い

| 振る舞い | 理由 |
|---|---|
| CommonValidator#validateTel は変更しない | IMP-001, CMN-001 |

#### (6) 確認方法

| ID | 種類 | 入力・操作 | 期待する結果 | どこで確認するか | 優先度 |
|---|---|---|---|---|---|
| TC-001 | 新規 | 電話番号を空にして登録 | 必須エラーが表示される | UserFormTest に追加 | 高 |
| TC-002 | 新規 | 090-1234-5678 で登録 | MSG-E020 の形式エラー | UserFormValidatorTest(新規) | 高 |
| TC-003 | 回帰 | 店舗登録で 03-1234-5678 | 従来どおり登録できる | ShopFormValidatorTest | 高 |

#### (7) 完了条件

- 確認方法の F-01 の項目がすべて期待どおり
- 既存のテストがすべて通る

---

### F-02

**電話番号の認証**(順番 3 / 新しい仕組み)

#### (1) ゴールと前提

| 項目 | 内容 |
|---|---|
| ゴール | 認証ボタンで SMS に認証コードを送り、入力されたコードで確かめられる |
| 前提(先に終わっている機能) | F-01 |
| 確定済みの判断 | DEC-005: SMS 送信は登録とは別の処理で行う |

#### (2) 作業手順

| 手順 | ファイル | 場所 | 直す行(今のコード) | やること | 手本にする既存実装 | 修正 |
|---|---|---|---|---|---|---|
| 1 | src/main/java/com/example/user/SmsAuthService.java | 新規ファイル | (新しく作る) | 認証コードの作成と SMS 送信<br>(手本なし) | (手本なし) | CHG-F02-003 |
| 2 | src/main/java/com/example/user/UserController.java | register の後 | `UserController.java:23` | POST /user/auth-code を追加する | `UserController.java:22` | CHG-F02-002 |
| 3 | src/main/resources/templates/user/register.html | 電話番号欄の後 | `register.html:10` | 認証ボタンと認証コード欄を追加する | `register.html:18` | CHG-F02-001 |

**手順2**

直す場所(CHG-F02-002): `src/main/java/com/example/user/UserController.java` 22〜29 行目(今のコード)

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

**手順3**

直す場所(CHG-F02-001): `src/main/resources/templates/user/register.html` 10〜13 行目(今のコード)

```html
10:   <div class="form-group">
11:     <label for="mail" th:text="#{label.user.mail}">メールアドレス</label>
12:     <input type="text" id="mail" th:field="*{mail}" class="form-control">
13:   </div>
```

#### (3) 新しく作るもの

| 種類 | 名前 | 置き場所 | 根拠(既存の命名・配置) |
|---|---|---|---|
| class | SmsAuthService | com.example.user | `UserService.java:1` |

#### (4) 合わせる書き方(周辺のコードから)

| 観点 | 書き方 | 根拠 |
|---|---|---|
| トランザクション | Service のメソッドに @Transactional | `UserService.java:14` |

#### (5) 守るべき既存の振る舞い

| 振る舞い | 理由 |
|---|---|
| 登録処理のトランザクションに SMS 送信を含めない | CON-001 |

#### (6) 確認方法

| ID | 種類 | 入力・操作 | 期待する結果 | どこで確認するか | 優先度 |
|---|---|---|---|---|---|
| TC-004 | 新規 | 認証ボタンを押す | 認証コードが SMS で送られ、入力欄が表示される | 画面で確認 | 高 |

#### (7) 完了条件

- 確認方法の F-02 の項目がすべて期待どおり

## 2. 確認事項

番号を付けて答えてください(例:「Q1: はい / Q2: ハイフンあり」)。**回答しなかった確認事項は、この資料に書かれている内容のまま確定します。**

| No | 機能 | 内容 | 回答例 |
|---|---|---|---|
| Q1 | F-02 | SMS 送信の手本にできる既存実装がありません。新しい方式で作ってよいですか? | 「よい」 / 「別途方式を決める」 |

## 付録

### 修正箇所と手順の対応

| 修正 | 機能 | 手順 |
|---|---|---|
| CHG-F03-001 | F-03 | 1 |
| CHG-F03-002 | F-03 | 3 |
| CHG-F03-003 | F-03 | 2 |
| CHG-F01-007 | F-01 | 1 |
| CHG-F01-005 | F-01 | 2 |
| CHG-F01-004 | F-01 | 3 |
| CHG-F01-003 | F-01 | 4 |
| CHG-F01-002 | F-01 | 5 |
| CHG-R-001 | F-01 | 6 |
| CHG-F01-001 | F-01 | 7 |
| CHG-F01-006 | F-01 | 8 |
| CHG-F02-003 | F-02 | 1 |
| CHG-F02-002 | F-02 | 2 |
| CHG-F02-001 | F-02 | 3 |

### レビュー担当の点検

| 点検 | 判定 | 指摘 | 根拠を開いて確かめた数 |
|---|---|---|---|
| フェーズ末の点検 | 条件付き合格 | 0 件(未対応 0 件) | 1 件 |

**承認の観点**

| No | 観点 | 結果 | メモ |
|---|---|---|---|
| 1 | 全修正が手順に入っているか | 問題なし |  |
| 2 | 順番の方針 | 問題なし |  |
| 3 | 手本の既存実装 | 要確認 | F-02 手順1は手本なし |
| 4 | 新しく作るものの名前・置き場所・書き方 | 問題なし |  |
| 5 | 確認方法の網羅 | 問題なし |  |
| 6 | 判断の反映 | 問題なし |  |

### 正本のファイル

- 03_plan/plan.yaml / steps/ / verification.yaml
- 影響と懸念の詳細は 02_impact/impact_report.md
