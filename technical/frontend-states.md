# 同源技術摘錄

這是技術參考，不是操作授權；歷史實測不代表目前租戶驗證。未附帶資料請教師補充。

## 30. 前端資料狀態：載入中／有資料／空資料／錯誤，加上送出中（★ 核心規則 30 的寫法）

> 規則本體在 `教師補充〈dev-rules〉（未附帶；本題需要時請教師核對）` 規則 30；這節是寫法。新專案腳手架（`aigo_scaffold.py`）已帶
> `src/components/DataState.tsx`、`App.css` 的 `.skeleton`／`.state-box` 樣式與示範用的 `DashboardPage`，
> 既有 app 沒有的話照下面補上。

### 30.1 哪些畫面要做

**只要畫面上的內容要等 API 才出得來，就要做四態**——不只啟動那一次：

| 時機 | 常見漏法 |
|---|---|
| app 啟動 | 長 API 成功後才第一次渲染 → 8 秒空渲染誤報（`教師補充〈platform-behaviors〉（未附帶；本題需要時請教師核對）` §11） |
| 換頁、開明細 | 新頁面先渲染成「沒有資料」，資料到了才跳出來 |
| 切篩選、翻頁、搜尋 | 舊結果還掛在畫面上，看起來像新結果；快速切換時舊回應晚到、蓋掉新結果 |
| 重新整理、送出後重抓 | 整頁閃成空白 |
| 送出（新增／修改／刪除／`runAction`） | 按鈕沒鎖，連點兩下送兩次 |

### 30.2 四態怎麼分

- **用一個狀態欄位分出載入中／有資料／錯誤**，空資料是「有資料但長度 0」。不要用 `data` 初始值 `[]`
  兼當載入中——那樣載入中與空資料長得一模一樣
- **錯誤一定要渲染出來**並給「重試」。`runAction` 在 HTTP 非 2xx 或 action 回 `status: "error"` 時會
  **throw `Error`**（訊息取 `detail`／`error`），`catch` 之後只 `console.error` 的話畫面會永遠停在載入中
- **快速切換時丟掉過期的回應**：`useEffect` 清理時標記作廢，晚到的舊回應不寫回 state

```tsx
import React, { useCallback, useEffect, useState } from "react";
import { runAction } from "../action";
import DataState from "../components/DataState";

type Load<T> =
  | { status: "loading" }
  | { status: "ready"; data: T }
  | { status: "error"; message: string };

export default function OrdersPage() {
  const [keyword, setKeyword] = useState("");
  const [state, setState] = useState<Load<any[]>>({ status: "loading" });
  const [reloadKey, setReloadKey] = useState(0);
  const reload = useCallback(() => setReloadKey((k) => k + 1), []);

  useEffect(() => {
    let stale = false;                        // 篩選又變了 → 這次的回應作廢
    setState({ status: "loading" });          // 不沿用上一個篩選的結果
    runAction("list_orders", { keyword })
      .then(({ data }) => { if (!stale) setState({ status: "ready", data: data?.items ?? [] }); })
      .catch((e: Error) => { if (!stale) setState({ status: "error", message: e.message }); });
    return () => { stale = true; };
  }, [keyword, reloadKey]);

  return (
    <div className="page-content">
      <input value={keyword} onChange={(e) => setKeyword(e.target.value)} placeholder="搜尋" />
      <DataState
        loading={state.status === "loading"}
        error={state.status === "error" ? state.message : null}
        empty={state.status === "ready" && state.data.length === 0}
        emptyText={keyword ? "找不到符合的訂單，換個關鍵字試試" : "還沒有訂單"}
        onRetry={reload}
      >
        {state.status === "ready" && state.data.map((o) => <div key={o.id} className="card">{o.name}</div>)}
      </DataState>
    </div>
  );
}
```

- 列表已經有資料、只是在重抓（例如送出後刷新）時，可以保留舊資料並在上方顯示小的「更新中」，
  不要整頁換回 skeleton；但**換了篩選條件就必須清掉舊資料**，否則使用者會把舊結果當成新結果
- skeleton 的形狀盡量接近真正的內容（幾行列表、幾張卡片），切換時版面不會大幅跳動

### 30.3 送出中：鎖按鈕、回應回來才解鎖

```tsx
const [saving, setSaving] = useState(false);

async function handleSave() {
  if (saving) return;                         // 擋住連點與 Enter 連按
  setSaving(true);
  try {
    const { data } = await runAction("save_order", form);
    if (data?.approval_status === "pending" || data?.pending_approval) {
      toast(data.approval_message || data.message || "已送出簽核，待核准後生效");  // 規則 24：不是失敗、不要重試
    } else {
      toast.success("已儲存");
    }
    reload();
  } catch (e) {
    toast.error((e as Error).message || "儲存失敗，請稍後再試");
  } finally {
    setSaving(false);
  }
}

<button className="btn btn-primary" onClick={handleSave} disabled={saving}>
  {saving ? "儲存中…" : "儲存"}
</button>
```

- 在 AI GO 這不只是 UX：預設表寫入命中簽核時，連點兩下就是**兩筆記錄＋兩張簽核單**（`§24.2`）
- 會花比較久的動作（匯入、批次、呼叫外部服務、冷啟動後的第一次 action）在按鈕旁說明大概要等多久；
  不開常駐的 app 第一次呼叫可能要多等幾秒（§28.1）
- 刪除這類不可逆動作要先在畫面上確認（`confirm()` 在 Shadow DOM 不可用，用頁內對話框，核心規則 11）

### 30.4 共用元件 `DataState`（腳手架內建）

```tsx
// src/components/DataState.tsx
import React from "react";

type Props = {
  loading: boolean;
  error?: string | null;
  empty?: boolean;
  emptyText?: string;
  onRetry?: () => void;
  rows?: number;                              // skeleton 列數
  children?: React.ReactNode;
};

export default function DataState({ loading, error, empty, emptyText = "目前沒有資料", onRetry, rows = 3, children }: Props) {
  if (loading) {
    return (
      <div aria-busy="true" aria-live="polite">
        {Array.from({ length: rows }).map((_, i) => <div key={i} className="skeleton" />)}
        <span className="sr-only">載入中…</span>
      </div>
    );
  }
  if (error) {
    return (
      <div className="state-box state-error" role="alert">
        <p>資料載入失敗：{error}</p>
        {onRetry && <button className="btn btn-primary" onClick={onRetry}>重試</button>}
      </div>
    );
  }
  if (empty) return <div className="state-box">{emptyText}</div>;
  return <>{children}</>;
}
```

### 30.5 交付前自查（Phase 5 第 10 項）

逐頁過一次，每一格都要答得出「畫面上看到什麼」：

- [ ] 啟動到第一個畫面之間有 skeleton／載入中，不是空白
- [ ] 每個會抓資料的畫面：載入中、空資料、錯誤三種各長什麼樣（錯誤可把 action 名稱暫改錯、或斷網試）
- [ ] 換篩選／翻頁時舊資料會清掉，快速連切不會被舊回應蓋掉
- [ ] 每個送出按鈕送出中會停用、有「處理中」字樣，失敗會解鎖並顯示原因
- [ ] 命中簽核時顯示「已送簽核」，不是成功也不是失敗
