# 🌐 ngrok 真實環境測試設定指南

使用 ngrok 可以讓您在本地開發環境中測試真實的 LINE Bot 互動效果。

## 🚀 安裝 ngrok

### macOS (推薦使用 Homebrew)
```bash
brew install ngrok
```

### 其他方式
1. **直接下載**：前往 https://ngrok.com/download
2. **解壓縮並安裝**：
   ```bash
   unzip ngrok-stable-darwin.zip
   sudo mv ngrok /usr/local/bin/
   ```

## 🔑 ngrok 認證設定

1. **註冊 ngrok 帳號**：https://dashboard.ngrok.com/signup
2. **獲取認證 Token**：https://dashboard.ngrok.com/get-started/your-authtoken
3. **設定認證**：
   ```bash
   ngrok authtoken YOUR_AUTHTOKEN_HERE
   ```

## 🏃‍♂️ 啟動本地測試環境

### 步驟 1：準備環境變數
創建 `.env` 檔案並設定 LINE Bot 資訊：
```bash
# 複製範本
cp .env.example .env

# 編輯環境變數
nano .env
```

在 `.env` 中填入：
```env
LINE_CHANNEL_ACCESS_TOKEN=your_line_channel_access_token
LINE_CHANNEL_SECRET=your_line_channel_secret
SECRET_KEY=your_secret_key_for_local_testing
FLASK_ENV=development
FLASK_DEBUG=true
```

### 步驟 2：安裝依賴並啟動應用
```bash
# 安裝依賴
pip install -r requirements.txt

# 啟動 Flask 應用（終端 1）
python app.py
```

預期輸出：
```
 * Running on http://0.0.0.0:5000
 * Debug mode: on
```

### 步驟 3：創建 ngrok 隧道
開啟新的終端視窗：
```bash
# 創建 HTTP 隧道（終端 2）
ngrok http 5000
```

您會看到類似的輸出：
```
Session Status                online
Account                      your_email@example.com
Version                      3.x.x
Region                       Asia Pacific (ap)
Latency                      45.123456ms
Web Interface                http://127.0.0.1:4040
Forwarding                   https://abc123def.ngrok.io -> http://localhost:5000
Forwarding                   http://abc123def.ngrok.io -> http://localhost:5000
```

**重要**：複製 `https://abc123def.ngrok.io` URL（每次啟動都會不同）

## 🔗 設定 LINE Bot Webhook

### 步驟 1：前往 LINE Developers Console
1. 登入：https://developers.line.biz/console/
2. 選擇您的 Provider 和 Channel

### 步驟 2：設定 Webhook URL
1. 前往 "Messaging API" 標籤
2. 在 "Webhook URL" 欄位填入：
   ```
   https://abc123def.ngrok.io/callback
   ```
   （將 `abc123def` 替換為您的實際 ngrok URL）

3. 點擊 "Verify" 驗證連線
4. 確保 "Use webhook" 是啟用狀態

### 步驟 3：測試連線
在 LINE 中與您的機器人對話：
- 發送：`開始`
- 應該收到歡迎 Flex Message

## 🔍 偵錯和監控

### ngrok Web Interface
在瀏覽器中開啟：`http://localhost:4040`
- 查看所有請求和回應
- 監控 webhook 呼叫
- 檢查錯誤訊息

### Flask Debug 模式
Flask 會在終端顯示：
- 收到的 webhook 請求
- 處理的訊息內容
- 任何錯誤訊息

### 常用偵錯指令
```bash
# 檢查 Flask 應用是否運行
curl http://localhost:5000/

# 檢查健康狀態
curl http://localhost:5000/health

# 測試 ngrok 隧道
curl https://your-ngrok-url.ngrok.io/health
```

## 🧪 測試流程

### 1. 基本功能測試
```
用戶輸入 → LINE → ngrok → 本地 Flask → 處理 → 回覆 → LINE → 用戶
```

### 2. 測試案例
- **歡迎訊息**：發送 `開始`
- **球員註冊**：`/register 測試球員 8 7 9`
- **查看列表**：`/list`
- **分隊功能**：`/team 2`
- **個人資料**：`/profile`

### 3. Flex Message 測試
1. 發送指令觸發 Flex Message
2. 檢查是否正確顯示
3. 測試按鈕互動（PostbackAction）
4. 驗證響應式設計

## ⚡ 進階技巧

### 自訂 ngrok 子域名（付費功能）
```bash
ngrok http 5000 --subdomain=basketball-bot
# 固定 URL: https://basketball-bot.ngrok.io
```

### 設定 ngrok 配置檔案
創建 `~/.ngrok2/ngrok.yml`：
```yaml
version: "2"
authtoken: YOUR_AUTHTOKEN
tunnels:
  basketball-bot:
    proto: http
    addr: 5000
    subdomain: basketball-bot
    bind_tls: true
```

使用配置檔案：
```bash
ngrok start basketball-bot
```

### 多個隧道同時運行
```bash
# HTTP 隧道
ngrok http 5000 --region=ap

# HTTPS 專用隧道
ngrok http 5000 --bind-tls=true
```

## 🚨 故障排除

### 常見問題和解決方案

#### 1. 連線被拒絕
```
Error: dial tcp 127.0.0.1:5000: connect: connection refused
```
**解決**：確認 Flask 應用正在運行

#### 2. Webhook 驗證失敗
```
400 Bad Request
```
**解決**：檢查 LINE Bot Channel Secret 設定是否正確

#### 3. ngrok 帳號限制
```
ERROR: failed to start tunnel
```
**解決**：免費帳號有並發隧道限制，關閉其他 ngrok 程序

#### 4. 環境變數問題
```
TypeError: can only concatenate str (not "NoneType") to str
```
**解決**：檢查 `.env` 檔案是否正確設定

### 偵錯檢查清單
- [ ] Flask 應用正在運行（port 5000）
- [ ] ngrok 隧道已建立
- [ ] LINE Webhook URL 正確設定
- [ ] 環境變數已正確載入
- [ ] 防火牆未阻擋連線

## 📊 效能監控

### ngrok 流量分析
- 在 `http://localhost:4040` 查看：
  - 請求延遲
  - 成功/失敗率
  - 流量統計

### Flask 效能監控
```bash
# 安裝監控工具
pip install flask-profiler

# 在 app.py 中添加
from flask_profiler import Profiler
profiler = Profiler()
profiler.init_app(app)
```

## 🔒 安全注意事項

1. **不要**在生產環境使用 ngrok
2. **不要**將 ngrok URL 分享給他人
3. **記得**在測試完成後關閉隧道
4. **定期**更換測試用的 Token 和 Secret

---

💡 **小技巧**：使用 tmux 或 screen 來管理多個終端會話，方便同時監控 Flask 和 ngrok！