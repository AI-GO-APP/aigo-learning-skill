# AI GO 學生學習版：Builder 的教學引導層

本 repo 是 **aigo-learning**，必須搭配 [aigo-builder](https://github.com/AI-GO-APP/aigo-app-builder-skill) 使用。
Builder 管技術、使用、串接與開發部署；學生學習版加白話說明、小練習、提示與理解驗收。無須安裝 aigo-client-collab。

## 學員第一則對話

先準備能操作本機資料夾的 Claude Code 或 Codex，並開啟自己的 AI-GO-Learning 資料夾。課程要求 Claude Pro 以上，或 Codex 搭配 ChatGPT Plus 以上；二選一。

> 請幫我準備 AI GO 學生學習版：https://github.com/AI-GO-APP/aigo-learning-skill 。我沒有程式經驗，請一步一步帶我，需要我做的事講清楚。

## AI 安裝時的做法

1. 先回報完整工作區等學員核對，檢查協作工具及 Python／uv／Node；缺少時一次引導下一步，不要求手寫設定檔。
2. 檢查專案與使用者層級的兩個 skill。已有可用 Builder 就沿用並核對路徑；沒有才依 Builder README 安裝。本學生學習版要求 Builder 1.74.0 以上、2.0.0 以下。不要拿學生學習版 0.3.x 的舊工具代替。
3. 預設專案安裝，不擅改全域設定。Builder repo 是公開的，來源為 AI-GO-APP/aigo-app-builder-skill；依選用工具安裝到有效技能位置。用 skills CLI 時不帶 -g，例：`npx skills add AI-GO-APP/aigo-app-builder-skill -y -a claude-code`，Codex 將 agent 換成 `codex`。已有安裝先核對，工具缺少時先說明如何補齊。
4. 學生學習版從最新穩定 release 下載 `aigo-learning-<版本>.zip`、SHA256SUMS；驗證 ZIP／PDF 雜湊及解壓後 PACKAGE 清單。Claude Code 放 `.claude/skills/aigo-learning/`，Codex 放 `.agents/skills/aigo-learning/`；不要再多包一層目錄。此包不含 Builder 技術副本。
5. 用 `python <學生學習版>/scripts/builder_runtime.py --workspace <工作區>` 核對 Builder 路徑與版本。用 `learning_bootstrap.py --workspace <工作區> --prepare-only` 建立或更新受管理的課程區塊及 CLAUDE.md 引用；保留區塊外原內容，舊工作區也適用。
6. 開新對話：直接描述目標；本資料夾固定使用學生學習版並搭配 Builder，不必每次輸入技能指令。依手冊取得助教提供的空間、email、群組名稱及 id，再建立非機密設定與登入。安裝本身不授權登入／建立／發布 App。

## 從 0.3.x 升級

先補齊 Builder 相依，再由 AI 執行 `learning_bootstrap.py --workspace <工作區> --upgrade-workspace`。它更新非機密的協作路徑與工作區引導，保留 App 分配、作業與憑證；不重新建立 App、不讀取帳密。
技能更新會移除套件清單中的舊技術副本；工作區始終放在技能安裝目錄外。未核對相容版本前仍可討論，不操作平台。

## 分工與範圍

技術與平台事實照 Builder 及實際證據；教學呈現照學生學習版。課程指定的帳號、App、群組、資料與已有授權，兩個技能共同遵守。
內部 App 建立時手動選自己的群組，立即回讀。使用虛構資料；App 與資料權限分別核對。預檢協助確認本題的帳號、App 與群組。
功能驗證、AI 協助程度與理解證據分開記錄。一般客戶專案可使用普通版 Builder，不需要套用課程節奏。

## 更新與維護

兩個 skill 分別從自己的 repo 更新，各有節流。進入實作前檢查學生學習版，再由 builder_runtime.py --update 檢查 Builder 並核對相容性；純觀念先回答，不假裝已檢查。未使用時沒有背景排程，不自動安裝全域 hooks。
UPSTREAM.json 宣告已安裝 Builder 的相依範圍，不是固定複製來源。平台工具與 Hosted CI 範本只在 Builder 維護。
學員教材來源在 docs/handbook.json，PDF 在 assets/student-handbook.pdf；維護者以本機 ai-go-app-present 的實際 AI GO 母版輸出。助教文件獨立保存在課程工作區，不進 repo。
發版與測試見 docs/RELEASING.md。測試以 AIGO_BUILDER_SKILL 指定相容 Builder source/install，不登入正式租戶。

## 想做什麼，直接問

> AI GO 能幫我做什麼？我想做【自己的情境】，給【誰】使用，請先給我兩三個能開始的小題。

小幫手會按 references/capabilities.md 導覽功能、查實際範本與帳號可用範圍；系統故障只走 Builder 平台問題回報。
