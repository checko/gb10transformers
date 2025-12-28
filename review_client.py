#!/usr/bin/env python3
"""
AI Code Review Client
Sends code and dynamic prompts to the Model Server.
"""

import os
import sys
import json
import glob
import time
import re
from pathlib import Path
from http.client import HTTPConnection

# Configuration - can be overridden via environment variables
# Set REVIEW_SERVER_HOST to connect to remote GPU server
SERVER_HOST = os.getenv("REVIEW_SERVER_HOST", "localhost")
SERVER_PORT = int(os.getenv("REVIEW_SERVER_PORT", "8000"))
CHUNK_SIZE = 300  # Reduced from 500 for better handling with detailed prompts
OVERLAP_SIZE = 50  # Lines of overlap between chunks to capture cross-chunk context
GLOBAL_CONTEXT_LINES = 50  # First N lines (imports/headers) prepended to all chunks
BASE_TIMEOUT = 1500  # 25 min timeout - model generates ~8k tokens at ~7 tok/s
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

def validate_diff(diff_text: str) -> tuple[bool, list[str]]:
    """
    Validate that the diff text appears to be a valid unified diff.
    Returns (is_valid, list of warnings).
    """
    warnings = []
    
    if not diff_text or not diff_text.strip():
        return True, []  # Empty diff is valid (no issues found)
    
    lines = diff_text.strip().splitlines()
    
    # Check for basic diff structure
    has_minus_header = any(line.startswith('---') for line in lines)
    has_plus_header = any(line.startswith('+++') for line in lines)
    has_hunk_header = any(line.startswith('@@') for line in lines)
    
    if not has_minus_header:
        warnings.append("Missing '--- original' header")
    if not has_plus_header:
        warnings.append("Missing '+++ reviewed' header")
    if not has_hunk_header:
        warnings.append("Missing @@ hunk header")
    
    # Check hunk header format: @@ -line,count +line,count @@
    hunk_pattern = re.compile(r'^@@\s*-\d+(?:,\d+)?\s+\+\d+(?:,\d+)?\s*@@')
    hunks = [line for line in lines if line.startswith('@@')]
    for hunk in hunks:
        if not hunk_pattern.match(hunk):
            warnings.append(f"Malformed hunk header: {hunk[:50]}...")
    
    # Check that diff has actual changes (+ or - lines)
    has_additions = any(line.startswith('+') and not line.startswith('+++') for line in lines)
    has_deletions = any(line.startswith('-') and not line.startswith('---') for line in lines)
    
    if not has_additions and not has_deletions:
        warnings.append("Diff has no actual changes (no + or - lines)")
    
    is_valid = len(warnings) == 0 or (has_hunk_header and (has_additions or has_deletions))
    
    return is_valid, warnings

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

    lines = content.splitlines(keepends=True)
    line_count = len(lines)
    comment_prefix = get_comment_style(file_path.suffix)
    prompt_template = load_prompt_template(file_path.suffix)
    
    # Extract global context (first N lines for imports/headers)
    global_context_end = min(GLOBAL_CONTEXT_LINES, line_count)
    global_context = "".join(lines[:global_context_end])
    
    print(f"Reviewing {file_path} ({line_count} lines) [Rules: {LANGUAGE_RULE_MAP.get(file_path.suffix.lower(), 'default')}]...")
    
    full_diff = ""
    
    # Calculate chunk boundaries with overlap
    # First chunk: 1 to CHUNK_SIZE
    # Second chunk: (CHUNK_SIZE + 1 - OVERLAP_SIZE) to (2 * CHUNK_SIZE - OVERLAP_SIZE)
    # etc.
    chunk_start = 1
    while chunk_start <= line_count:
        chunk_end = min(chunk_start + CHUNK_SIZE - 1, line_count)
        is_first = (chunk_start == 1)
        
        # Calculate overlap region (context from previous chunk)
        overlap_start = None
        overlap_end = None
        overlap_context = ""
        if not is_first and chunk_start > OVERLAP_SIZE:
            overlap_start = chunk_start - OVERLAP_SIZE
            overlap_end = chunk_start - 1
            overlap_context = "".join(lines[overlap_start - 1:overlap_end])
        
        chunk_lines = chunk_end - chunk_start + 1
        # Dynamic timeout: Base 30s + 0.5s per line
        dynamic_timeout = int(BASE_TIMEOUT + (chunk_lines * 0.5))
        
        print(f"  -> Chunk {chunk_start}-{chunk_end} (Timeout: {dynamic_timeout}s)...")
        
        # Build header instruction for first chunk
        header_instruction = ""
        if is_first:
            header_instruction = (
                "CRITICAL INSTRUCTION: You MUST comment on missing headers.\n"
                "If the file lacks SPDX, Copyright, or Author headers, insert a comment at the very top of the file.\n"
            )
        
        # Build context instruction
        context_instruction = ""
        
        # Add global context instruction (imports/headers) for non-first chunks
        if not is_first and global_context_end > 0:
            context_instruction += (
                f"\n[GLOBAL CONTEXT - DO NOT REVIEW - Lines 1-{global_context_end}]\n"
                "The following lines show imports and file headers for context:\n"
                f"```\n{global_context}```\n"
                "[END GLOBAL CONTEXT]\n"
            )
        
        # Add overlap context instruction
        if overlap_start and overlap_end:
            context_instruction += (
                f"\n[OVERLAP CONTEXT - DO NOT REVIEW - Lines {overlap_start}-{overlap_end}]\n"
                "The following lines are context from the previous chunk:\n"
                f"```\n{overlap_context}```\n"
                "[END OVERLAP CONTEXT]\n"
            )
        
        # Dynamic Prompt Formatting
        current_prompt = prompt_template.replace("{start_line}", str(chunk_start))
        current_prompt = current_prompt.replace("{end_line}", str(chunk_end))
        current_prompt = current_prompt.replace("{comment_prefix}", comment_prefix)
        current_prompt = current_prompt.replace("{header_instruction}", header_instruction)
        
        # Append context instruction before the review rules
        if context_instruction:
            # Insert context after FOCUS INSTRUCTION section
            focus_marker = "## FOCUS INSTRUCTION"
            if focus_marker in current_prompt:
                parts = current_prompt.split(focus_marker, 1)
                # Find the end of the FOCUS INSTRUCTION paragraph
                focus_section_end = parts[1].find("\n\n")
                if focus_section_end != -1:
                    current_prompt = (
                        parts[0] + focus_marker + 
                        parts[1][:focus_section_end + 2] + 
                        context_instruction + 
                        parts[1][focus_section_end + 2:]
                    )
        
        chunk_diff = send_request(content, current_prompt, dynamic_timeout)
        
        if chunk_diff.strip():
            # Validate the diff before adding
            is_valid, diff_warnings = validate_diff(chunk_diff)
            if diff_warnings:
                print(f"    [WARN] Diff validation issues: {'; '.join(diff_warnings)}")
            full_diff += f"\n{chunk_diff}\n"
        
        # Move to next chunk (subtract overlap to create sliding window)
        chunk_start = chunk_end + 1 - OVERLAP_SIZE if chunk_end < line_count else line_count + 1

    if full_diff.strip():
        # Final validation of combined diff
        is_valid, final_warnings = validate_diff(full_diff)
        if final_warnings:
            print(f"  [WARN] Final diff has issues: {'; '.join(final_warnings)}")
        
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
