# 版控、上游同步與發布

本 repo 為公開學生來源：技能、規則、提示詞、教學 PDF 及測試。不要放學生帳密、個人設定或真實客戶資料。
Builder 為獨立安裝的技術技能；UPSTREAM.json 宣告相容版本，不再匯入工具或技術摘錄。
兩個技能各自更新，學習版以 builder_runtime.py 檢查安裝路徑、相容性及 Builder 自己的更新器。

## 發版順序

1. 更新 VERSION。技能、PDF 及 release 都使用相同版本。教學規則、提示詞與教材來源在同一 commit 檢視。
2. `python tools/build_handbook.py --present-skill <本機 ai-go-app-present 路徑>` 以實際 AI GO B2B 母版建 PDF；渲染後逐頁目視，檢查字、提示詞、順序與規則是否完整。維護者本機需 Node／Chrome 及該工具相依；學生安裝不需私有 present 工具。文件來源會記錄實際頁數供打包核對。
3. `python tools/build_release.py --output <新的輸出資料夾>` 更新 PACKAGE.json，產生學生 ZIP、PDF、SHA256SUMS 與 RELEASE.json。
4. 以 AIGO_BUILDER_SKILL 指定相容 Builder，測試相依缺少／舊版拒絕、課程標記、舊工作區升級、範圍轉接、套件完整性、更新失敗復原、路徑安全、作業保留及 PDF；用最終 ZIP 解壓再驗證。
5. commit／push，確認公開內容沒有憑證或個人設定。GitHub main 的 PACKAGE 必須與來源一致，否則更新器會中止。
6. commit 後再次建置到新的輸出目錄，使 RELEASE.json 記錄該 commit；確認工作樹無變更、CI 通過後，在該 commit 建 `v<版本>` tag 及 GitHub release，附上四種產物。不要使用 GitHub 自動產生的原始碼 ZIP 當學生安裝包。
7. 從 GitHub 重新下載驗證 SHA-256，核對 release 指向同一 commit。public release 不需要學生取得 Builder repo 權限。

公開資產檔名固定使用 ASCII（含 PDF），避免 GitHub 改寫中文名稱後與校驗清單不一致；PDF 內文維持繁體中文。

## 更新機制

學生進入實作前會呼叫 check_update，網路檢查間隔 3 小時；純概念問答或明確禁止本機變更時留到實作前。檢查自己的 GitHub main commit；
即使 VERSION 未變，只要 commit 有更動，也會核對 manifest 後更新技能檔案。維護者仍應遵守版本遞增。
先下載並驗證完整套件，再替換列入 manifest 的技能檔案，失敗復原。舊版列入 manifest 的技術副本會退出，技術改由已安裝 Builder 提供；未知額外檔案與工作區不刪除。
若技能目錄誤放 .aigo 或 .env，更新中止並說明原因。main 有未提交變更或在功能分支的開發副本略過。
檢查節流狀態在 ~/.aigo-learning/，不與 Builder 的 ~/.aigo/update_check.json 共用。
第一次啟用時才開始檢查；未使用技能時不會背景啟動。不建立電腦排程或修改全域 hook。
