# 🎨 Flex Message UI 測試指南

本指南將教您如何在本地測試和預覽籃球分隊機器人的 Flex Message UI 設計。

## 🚀 方法 1：LINE Flex Message Simulator（推薦）

### 步驟 1：生成測試 JSON

```bash
# 運行測試腳本
python test_flex_messages.py

# 選擇要測試的訊息類型 (1-8)
# 推薦選擇 7 或 8 來生成所有測試檔案
```

### 步驟 2：使用 LINE 官方模擬器

1. **前往 LINE Flex Message Simulator**：
   👉 https://developers.line.biz/flex-simulator/

2. **貼上 JSON 內容**：
   - 複製 `test_flex_messages.py` 輸出的 JSON
   - 或使用 `flex_message_tests/` 目錄中的 JSON 檔案
   - 貼到模擬器的左側編輯器

3. **即時預覽**：
   - 右側會顯示真實的 LINE 聊天介面效果
   - 可以測試不同螢幕尺寸的顯示效果
   - 支援深色/淺色主題切換

## 📱 測試內容說明

### 可測試的 Flex Message 類型：

| 訊息類型 | 檔案名 | 說明 |
|---------|--------|------|
| 歡迎訊息 | `welcome.json` | 初次使用時的歡迎界面 |
| 註冊成功 | `register_success.json` | 球員註冊完成後的確認訊息 |
| 球員列表 | `player_list.json` | 顯示所有已註冊球員的卡片式列表 |
| 空球員列表 | `empty_player_list.json` | 沒有球員時的提示訊息 |
| 分隊結果 | `team_result.json` | 自動分隊後的結果展示 |
| 個人資料 | `profile.json` | 個別球員的詳細資料頁面 |

### UI 設計特色：

✨ **籃球主題配色**：
- 主要色：橘色 (#FF6B35) - 籃球色彩
- 輔助色：藍色 (#4A90E2) - 專業感
- 成功色：綠色 (#28A745) - 正面回饋

🎯 **互動元素**：
- PostbackAction 按鈕：直接觸發功能
- 技能進度條：視覺化技能評分
- 卡片式佈局：清晰的資訊層次

📊 **資料視覺化**：
- 技能條：█████░░░░░ (填滿/空白)
- 統計圖表：投籃🎯/防守🛡️/體力💪
- 平衡度評分：⚖️ X.X/10

## 🔧 方法 2：本地快速測試

### 快速生成特定訊息：

```python
# 在 Python 中快速測試
from test_flex_messages import FlexMessageTester

tester = FlexMessageTester()

# 測試歡迎訊息
tester.test_welcome_message()

# 測試註冊成功
tester.test_register_success_message()

# 測試球員列表  
tester.test_player_list_message()
```

### 自訂測試資料：

```python
from models import Player

# 創建自訂球員進行測試
custom_player = Player("test", "您的名字", 9, 8, 7)
tester = FlexMessageTester()
profile_flex = tester.handler._create_profile_flex(custom_player)
print(tester.flex_to_json(profile_flex))
```

## 🌐 方法 3：ngrok 真實環境測試

### 步驟 1：安裝 ngrok

```bash
# macOS
brew install ngrok

# 或直接下載：https://ngrok.com/download
```

### 步驟 2：啟動本地服務器

```bash
# 終端 1：啟動 Flask 應用
python app.py

# 終端 2：創建公開隧道
ngrok http 5000
```

### 步驟 3：設定 LINE Bot Webhook

1. 複製 ngrok 提供的公開 URL（如：`https://abc123.ngrok.io`）
2. 前往 LINE Developers Console
3. 設定 Webhook URL：`https://abc123.ngrok.io/callback`
4. 啟用 Webhook

### 步驟 4：真實測試

- 在 LINE 中與機器人對話
- 發送 `開始` 測試歡迎訊息
- 測試註冊：`/register 測試 8 7 9`
- 測試分隊：`/team 2`

## 🎨 UI 調整技巧

### 1. 顏色調整

在 `line_handler.py` 中修改顏色常數：

```python
# 主題色彩
PRIMARY_COLOR = "#FF6B35"    # 橘色
SECONDARY_COLOR = "#4A90E2"  # 藍色
SUCCESS_COLOR = "#28A745"    # 綠色
```

### 2. 佈局調整

修改 Flex Message 組件：

```python
# 調整間距
SpacerComponent(size="md")  # xs, sm, md, lg, xl

# 調整文字大小
TextComponent(size="lg")    # xs, sm, md, lg, xl

# 調整按鈕樣式
ButtonComponent(style="primary")  # primary, secondary, link
```

### 3. 技能條樣式

在 `_create_skill_bar` 方法中調整：

```python
# 不同的進度條樣式
skill_bar = "█" * filled_bars + "░" * empty_bars  # 方塊樣式
skill_bar = "●" * filled_bars + "○" * empty_bars  # 圓點樣式  
skill_bar = "▰" * filled_bars + "▱" * empty_bars  # 線條樣式
```

## ❗ 常見問題

### Q: JSON 格式錯誤
**A:** 確認 `line-bot-sdk` 版本正確，使用 `pip install line-bot-sdk==3.8.0`

### Q: 模擬器顯示異常
**A:** 檢查 JSON 是否有語法錯誤，使用 `json.loads()` 驗證

### Q: 真實測試環境變數錯誤
**A:** 確認 `.env` 檔案設定正確，或在 Render 設定環境變數

### Q: ngrok 連線問題
**A:** 確認防火牆設定，並檢查 ngrok 帳號認證

## 🔄 開發流程建議

1. **設計階段**：使用 Flex Message Simulator 快速原型設計
2. **開發階段**：使用測試腳本生成 JSON 驗證功能
3. **測試階段**：使用 ngrok 在真實環境中測試
4. **部署階段**：部署到 Render 進行最終驗證

---

💡 **小技巧**：將常用的 JSON 保存為範本，方便快速修改和測試新的 UI 設計！