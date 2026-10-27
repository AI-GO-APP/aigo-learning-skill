# 學習版雙作品：內部 Custom App ＋ 對外 Hosted App

## 共同題目與順序

以一個服務店家的「介紹／申請預約 → 內部確認與跟進」為主例。學員可改成官網、詢價或報名。先選真實想做的小情境，不預設已有公司問題或接案。

1. 確認誰會使用、哪些頁面匿名可看、哪些資料只能內部看，寫需求、規格與驗收。
2. 內部 Custom App：先做處理清單，建立時手動選助教提供的專屬群組，立即回讀。
3. 對外 Hosted App：先做本機官網與表單，再接同一份已核對的申請資料來源。第一版是「申請型預約」，送出不等於名額已確認。
4. 匿名訪客看官網、送申請；內部人員查看與處理。需要客戶登入、查看歷史、付款或自動搶時段，另明確設計身分、授權、並行鎖與副作用，不能假裝基本版已包含。
5. 兩邊各驗收，再驗整條流程。客人的網址不能要求課程帳號或助教帳號登入。

## Hosted App 實作路徑

初次只討論產品線時讀 `technical/hosted-apps.md` §1；開始實作才按問題讀 §2（應用形態）、§3（部署）、§5–6（資料與可見度）。不要預讀整份容器／排程細節，也不要載入一般版入口。歷史平台實測不代表本次可用。

- 預先盤點租戶兩條產品線與可用權限。拿到 401／403 就核對並請助教補齊，不提高權限或換帳號。
- 須先有確認規格及本次建立 App 授權，才以自己的學員身分登記 Hosted App；可以用建立但不部署的方式先取得 id。核對 `id`、`slug`、`created_by`、`visibility`。slug 不猜，目標 id 不混用 Custom App id。
- 將本題 Hosted App 加到 `.aigo/config.json` 的 apps（`kind: hosted`），以及 `.aigo/learning.json` 的 hosted_apps。非機密設定由 AI 協助寫；學員不手編 JSON。範例見 operations.md。
- 每次 Hosted 平台寫入前用 `learning_scope.py --workspace <工作區> --app <別名> --kind hosted` 唯讀核對。公開階段要有明確公開內容與授權，設定 `public_approved: true`；工具不會自動把 private 改 public。
- 公開 Hosted App 的 `access_role_ids` 必須為空，不能硬掛學員群組後說客人可匿名進入。保護內部資料要靠伺服端授權與最小資料引用，不能以公開網站可見度代替。
- API 伺服器端才使用平台注入的環境變數與 `/open` 資料平面。瀏覽器不接收平台金鑰、Deploy Token、員工 token 或整張客戶表。
- 先從平台實際表與欄位建立引用。Hosted 用 `attached_integration_id` 加引用；不是 Hosted App id。沒有引用先處理，不繞過 403。公開表單只收確認欄位，驗證輸入、限制回傳、避免重送，匿名請求不可列出別人的資料。

## Hosted 發布與驗收

一個 App 一個 repo，學員自己登入 GitHub；預設先提 private，公開原始碼另經學員確認。AI 協助產生檔案與設定說明，學生不手寫 workflow。

1. 使用 `assets/hosted-deploy.example.yml` 與 `assets/hosted-ci.py` 建立自己 App 的部署流程；參數放 deploy.json，憑證由學員自行放該 repo 的 `AIGO_DEPLOY_TOKEN` Actions secret。不要把課程平台帳密放 GitHub。
2. 專案必有 Dockerfile、VERSION、明確打包清單；提供 `/health` 回傳 VERSION 與 tarball 內 `.aigo-build.json` 的本次 commit。預設不開常駐，需開啟時先確認理由、費用與退場條件。
3. 功能分支 → 本機建置／驗證 → PR → squash merge main → GitHub Actions 部署。路徑只含程式／部署設定；舊 run 若不是 main 最新就略過，避免舊版蓋新版。
4. 範本只部署到確認過的 App id，不註冊新 App，不改可見度、常駐、環境變數、資料引用或網域。這些由學員在本機授權後另處理。
5. 部署 active 後核對 `/health` commit、新網址主要路由、匿名訪客流程；再以虛構資料實測「送申請 → 內部收到 → 更新狀態」。相同請求不產生重複紀錄，匿名不可讀取其他申請或內部資料。
6. 依 technical/hosted-apps.md §3.4 核對本次其他適用閘門（包含 runtime-settings、資料持久化及必要環境變數）；範本 CI 通過只代表部署／版本檢查，不代表資料授權或業務功能已驗收。

提示詞：
> 我確認先做服務官網＋申請型預約，另有內部處理清單。請先寫兩個 App 的規格、公開／內部資料界線及共同驗收案例，再分小步帶我做；Hosted 先做本機原型，不部署。資料、權限或 API 尚未核對就標待確認，不切到一般版。
