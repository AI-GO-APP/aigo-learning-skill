# 從零開始：先準備工具，再固定作業資料夾

## 學生只需準備

- 二選一：Claude Code 搭配 Claude Pro 以上，或 Codex 搭配 ChatGPT Plus 以上。月繳參考價皆約 US$20 起；未含稅、以官方結帳為準。這是課程選擇，不把 ChatGPT Pro 當門檻；兩家不用都訂。訂閱有使用量限制，API 另計費。
- 一張開通卡：登入網址、email、專屬群組名稱及編號。先讀既有設定，不要求學生重找已給資料。系統故障沿用 Builder 平台問題回報，不設第二管道。
- 一個電腦上的 AI-GO-Learning 資料夾。所有後續對話在此開啟；不需要反覆講模式，也不要求手寫 JSON。

還沒安裝協作工具，可先在 Claude／ChatGPT 網頁問：
> 我沒有程式經驗，要用【Claude Code／Codex】做作品。我的電腦是【Windows／Mac】。請教我從哪裡下載、怎麼登入，並開啟 AI-GO-Learning 資料夾。

本機第一則對話：
> 請幫我準備 AI GO 學生學習版：https://github.com/AI-GO-APP/aigo-learning-skill 。我沒有程式經驗，請一步一步帶我，需要我做的事講清楚。

## AI 必須自行處理的安裝規則

按 README 的安裝契約：先核對完整路徑及既有安裝；準備兩個 skill、驗證 release 與相容版本、保留原檔、不改全域設定；以 --prepare-only 建立／更新本專案 AGENTS.md 與 CLAUDE.md 引用。安裝不授權登入、建 App 或發布。
Python 3.10+、uv、Node.js LTS 缺少時由 AI 查官方步驟並分步引導；需要系統權限、購買、帳號登入或金鑰時由學生自行完成。不覆蓋原環境或把訂閱切成 API 計費。

已有標記的舊工作區也用 --prepare-only 更新受管理區塊，保留區塊外原規則。已有 .aigo/learning.json 時才用 --upgrade-workspace 更新非機密協作資料，保留原 App 分配與憑證；不重建作品。

## 開通與登入

取得開通卡後，用 learning_bootstrap.py 的 --tenant-url、--email、--role-id 建立非機密設定；先核對工作區，已有設定不覆寫。群組名稱可作辨識，id 依開通卡，不由 AI 猜。
登入採 Builder 官方流程；密碼／金鑰由學生自行輸入，不讀出、不印出、不進 repo。登入與作品操作分開，沿用本次授權。
遇到工具或功能問題先由 AI 查 capabilities.md、檔案與目前身分；開通資料缺漏請原開通人員補齊；系統故障由 Builder 平台問題回報，不另找渠道。

官方來源（2026-10-28 核對）：
- https://claude.com/pricing
- https://code.claude.com/docs/en/quickstart
- https://help.openai.com/en/articles/6950777-what-is-chatgpt-plus
- https://chatgpt.com/codex/pricing/
- https://learn.chatgpt.com/docs/quickstart
