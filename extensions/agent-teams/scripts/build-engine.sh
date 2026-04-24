#!/usr/bin/env bash
set -e

EXT_DIR=".specify/extensions/agent-teams/engine"
RUST_TARGET="$EXT_DIR/target/release/omx-runtime"

if [ -f "$RUST_TARGET" ] && [ -d "$EXT_DIR/node_modules" ]; then
    # Already built, skip
    exit 0
fi

echo "Building AgentTeams Execution Engine (first run only)..."

cd "$EXT_DIR"

# Install Node dependencies for the TS orchestrator state machine
echo "-> Installing npm dependencies..."
npm install --silent

# Compile the Rust isolation engine
if [ ! -f "$RUST_TARGET" ]; then
    echo "-> Compiling Rust sandbox engine..."
    cargo build --release --quiet
fi

echo "Engine built successfully."
