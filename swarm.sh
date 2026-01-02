#!/bin/bash
# HyperClaude Swarm Helper Script
# Provides convenient commands for managing workers

SESSION="swarm"
WINDOW="main"
WORKERS=6
HYPERCLAUDE_DIR="$HOME/.hyperclaude"

usage() {
    echo "Usage: $0 <command> [args]"
    echo ""
    echo "Commands:"
    echo "  clear          - Clear all workers' contexts"
    echo "  clear N        - Clear worker N's context"
    echo "  send N 'msg'   - Send message to worker N"
    echo "  read N         - Read output from worker N"
    echo "  status         - Show all workers' status"
    echo "  ready          - Check if all workers are ready (0 tokens)"
    echo "  results        - Show all workers' result files"
    echo "  result N       - Show worker N's result file"
    echo "  locks          - Show active file locks"
    echo "  logs           - Tail all recent log files"
    echo ""
    echo "Workers are numbered 0-$((WORKERS-1))"
}

clear_worker() {
    local n=$1
    tmux send-keys -t "$SESSION:$WINDOW.$n" "/clear" && tmux send-keys -t "$SESSION:$WINDOW.$n" Enter
}

clear_all() {
    for i in $(seq 0 $((WORKERS-1))); do
        clear_worker $i
    done
    echo "Cleared all $WORKERS workers"
}

send_to_worker() {
    local n=$1
    shift
    local msg="$*"
    tmux send-keys -t "$SESSION:$WINDOW.$n" "$msg" && tmux send-keys -t "$SESSION:$WINDOW.$n" Enter
    echo "Sent to worker $n: $msg"
}

read_worker() {
    local n=$1
    local lines=${2:-30}
    tmux capture-pane -t "$SESSION:$WINDOW.$n" -p -S -$lines
}

show_status() {
    for i in $(seq 0 $((WORKERS-1))); do
        echo "=== Worker $i ==="
        tmux capture-pane -t "$SESSION:$WINDOW.$i" -p -S -5 | tail -5
        echo ""
    done
}

check_ready() {
    local all_ready=true
    for i in $(seq 0 $((WORKERS-1))); do
        local tokens=$(tmux capture-pane -t "$SESSION:$WINDOW.$i" -p -S -5 | grep -o '[0-9]* tokens' | grep -o '[0-9]*')
        if [ "$tokens" = "0" ] || [ -z "$tokens" ]; then
            echo "Worker $i: ready (0 tokens)"
        else
            echo "Worker $i: busy ($tokens tokens)"
            all_ready=false
        fi
    done
    $all_ready && echo "All workers ready!" || echo "Some workers busy"
}

show_results() {
    echo "Worker Results"
    echo "============================================"
    for i in $(seq 0 $((WORKERS-1))); do
        local result_file="$HYPERCLAUDE_DIR/results/worker-$i.txt"
        echo ""
        echo "=== Worker $i ==="
        if [ -f "$result_file" ]; then
            cat "$result_file"
        else
            echo "(no result file)"
        fi
    done
}

show_result() {
    local n=$1
    local result_file="$HYPERCLAUDE_DIR/results/worker-$n.txt"
    if [ -f "$result_file" ]; then
        cat "$result_file"
    else
        echo "No result file for worker $n"
    fi
}

show_locks() {
    echo "Active File Locks"
    echo "============================================"
    local locks_dir="$HYPERCLAUDE_DIR/locks"
    if [ -d "$locks_dir" ]; then
        for lock_file in "$locks_dir"/*.lock; do
            if [ -f "$lock_file" ]; then
                echo ""
                echo "=== $(basename "$lock_file") ==="
                cat "$lock_file"
            fi
        done
        if [ ! -f "$locks_dir"/*.lock ] 2>/dev/null; then
            echo "No active locks"
        fi
    else
        echo "No locks directory"
    fi
}

show_logs() {
    local logs_dir="$HYPERCLAUDE_DIR/logs"
    if [ -d "$logs_dir" ]; then
        # Find most recent session
        local latest=$(ls -td "$logs_dir"/session-* 2>/dev/null | head -1)
        if [ -n "$latest" ]; then
            echo "Tailing logs from: $latest"
            echo "============================================"
            tail -f "$latest"/*.log 2>/dev/null
        else
            echo "No log sessions found"
        fi
    else
        echo "No logs directory"
    fi
}

case "$1" in
    clear)
        if [ -n "$2" ]; then
            clear_worker "$2"
            echo "Cleared worker $2"
        else
            clear_all
        fi
        ;;
    send)
        if [ -z "$2" ] || [ -z "$3" ]; then
            echo "Usage: $0 send N 'message'"
            exit 1
        fi
        send_to_worker "$2" "${@:3}"
        ;;
    read)
        if [ -z "$2" ]; then
            echo "Usage: $0 read N [lines]"
            exit 1
        fi
        read_worker "$2" "$3"
        ;;
    status)
        show_status
        ;;
    ready)
        check_ready
        ;;
    results)
        show_results
        ;;
    result)
        if [ -z "$2" ]; then
            echo "Usage: $0 result N"
            exit 1
        fi
        show_result "$2"
        ;;
    locks)
        show_locks
        ;;
    logs)
        show_logs
        ;;
    *)
        usage
        exit 1
        ;;
esac
