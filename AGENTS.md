# 維護範圍

這是公開的 AI GO 學生技能來源與發行 repo。學生規則、教材、提示詞在本 repo 維護。
Builder 只作固定 commit 的技術來源，見 UPSTREAM.json；不可載入 Builder 的 SKILL.md。
學生與客戶資料、帳密、token、內部測試對話與本機設定不能提交。

版本變更：更新 VERSION、教材來源與規則；建置 PDF、產生 PACKAGE.json、測試，再 commit。
release 的 tag、ZIP、PDF、SHA256SUMS 必須來自同一 commit。發版前重建並比對 hash。
學生更新器只認 AI-GO-APP/aigo-learning-skill，不能改動 Builder 安裝或工作區。
測試使用假的 token 與虛構資料，不登入／修改正式租戶。不要把 compile、HTTP 200 或草稿當成完整驗收。
