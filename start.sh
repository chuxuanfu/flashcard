#!/bin/bash

# Flashcard 复习系统启动脚本

cd "$(dirname "$0")"

# 先杀掉已有的进程
echo "检查并停止旧进程..."
pkill -f "uvicorn backend.main:app" 2>/dev/null && echo "已停止旧进程" || echo "没有运行中的进程"
sleep 1

# 使用 Python 3.12
PYTHON="/opt/homebrew/bin/python3.12"

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "创建虚拟环境..."
    $PYTHON -m venv venv
fi

# 激活虚拟环境
source venv/bin/activate

# 检查是否需要安装依赖
if ! python -c "import fastapi" 2>/dev/null; then
    echo "安装依赖..."
    pip install --upgrade pip -q
    pip install fastapi uvicorn python-multipart aiofiles python-jose passlib pydantic -q
fi

# 初始化数据库
python -c "from backend.database import init_database; init_database()"

# 获取本机 IP
LOCAL_IP=$(ipconfig getifaddr en0 2>/dev/null || echo 'YOUR_IP')

# 启动服务器
echo ""
echo "=========================================="
echo "  📚 Flashcard 复习系统启动成功！"
echo "=========================================="
echo ""
echo "  本地访问: http://localhost:8000"
echo "  局域网访问: http://${LOCAL_IP}:8000"
echo ""
echo "  按 Ctrl+C 停止服务器"
echo "=========================================="
echo ""

uvicorn backend.main:app --host 0.0.0.0 --port 8000
