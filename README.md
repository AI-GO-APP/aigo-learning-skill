# AI GO 學習版技能

從零基礎起手、工具與設定協作，到內部 Custom App＋對外 Hosted App、整合驗收及 PDF 成果。
一般開發技能統一稱「一般版」，提供學員的技能稱「學習版」。

## 課前與第一則對話

準備 Claude Pro 以上，或 Codex 搭配 ChatGPT Pro；兩家不用都訂。
助教會提供公司空間網址、學員 email、專屬群組名稱與 id。
在協作工具開啟本機練習資料夾，貼：

> 我沒有程式經驗。請從 https://github.com/AI-GO-APP/aigo-learning-skill 讀 README，下載最新穩定 release 的學習版 ZIP，驗證 SHA256SUMS 與 PACKAGE.json。先回報工作區完整路徑等我確認，再依目前工具安裝到本專案；只裝學習版、檢查一般版混用，不覆蓋作業或全域設定。完成後教我開新對話啟用；不登入 AI GO、不建 App。

Python、uv、Node.js 的檢查與安裝及非機密設定由 AI 引導，不要求新手手寫 JSON。
完整準備、官方價格來源及提示詞見 references/onboarding.md；每種情景與 FAQ 見 PDF。

## 下載與安裝

從 [Releases](https://github.com/AI-GO-APP/aigo-learning-skill/releases) 下載同版本的學生 ZIP 與 PDF。
使用 release 的學生安裝包，不要把 GitHub 自動產生的 Source code ZIP 當成學生安裝包。

將整個 `aigo-learning/` 解壓至自己的練習專案：

| 工具 | 專案內位置 | 新對話啟用 |
|---|---|---|
| Claude Code | `.claude/skills/aigo-learning/` | `/aigo-learning` |
| Codex | `.agents/skills/aigo-learning/` | `$aigo-learning` |

請確認該目錄內直接有 SKILL.md、VERSION、PACKAGE.json，不要多套一層資料夾。
先檢查是否另有一般版 aigo-builder 同時啟用，再依 PDF 的步驟完成工作區與帳號設定。

## 更新

每次啟用時執行 `scripts/check_update.py`。網路檢查每個安裝最多每 3 小時一次，
發現 GitHub main 有新版就更新該學生技能安裝，完成後重新讀入口與必要參考。
這不是背景排程，未使用技能時不會定時啟動。工作區與作業必須在技能目錄外。
`--status` 僅顯示本機完整性與版本；網路失敗保留目前版本並如實回報，不清除作業。
功能分支或有未提交變更的 Git 開發副本略過自動更新；學生 ZIP 安裝照常更新。

## 維護與來源

`UPSTREAM.json` 固定 Builder commit、版本與來源雜湊。技術工具及摘錄經教師複核後匯入，
不直接跟著 Builder main 更換教學行為。學生只跟本 repo 的已提交版本更新。

```text
python tools/build_handbook.py --present-skill <本機_ai-go-app-present_路徑>
python tools/build_release.py --output <全新的輸出目錄>
python -m unittest discover -s tests -v
```

維護者出手冊使用本機 ai-go-app-present 的 AI GO B2B 母版（非泛用 Presentations 版型）；學生安裝不需這個私有製作工具。
學員成果產生器的 PDF 相依：`scripts/requirements-pdf.txt`。逐頁目視確認屬發版工作，不能以渲染成功代替。
詳細發版步驟見 docs/RELEASING.md。
