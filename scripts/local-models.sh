#!/usr/bin/env bash
# The local eval sidecar: the two llama.cpp servers that make a retrieval run a measurement.
#
# `EMBED_BASE_URL=http://127.0.0.1:8080/v1` and `RERANK_BASE_URL=http://127.0.0.1:8081/v1` are only
# useful while these processes live, and both were started by hand once. This script is the command
# an artifact can cite: the same paths, the same flags, the same ports, up or down in one step.
#
#   scripts/local-models.sh start    # both servers, then wait for /health
#   scripts/local-models.sh stop     # both servers, then wait for the ports to close
#   scripts/local-models.sh status   # what /health says right now
#
# The flags are not decoration. `bge-m3` must be pooled with `cls` and normalised, or it answers in a
# different vector space than the one the index was built in; the reranker needs `--reranking`, which
# is what exposes the Cohere-shaped `/v1/rerank` the adapter speaks. `-ngl 99` is full Metal
# offload: change it and the latency in `docs/measurements/` stops describing this machine.
set -euo pipefail

EMBED_MODEL=${EMBED_MODEL:-$HOME/models/bge-m3/bge-m3-Q8_0.gguf}
RERANK_MODEL=${RERANK_MODEL:-$HOME/models/bge-rerank/bge-reranker-v2-m3-Q8_0.gguf}
EMBED_PORT=${EMBED_PORT:-8080}
RERANK_PORT=${RERANK_PORT:-8081}
LLAMA_SERVER=${LLAMA_SERVER:-llama-server}
RUN_DIR=${RUN_DIR:-/tmp/local-models}
LOG_DIR=${LOG_DIR:-/tmp}
CONTEXT=${CONTEXT:-8192}
GPU_LAYERS=${GPU_LAYERS:-99}

usage() {
    sed -n '2,16p' "$0" | sed 's/^# \{0,1\}//'
    exit 2
}

start_one() {
    local name=$1 model=$2 port=$3
    shift 3
    if [ ! -f "$model" ]; then
        echo "missing model for $name: $model" >&2
        return 1
    fi
    if curl -fsS --noproxy '*' -o /dev/null "http://127.0.0.1:${port}/health" 2>/dev/null; then
        echo "$name already listens on :$port"
        return 0
    fi
    mkdir -p "$RUN_DIR"
    local log="$LOG_DIR/local-models-${name}.log"
    "$LLAMA_SERVER" -m "$model" "$@" \
        -c "$CONTEXT" -ngl "$GPU_LAYERS" --port "$port" >"$log" 2>&1 &
    echo $! >"$RUN_DIR/${name}.pid"
    echo "$name starting on :$port (log $log)"
}

wait_for() {
    local name=$1 port=$2
    for _ in $(seq 1 120); do
        if curl -fsS --noproxy '*' -o /dev/null "http://127.0.0.1:${port}/health" 2>/dev/null; then
            echo "$name ready on :$port"
            return 0
        fi
        sleep 1
    done
    echo "$name did not answer on :$port within 120 s; see $LOG_DIR/local-models-${name}.log" >&2
    return 1
}

stop_one() {
    local name=$1 port=$2 pidfile="$RUN_DIR/${name}.pid"
    if [ -f "$pidfile" ]; then
        local pid
        pid=$(cat "$pidfile")
        if kill "$pid" 2>/dev/null; then
            echo "$name stopped (pid $pid)"
        fi
        rm -f "$pidfile"
    else
        echo "$name has no pidfile in $RUN_DIR; nothing to stop"
    fi
    if curl -fsS --noproxy '*' -o /dev/null "http://127.0.0.1:${port}/health" 2>/dev/null; then
        echo "port :$port still answers; a server started outside this script owns it" >&2
    fi
}

status_one() {
    local name=$1 port=$2
    if curl -fsS --noproxy '*' "http://127.0.0.1:${port}/health" 2>/dev/null; then
        echo " <- $name on :$port"
    else
        echo "$name on :$port: down"
    fi
}

case "${1:-}" in
start)
    start_one embed "$EMBED_MODEL" "$EMBED_PORT" \
        --embedding --pooling cls --embd-normalize 2
    start_one rerank "$RERANK_MODEL" "$RERANK_PORT" --reranking
    wait_for embed "$EMBED_PORT"
    wait_for rerank "$RERANK_PORT"
    cat <<EOF

Now run a measurement, for example:

  EMBED_PROVIDER=openai EMBED_BASE_URL=http://127.0.0.1:${EMBED_PORT}/v1 \\
  EMBED_PROFILE=local-bge-m3 RERANK_BASE_URL=http://127.0.0.1:${RERANK_PORT}/v1 \\
  RERANK_PROFILE=local-bge-reranker-v2-m3 make eval-rerank

Reindex before the first run: the index records the embedder that built it, and a bge-m3 index is
rejected by a hashing process and the other way round.
EOF
    ;;
stop)
    stop_one rerank "$RERANK_PORT"
    stop_one embed "$EMBED_PORT"
    ;;
status)
    status_one embed "$EMBED_PORT"
    status_one rerank "$RERANK_PORT"
    ;;
*)
    usage
    ;;
esac
