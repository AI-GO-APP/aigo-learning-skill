# 學習版：零程式經驗的開始方式

## 課前由學員完成

1. 二選一準備可在本機讀寫專案的協作工具：Claude Code 或 Codex。課程要求至少 Pro 等級；這是課程準備要求，不是所有工具的最低技術門檻。
2. Claude 路線：Claude Pro 以上，月繳約 US$20；Max 從 US$100 起。Codex 路線：使用 ChatGPT Pro，目前從 US$100／月起。ChatGPT Plus 雖可使用 Codex，仍低於本課 Pro 準備要求。兩家方案名稱不等價，不必兩邊都訂。
3. 價格核對於 2026-10-27，未含適用稅費，之後以官方結帳為準。AI GO 課程帳號由助教提供；方案、額度與 Hosted 權限依開通資料，不推定含第三方訂閱或額外服務費。
4. 助教會提供公司空間網址（租戶網址）、學員 email、專屬群組名稱及 id。不要叫學員自己猜 id，缺少時請助教補齊。
5. 用檔案總管／Finder 建 AI-GO-Learning，於協作工具選取本機資料夾，再開始第一則對話。

尚未安裝協作工具時，可先在 Claude／ChatGPT 網頁貼：
> 我沒有程式經驗，要用 Claude Code 或 Codex 參加 AI GO 課程。請先問我作業系統及選用工具，再用官方下載頁教我安裝、用自己的 Pro 帳號登入，並開啟 AI-GO-Learning 本機資料夾；一次只給下一步，不要求先裝 Python 或手寫設定檔。

## 第一則本機對話

> 我沒有程式經驗。請從 https://github.com/AI-GO-APP/aigo-learning-skill 讀取 README，下載最新穩定 release 的學習版安裝 ZIP，依 SHA256SUMS 與 PACKAGE.json 驗證。先回報目前完整工作區路徑，讓我核對。確認後，依目前工具安裝到本專案 .claude/skills/ 或 .agents/skills/；已有安裝先核對，不覆蓋作業。只安裝學習版，檢查一般版是否同時啟用，不擅改全域設定。完成後教我開新對話啟用 aigo-learning；不登入 AI GO、不建立或發布 App。

## AI 引導完成，不丟給學員手寫

- 先檢查作業系統與既有版本，再解釋並安裝缺少的免費工具：Python 3.10+、uv、Node.js LTS。只有需要的時候再補 Git、GitHub CLI、容器工具。不可直接覆寫既有版本、環境變數或全域設定。
- 安裝需系統權限或圖形介面時，給明確的按鈕與下一步，等學員完成；不假裝已裝好。尚無工具也能先做需求、流程與規格。
- 取得助教提供的非機密資料後，使用 `scripts/learning_bootstrap.py --workspace <工作區> --tenant-url <網址> --email <email> --role-id <id>` 建立結構與非機密設定。這支工具不登入、不建 App、不覆蓋既有設定。
- 學員只須在本機自己輸入帳密；AI 提供憑證檔絕對路徑與開啟方式，不讀出內容。填好後依已有授權核對登入身分。
- 提到程式、設定或錯誤碼時，先用白話說明。所有後續情景附可貼提示詞，明確寫出允許操作與停止邊界。

官方來源：
- https://claude.com/pricing
- https://code.claude.com/docs/en/quickstart
- https://learn.chatgpt.com/docs/pricing
- https://learn.chatgpt.com/docs/quickstart
