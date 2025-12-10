# 🏀 籃球分隊 LINE Bot

一個智能的籃球分隊系統，使用 LINE Bot 作為介面，能根據球員技能自動分配平衡的隊伍。

## ✨ 功能特色

- **球員管理**：註冊、查詢、修改球員資料
- **技能評估**：設定投籃、防守、體力等技能等級（1-10）
- **智能分隊**：基於技能平衡的自動分隊演算法
- **多種分隊模式**：支援 2-10 隊的分組
- **LINE Bot 整合**：友善的聊天介面操作

## 🛠️ 技術架構

- **後端**：Python 3.8+ + Flask
- **資料庫**：SQLite（可擴展為其他資料庫）
- **聊天介面**：LINE Bot API
- **部署**：支援 Heroku、Railway 等平台

## 📱 LINE Bot 指令

### 基本指令
- `/register 姓名 投籃 防守 體力` - 註冊球員（技能值 1-10）
- `/list` - 查看所有球員列表
- `/team [隊數]` - 開始自動分隊（預設 2 隊）
- `/profile` - 查看個人資料
- `/delete` - 刪除個人資料
- `/help` - 查看使用說明

### 使用範例
```
/register 小明 8 7 9
/team 3
分隊 2
球員列表
```

## 🚀 快速開始

### 1. 環境需求
- Python 3.8+
- LINE Developers 帳號

### 2. 安裝依賴
```bash
pip install -r requirements.txt
```

### 3. 設定環境變數
複製 `.env.example` 為 `.env` 並填入 LINE Bot 資訊：
```bash
cp .env.example .env
```

編輯 `.env` 檔案：
```env
LINE_CHANNEL_ACCESS_TOKEN=your_channel_access_token
LINE_CHANNEL_SECRET=your_channel_secret
SECRET_KEY=your-secret-key
```

### 4. 運行應用程式
```bash
python app.py
```

### 5. 設定 LINE Bot Webhook
在 LINE Developers Console 設定 Webhook URL：
```
https://your-domain.com/callback
```

## 🔧 LINE Bot 設定步驟

### 1. 建立 LINE Bot
1. 前往 [LINE Developers Console](https://developers.line.biz/)
2. 登入並建立新的 Provider
3. 建立新的 Channel（Messaging API）
4. 取得 Channel Access Token 和 Channel Secret

### 2. 設定 Webhook
1. 在 Channel 設定中啟用 Webhook
2. 設定 Webhook URL：`https://your-domain.com/callback`
3. 驗證 Webhook 連線

### 3. 測試機器人
1. 使用 QR Code 或 Bot ID 加入好友
2. 發送 `開始` 或 `/help` 測試功能

## 📊 分隊演算法

系統使用**技能平衡演算法**：

1. **技能評分**：根據投籃、防守、體力計算綜合評分
2. **平衡分配**：使用貪心演算法確保隊伍間實力平衡
3. **隨機因子**：加入 20% 隨機性避免固定分組
4. **公平性**：最小化隊伍間評分差異

## 🚀 部署

### Heroku 部署
```bash
# 1. 安裝 Heroku CLI
# 2. 登入 Heroku
heroku login

# 3. 建立應用程式
heroku create your-app-name

# 4. 設定環境變數
heroku config:set LINE_CHANNEL_ACCESS_TOKEN=your_token
heroku config:set LINE_CHANNEL_SECRET=your_secret
heroku config:set SECRET_KEY=your_secret_key

# 5. 部署
git push heroku main
```

### Railway 部署
1. 連結 GitHub repository
2. 設定環境變數
3. 自動部署

### 其他平台
支援任何支援 Python + Flask 的平台，確保：
- 安裝 requirements.txt 中的依賴
- 設定正確的環境變數
- 開放對應的 Port

## 📁 專案結構

```
basketball-team-generator/
├── app.py              # Flask 主應用程式
├── models.py           # 資料模型和資料庫操作
├── team_algorithm.py   # 分隊演算法
├── line_handler.py     # LINE Bot 訊息處理
├── config.py           # 應用程式設定
├── requirements.txt    # Python 依賴套件
├── .env.example        # 環境變數範本
├── Procfile           # Heroku 部署設定
└── README.md          # 專案說明
```

## 🛡️ 安全性

- 使用環境變數存儲敏感資訊
- 驗證 LINE Bot Webhook 簽名
- 輸入驗證和清理
- SQL 注入防護

## 🤝 貢獻

歡迎提交 Issue 和 Pull Request！

## 📄 授權

MIT License

## 📞 聯絡

如有問題或建議，請建立 Issue 或聯絡開發者。

---

⭐ 如果這個專案對您有幫助，請給它一個星星！