#!/bin/bash
# Cantor 服务停止脚本

set -e

CANTOR_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PID_DIR="$CANTOR_DIR/.pids"

echo "🛑 停止 Cantor 服务..."

# 停止 Brain
if [ -f "$PID_DIR/brain.pid" ]; then
    PID=$(cat "$PID_DIR/brain.pid")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "  停止 Brain (PID: $PID)..."
        kill "$PID" 2>/dev/null || true
        sleep 1
        # 强制终止如果还在运行
        if ps -p "$PID" > /dev/null 2>&1; then
            kill -9 "$PID" 2>/dev/null || true
        fi
    fi
    rm -f "$PID_DIR/brain.pid"
    echo "  ✅ Brain 已停止"
else
    echo "  ℹ️  Brain 未运行"
fi

# 停止 Gateway
if [ -f "$PID_DIR/gateway.pid" ]; then
    PID=$(cat "$PID_DIR/gateway.pid")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "  停止 Gateway (PID: $PID)..."
        kill "$PID" 2>/dev/null || true
        sleep 1
        # 强制终止如果还在运行
        if ps -p "$PID" > /dev/null 2>&1; then
            kill -9 "$PID" 2>/dev/null || true
        fi
    fi
    rm -f "$PID_DIR/gateway.pid"
    echo "  ✅ Gateway 已停止"
else
    echo "  ℹ️  Gateway 未运行"
fi

echo ""
echo "✅ 所有服务已停止"
