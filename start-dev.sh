#!/bin/bash
# 開發模式：分別啟動後端與前端

echo "=== 啟動後端 (port 8002) ==="
cd backend
.venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8002 &
BACKEND_PID=$!
cd ..

sleep 2

echo "=== 啟動前端 (port 5173) ==="
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "後端: http://localhost:8002"
echo "前端: http://localhost:5173"
echo ""
echo "按 Ctrl+C 停止所有服務"

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT
wait
