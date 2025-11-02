#!/bin/bash
# Script to start the Flask server with gunicorn

# Load configuration and get server settings
CONFIG_FILE="${1:-config.json}"
HOST=$(python3 -c "import json, sys; config = json.load(open('$CONFIG_FILE')); print(config.get('server', {}).get('host', '0.0.0.0'))")
PORT=$(python3 -c "import json, sys; config = json.load(open('$CONFIG_FILE')); print(config.get('server', {}).get('port', 8080))")

# Get local IP address
get_local_ip() {
    if command -v ip &> /dev/null; then
        ip route get 8.8.8.8 2>/dev/null | awk '{print $7; exit}' | head -1
    elif command -v ifconfig &> /dev/null; then
        ifconfig | grep "inet " | grep -v 127.0.0.1 | awk '{print $2}' | head -1 | sed 's/addr://'
    else
        python3 -c "import socket; s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.connect(('8.8.8.8', 80)); print(s.getsockname()[0]); s.close()" 2>/dev/null
    fi
}

LOCAL_IP=$(get_local_ip)

echo "============================================================"
echo "SERVER STARTING..."
echo "============================================================"
echo "Server listening on: ${HOST}:${PORT}"

if [ "$HOST" = "0.0.0.0" ] || [ -z "$HOST" ]; then
    if [ -n "$LOCAL_IP" ]; then
        echo ""
        echo "Access from other devices on your network:"
        echo "  http://${LOCAL_IP}:${PORT}/"
        echo "  http://${LOCAL_IP}:${PORT}/video_feed"
        echo "  http://${LOCAL_IP}:${PORT}/api/status"
        echo ""
        echo "On this computer:"
        echo "  http://localhost:${PORT}/"
    else
        echo ""
        echo "Could not determine local IP. Use your machine's IP address."
    fi
else
    echo "Server URL: http://${HOST}:${PORT}/"
fi

echo "============================================================"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Try to find gunicorn (check venv first, then system)
if [ -f "venv/bin/gunicorn" ]; then
    GUNICORN="venv/bin/gunicorn"
elif [ -f "./venv/bin/gunicorn" ]; then
    GUNICORN="./venv/bin/gunicorn"
elif command -v gunicorn &> /dev/null; then
    GUNICORN="gunicorn"
else
    echo "ERROR: gunicorn not found!"
    echo "Please install it with: pip install gunicorn"
    echo ""
    echo "Or run the server directly with Flask:"
    echo "  python app.py"
    exit 1
fi

# Run with gunicorn
# -w 1: 1 worker (camera connection is single)
# --threads 2: 2 threads per worker for handling requests
# --timeout 120: 120 second timeout for long connections
$GUNICORN -w 1 -b ${HOST}:${PORT} --threads 2 --timeout 120 app:app

