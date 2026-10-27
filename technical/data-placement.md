# 同源技術摘錄

這是技術參考，不是操作授權；歷史實測不代表目前租戶驗證。未附帶資料請教師補充。

## 19. 資料承載體總決策（★ SSOT——所有分流指引以本節為準）

平台可用的資料承載體有**四種**＋一種已退場：**預設表原生欄位／預設表延伸欄位（EAV）／
預設表 `custom_data` JSONB／自建表（重用加欄或新建）**；CustomObject 已退場僅存量維護。
`教師補充〈dev-rules〉（未附帶；本題需要時請教師核對）` 規則 18、§22 遷移映射、`教師補充〈migration-workflow〉（未附帶；本題需要時請教師核對）` §2.4 的分流都是本節這棵樹的投影
——彼此如有出入，以本節為準。

**直接開發與現有應用遷入用同一棵樹**，只是輸入不同：直接開發的輸入是需求分析的
資料表清單；遷入的輸入是外部 schema 的映射表——判定邏輯完全一致，不因「這是搬進來的」
就放寬。

### 決策樹（表級 → 欄位級）

```
一個資料需求（新功能的表／欄位，或遷入映射中的外部表／欄位）
│
├─ 表級：平台有沒有同語意的實體？（案件追蹤→商機、往來機關→客戶、交付物→里程碑、待辦→活動…
│        先用業務語言查 教師補充〈default-table-lookup〉（未附帶；本題需要時請教師核對） §2 ＋ Meta API 標題；新建與遷入同一問，
│        舉證責任在「為什麼不用預設表」）
│   ├─ 有 → Data Reference 軌：把該預設表加入引用；每個欄位進下面「欄位級」
│   └─ 沒有（查過查表與 Meta 仍無，並把對照結果寫進資料承載表）→ 自建表軌：
│       租戶已有語意相同的自建表？
│       ├─ 有 → 重用；欄位不足 → 加實體欄位（教師補充〈data-center〉（未附帶；本題需要時請教師核對） §7）
│       └─ 無 → 新建自建表（建表規格 → 用戶確認 → POST /data-center/tables）
│
└─ 欄位級（只有預設表需要走這段；自建表缺欄一律加實體欄位）：
    原生欄位語意對得上？ → 原生欄位（永遠優先）
    對不上 → ★ 第一問：**這個 app 執行期要讀或寫這個欄位嗎？**
    ├─ 要（前端顯示、帶進表單、action 計算…）
    │   → custom_data JSONB，或整個實體改走自建表
    │     （★ **延伸欄位在 app 執行期取不到值**——action 打 EAV 端點 401、
    │      前端要 builder.access；四條通道全斷見 教師補充〈data-center〉（未附帶；本題需要時請教師核對） §10）
    └─ 不要（只在資料中心 UI 由管理者維護、給平台功能／報表看）
        ├─ 租戶級正式欄位（要型別驗證、資料中心 UI 可見可管理）
        │   → 延伸欄位（EAV，教師補充〈data-center〉（未附帶；本題需要時請教師核對） §10；ctx.db／db.ts 不回傳其值）
        └─ app 私有標記（app_domain 恆在此）、暫時性、鬆散擴充
            → custom_data JSONB（標記規範見 `教師補充〈dev-rules〉（未附帶；本題需要時請教師核對）` 規則 19）
```

### 決策流程（動手前的盤點順序）

1. **先盤點兩邊**（★ 兩邊都不可跳過）：
   - `GET /api/v1/data-center/tables` — 租戶既有自建表
   - **預設表語意對照**：每個實體用業務語言查 `教師補充〈default-table-lookup〉（未附帶；本題需要時請教師核對）` §2，再用 Meta API 看標題
     （`教師補充工具〈aigo_data〉（未附帶） meta tables --source erp --grep`）。`GET /api/v1/refs/available-tables`（§20.1）
     只是表名清單、`comment` 實務上為空，不能當語意來源。結果寫進資料承載表（教師補充〈SKILL〉（未附帶；本題需要時請教師核對） Phase 1.5 第 3 項）
2. 既有自建表語意相同 → **直接重用**，不要新建；重用的表**欄位不足 → 加實體欄位**
   （`教師補充〈data-center〉（未附帶；本題需要時請教師核對）` §7），不要因缺欄就另建表或把結構化欄位塞進 json 欄
3. 對候選預設表查欄位（§20.2，**欄位有無只認引用面 columns**），確認權限是否足夠；
   缺欄位時依決策樹的欄位級分流——**app 要讀寫的欄位**用 `custom_data` JSONB 或改走自建表、
   只在資料中心 UI 維護的租戶級正式欄位才用**延伸欄位**（EAV，`教師補充〈data-center〉（未附帶；本題需要時請教師核對）` §10）
   （預設表本體不可加實體欄位）
4. 每張表／每個欄位走上面的決策樹定案
5. 走 Data Reference → 把表加入引用（引用狀態一律以 `GET /api/v1/refs/apps/{app_id}` 為準，
   **不要看 `db.json`**，見 `教師補充〈platform-behaviors〉（未附帶；本題需要時請教師核對）` §6）。
   可用 API `POST /api/v1/refs/apps/{app_id}`（`builder.access`，
   body `{table_name, columns[], permissions[]}`），或引導用戶到 Builder 後台操作
   走自建表 → 產出建表規格交用戶確認，再 `POST /api/v1/data-center/tables`；
   **建好（或決定重用既有自建表）後，同樣要替 app 登記引用**——用同一支 `POST /api/v1/refs/apps/{app_id}`
   （Builder「待允許的資料表」只在被擋下之後才有那一列，是事後補救，不能事前登記）。
   REST 與資料中心 UI 建表都不會自動登記（Builder AI 建表、套用模板才會）；沒登記，`ctx.db` 會回「自建表不存在」（`教師補充〈data-center〉（未附帶；本題需要時請教師核對）` §7）

### 選擇矩陣（速查——結論與決策樹一致）

| 條件 | 選擇 | 說明 |
|------|------|------|
| 平台有同語意的實體（`教師補充〈default-table-lookup〉（未附帶；本題需要時請教師核對）` §2 或 Meta API 命中） | **Data Reference** | 與平台功能共用同一份資料；舉證責任在「為什麼不用」 |
| 租戶已有語意相同的自建表 | **重用該自建表** | 自建表跨 app 共用，重複建 = 資料分裂 |
| 重用的自建表缺欄位 | **加實體欄位** | `教師補充〈data-center〉（未附帶；本題需要時請教師核對）` §7；不要另建表或塞 json |
| 平台沒有同語意實體（查過查表與 Meta 仍無，理由已寫進資料承載表） | **自建表** | 真實資料表、真外鍵、200 張配額 |
| 需要真正的關聯完整性（刪除被引用列要被擋） | **自建表** | relation → 自建表會建真 FK（但**沒有 cascade**，`教師補充〈data-center〉（未附帶；本題需要時請教師核對）` §3） |
| 需要唯一約束／冪等寫入／併發防線 | **自建表 unique 欄** | 預設表**沒有**唯一約束可用；需要冪等的預設表寫入要先在自建表搶錨點（§23.9） |
| 自建表要指回預設表實體（遷入案的 `user_id` 等） | **`text` 存 UUID** | relation → 預設表只有部分表可用、無法事先查（`教師補充〈data-center〉（未附帶；本題需要時請教師核對）` §3）；規劃時一律當不支援 |
| 預設表缺欄位，且 **app 執行期要讀寫它** | **`custom_data`**，或整個實體改走自建表 | ★ 延伸欄位在 app 內取不到值（`教師補充〈data-center〉（未附帶；本題需要時請教師核對）` §10 通道表） |
| 預設表缺「租戶級正式欄位」，且**只在資料中心 UI 維護、app 不讀** | **延伸欄位** | EAV overlay；讀寫走獨立端點、需 `builder.access`（`教師補充〈data-center〉（未附帶；本題需要時請教師核對）` §10） |
| app 私有標記、臨時、鬆散、不值得定義欄位 | **預設表 `custom_data`** | 免定義成本；`app_domain` 恆在此 |

### 入口情景對照（同一棵樹的三個入口）

| 情景 | 輸入 | 走法 |
|------|------|------|
| 直接開發新功能 | Phase 1.5 需求分析的資料表清單 | 每張表／欄位直接走決策樹 |
| 現有應用遷入（Custom App） | `教師補充〈migration-workflow〉（未附帶；本題需要時請教師核對）` §2.4 的映射表 | 外部每張表／欄位經映射走**同一棵樹**；映射未經用戶確認不得匯入（§2.5 閘門） |
| 現有應用遷入（Hosted App） | 同上 | **分流結果相同**；差別只在存取方式改走 Open Proxy（`教師補充〈hosted-apps〉（未附帶；本題需要時請教師核對）` §7.1），原 DB 退場 |

### 禁止項（不進決策樹的選項）

- **CustomObject**（`data.json`／`listRecords`／`ctx.db.query_object`）——已退場，
  存量維護、新需求禁用（`教師補充〈CONTEXT〉（未附帶；本題需要時請教師核對）`、`教師補充〈data-center〉（未附帶；本題需要時請教師核對）` §8）
- **app 內自建使用者／角色表**——身分與權限沿用平台（`教師補充〈dev-rules〉（未附帶；本題需要時請教師核對）` 規則 23）；
  遷入專案的 users 表走 `教師補充〈project_deconstruction_template〉（未附帶；本題需要時請教師核對）` 的認證映射
- ★ **不是資料層的東西**（強制；「寫得進去」不等於「可以放」）：

  | 東西 | 為什麼不行 | 改放哪 |
  |---|---|---|
  | **runner 本機檔案**：action 用 `open()` 寫 `.json`／sqlite／pickle 當輕量 db | runner **不擋寫檔**——語言級沙箱已整個拆掉（`infra/runner/runner/sandbox.py` 檔頭：白名單 import／builtins 限制／黑名單全移除，隔離只剩 pod＋NetworkPolicy）；`/tmp` 是 1 GiB `emptyDir`、`/var/tmp` 也可寫，只有 `/app` 因 uid 65532 寫不進。但 emptyDir 隨 pod 消失：已發布 runner 預設縮到零（§28）、每次 publish 換新 revision，檔案都清空 | 自建表（決策樹）。一次請求內的暫存檔可以用 `/tmp`，請求結束就當它不存在 |
  | **程序內全域變數／module-level cache** 當狀態 | 同一顆 pod 連續呼叫看得到（實測 pid 不變、計數累加），縮零與重部署就歸零 | 自建表；跨請求快取一律不做、每次重算（§23.9 的 Loader 只限一個請求範圍） |
  | **前端 `localStorage`／IndexedDB** 存業務資料 | 只在該瀏覽器、該裝置；換機或清站台資料就沒了，其他人也看不到 | 自建表／`custom_data`；localStorage 只放 UI 偏好（§9 首訪提示那種 per-slug 記憶） |

  **為什麼開發期測不出來**：`use_dev=true` 的試跑跑在**租戶共用的 dev-runner**（一顆 pod、
  同租戶所有 app 共用；實測連續跑兩天多沒換過 pid），檔案會一直在——A app 寫的 B app 還讀得到。
  上線後走 per-app runner 才開始消失，症狀是「打開是舊數字」「資料隔一陣子回到初始值」
  「count 從頭數」，與規則 31 同一類「開發時測不出來、上線就爆」。
  （2026-09-13 測試租戶實打：探針 action `open()` 寫 `/tmp` 連跑三次 count 1→2→3、
  sqlite rows 累加到 3、`httpx`／`requests`／`subprocess` 全部 importable；已發布 runner
  縮零後 `/tmp` 消失這一點是從 operator `resources.go` 的 emptyDir 掛載推出，未實打）

### 兩軌的關鍵差異

| | Data Reference | 自建表 |
|---|---|---|
| 歸屬 | 引用平台既有表 | 租戶自有的新表 |
| 跨 app | 共用，靠 `app_domain` 區分來源 | 共用，**不需要也不該用** `app_domain` |
| 外鍵 | 無原生 FK | relation → 自建表**有真 FK** |
| 建立方式 | Builder 後台加入引用 | `POST /data-center/tables`（需 `datacenter.schema_write`）＋**登記引用**（Builder AI 建表、套用模板才自動登記） |
| 怎麼盤點 | `GET /refs/apps/{app_id}`（**不是** `db.json`，那個恆為 `{}`） | 租戶有哪些：`GET /data-center/tables`（租戶級，不在 VFS）；這支 app 引用了哪些：`GET /refs/apps/{app_id}` |

### 預設表常見結構

預設表通常包含以下標準欄位：

| 欄位 | 型別 | 說明 |
|------|------|------|
| `id` | UUID | 主鍵 |
| `name` | VARCHAR | 名稱 |
| `active` | BOOLEAN | 啟用狀態 |
| `description` | TEXT | 描述 |
| `custom_data` | JSONB | **App 擴充資料**（app_domain + 自訂欄位） |
| `user_id` | UUID | 負責人 |
| `customer_id` | UUID | 客戶 |
| `stage_id` | UUID | 階段 |
| `created_at` | TIMESTAMP | 建立時間 |
| `updated_at` | TIMESTAMP | 更新時間 |
