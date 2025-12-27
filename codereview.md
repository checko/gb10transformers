# AI Code Reviewer Specification

## Overview
`codereview.py` is a command-line interface (CLI) tool designed to perform automated code reviews using the **Qwen/Qwen3-Coder-30B-A3B-Instruct** Large Language Model (LLM). It is optimized for the NVIDIA GB10 (Blackwell) architecture.

## Features
- **Input Handling**: Accepts a single file path or a directory path as the first argument.
- **Recursive Processing**: If a directory is provided, it recursively finds source code files.
- **In-Place Review**: Generates a new file with the suffix `_r` (e.g., `test.py` -> `test.py_r`) containing the original code interlaced with AI-generated review comments.
- **Hardware Optimization**: Leverages `torch.bfloat16` and specific device mapping for GB10 VRAM efficiency.

## Technical Specifications

### 1. Model Configuration
- **Model ID**: `Qwen/Qwen3-Coder-30B-A3B-Instruct`
- **Precision**: `bfloat16` (BF16)
- **Loading Strategy**: 
  - `device_map="cuda:0"`
  - `trust_remote_code=True` (Required for Qwen models)
  - `max_memory` set implicitly by device capabilities (120GB available).

### 2. Input/Output
- **Command**: `python codereview.py <input_path>`
- **Input**:
  - Valid file path: Reviews the single file.
  - Valid directory path: Reviews all supported source files within.
- **Output**:
  - For input file `filename.ext`, the output is written to `filename.ext_r`.
  - The output file must contain the **complete original source code** with review comments inserted at relevant lines.

### 3. Supported File Extensions
The tool processes the following extensions by default when scanning directories:
- `.py`, `.c`, `.cpp`, `.h`, `.hpp`, `.cc`, `.java`, `.js`, `.ts`, `.go`, `.rs`, `.sh`

### 4. Prompt Engineering
The system prompt instructs the model to:
1.  Act as an expert code reviewer.
2.  Output the code exactly as provided.
3.  Insert comments starting with `// REVIEW:`, `# REVIEW:`, or `<!-- REVIEW: -->` (language appropriate) immediately *before* the line being discussed.
4.  Focus on: Logic bugs, Security risks, Performance issues, and Code style/Best practices.

### 5. Environment
- Requires Python 3.10+
- Dependencies: `torch`, `transformers`, `accelerate` (implicitly).
- Must be run within the project's virtual environment (`.venv`).

## Execution Flow
1.  **Initialize**: Load Model and Tokenizer (once).
2.  **Discovery**: Resolve input argument to a list of files.
3.  **Process Loop**:
    - Read source file.
    - Format Prompt: "Review the following code..."
    - Generate Response.
    - Extract code/comments from response.
    - Write to `*_r` file.
4.  **Completion**: Print summary of processed files.
