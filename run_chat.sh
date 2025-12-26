#!/bin/bash
# LLM Chat Startup Script
# Sets required environment variables for DGX Spark (Blackwell GPU)

# Set TRITON_PTXAS_PATH to use system ptxas (supports Blackwell sm_121)
export TRITON_PTXAS_PATH=/usr/local/cuda/bin/ptxas

# Set UTF-8 encoding for Chinese/Unicode input support
export PYTHONIOENCODING=utf-8
export LC_ALL=en_US.UTF-8

# Activate virtual environment
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/.venv/bin/activate"

# Run the chat application
python "$SCRIPT_DIR/llmchat.py" "$@"

