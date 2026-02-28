#!/bin/bash
# 检查依赖并启动 Cantor Brain
echo "Checking requirements..."
if ! python3 -c "import fastapi" &> /dev/null; then
    echo "Installing requirements (fastapi, uvicorn, pydantic-settings)..."
    pip install fastapi uvicorn pydantic-settings
fi

echo "Starting Cantor Brain on port 8000..."
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
