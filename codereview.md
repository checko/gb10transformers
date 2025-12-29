# AI Code Reviewer Specification

## Overview
A client-server code review system using the **Qwen/Qwen3-Coder-30B-A3B-Instruct** LLM, optimized for NVIDIA GB10 (Blackwell) architecture. The server runs on a GPU machine, while clients can connect remotely from any Linux or Windows machine.

## Architecture

```
┌─────────────────┐         HTTP          ┌─────────────────┐
│  review_client  │ ──────────────────────►  model_server   │
│  (Any Machine)  │     POST /review      │  (GPU Machine)  │
│  Linux/Windows  │ ◄────────────────────  │  GB10 + 120GB   │
└─────────────────┘        JSON           └─────────────────┘
```

## Features
- **Remote Operation**: Client runs on any machine, server runs on GPU machine
- **Language-Specific Rules**: Tailored review rules for Python, C++, Java, JavaScript, Go, Rust, Shell
- **Few-Shot Prompting**: Examples of correct diff format improve output quality
- **Sliding Window**: 50-line overlap between chunks captures cross-boundary issues
- **Global Context Injection**: First 50 lines (imports) prepended to all chunks
- **Diff Validation**: Output validated for correct unified diff format

## Server Setup (GPU Machine)

### Start Server
```bash
./start_server.sh
```

### Environment Variables
| Variable | Default | Description |
|----------|---------|-------------|
| `SERVER_HOST` | 0.0.0.0 | Bind address (0.0.0.0 = all interfaces) |
| `SERVER_PORT` | 8000 | Port to listen on |
| `MODEL_ID` | Qwen/Qwen3-Coder-30B-A3B-Instruct | Model to load |

## Client Usage

### Linux
```bash
export REVIEW_SERVER_HOST=192.168.x.x  # GPU server IP
python review_client.py /path/to/code
```

### Windows (PowerShell)
```powershell
$env:REVIEW_SERVER_HOST = "192.168.x.x"
python review_client.py C:\path\to\code
```

### Environment Variables
| Variable | Default | Description |
|----------|---------|-------------|
| `REVIEW_SERVER_HOST` | localhost | Server IP address |
| `REVIEW_SERVER_PORT` | 8000 | Server port |

## Technical Specifications

### Model Configuration
- **Model ID**: `Qwen/Qwen3-Coder-30B-A3B-Instruct`
- **Precision**: `bfloat16` (BF16)
- **Device**: `cuda:0` with 120GB VRAM

### Chunking Strategy
- **Chunk Size**: 300 lines (configurable)
- **Overlap**: 50 lines between chunks
- **Global Context**: First 50 lines prepended to all chunks

### Supported File Extensions
`.py`, `.c`, `.cpp`, `.h`, `.hpp`, `.cc`, `.java`, `.js`, `.ts`, `.go`, `.rs`, `.sh`, `.kt`, `.swift`

### Output Format
- Unified diff format (`.diff` file)
- Comments use language-appropriate prefix: `# REVIEW:`, `// REVIEW:`
- Each issue tagged with rule ID: `[CRITICAL-9]`, `[HIGH-1]`, `[MEDIUM-2]`, etc.

## Client Files Required
To run the client on a remote machine, copy:
- `review_client.py` (for local model server)
- `review_client_ollama.py` (for Ollama API)
- `rules/` directory (with all rule files)
- `prompt_rules.md` (fallback rules)

## Ollama Alternative

Use `review_client_ollama.py` to leverage a remote Ollama server instead of the local model server.

### Usage
```bash
# Default configuration
python review_client_ollama.py /path/to/code

# Custom Ollama server
export OLLAMA_HOST=192.168.x.x
export OLLAMA_MODEL=qwen3-coder:30b
python review_client_ollama.py ./src
```

### Environment Variables
| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_HOST` | 192.168.145.70 | Ollama server IP |
| `OLLAMA_PORT` | 11434 | Ollama server port |
| `OLLAMA_MODEL` | qwen3-coder:30b | Model name |

### API Endpoint
Uses Ollama's native chat API: `POST /api/chat`

### Output Files
- Local model server: `*.diff`
- Ollama client: `*.ollama.diff`

### Comparing Results
```bash
python review_client.py file.py        # → file.py.diff
python review_client_ollama.py file.py  # → file.py.ollama.diff
diff file.py.diff file.py.ollama.diff  # Compare outputs
```

## Review Rules
Rules are organized by language in `rules/`:
| File | Languages |
|------|-----------|
| `rules_python.md` | Python |
| `rules_cpp.md` | C, C++, Headers |
| `rules_java.md` | Java, Kotlin, Swift |
| `rules_javascript.md` | JavaScript, TypeScript |
| `rules_go.md` | Go |
| `rules_rust.md` | Rust |
| `rules_shell.md` | Bash, Shell |

## Environment Requirements
- **Python**: 3.10+
- **Server**: NVIDIA GPU with CUDA, 60GB+ VRAM
- **Dependencies**: `torch`, `transformers`, `accelerate`
