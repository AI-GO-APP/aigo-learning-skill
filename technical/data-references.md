# 同源技術摘錄

這是技術參考，不是操作授權；歷史實測不代表目前租戶驗證。未附帶資料請教師補充。

## 20. Data Reference 探索 API

用於在開發規劃階段（Phase 1.5）探索所有可用的預設表，決定哪些表適合作為 Data Reference。

### 20.1 查詢可用資料表清單

```http
GET /api/v1/refs/available-tables
Authorization: Bearer {access_token}
```

功能：列出資料庫中所有目前可以被 Custom App 引用的資料表名稱與備註。自動排除系統敏感黑名單表。

> ⚠️ **`comment` 實務上是空字串**（2026-09-09 核自原始碼：它取資料庫的表註解，平台的業務表沒有宣告；
> issue #53 實查 359 張全空）。下面回應範例裡的備註是理想樣貌，**不要拿本端點做語意判斷**——
> 表的中文標題與功能區在 Meta API（`GET /api/v1/data-center/meta/tables`，
> `教師補充工具〈aigo_data〉（未附帶） meta tables --source erp`），業務語言的索引在 `教師補充〈default-table-lookup〉（未附帶；本題需要時請教師核對）` §2；
> 本端點只用來確認「引用面有沒有這張表」。

權限限制：帳號必須擁有 `builder.access` 權限。

回應範例：

```json
[
  {"name": "customers", "comment": "客戶/夥伴"},
  {"name": "sale_orders", "comment": "銷售訂單"},
  {"name": "project_projects", "comment": "專案"},
  {"name": "project_tasks", "comment": "專案任務"},
  {"name": "account_invoices", "comment": "發票"},
  {"name": "product_templates", "comment": "產品模板"}
]
```

### 20.2 查詢特定資料表欄位

```http
GET /api/v1/refs/tables/{table_name}/columns
Authorization: Bearer {access_token}
```

功能：列出指定資料表下可用的欄位資訊（含欄位名稱、資料型別、是否可為 Null、是否為系統欄位）。

權限限制：帳號必須擁有 `builder.access` 權限。

★ **這一面是欄位的唯一權威**。`GET /data-center/meta/tables/{key}` 的 `fields` 是給 Workspace
grid／表單用的**策展白名單**，實體表有、白名單未列的欄位不輸出（`hr_employees`：Meta 20 欄
vs 引用面 42 欄，缺的正是戶籍／通訊地址那批）。判「平台有沒有這個欄位」只看本端點，
Meta 面只用來讀中文標題與值域——理由與逐表落差見 `教師補充〈default-table-lookup〉（未附帶；本題需要時請教師核對）` §0（issue #70）。

回應範例：

```json
[
  {"name": "id", "type": "UUID", "nullable": false, "is_system": true},
  {"name": "tenant_id", "type": "UUID", "nullable": false, "is_system": true},
  {"name": "name", "type": "VARCHAR(255)", "nullable": false, "is_system": false},
  {"name": "email", "type": "VARCHAR(255)", "nullable": true, "is_system": false},
  {"name": "phone", "type": "VARCHAR(50)", "nullable": true, "is_system": false},
  {"name": "custom_data", "type": "JSONB", "nullable": true, "is_system": false},
  {"name": "created_at", "type": "TIMESTAMP", "nullable": false, "is_system": true},
  {"name": "updated_at", "type": "TIMESTAMP", "nullable": false, "is_system": true}
]
```

欄位說明：

| 欄位 | 說明 |
|------|------|
| `name` | 欄位名稱 |
| `type` | 資料型別（UUID, VARCHAR, TEXT, INTEGER, BOOLEAN, NUMERIC, JSONB, DATE, TIMESTAMP 等） |
| `nullable` | 是否可為 NULL |
| `is_system` | 是否為系統欄位（id, tenant_id, created_at, updated_at 等，不可手動寫入） |

> ⚠️ **這四個鍵就是全部——帶 CHECK 約束的欄位其合法值域從這裡看不到**（2026-09-02 實測）。
> 照 `type: VARCHAR` 填語意合理的值（`customer_type: "person"`）會直接 **500**
> `CheckViolationError`，回應是資料庫例外原文，不指出欄位也不列合法值。
> 值域來源有兩個，規劃匯入 payload 時**先查再寫**，不要對正式租戶試寫：
>
> 1. **Meta API** `GET /api/v1/data-center/meta/tables/{key}`（登入即可）——回傳 `FieldDef`，
>    select 型欄位帶 `options`。**2026-09-03 測試租戶實測已可用**（193 張：85 預設＋108 自建）：
>    `crm_clients` 回 `customer_type ∈ [company, individual]`、`sale_orders` 回 `state`／`tax_type`／
>    `invoice_format` 的值域。⚠️ **Meta key ≠ proxy／refs 面的表名**（客戶在 Meta 是 `crm_clients`，
>    proxy 面是 `customers`）——先 `教師補充工具〈aigo_data〉（未附帶） meta tables --grep` 找 key 再取
>    （`教師補充〈data-operations〉（未附帶；本題需要時請教師核對）` §4）
> 2. 下表——從平台原始碼 `backend/app/models` 的 `CheckConstraint` 整理（2026-09-01 main），
>    Meta API 打不到或表不在其中時用這張

#### 20.2.1 常用預設表的 CHECK 值域（核自原始碼；`customer_type` 兩值已 prod 實測 201）

| 表 | 欄位 | 合法值 |
|---|---|---|
| `customers` | `customer_type`（必填） | `company`（配 `is_company=true`）／`individual` |
| `customers` | `status` | `active`／`suspended` |
| `sale_orders` | `state` | `draft`／`sent`／`sale`／`done`／`cancel` |
| `sale_orders`、`sale_order_lines` | `invoice_status`（可空） | `no`／`to_invoice`／`invoiced` |
| `sale_order_lines` | `display_type`（可空） | `line_section`／`line_note` |
| `product_templates` | `type` | `consu`／`service`／`combo` |
| `product_templates` | `invoice_policy`（可空） | `order`／`delivery` |
| `product_templates` | `service_type`（可空） | `manual`／`timesheet` |
| `product_templates` | `expense_policy`（可空） | `no`／`cost`／`sales_price` |
| `account_payments` | `payment_type` | `inbound`／`outbound` |
| `account_payments` | `partner_type`（可空） | `customer`／`supplier` |
| `account_payments` | `state` | `draft`／`posted`／`cancel`／`reconciled` |
| `crm_leads` | `type` | `lead`／`opportunity` |
| `crm_leads` | `priority` | `'0'`／`'1'`／`'2'`／`'3'`（字串） |
| `crm_activities` | `activity_type` | `email`／`call`／`meeting`／`todo` |
| `crm_activities` | `state` | `planned`／`done`／`overdue`／`cancelled` |
| `hr_leaves` | `state` | `draft`／`confirm`／`refuse`／`validate1`／`validate`／`cancel` |
| `hr_expenses` | `state` | `draft`／`reported`／`approved`／`done`／`refused` |
| `hr_expense_sheets` | `state` | `draft`／`submit`／`approve`／`post`／`done`／`cancel` |

不在表上的欄位：先打 Meta API；再不行，把該欄留空或填 `draft` 一類最保守的值先建列，
值域確認後再 PATCH——**不要**在正式租戶用試寫法窮舉。

**必填欄**（`nullable=False` 且無預設值，如 `customers.customer_type`、`hr_expenses.employee_id`、
`project_milestones.project_id`）與**唯讀表**（`stock_moves`、`analytic_lines` 等平台獨寫表）的清單在
`教師補充〈default-table-lookup〉（未附帶；本題需要時請教師核對）` §4——匯入 payload 缺必填欄、或寫到唯讀表，都不是值域問題，先查那裡。

> 上面的回應範例是 `customers` 這類「自帶 `tenant_id`」的表。**不是每張表都有 `tenant_id`**，
> 缺了也不代表沒保護——見 §20.3。

### 20.3 租戶邊界：不要用「有沒有 `tenant_id`」判斷

這是最容易誤判的一點。你會看到某些表的欄位清單裡**沒有** `tenant_id`，例如
`msg_messages`、`announcement_reads`、`import_mappings`、`ir_sequences`、`account_accounts`。

**這些都不是 bug，租戶隔離也沒有失效。** DB Proxy 的租戶邊界依表而定，有四種形態：

| 形態 | 邊界怎麼來 | 例子 |
|---|---|---|
| 自帶 `tenant_id` | 直接過濾（多數表） | `customers`、`sale_orders` |
| **欄位別名** | 租戶欄位存在，但欄位名是歷史欄位名 `company_id` | `ir_sequences`、`partner_banks` |
| **父表歸屬** | 子表本身無租戶欄位，靠 `EXISTS` 子查詢繞父表驗證 | `msg_messages`→`msg_threads`、`announcement_reads`→`announcements`、`import_mappings`→`import_jobs` |
| **全域表** | 平台 seed 的參考資料，全租戶共用，**刻意不過濾**；讀放行、寫 403 | `countries`、`currencies`、`account_accounts` |

上表的例子是舉例、不是窮舉，**不要拿這份清單當判定依據**（真正的依據見下面守則 2）。
（自建表不在此列，那是另一軌，見 §19。）

**兩條實作守則：**

1. **不要自己補 `WHERE tenant_id = ...`。** 邊界由 Proxy 注入，你手動補在後三種形態的表上，
   只會因為欄位不存在而直接失敗。
2. **不要因為「這張表沒有 `tenant_id`」就改用別的資料表、或自己加一層過濾。**
   平台的判定依據是後端的顯式登記表，不是欄位偵測。

> **反過來也成立**：若你查詢某張表時拿到「欄位不存在」類的 500，代表這張表未被登記為
> 上述任一形態——它不是給 App 引用的表，換一張，不要試圖繞過。

### 20.4 典型使用流程

```
Phase 1.5 實作計畫時：

1. GET /api/v1/refs/available-tables
   → 取得所有可用預設表清單

2. 對每個候選表 GET /api/v1/refs/tables/{name}/columns
   → 確認欄位結構、是否有 custom_data (JSONB)
   ★ 欄位判定只認這一步；Meta 面的 fields 是策展白名單會少欄（§20.2）

3. 決定資料架構：哪些需求用預設表、哪些用自建表（見 §19）

4. 在 AI GO Builder 後台將選定的預設表加入 Data Reference

5. 用 GET /api/v1/refs/apps/{app_id} 確認引用已包含所需的表

6. 要移除引用：DELETE /api/v1/refs/{ref_id}（ref_id 從第 5 步的清單取；204，再刪 404「引用不存在」）
   ⚠️ 不是 DELETE /api/v1/refs/apps/{app_id}/{ref_id}——那條路徑不存在，回 404「Not Found」
   （2026-09-08 prod 實打）。改欄位／權限用 PATCH /api/v1/refs/{ref_id}
```

> **重要**：`available-tables` 僅列出可用表名，實際將表加入 App 的 Data Reference 需在 AI GO Builder 後台操作。
> 加入後，該表的 schema 由 Runtime 在執行期注入；**VFS 裡的 `src/db.json` 實測恆為 `{}`，
> 不能用來確認引用狀態**——一律查 `GET /api/v1/refs/apps/{app_id}`（見 `教師補充〈platform-behaviors〉（未附帶；本題需要時請教師核對）` §6）。

> **自建表也走同一組引用**：`/refs/apps/{app_id}` 不只給預設表。app 要讀寫的自建表同樣得登記
> （事前用 `POST /api/v1/refs/apps/{app_id}`，`builder.access`；被擋下後才可在 Builder「資料與 API 權限」分頁的「待允許的資料表」補），
> 登記後即時生效、不必重新發布。完整說明與建表路徑對照 → `教師補充〈data-center〉（未附帶；本題需要時請教師核對）` §7「app 讀寫自建表要先登記引用」。
