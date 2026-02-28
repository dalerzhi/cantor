#!/bin/bash
# Cantor 服务启动脚本
# 启动 Gateway (Go WebSocket) 和 Brain (FastAPI)

set -e

CANTOR_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PID_DIR="$CANTOR_DIR/.pids"

mkdir -p "$PID_DIR"

# 检查 Redis 是否运行
echo "🔍 检查 Redis..."
if ! redis-cli ping > /dev/null 2>&1; then
    echo "❌ Redis 未运行，请先启动 Redis: redis-server"
    exit 1
fi
echo "✅ Redis 运行正常"

# 启动 Gateway
echo "🚀 启动 Cantor Gateway (端口 8766)..."
cd "$CANTOR_DIR/cantor-gateway"
if [ -f "$PID_DIR/gateway.pid" ]; then
    OLD_PID=$(cat "$PID_DIR/gateway.pid")
    if ps -p "$OLD_PID" > /dev/null 2>&1; then
        echo "⚠️  Gateway 已在运行 (PID: $OLD_PID)，先停止..."
        kill "$OLD_PID" 2>/dev/null || true
        sleep 1
    fi
fi
go run main.go > "$CANTOR_DIR/logs/gateway.log" 2>&1 &
echo $! > "$PID_DIR/gateway.pid"
sleep 2

# 检查 Gateway 是否成功启动
if ps -p $(cat "$PID_DIR/gateway.pid") > /dev/null 2>&1; then
    echo "✅ Gateway 启动成功 (PID: $(cat "$PID_DIR/gateway.pid"))"
else
    echo "❌ Gateway 启动失败，查看日志: $CANTOR_DIR/logs/gateway.log"
    exit 1
fi

# 启动 Brain
echo "🚀 启动 Cantor Brain (端口 8000)..."
cd "$CANTOR_DIR/cantor-brain"
if [ -f "$PID_DIR/brain.pid" ]; then
    OLD_PID=$(cat "$PID_DIR/brain.pid")
    if ps -p "$OLD_PID" > /dev/null 2>&1; then
        echo "⚠️  Brain 已在运行 (PID: $OLD_PID)，先停止..."
        kill "$OLD_PID" 2>/dev/null || true
        sleep 1
    fi
fi

# 激活虚拟环境并启动
source .venv/bin/activate
python main.py > "$CANTOR_DIR/logs/brain.log" 2>&1 &
echo $! > "$PID_DIR/brain.pid"
sleep 2

# 检查 Brain 是否成功启动
if ps -p $(cat "$PID_DIR/brain.pid") > /dev/null 2>&1; then
    echo "✅ Brain 启动成功 (PID: $(cat "$PID_DIR/brain.pid"))"
else
    echo "❌ Brain 启动失败，查看日志: $CANTOR_DIR/logs/brain.log"
    exit 1
fi

echo ""
echo "🎉 Cantor 服务已全部启动!"
echo "   - Gateway: ws://localhost:8766/ws"
echo "   - Brain API: http://localhost:8000"
echo "   - Brain Docs: http://localhost:8000/docs"
echo ""
echo "查看日志: tail -f $CANTOR_DIR/logs/*.log"
