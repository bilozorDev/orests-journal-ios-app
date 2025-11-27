#!/bin/bash

# Backend Development Startup Script
# Opens all services as tabs in Terminal

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"

echo "Starting backend services in Terminal..."

osascript <<EOF
tell application "Terminal"
    activate

    -- Tab 1: Redis
    do script "echo 'Redis Server' && redis-server"
    delay 0.3

    -- Tab 2: FastAPI
    tell application "System Events" to tell process "Terminal" to keystroke "t" using command down
    delay 0.3
    do script "echo 'FastAPI Server' && cd '$BACKEND_DIR' && source venv/bin/activate && uvicorn app.main:app --reload" in selected tab of front window

    -- Tab 3: Celery Worker
    tell application "System Events" to tell process "Terminal" to keystroke "t" using command down
    delay 0.3
    do script "echo 'Celery Worker' && cd '$BACKEND_DIR' && source venv/bin/activate && celery -A app.core.celery_app worker --loglevel=info" in selected tab of front window

    -- Tab 4: Celery Beat
    tell application "System Events" to tell process "Terminal" to keystroke "t" using command down
    delay 0.3
    do script "echo 'Celery Beat' && cd '$BACKEND_DIR' && source venv/bin/activate && celery -A app.core.celery_app beat --loglevel=info" in selected tab of front window
end tell
EOF

echo "All services started in Terminal tabs!"
echo "Use ./stop-dev.sh to stop all services"
