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

### Code Review

| File | Description |
|------|-------------|
| `codereview.py` | AI Code Reviewer using Qwen3-Coder-30B |
| `run_review.sh` | Execution script for code review (sets env vars) |
| `check_model_req.py` | VRAM feasibility check for 30B models |
| `codereview.md` | Feature specification |

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

## AI Code Review

An automated code review system using the Qwen3-Coder-30B model with remote client-server support.

### Quick Start (Local)
```bash
# Start the server (loads model once)
./start_server.sh &

# Review a file
python review_client.py file.py

# Review a directory
python review_client.py ./src
```

### Remote Usage

**On GPU Server (GB10):**
```bash
./start_server.sh  # Listens on 0.0.0.0:8000
```

**On Client Machine (Linux):**
```bash
export REVIEW_SERVER_HOST=192.168.x.x
python review_client.py /path/to/code
```

**On Client Machine (Windows):**
```powershell
$env:REVIEW_SERVER_HOST = "192.168.x.x"
python review_client.py C:\path\to\code
```

### Features
- **Language-Specific Rules**: Python, C++, Java, JavaScript, Go, Rust, Shell
- **Few-Shot Prompting**: Examples improve diff format consistency
- **Sliding Window**: 50-line overlap captures cross-chunk issues
- **Global Context**: First 50 lines (imports) prepended to all chunks
- **Diff Validation**: Validates output for correct unified diff format

### Environment Variables
| Variable | Default | Description |
|----------|---------|-------------|
| `REVIEW_SERVER_HOST` | localhost | Server IP (client) |
| `REVIEW_SERVER_PORT` | 8000 | Server port (client) |
| `SERVER_HOST` | 0.0.0.0 | Bind address (server) |
| `SERVER_PORT` | 8000 | Listen port (server) |

### Client Files (for remote machines)
Copy to any machine:
- `review_client.py`
- `rules/` directory
- `prompt_rules.md`

The tool uses `Qwen/Qwen3-Coder-30B-A3B-Instruct` to analyze code for bugs, security risks, and style issues.

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
