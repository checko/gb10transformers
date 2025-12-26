# LLM Chat for DGX Spark

A CLI chat application using HuggingFace Transformers with the `openai/gpt-oss-120b` model, optimized for NVIDIA DGX Spark (GB10 Blackwell).

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the chat application
./run_chat.sh
```

## Files

### Main Application

| File | Description |
|------|-------------|
| `llmchat.py` | Main chat application with multi-turn conversation, streaming output, and special commands |
| `llmchat_config.yaml` | Configuration file for model, system prompt, reasoning level, and token limits |
| `run_chat.sh` | Startup script that sets required environment variables (TRITON_PTXAS_PATH, UTF-8) |
| `llmchat.md` | Software specification document |

### Utilities

| File | Description |
|------|-------------|
| `check_gpu.py` | Verify GPU availability and CUDA setup |
| `envcheck.py` | Check environment for large model support (memory, GPU) |

### CI/CD Tools

| File | Description |
|------|-------------|
| `ai_review.py` | GitLab CI code review tool using Ollama/HuggingFace for automated code analysis |

### Test Scripts

| File | Description |
|------|-------------|
| `test1.py` | Simple HuggingFace pipeline test (sentiment analysis) |

## Chat Commands

| Command | Description |
|---------|-------------|
| `/bye` | Exit the application |
| `/clear` | Reset conversation history |
| `/system <prompt>` | Change system prompt |
| `/save [filename]` | Save conversation to file |
| `/reason <low\|medium\|high>` | Change reasoning effort level |

## Configuration

Edit `llmchat_config.yaml`:

```yaml
model: "openai/gpt-oss-120b"
system_prompt: "You are a helpful AI assistant."
reasoning_level: "medium"    # low, medium, high
max_new_tokens: 32768
max_history_tokens: null     # null = no limit
show_thinking: true          # Show chain-of-thought reasoning
```

## Hardware Requirements

- **Platform**: NVIDIA DGX Spark (GB10 Superchip)
- **Memory**: 128 GB unified LPDDR5x
- **GPU**: Blackwell Architecture (sm_121)
- **CUDA**: 13.0+

## Known Issues & Solutions

### 1. ptxas sm_121a Error
**Solution**: The `run_chat.sh` script sets `TRITON_PTXAS_PATH=/usr/local/cuda/bin/ptxas` to use the system's CUDA 13 ptxas.

### 2. Meta Device Error
**Solution**: Model loading uses `device_map="cuda:0"` with explicit `torch.bfloat16` dtype.

### 3. Flash Attention Incompatibility
**Status**: `flash-attn` requires CUDA 12, DGX Spark has CUDA 13. Using default SDPA attention.

## Dependencies

```
transformers
torch
accelerate
pyyaml
kernels
```

## License

MIT License
