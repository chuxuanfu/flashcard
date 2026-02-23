# 📚 Flashcard 复习系统

基于艾宾浩斯遗忘曲线的个人学习复习系统。

## 功能特点

- 🎴 **卡片翻转** - 先看问题，点击翻转看答案
- 📅 **智能复习** - 基于艾宾浩斯遗忘曲线自动安排复习（1天、3天、1周、2周、1个月、3个月、1年）
- 🏷️ **标签管理** - 自定义标签分类，支持合并
- 📷 **多媒体支持** - 支持图片和音频
- 📱 **移动端适配** - 手机友好的响应式设计
- 💾 **本地存储** - 数据存在本地，支持导入导出

## 快速开始

### 1. 修改密码

编辑 `backend/config.py`，修改以下内容：

```python
# 登录密码（请改成你自己的密码）
PASSWORD = "your_password_here"

# JWT 密钥（运行下面命令生成）
SECRET_KEY = "..."
```

生成密钥：
```bash
openssl rand -hex 32
```

### 2. 启动服务

```bash
cd flashcard-app
./start.sh
```

首次运行会自动：
- 创建虚拟环境
- 安装依赖
- 初始化数据库

### 3. 访问系统

- 本地：http://localhost:8000
- 手机（局域网）：http://你的电脑IP:8000

## 外网访问（Cloudflare Tunnel）

### 安装 Cloudflared

```bash
brew install cloudflared
```

### 登录 Cloudflare

```bash
cloudflared tunnel login
```

### 创建隧道

```bash
cloudflared tunnel create flashcard
```

### 配置域名

```bash
cloudflared tunnel route dns flashcard your-subdomain.yourdomain.com
```

### 启动隧道

```bash
cloudflared tunnel run --url http://localhost:8000 flashcard
```

### 设置开机自启

```bash
# 创建 plist 文件
sudo cloudflared service install

# 启动服务
sudo launchctl load /Library/LaunchDaemons/com.cloudflare.cloudflared.plist
```

## 项目结构

```
flashcard-app/
├── backend/           # 后端代码
│   ├── main.py       # FastAPI 入口
│   ├── config.py     # 配置文件
│   ├── database.py   # 数据库
│   ├── schemas.py    # 数据模型
│   ├── routers/      # API 路由
│   └── utils/        # 工具函数
├── frontend/          # 前端代码
│   ├── index.html    # 主页面
│   ├── css/          # 样式
│   └── js/           # JavaScript
├── data/              # 数据目录
│   ├── flashcards.db # SQLite 数据库
│   └── media/        # 媒体文件
├── start.sh          # 启动脚本
└── requirements.txt  # Python 依赖
```

## 复习周期说明

| 阶段 | 间隔 | 说明 |
|------|------|------|
| 0 | 当天 | 首次学习 |
| 1 | +1天 | 第1次复习 |
| 2 | +3天 | 第2次复习 |
| 3 | +7天 | 第3次复习 |
| 4 | +14天 | 第4次复习 |
| 5 | +30天 | 第5次复习 |
| 6 | +90天 | 第6次复习 |
| 7 | +365天 | 第7次复习（完成！）|

## 导入格式

### CSV 格式

```csv
question,answer,tags,image,audio
"问题内容","答案内容","标签1;标签2","images/xxx.jpg","audio/xxx.mp3"
```

### JSON 格式

```json
{
  "cards": [
    {
      "question": "问题",
      "answer": "答案",
      "tags": "标签1;标签2"
    }
  ],
  "tags": [
    {"name": "标签1", "color": "#3B82F6"}
  ]
}
```

### 包含媒体的 ZIP

```
export.zip
├── data.csv (或 data.json)
└── media/
    ├── images/
    └── audio/
```

## API 文档

启动服务后访问：http://localhost:8000/docs

## 常见问题

### Q: 忘记密码怎么办？
A: 直接修改 `backend/config.py` 中的 `PASSWORD`

### Q: 如何备份数据？
A: 复制整个 `data/` 文件夹，或使用导出功能

### Q: 如何迁移到新电脑？
A: 复制整个 `flashcard-app` 文件夹即可

## License

MIT
