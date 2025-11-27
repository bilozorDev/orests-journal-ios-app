#!/bin/bash

# Backend Development Shutdown Script
# Gracefully stops all backend services and closes Terminal

echo "Stopping backend services..."

# Stop Celery Beat
if pgrep -f "celery.*beat" > /dev/null; then
    echo "Stopping Celery Beat..."
    pkill -f "celery.*beat"
fi

# Stop Celery Worker
if pgrep -f "celery.*worker" > /dev/null; then
    echo "Stopping Celery Worker..."
    pkill -f "celery.*worker"
fi

# Stop FastAPI/Uvicorn
if pgrep -f "uvicorn" > /dev/null; then
    echo "Stopping FastAPI..."
    pkill -f "uvicorn"
fi

# Stop Redis
if pgrep -f "redis-server" > /dev/null; then
    echo "Stopping Redis..."
    pkill -f "redis-server"
fi

sleep 1

# Close Terminal windows running dev services
echo "Closing Terminal windows..."
osascript <<EOF
tell application "Terminal"
    close (every window whose name contains "redis-server" or name contains "uvicorn" or name contains "celery")
end tell
EOF

echo "All services stopped!"
