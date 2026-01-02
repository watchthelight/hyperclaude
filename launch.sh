#!/bin/bash
# HyperClaude Swarm Launcher
# Creates a tmux session with 6 Claude worker instances + 1 manager

set -e

SESSION="swarm"
WINDOW="main"
WORKER_COUNT=6

# Kill existing session if present
tmux kill-session -t "$SESSION" 2>/dev/null || true

# Create new session with first pane (worker 0)
tmux new-session -d -s "$SESSION" -n "$WINDOW" -x 200 -y 50

# Start claude in the first pane (worker 0)
tmux send-keys -t "$SESSION:$WINDOW" "claude --dangerously-skip-permissions" Enter

# Create remaining worker panes (1-5)
for i in $(seq 1 $((WORKER_COUNT - 1))); do
    tmux split-window -t "$SESSION:$WINDOW" -h
    tmux send-keys -t "$SESSION:$WINDOW" "claude --dangerously-skip-permissions" Enter
    tmux select-layout -t "$SESSION:$WINDOW" tiled
done

# Final layout adjustment
tmux select-layout -t "$SESSION:$WINDOW" tiled

echo "HyperClaude swarm launched!"
echo "Session: $SESSION, Window: $WINDOW"
echo "Workers: 0-$((WORKER_COUNT - 1)) in panes swarm:main.0 through swarm:main.$((WORKER_COUNT - 1))"
echo ""
echo "To attach: tmux attach -t $SESSION"
echo "To start manager: claude (in a separate terminal)"
