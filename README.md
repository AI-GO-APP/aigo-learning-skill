# AI GO 學員學習技能

從工具與工作區設定、需求描述、規格確認，到小步實作、功能驗收與 PDF 成果輸出。

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
python tools/build_handbook.py
python tools/build_release.py --output <全新的輸出目錄>
python -m unittest discover -s tests -v
```

PDF 相依：`scripts/requirements-pdf.txt`。逐頁目視確認屬發版工作，不能以渲染成功代替。
詳細發版步驟見 docs/RELEASING.md。
