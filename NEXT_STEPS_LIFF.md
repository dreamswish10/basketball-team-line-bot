# LIFF 群組檢視功能 — 還沒做完的事

新增的 `/view` 指令會回一個 LIFF 連結，點進去可以看本群的分隊紀錄與統計。
程式碼骨架已寫完，但還沒實際跑過。回辦公室後接著做：

## 1. LINE 後台設定（必做，否則整個功能不會動）

- [ ] 到 LINE Developers Console，**同一個 Provider** 下新建 channel：
      Create a new channel → **LINE Login**
      （⚠️ 2024 起 LIFF 不能再加在 Messaging API channel 上）
- [ ] 進到那支 LINE Login channel → LIFF 分頁 → Add LIFF app：
  - Endpoint URL: `https://<部署網域>/view`
  - Size: **Full**（或 Tall）
  - Scope: 至少勾 **openid**（要拿 id_token）+ profile
  - Bot link feature: 視需求
- [ ] 抄下兩個值：
  - LIFF app 的 **LIFF ID**（形如 `2001234567-aBcDeFgH`）→ 填 `LIFF_ID`
  - LINE Login channel 的 **Channel ID**（純數字，Basic settings 頁）→ 填 `LIFF_CHANNEL_ID`

## 2. 環境變數

- [ ] 本地 `.env` 補上：
  ```
  LIFF_ID=2001234567-aBcDeFgH
  LIFF_CHANNEL_ID=2001234567
  PUBLIC_BASE_URL=https://<部署網域>
  ```
- [ ] 部署環境（Render/其他）的 dashboard 也補上同樣三個變數

## 3. 實機測試

- [ ] 部署後在群組裡打 `/view`，確認有收到 LIFF 連結
- [ ] 點連結（要在 LINE 內開），看 `view.html` 是否正常載入
- [ ] 確認四個頁籤都有資料：摘要 / 歷史分隊 / 球員統計 / 隊友共現
- [ ] 邊界情境：
  - [ ] 把帳號踢出群組後再點連結 → 應該 403「不是本群成員」
  - [ ] 換另一個群組 → 資料應該不同
  - [ ] 新建沒紀錄的群組 → 不應該炸，應顯示空狀態

## 4. 已知 / 待議的小事

- [ ] `attendances` collection 沒有 `group_id` 欄位，目前是用「成員交集」過濾
      （`src/services/stats_service.py:18-22` 有註解說明）。
      跨群打球的玩家會讓兩邊都看到同一場 — 之後若要乾淨切分，得在
      `attendances` 寫入時補 `group_id`，並回填歷史資料。
- [ ] `get_group_user_ids` 在單一 request 內被叫 4 次（summary/divisions/players/pairs 各一次）
      → 可在 `api_group_data` 算一次傳下去，省 DB query
- [ ] 歷史分隊目前硬切 20 場，沒有「載入更多」
- [ ] `app.py` 那個 `static_folder='static'` 指向不存在的 `src/static/`，
      目前 view.html 沒用到 static 檔（CSS/JS 都 inline + CDN），可留可拆
- [ ] `view.html` 的 fetch 沒有 timeout / retry，網路爛時會卡在 loading
- [ ] 沒有寫單元測試（`stats_service.py` 的四個聚合函式很適合補 test）

## 5. 完成後

- [ ] 刪掉這支 `NEXT_STEPS_LIFF.md`
- [ ] 開 PR 合回 main
