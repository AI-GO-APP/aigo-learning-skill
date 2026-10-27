# 雙 skill 操作與範圍核對

1. 學習版更新自己的 repo；builder_runtime.py --workspace <工作區> --update 檢查已安裝 Builder 的更新及版本。
2. 讀 Builder 入口，技術指令都使用已核對的 Builder 完整路徑。操作 cwd 是學員工作區，不是技能安裝目錄。
3. 安裝後 learning_bootstrap.py --workspace <工作區> --prepare-only 保留原內容並加入課程 AGENTS.md／CLAUDE.md 引用。
4. 助教提供租戶網址、email、群組名稱與 id 後，以 learning_bootstrap.py 建非機密設定；舊工作區用 --upgrade-workspace，不重建 App 或憑證。
5. 登入照 Builder 支援的方法，優先向新手說明瀏覽器登入；帳密檔也由學員自己填。AI 不讀出憑證、不代填、不放 repo。
6. 內部 App 在建立介面手動選助教群組，立即回讀；未確認前不匯入、同步、編譯或發布。再用 Builder 登錄實際 id、slug、kind 與明確別名。

每次寫入前：
`python <學習版>/scripts/learning_scope.py --workspace <工作區> --app <別名> [--kind hosted]`

這個薄轉接會在獨立的 Builder 執行環境呼叫 scripts/aigo_learning_scope.py，不混用 Python 內已匯入的舊同名工具。
它核對有效空間、學員身分、App 分配、產品線與可見度；Custom 為專屬群組，Hosted 為建立者／slug／公開授權。
Builder 的 Custom 同步、刪檔、編譯、發布在課程標記生效時還會各自核對；full_deploy 沿用同一課程上下文。
其他資料寫入、外部服務、Hosted 與平台 UI 仍按本次範圍及 Builder 適用閘門處理，不能宣稱 guard 已攔截所有 API 或形成沙箱。

平台授權與逐筆資料界線仍由伺服端保障，App 群組設定不等於資料隔離。使用虛構資料，不讀其他學生內容作示範。
修改前讀回 App 現況與版本；Custom 與 Hosted 的同步、部署、正式網址驗證各照 Builder。不是 HTTP 200 或 CI 綠燈就宣告完成。
發布及有副作用測試必須有涵蓋本次範圍的授權；結果未知先查證，不盲目重送。

Hosted 的非機密設定由 AI 依 Builder 協助，學員不手寫 JSON。profile 的 hosted_apps 包含本題真實 id、slug、visibility、public_approved；
公開授權只有學員確認後設 true。公開網站不掛內部群組；資料引用、伺服端欄位與匿名回傳範圍另驗收。
Hosted CI 範本讀 Builder 的 resources/hosted-ci.py 與 resources/hosted-deploy.example.yml，複製到自己的 App repo 後依規格設定。
