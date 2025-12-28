#!/usr/bin/env python3
"""
AI Code Review Client
Sends code and dynamic prompts to the Model Server.
"""

import sys
import json
import glob
import time
from pathlib import Path
from http.client import HTTPConnection

# Configuration
SERVER_HOST = "localhost"
SERVER_PORT = 8000
CHUNK_SIZE = 500
RULES_DIR = Path(__file__).parent / "rules"
DEFAULT_RULES_FILE = "prompt_rules.md"  # Fallback if no language-specific rules exist

SUPPORTED_EXTENSIONS = {
    '.py', '.c', '.cpp', '.h', '.hpp', '.cc', 
    '.java', '.js', '.ts', '.go', '.rs', '.sh', 
    '.kt', '.swift'
}

# Map file extensions to their language-specific rule files
LANGUAGE_RULE_MAP = {
    # Python
    '.py': 'rules_python.md',
    # C/C++
    '.c': 'rules_cpp.md',
    '.cpp': 'rules_cpp.md',
    '.cc': 'rules_cpp.md',
    '.h': 'rules_cpp.md',
    '.hpp': 'rules_cpp.md',
    # Java/Kotlin
    '.java': 'rules_java.md',
    '.kt': 'rules_java.md',
    # JavaScript/TypeScript
    '.js': 'rules_javascript.md',
    '.ts': 'rules_javascript.md',
    # Go
    '.go': 'rules_go.md',
    # Rust
    '.rs': 'rules_rust.md',
    # Shell
    '.sh': 'rules_shell.md',
    # Swift (uses Java rules as closest match)
    '.swift': 'rules_java.md',
}

def get_comment_style(file_extension: str) -> str:
    ext = file_extension.lower()
    if ext in ['.py', '.sh', '.yaml', '.yml', '.rb']:
        return "# REVIEW: "
    elif ext in ['.c', '.cpp', '.h', '.hpp', '.cc', '.java', '.js', '.ts', '.go', '.rs', '.kt', '.swift']:
        return "// REVIEW: "
    else:
        return "REVIEW: "

def load_prompt_template(file_extension: str) -> str:
    """Load the appropriate rule file based on file extension."""
    ext = file_extension.lower()
    
    # Try language-specific rules first
    if ext in LANGUAGE_RULE_MAP:
        rule_file = RULES_DIR / LANGUAGE_RULE_MAP[ext]
        if rule_file.exists():
            with open(rule_file, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            print(f"[WARN] Rule file '{rule_file}' not found, falling back to default.")
    
    # Fallback to default rules
    default_path = Path(__file__).parent / DEFAULT_RULES_FILE
    try:
        with open(default_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"[ERROR] Default prompt file '{DEFAULT_RULES_FILE}' not found.")
        sys.exit(1)

def send_request(code: str, prompt: str, timeout: int) -> str:
    try:
        conn = HTTPConnection(SERVER_HOST, SERVER_PORT, timeout=timeout)
        headers = {'Content-type': 'application/json'}
        payload = json.dumps({'code': code, 'prompt': prompt})
        
        conn.request('POST', '/review', payload, headers)
        response = conn.getresponse()
        
        if response.status != 200:
            print(f"[ERROR] Server returned {response.status}: {response.reason}")
            return ""
            
        data = json.loads(response.read().decode())
        conn.close()
        return data.get('diff', '')
    except ConnectionRefusedError:
        print("[ERROR] Could not connect to server. Is it running?")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Request failed: {e}")
        return ""

def review_file(file_path: Path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"[WARN] Could not read {file_path}: {e}")
        return

    comment_prefix = get_comment_style(file_path.suffix)
    line_count = len(content.splitlines())
    prompt_template = load_prompt_template(file_path.suffix)
    
    print(f"Reviewing {file_path} ({line_count} lines) [Rules: {LANGUAGE_RULE_MAP.get(file_path.suffix.lower(), 'default')}]...")
    
    full_diff = ""
    
    for start_line in range(1, line_count + 1, CHUNK_SIZE):
        end_line = min(start_line + CHUNK_SIZE - 1, line_count)
        is_first = (start_line == 1)
        
        chunk_lines = end_line - start_line + 1
        # Dynamic timeout: Base 30s + 0.5s per line
        # e.g. 500 lines -> 30 + 250 = 280s
        dynamic_timeout = int(30 + (chunk_lines * 0.5))
        
        print(f"  -> Chunk {start_line}-{end_line} (Timeout: {dynamic_timeout}s)...")
        
        header_instruction = ""
        if is_first:
            header_instruction = (
                "CRITICAL INSTRUCTION: You MUST comment on missing headers.\n"
                "If the file lacks SPDX, Copyright, or Author headers, insert a comment at the very top of the file.\n"
            )
            
        # Dynamic Prompt Formatting
        # We use safe substitution or simple replace to avoid issues if the prompt has other curly braces
        # But since we control the prompt file, .format() is preferred if we escape other braces.
        # However, code prompts might have regex curly braces.
        # Safer approach: strict replacement of known keys.
        
        current_prompt = prompt_template.replace("{start_line}", str(start_line))
        current_prompt = current_prompt.replace("{end_line}", str(end_line))
        current_prompt = current_prompt.replace("{comment_prefix}", comment_prefix)
        current_prompt = current_prompt.replace("{header_instruction}", header_instruction)
        
        chunk_diff = send_request(content, current_prompt, dynamic_timeout)
        
        if chunk_diff.strip():
            full_diff += f"\n{chunk_diff}\n"

    if full_diff.strip():
        output_path = file_path.parent / (file_path.name + ".diff")
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(full_diff.strip())
        print(f"  Saved diff to: {output_path}")
    else:
        print("  No issues found.")

def process_path(path_str: str):
    path = Path(path_str)
    if not path.exists():
        print(f"[ERROR] Path not found: {path_str}")
        return

    files = []
    if path.is_file():
        files.append(path)
    elif path.is_dir():
        for ext in SUPPORTED_EXTENSIONS:
            files.extend(path.rglob(f"*{ext}"))
            
    if not files:
        print("No supported files found.")
        return
        
    for f in files:
        if f.name.endswith(".diff") or f.name.endswith("_r"):
            continue
        review_file(f)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python review_client.py <file_or_folder>")
        sys.exit(1)
        
    process_path(sys.argv[1])
