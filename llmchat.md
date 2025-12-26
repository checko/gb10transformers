# LLM Chat Application Specification

## Overview
A CLI-based chat application using HuggingFace Transformers to interact with the `openai/gpt-oss-120b` model, optimized for NVIDIA DGX Spark (GB10).

## Target Hardware
| Spec | Value |
|------|-------|
| Platform | NVIDIA DGX Spark (GB10 Superchip) |
| Memory | 128 GB unified LPDDR5x |
| GPU | Blackwell Architecture |

## Model Configuration
| Setting | Value |
|---------|-------|
| Model | `openai/gpt-oss-120b` |
| Quantization | MXFP4 (native to model) |
| Context Window | 131,072 tokens |
| Default max_new_tokens | 32,768 |
| Reasoning Levels | low, medium, high |

## Features

### CLI Interface
- Interactive loop with `You: ` prompt
- Token-by-token streaming output
- Exit with `/bye` command

### Conversation Management
- Multi-turn history (all messages preserved)
- Configurable history limit via `max_history_tokens`
- System prompt loaded from config file

### Commands
| Command | Description |
|---------|-------------|
| `/bye` | Exit the application |
| `/clear` | Reset conversation history |
| `/system <prompt>` | Change system prompt |
| `/save [filename]` | Save conversation to file (default: `chat_YYYYMMDD_HHMMSS.txt`) |
| `/reason <low\|medium\|high>` | Change reasoning effort level |

## Configuration File

**File:** `llmchat_config.yaml`

```yaml
model: "openai/gpt-oss-120b"
system_prompt: "You are a helpful AI assistant."
reasoning_level: "medium"
max_new_tokens: 32768
max_history_tokens: null  # null = no limit
```

## File Structure
```
learntransformer/
├── llmchat.py           # Main application
├── llmchat_config.yaml  # Configuration file
└── llmchat.md           # This specification
```

## Dependencies
- `transformers` (HuggingFace)
- `torch`
- `pyyaml`
- `kernels` (for gpt-oss optimized inference)
