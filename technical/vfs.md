# 同源技術摘錄

這是技術參考，不是操作授權；歷史實測不代表目前租戶驗證。未附帶資料請教師補充。

## 3. VFS 標準檔案樹

```
package.json
src/main.tsx          ★ 入口點
src/App.tsx           路由 + Layout
src/App.css           全域樣式
src/api.ts            [SDK] 自建表 CRUD（+ legacy CustomObject 方法）
src/db.ts             [SDK★] DB Proxy
src/action.ts         [SDK] Server Action
src/approval.ts       [SDK★] 簽核操作（見 §24.4）
src/user.ts           [SDK★] 登入者角色／權限快照（見 §6）
src/data.json         [INJ] legacy CustomObject 定義（已退場，見 教師補充〈CONTEXT〉（未附帶；本題需要時請教師核對））
src/db.json           [INJ] Data Reference
src/actions.json      [INJ] Action 清單
src/pages/            頁面元件
src/components/       共用元件
actions/manifest.json Action 註冊
actions/*.py          Action 實作
```

> **★ 標記的 SDK 檔案不是建立 App 時就有的**——只有 `api.ts` / `action.ts` 隨 App 建立產生，
> `db.ts` / `approval.ts` / `user.ts` 要**到 Builder 後台開一次「開發」分頁**才會補進 VFS。
> 純走 API 的開發流程 `import "../user"` 會編譯失敗，補救見 `教師補充〈platform-behaviors〉（未附帶；本題需要時請教師核對）` §10.2。
> SDK 檔案開頭都有 `/* @ai-go-sdk */` 標記，平台以此判斷可否覆寫——**不要動它們**。


## 4. 程式碼注入 API

| 操作 | 方法 | 端點 |
|------|------|------|
| 取得 App | GET | `/api/v1/builder/apps/{slug_or_id}` |
| 局部更新 | PATCH | `/api/v1/builder/apps/{id}/source/files` |
| 刪除檔案 | DELETE | `/api/v1/builder/apps/{id}/source/files` |
| 全量覆寫 | PUT | `/api/v1/builder/apps/{id}/source` |

樂觀鎖：帶入 `expected_version`，版本不匹配回傳 409。


## 5. 編譯 API

```http
POST /api/v1/compile/compile/{slug}?dev=true
→ {"success": true, "html": "...", "bundle_js": "...", "css": "..."}
→ {"success": false, "error": "..."}
```

限制：取得 App ID 後查 `GET /api/v1/builder/apps/{app_id}/limits`（平台 Bearer token、`builder.access`）。`vfs` 回檔數、UTF-8 單檔 bytes 與編譯 timeout；`action` 回執行時間範圍；`egress` 回有效全域上限，停用時為 null。個別外部服務可能另設較低值。404／503 代表目前無法取得，勿改用固定值。

編譯與發布回應的 `skipped_files` 含 path、size、reason；不論 success 與否都要讀取。空陣列代表沒有略過，null／缺欄位代表未知。node_modules 與 tsconfig 不計入檔數；其餘輸入即使略過仍計數。

單檔超限仍會被略過，檔數超限會使編譯失敗；靜態 import 被略過的檔案也可能使
整體編譯失敗。請檢查報告並向用戶說明哪些內容未納入，不能只看 success。

本節的 API 需要平台部署 #1673；尚未部署時明確回報限制未知，不採用歷史版本數字。
本文件其餘章節有日期的實測 timeout 數字只代表當時環境；當前 Action／egress 的全域
範圍與預設以 limits 為準，個別服務以該服務設定為準。

External 模組（不需安裝）：react, react-dom, lucide-react, react-router-dom, react-hot-toast


## 9. Shadow DOM CSS 規範

```css
/* ✅ 正確 */
:host, :root { --primary: #2563eb; }
html, :host { line-height: 1.5; }

/* ❌ 錯誤 */
:root { --primary: #2563eb; }
```

JS API 限制：confirm()→false, alert()→不顯示, prompt()→null。
容器必須：`height: 100vh; overflow-y: auto`。

**平台標識（2026-08 改版）**：舊的右下角常駐藥丸已改為**頂部滿版橫條**
「第三方應用程式｜由 AI GO 平台代管，非官方頁面」——只在每個使用者
**首次造訪**顯示 5 秒後自動消失（per-slug 記在 localStorage），
`pointer-events: none` 不吃點擊。App 不再需要為它避讓右下角；
但**不要嘗試用 CSS/DOM 蓋掉或移除它**——平台有 MutationObserver 自癒
（移除會掛回、竄改樣式會整體重設），這是明文防護面。


## 10. VFS 注入規範

- 每次注入必須提供完整的檔案內容（raw string）
- 禁止字串拼接或模板佔位符
- 禁止 `// ... 省略` 之類的佔位

**路徑會在寫入前正規化（2026-08 起）**：

- 非法路徑直接 **400 `無效的檔案路徑`**（不再靜默寫入髒 key）：
  含 `\` 反斜線、以 `/` 開頭、含 `..` 段、normalize 後為空
- 大小寫自動折疊三處：首段 `Actions/`→`actions/`、第二段 `_Shared/`→`_shared/`、
  副檔名 `.PY`→`.py`；其餘路徑段大小寫不動
- `actions/./foo.py` 與 `actions/foo.py` 視為同一檔（last-wins 合併，不再分叉）

action 路徑約定不變：`actions/**.py` 是可呼叫 action（`action_name` = 去前綴去副檔名，
如 `sub/x` ↔ `actions/sub/x.py`）；`actions/_shared/**.py` 是共用模組——
**不是 action**，不要求 `execute(ctx)`、不可用 action_name 呼叫。
