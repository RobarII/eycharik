#!/usr/bin/env bash
# The FRIDA-Decisions sidecar: start, stop, status (ADR 0037).
#
# The model runs in its own process with its own dependency (`mlx`, `onnxruntime` or `torch`), so it
# cannot share the product venv: `uv run --with` resolves that environment next to the repository and
# leaves `apps/api` free of a tensor runtime. The command is the same one an artifact can cite.
#
#   scripts/frida-serve.sh start    # sidecar on :8090, MLX bf16, warms up before it answers
#   scripts/frida-serve.sh stop
#   scripts/frida-serve.sh status
#
# Overrides: FRIDA_PORT, FRIDA_BACKEND (mlx|onnx|torch), FRIDA_DTYPE (bfloat16|float32),
# FRIDA_MODEL (a folder or a Hub repo id), FRIDA_PKG (a pinned package spec).
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)
FRIDA_MODEL=${FRIDA_MODEL:-$HOME/models/frida-decisions}
FRIDA_PORT=${FRIDA_PORT:-8090}
FRIDA_BACKEND=${FRIDA_BACKEND:-mlx}
FRIDA_DTYPE=${FRIDA_DTYPE:-bfloat16}
FRIDA_PKG=${FRIDA_PKG:-frida-decisions[mlx] @ git+https://github.com/ai-forever/FRIDA-Decisions@v0.4.0}
RUN_DIR=${RUN_DIR:-/tmp/frida-serve}
LOG=${LOG:-/tmp/frida-serve.log}

usage() {
    sed -n '2,13p' "$0" | sed 's/^# \{0,1\}//'
    exit 2
}

healthy() {
    curl -fsS --noproxy '*' -o /dev/null "http://127.0.0.1:${FRIDA_PORT}/health" 2>/dev/null
}

start() {
    if healthy; then
        echo "frida-decisions already answers on :$FRIDA_PORT"
        return 0
    fi
    if [ ! -d "$FRIDA_MODEL" ] && [ ! -f "$FRIDA_MODEL" ]; then
        echo "no local model at $FRIDA_MODEL; either download it (hf download ai-forever/FRIDA-Decisions --local-dir ~/models/frida-decisions) or pass a Hub id in FRIDA_MODEL" >&2
        return 1
    fi
    mkdir -p "$RUN_DIR"
    cd "$ROOT"
    FRIDA_PKG="$FRIDA_PKG" uv run --with "$FRIDA_PKG" python scripts/frida_serve.py \
        --backend "$FRIDA_BACKEND" --dtype "$FRIDA_DTYPE" \
        --model "$FRIDA_MODEL" --port "$FRIDA_PORT" >"$LOG" 2>&1 &
    echo $! >"$RUN_DIR/pid"
    for _ in $(seq 1 180); do
        # `/health` answers 503 while the weights load and the warm-up runs; that is the wait.
        if healthy; then
            echo "frida-decisions ready on :$FRIDA_PORT ($FRIDA_BACKEND $FRIDA_DTYPE, log $LOG)"
            return 0
        fi
        sleep 1
    done
    echo "frida-decisions did not answer on :$FRIDA_PORT within 180 s; see $LOG" >&2
    return 1
}

stop() {
    if [ -f "$RUN_DIR/pid" ]; then
        pid=$(cat "$RUN_DIR/pid")
        kill "$pid" 2>/dev/null && echo "frida-decisions stopped (pid $pid)"
        rm -f "$RUN_DIR/pid"
    else
        echo "no pidfile in $RUN_DIR; nothing to stop"
    fi
    if healthy; then
        echo "port :$FRIDA_PORT still answers; a sidecar started outside this script owns it" >&2
    fi
}

status() {
    if health=$(curl -fsS --noproxy '*' "http://127.0.0.1:${FRIDA_PORT}/health" 2>/dev/null); then
        echo "$health <- frida-decisions on :$FRIDA_PORT"
    else
        echo "frida-decisions on :$FRIDA_PORT: down"
    fi
}

case "${1:-}" in
start) start ;;
stop) stop ;;
status) status ;;
*) usage ;;
esac
