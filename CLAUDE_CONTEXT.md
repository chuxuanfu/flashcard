# Flashcard 复习系统 - 项目上下文

> 新对话时让 Claude 先读取这个文件: `请先读取 /Users/chuxuanfu/flashcard-app/CLAUDE_CONTEXT.md`

## 项目位置
`/Users/chuxuanfu/flashcard-app/`

## 技术栈
- **后端**: Python 3.12 + FastAPI
- **前端**: 原生 HTML + CSS + JavaScript  
- **数据库**: SQLite (`data/flashcards.db`)
- **虚拟环境**: 使用 `/opt/homebrew/bin/python3.12`
- **时区**: 洛杉矶时间 (UTC-8)

## 启动命令
```bash
cd /Users/chuxuanfu/flashcard-app && ./start.sh
```
启动脚本会自动杀掉旧进程，无需手动 pkill。

## 项目结构
```
flashcard-app/
├── backend/
│   ├── main.py          # FastAPI 入口
│   ├── config.py        # 配置(密码、JWT密钥、艾宾浩斯间隔)
│   ├── database.py      # SQLite 连接
│   ├── schemas.py       # Pydantic 数据模型
│   ├── routers/
│   │   ├── auth.py      # 登录认证 (JWT)
│   │   ├── cards.py     # 卡片 CRUD + 批量操作 + 媒体上传
│   │   ├── tags.py      # 标签管理 + 合并
│   │   ├── review.py    # 复习逻辑 (基于 review_schedule 表)
│   │   └── transfer.py  # 导入导出 (CSV/JSON/ZIP)
│   └── utils/
│       ├── scheduler.py # 艾宾浩斯算法
│       └── media.py     # 文件上传处理
├── frontend/
│   ├── index.html       # 单页应用主页
│   ├── css/style.css    # 响应式样式
│   └── js/
│       ├── api.js       # API 封装类
│       └── app.js       # 主应用逻辑
├── data/
│   ├── flashcards.db    # SQLite 数据库
│   └── media/           # 图片和音频文件
├── start.sh             # 启动脚本
└── README.md            # 使用说明
```

## 主要功能 (4个Tab)
1. **🏠 今日** - 复习今日到期的卡片
   - 翻转查看答案（**只有答案面显示图片/音频**）
   - 标记掌握/未掌握
   - 可按标签筛选
   
2. **➕ 添加** - 创建卡片
   - 支持文字 + 图片 + 音频 + 标签
   
3. **⚠️ 弱项** - 所有标记为弱项的卡片

4. **📁 管理** - 三个子Tab:
   - **卡片**: 浏览/搜索/筛选/全选/批量移动删除
   - **标签**: 添加/编辑/删除/合并
   - **导入导出**: CSV/JSON/ZIP

---

## 复习逻辑 (艾宾浩斯) - 重要！

### 间隔计算方式：直接间隔（非累计）
从首次学习日期**直接加**对应天数：
- 第1次复习：首次学习 + **1天**
- 第2次复习：首次学习 + **3天**
- 第3次复习：首次学习 + **7天**
- 第4次复习：首次学习 + **14天**
- 第5次复习：首次学习 + **30天**
- 第6次复习：首次学习 + **90天**
- 第7次复习：首次学习 + **365天**

**示例**（首次学习 2/22/2026）：
| 阶段 | 间隔 | 复习日期 |
|------|------|----------|
| 第1次 | +1天 | 2/23/2026 |
| 第2次 | +3天 | 2/25/2026 |
| 第3次 | +7天 | 3/1/2026 |
| 第4次 | +14天 | 3/8/2026 |
| 第5次 | +30天 | 3/24/2026 |
| 第6次 | +90天 | 5/23/2026 |
| 第7次 | +365天 | 2/22/2027 |

### review_schedule 表
每张卡片在 `review_schedule` 表中有7条记录，分别对应7个复习阶段：
- `card_id`: 卡片ID
- `stage`: 阶段 (1-7)
- `scheduled_date`: 预定复习日期
- `reviewed`: 是否已复习 (0/1)
- `reviewed_at`: 复习时间

### 今日复习逻辑
查询条件：`scheduled_date <= 今天 AND reviewed = 0`
- 显示所有预定日期在今天或之前、且尚未复习的卡片

### 复习结果处理
- **掌握**：标记该阶段 `reviewed = 1`，**不影响弱项标记**
- **未掌握**：只标记 `is_weak = 1`，**不改变复习计划**（继续出现在今日复习）

### 弱项标记
- **只能手动取消**：掌握卡片不会自动取消弱项标记
- 可在编辑弹窗或弱项Tab中取消

### 修改首次学习日期
- 重新生成所有阶段的复习计划
- 保留已完成阶段的状态

---

## 数据库表

### cards
```sql
id, question, answer, image_path, audio_path, 
created_at, is_weak, current_stage, next_review, completed
```

### review_schedule（新增）
```sql
id, card_id, stage, scheduled_date, reviewed, reviewed_at
```

### tags
```sql
id, name, color
```

### card_tags
```sql
card_id, tag_id
```

### review_history
```sql
id, card_id, reviewed_at, stage, mastered
```

---

## API 端点
- `POST /api/auth/login` - 登录
- `GET/POST /api/cards` - 卡片列表/创建
- `PUT/DELETE /api/cards/{id}` - 更新/删除卡片
- `PUT/POST /api/cards/{id}/media` - 删除/上传媒体
- `GET /api/review/today` - 今日待复习
- `POST /api/review/submit` - 提交复习结果
- `GET /api/review/schedule/{card_id}` - 获取复习计划
- `PUT /api/review/schedule/{card_id}/stage/{stage}` - 更新阶段状态
- `GET/POST /api/tags` - 标签管理
- `POST /api/tags/merge` - 合并标签
- `GET /api/transfer/export` - 导出
- `POST /api/transfer/import` - 导入

---

## 已完成的功能
- ✅ 密码登录 (JWT Token, 30天过期)
- ✅ 卡片 CRUD + 批量操作
- ✅ 翻转卡片复习（只有答案面显示媒体）
- ✅ 基于 review_schedule 的复习调度
- ✅ 弱项标记（持久化，只能手动取消）
- ✅ 复习计划可视化和手动编辑
- ✅ 标签管理 + 合并
- ✅ 导入导出 (CSV/JSON/ZIP)
- ✅ 图片/音频上传、删除、替换

---

## 已解决的问题和Bug

### 1. 问题面显示媒体
**问题**：复习时问题面也显示图片/音频
**解决**：修改 `renderCardContent()` 函数，只在 `!isQuestion` 时渲染媒体

### 2. 弱项标记自动清除
**问题**：点击"掌握"后弱项标记被自动取消
**解决**：从 `submit_review()` 中移除 `is_weak = 0`

### 3. 复习时间累计计算错误
**问题**：复习时间使用累计间隔（1→4→11天），应该是直接间隔（1→3→7天）
**解决**：修改 `generate_schedule_for_card()` 使用 `start_date + timedelta(days=INTERVALS[stage])`

### 4. JavaScript 模板字符串转义
**问题**：Python 生成 JS 代码时 `` ` `` 被转义成 `\``
**解决**：修复转义字符，确保模板字符串正确

### 5. api.js 方法位置错误
**问题**：新方法被添加到类外面导致语法错误
**解决**：重写 api.js，确保方法在类内部

### 6. 逾期判断时区问题
**问题**：`new Date(scheduled_date) < new Date()` 有时区差异
**解决**：改用字符串比较 `scheduled_date < today`，today 格式为 `YYYY-MM-DD`

### 7. 日期显示缺少年份
**问题**：第7次复习是明年，但只显示月/日
**解决**：修改 `formatDate()` 函数，不同年份时显示完整日期

### 8. 创建卡片时间错误
**问题**：`CURRENT_TIMESTAMP` 使用 UTC 时间，比本地时间快8小时
**解决**：创建卡片时显式设置 `created_at = today.strftime("%Y-%m-%d %H:%M:%S")`

---

## 待完成/可改进
- 外网访问 (Cloudflare Tunnel)
- 开机自启动 (launchd)
- 更多统计数据展示
- 复习历史查看

---

## 访问地址
- 本地: http://localhost:8000
- 局域网: http://192.168.4.22:8000
- API文档: http://localhost:8000/docs

## 配置文件
`backend/config.py`
- `PASSWORD`: 登录密码
- `SECRET_KEY`: JWT密钥
- `EBBINGHAUS_INTERVALS`: [0, 1, 3, 7, 14, 30, 90, 365]
