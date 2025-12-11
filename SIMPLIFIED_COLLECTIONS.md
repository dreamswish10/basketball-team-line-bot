# 簡化的 MongoDB Collections 結構

本文檔說明新增的兩個簡化 MongoDB Collections 及其使用方法。

## 新增的 Collections

### 1. attendances 出席記錄
用於管理每日出席和分隊情況。

#### 結構範例
```json
{
  "_id": ObjectId("..."),
  "date": "2025-12-10",
  "teams": [
    {
      "teamId": "A",
      "members": [
        { "userId": "U123", "name": "Jed" },
        { "userId": "U234", "name": "Alice" }
      ]
    },
    {
      "teamId": "B", 
      "members": [
        { "userId": "U345", "name": "Bob" }
      ]
    }
  ],
  "updated_at": ISODate("...")
}
```

#### 限制規則
- 每隊最多 3 個成員
- 一個日期只能有一條記錄
- teamId 通常為 "A", "B", "C" 等

### 2. aliasMap 別名對應
用於管理用戶ID和別名的對應關係。

#### 結構範例
```json
{
  "_id": ObjectId("..."),
  "userId": "U123",
  "aliases": ["大漢堡", "Jed小隊長"],
  "updated_at": ISODate("...")
}
```

## Repository 類

### AttendancesRepository

**主要方法：**

- `create_or_update_attendance(date, teams)` - 創建或更新出席記錄
- `get_attendance_by_date(date)` - 獲取指定日期的出席記錄
- `get_recent_attendances(limit)` - 獲取最近的出席記錄
- `add_user_to_team(date, team_id, user_id, name)` - 將用戶添加到隊伍
- `remove_user_from_attendance(date, user_id)` - 從出席記錄移除用戶
- `get_user_attendances(user_id, limit)` - 獲取用戶的出席歷史

### AliasMapRepository

**主要方法：**

- `create_or_update_alias(user_id, aliases)` - 設定用戶別名
- `get_aliases_by_user_id(user_id)` - 獲取用戶的所有別名
- `find_user_by_alias(alias)` - 根據別名查找用戶ID
- `add_alias_to_user(user_id, new_alias)` - 為用戶添加新別名
- `remove_alias_from_user(user_id, alias)` - 移除用戶的特定別名
- `search_aliases(search_term)` - 搜索包含特定詞彙的別名

## 使用範例

### Python 代碼範例

```python
from src.database.mongodb import get_database
from src.models.mongodb_models import AttendancesRepository, AliasMapRepository

# 初始化
db = get_database()
attendances_repo = AttendancesRepository(db)
alias_repo = AliasMapRepository(db)

# 出席管理
# 添加用戶到隊伍
attendances_repo.add_user_to_team("2025-12-10", "A", "U123", "Jed")
attendances_repo.add_user_to_team("2025-12-10", "A", "U234", "Alice")

# 獲取今日出席情況
today_attendance = attendances_repo.get_attendance_by_date("2025-12-10")

# 別名管理
# 設定用戶別名
alias_repo.create_or_update_alias("U123", ["大漢堡", "Jed小隊長"])

# 根據別名查找用戶
user_id = alias_repo.find_user_by_alias("大漢堡")  # 返回 "U123"
```

## 別名管理工具

### 互動式別名設定
```bash
# 啟動互動式別名管理
python scripts/setup_aliases.py

# 或明確指定互動模式
python scripts/setup_aliases.py interactive
```

### 快速設定預設別名
```bash
# 設定一些預設的別名數據
python scripts/setup_aliases.py setup-defaults
```

### 其他命令
```bash
# 列出所有別名
python scripts/setup_aliases.py list

# 導出別名為 JSON
python scripts/setup_aliases.py export

# 查看幫助
python scripts/setup_aliases.py help
```

## 服務啟動建議

在服務啟動時，建議先運行別名設定工具來建立基本的別名映射：

```bash
# 1. 啟動服務前設定別名
python scripts/setup_aliases.py setup-defaults

# 2. 或進入互動式模式手動設定
python scripts/setup_aliases.py interactive

# 3. 然後啟動主服務
python run.py
```

## 索引設定

新的 Collections 會自動建立以下索引：

**attendances:**
- `date` (unique)
- `date` (descending)
- `teams.members.userId`
- `teams.teamId`

**aliasMap:**
- `userId` (unique)
- `aliases`
- `aliases` (text search)

## 注意事項

1. **隊伍成員限制**：每隊最多 3 個成員，超過會被拒絕
2. **日期格式**：使用 "YYYY-MM-DD" 格式
3. **別名搜索**：支援精確匹配和模糊匹配
4. **數據清理**：別名會自動去重和去除空白
5. **索引優化**：包含文本搜索索引以提升搜索效能

## 遷移說明

這兩個新的 Collections 是對現有系統的補充，不會影響現有的 `players`、`groups`、`group_members`、`divisions` collections。可以根據需求逐步遷移到這個簡化的結構。