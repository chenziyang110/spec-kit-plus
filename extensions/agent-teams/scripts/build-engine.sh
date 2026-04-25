#!/usr/bin/env bash
set -e

EXT_DIR=".specify/extensions/agent-teams/engine"
RUST_TARGET="$EXT_DIR/target/release/omx-runtime"
RUST_TARGET_EXE="$EXT_DIR/target/release/omx-runtime.exe"
RUNTIME_CLI="$EXT_DIR/dist/team/runtime-cli.js"

if { [ -f "$RUST_TARGET" ] || [ -f "$RUST_TARGET_EXE" ]; } && [ -f "$RUNTIME_CLI" ] && [ -d "$EXT_DIR/node_modules" ]; then
    # Already built, skip
    exit 0
fi

echo "Building AgentTeams Execution Engine (first run only)..."

cd "$EXT_DIR"

# Install Node dependencies for the TS orchestrator state machine
echo "-> Installing npm dependencies..."
npm install --silent

# Compile the TS runtime/orchestrator
echo "-> Building bundled TS runtime..."
npm run build --silent

# Compile the Rust isolation engine
if [ ! -f "$RUST_TARGET" ] && [ ! -f "$RUST_TARGET_EXE" ]; then
    echo "-> Compiling Rust sandbox engine..."
    cargo build -p omx-runtime --release --quiet
fi

echo "Engine built successfully."
