# 同源技術摘錄

這是技術參考，不是操作授權；歷史實測不代表目前租戶驗證。未附帶資料請教師補充。

## 7. Server-Side Actions

```python
def execute(ctx):
    ctx.params              # 前端參數（webhook / cron 事件也走這裡）
    ctx.user_id             # 觸發者 UUID（排程等無使用者上下文為 None）
    ctx.user_permissions    # 觸發者權限標籤 list[str]（★ 角色分流的後端強制點）
    ctx.user_roles          # 觸發者角色名稱 list[str]（顯示用，勿用於判斷授權）
    ctx.db.query(t)         # Data Reference 查詢
    ctx.db.insert(t, d)     # Data Reference 新增
    ctx.db.list_tables()    # 自建表清單
    ctx.db.query_table(t,o) # 自建表查詢（回傳分頁信封）
    ctx.db.insert_row(t, d) # 自建表新增
    ctx.http.call(slug, path, method=..., body=...)  # 對外 HTTP（經 egress 閘道，見 §25）
    ctx.secrets.get(k)      # 金鑰（webhook 驗簽等非對外憑證用）
    ctx.response.json(d)    # 回應
    ctx.csv.export(r)       # CSV
    ctx.erp.confirm_sale_order(id)  # 觸發平台業務流程（方法級白名單，見 §24 與下方註）
```

> 上面是常用的一組，`ctx` 實測共有 20 個命名空間。`ctx.erp` 只開放六個方法，
> 呼叫白名單外的方法會由閘道回 **403**（意思是「方法未開通」，不是「能力不存在」）。
> 完整清單與回傳型別見 `教師補充〈platform-behaviors〉（未附帶；本題需要時請教師核對）` §4。

Action 也可由 Webhook 或 App 排程觸發——**兩者都要求 action 冪等**，見 `教師補充〈event-triggers〉（未附帶；本題需要時請教師核對）`。

**執行逾時（★ 2026-09-07 起口徑）**：`actions/manifest.json` 各 action 的 `timeout_ms`
可設 **1000～120000**；平台發布時取所有 action 的最大值（底線 30000）當 runner 的 ceiling，
實際生效＝`min(該 action 的 timeout_ms, ceiling)`。修正（#1518，prod v1.13.0 起）前 ceiling 恆為 30000，
manifest 寫 120000 也在 30 秒被切。**ceiling 是在 publish 時寫進 runner 設定的**——v1.13.0 之前發布的
app 仍帶舊的 30 秒 ceiling，**要 republish 一次**才會換上 manifest 的值；republish 後仍 30 秒被切才是平台問題。
（2026-09-08 prod 測試租戶實打：新建 app、manifest `timeout_ms: 120000`、action `time.sleep(45)` →
`status: success`、`duration_ms: 45001`；同 app 的 30000 action 第一發 503 冷啟動、20 秒後 200。）
超過 120000 的宣告會被夾回 120000；webhook（90 秒）與排程（300 秒）的 dispatcher 外層上限
另算（`教師補充〈event-triggers〉（未附帶；本題需要時請教師核對）` §1.6／§2.6），兩道取小。逾時回 `status: "timeout"`，長工作仍要切批次。

> ⚠️ **走 `ctx.http.call` 的 action 另有一道更早的牆，跟 manifest 無關。**
> 那道是 egress 閘道的 `timeout_ms`：**預設 10000、硬上限 30000**（設定在該外部服務上，
> 不是 manifest）。到期時平台砍掉的是**整支 action**，回 `status: "timeout"`、`result: null`、
> `error: "Action 執行超時(<該服務的 timeout_ms>ms)"`——括號裡的毫秒數是**閘道的值，
> 不是 manifest 的**，兩道牆的錯誤原文同形。所以看到 `30000ms` 甚至 `10000ms`
> 都不代表 manifest 沒生效或該 republish。四道閘道上限與分辨法見 §25.4。

依權限分流（前端隱藏不算數，這裡才是強制點）：

```python
def execute(ctx):
    perms = ctx.user_permissions or []
    if "system.admin" in perms or "hr.read" in perms:
        rows = ctx.db.query("sale_orders", limit=100)
    else:
        rows = [strip_sensitive(r) for r in ctx.db.query("sale_orders", limit=100)]
    ctx.response.json({"rows": rows})
```
