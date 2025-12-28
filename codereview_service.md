# AI Code Review Service Architecture

## Overview
To enable rapid iteration on prompt engineering and code review logic without the overhead of reloading the 30B parameter model each time, the system is refactored into a **Client-Server Architecture**.

## Components

### 1. Model Server (`model_server.py`)
- **Responsibility**: Loads the LLM (`Qwen/Qwen3-Coder-30B-A3B-Instruct`) into GPU memory **once** and keeps it resident.
- **Protocol**: HTTP (using standard library `http.server`).
- **Endpoint**: `POST /review`
- **Port**: 8000 (default)
- **Input**: JSON payload containing:
  - `code`: Source code to review.
  - `prompt`: The full system prompt (allows dynamic updates).
  - `filename`: Name of the file (for context).
  - `line_range`: Start and end lines for chunked review.
- **Output**: JSON payload containing:
  - `review_diff`: The generated unified diff.

### 2. Review Client (`review_client.py`)
- **Responsibility**: Handles file I/O and user interaction.
- **Workflow**:
  1. Reads the target source file(s).
  2. Reads the **external prompt file** (`prompt_rules.md`).
  3. Splits content into chunks (if necessary).
  4. Calculates **Dynamic Timeout** for each chunk.
  5. Sends requests to the Server.
  6. Aggregates responses and writes the `.diff` output file.
- **Usage**: `python review_client.py <file_or_directory>`

### 3. Prompt Configuration (`prompt_rules.md`)
- **Responsibility**: Stores the system prompt and review rules.
- **Benefit**: Can be edited in real-time. The client reads this file for *every* request, ensuring the server always uses the latest instructions.

### 4. Robustness & Timeouts
- **Client Side**: Uses a **Dynamic Timeout** strategy to prevent premature termination on large files.
  - Formula: `Timeout = 30s + (0.5s * line_count)`
  - Example: A 500-line chunk allows for ~4.5 minutes (280s) of processing time.
- **Server Side**: Implements graceful error handling for `BrokenPipeError` and `ConnectionResetError`.
  - If a client disconnects (e.g., killed by system watchdog), the server logs the event and **continues running**, ready for the next request.

## Workflow

1. **Start Server**:
   ```bash
   ./start_server.sh &
   ```
   *Wait for "Model loaded" message.*

2. **Iterate**:
   - Edit `prompt_rules.md` to refine instructions.
   - Run client:
     ```bash
     python review_client.py test_review/bad_python.py
     ```
   - Check `test_review/bad_python.py.diff`.

3. **Stop Server**:
   ```bash
   pkill -f model_server.py
   ```

## API Specification

**POST /review**

**Request Body:**
```json
{
  "code": "def foo():\n    pass",
  "prompt": "You are a code reviewer...",
  "filename": "foo.py",
  "start_line": 1,
  "end_line": 100
}
```

**Response Body:**
```json
{
  "diff": "---\n+++ \n@@ ... @@\n+ # REVIEW: Fix this..."
}
```
