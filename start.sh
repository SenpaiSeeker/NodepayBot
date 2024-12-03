function auto() {
    curl -sL https://raw.githubusercontent.com/SenpaiSeeker/tools/refs/heads/main/api-proxy.sh | bash -s proxies.txt
    sleep 10
    python3 main.py &
    PID=$!
    echo "running with PID: $PID"
}

function stop() {
    if [ ! -z "$PID" ]; then
        echo "Stopping with PID: $PID"
        kill -9 $PID
        clear
    else
        echo "No process found to stop."
    fi
}

while true; do
    echo "Starting auto process..."
    auto
    sleep $((RANDOM % 360 * 10 * 3))
    stop
done
