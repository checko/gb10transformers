#!/usr/bin/env python3
"""
AI Code Reviewer
CLI tool using Qwen3-Coder-30B to review code files.
Optimized for NVIDIA DGX Spark (GB10).

See codereview.md for full specification.
"""

import os
import sys
import glob
from pathlib import Path
from typing import List, Optional

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

# Supported extensions for directory scanning
SUPPORTED_EXTENSIONS = {
    '.py', '.c', '.cpp', '.h', '.hpp', '.cc', 
    '.java', '.js', '.ts', '.go', '.rs', '.sh', 
    '.kt', '.swift'
}

# Model Config
MODEL_ID = "Qwen/Qwen3-Coder-30B-A3B-Instruct"
CHUNK_SIZE = 500  # Lines per review chunk

class CodeReviewer:
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.device = "cuda:0" if torch.cuda.is_available() else "cpu"

    def load_model(self):
        """Load the model and tokenizer."""
        print(f"[INFO] Loading model: {MODEL_ID}")
        print(f"[INFO] Target Device: {self.device}")
        
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=True, local_files_only=True)
            
            # Using device_map="cuda:0" and bfloat16 as per spec
            self.model = AutoModelForCausalLM.from_pretrained(
                MODEL_ID,
                torch_dtype=torch.bfloat16,
                device_map=self.device,
                trust_remote_code=True,
                use_safetensors=True,
                low_cpu_mem_usage=True,
                attn_implementation="sdpa",
                local_files_only=True,
            )
            print("[INFO] Model loaded successfully!")
        except Exception as e:
            print(f"[ERROR] Failed to load model: {e}")
            sys.exit(1)

    def get_comment_style(self, file_extension: str) -> str:
        """Return the appropriate comment prefix for the file type."""
        ext = file_extension.lower()
        if ext in ['.py', '.sh', '.yaml', '.yml', '.rb']:
            return "# REVIEW: "
        elif ext in ['.c', '.cpp', '.h', '.hpp', '.cc', '.java', '.js', '.ts', '.go', '.rs', '.kt', '.swift']:
            return "// REVIEW: "
        else:
            return "REVIEW: " # Default fallback

    def review_chunk(self, content: str, start_line: int, end_line: int, comment_prefix: str, is_first_chunk: bool) -> str:
        """Generate review for a specific line range."""
        
        header_instruction = ""
        if is_first_chunk:
            header_instruction = (
                "CRITICAL INSTRUCTION: You MUST comment on missing headers.\n"
                "If the file lacks SPDX, Copyright, or Author headers, insert a comment at the very top of the file.\n"
            )

        system_prompt = (
            "You are an expert Senior Software Engineer and Security Auditor.\n"
            "Your task is to review the provided source code and produce a UNIFIED DIFF that inserts comments where issues are found.\n"
            "\n"
            "OUTPUT INSTRUCTIONS:\n"
            "1. Output ONLY a Unified Diff (patch). Do NOT output the full source file.\n"
            "2. The diff should apply to the original file to add your comments.\n"
            f"3. Use the comment prefix '{comment_prefix}'.\n"
            "4. Insert comments immediately BEFORE the line they refer to.\n"
            "5. Use standard Unified Diff format:\n"
            "   --- original\n"
            "   +++ reviewed\n"
            "   @@ -line,count +line,count @@\n"
            "    context line\n"
            "   +comment line\n"
            "    target line\n"
            "\n"
            "6. Do not wrap the output in Markdown code blocks. Just output raw diff text.\n"
            "7. IGNORE existing comments in the code that look like issue tags (e.g. '[CRITICAL-1]').\n"
            "   You must generate your OWN review comments with the correct prefix.\n"
            "\n"
            f"FOCUS INSTRUCTION: The full file is provided for context, but you must ONLY review and output diffs for lines {start_line} to {end_line}.\n"
            "Do NOT output any diff hunks outside this range.\n"
            "\n"
            f"{header_instruction}\n"
            "REVIEW RULES:\n"
            "PART 1: HEADERS (MANDATORY CHECKS - Only for first chunk)\n"
            "- [HEADER-1] Check for SPDX-License-Identifier.\n"
            "- [HEADER-2] Check for Copyright notice (ensure year is current).\n"
            "- [HEADER-3] Check for Author information.\n"
            f"   -> IF MISSING: Insert a comment at line 1: '{comment_prefix}[HEADER-X] Missing header...'.\n"
            "\n"
            "PART 2: CRITICAL RISKS (Must Fix)\n"
            "- [CRITICAL-1] Memory: Check malloc/new return values and free/delete usage.\n"
            "- [CRITICAL-3/4/5] Concurrency: Check for race conditions, deadlocks, and thread safety.\n"
            "- [CRITICAL-7] Security: Avoid unsafe functions (strcpy, SQL injection).\n"
            "- [CRITICAL-9] Security: NO hard-coded secrets/passwords/keys.\n"
            "- [CRITICAL-10] Security: Validate all user inputs.\n"
            "\n"
            "PART 3: HIGH RISKS (Strongly Recommended)\n"
            "- [HIGH-1] Avoid Global Variables.\n"
            "- [HIGH-3] Error Handling: Use try-catch/result checks and ensure resource cleanup.\n"
            "- [HIGH-5] Resources: Close files, sockets, and connections.\n"
            "- [HIGH-7] Logging: Log security events but exclude sensitive info.\n"
            "\n"
            "PART 4: MEDIUM RISKS (Best Practices)\n"
            "- [MEDIUM-2] Avoid Magic Numbers -> Use constants.\n"
            "- [MEDIUM-3] Reduce Complexity -> Refactor deep nesting (>3 layers).\n"
            "- [MEDIUM-4] Control Flow -> Handle default/else cases.\n"
            "\n"
            "PART 5: LOW RISKS (Style)\n"
            "- [LOW-1] Naming: Enforce standard conventions. For Python, flag ONLY if function/variable names are NOT snake_case. For Java/C++, flag ONLY if NOT CamelCase.\n"
            "- [LOW-3] Structure: Keep classes in separate files where appropriate.\n"
        )
        
        # Add line numbers to content for the model to see
        # This helps the model respect the line range
        # Note: We don't change the actual content input, but we rely on the model counting.
        # Alternatively, we can prepend line numbers, but that might confuse the diff generation.
        # Qwen-Coder is good at counting, so we will try raw content first.
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Filename: input_file\n\n{content}"}
        ]

        # Prepare inputs
        text = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )
        
        model_inputs = self.tokenizer([text], return_tensors="pt").to(self.device)

        # Ensure pad_token is set
        if self.tokenizer.pad_token_id is None:
            self.tokenizer.pad_token_id = self.tokenizer.eos_token_id

        # Generate
        generated_ids = self.model.generate(
            model_inputs.input_ids,
            attention_mask=model_inputs.attention_mask,
            max_new_tokens=4096, # reduced token limit per chunk is fine
            temperature=0.2, 
            do_sample=True,
            pad_token_id=self.tokenizer.eos_token_id
        )
        
        # Decode
        generated_ids = [
            output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
        ]
        response = self.tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
        
        return self._clean_response(response)

    def generate_review(self, file_path: Path) -> str:
        """Read file and generate review content in chunks."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"[WARN] Could not read {file_path}: {e}")
            return ""

        comment_prefix = self.get_comment_style(file_path.suffix)
        line_count = len(content.splitlines())
        
        print(f"    File has {line_count} lines. Analyzing in chunks of {CHUNK_SIZE} lines...")
        
        full_diff = ""
        
        for start_line in range(1, line_count + 1, CHUNK_SIZE):
            end_line = min(start_line + CHUNK_SIZE - 1, line_count)
            is_first = (start_line == 1)
            
            print(f"    -> Processing chunk: Lines {start_line}-{end_line}")
            
            chunk_diff = self.review_chunk(content, start_line, end_line, comment_prefix, is_first)
            
            if chunk_diff.strip():
                full_diff += f"\n{chunk_diff}\n"
                
        return full_diff.strip()

    def _clean_response(self, response: str) -> str:
        """Clean up markdown code blocks if the model included them."""
        lines = response.splitlines()
        
        # Check for start/end code fences
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
            
        return "\n".join(lines)

    def process_path(self, path_str: str):
        """Process a file or directory."""
        path = Path(path_str)
        
        if not path.exists():
            print(f"[ERROR] Path does not exist: {path_str}")
            return

        files_to_process = []
        
        if path.is_file():
            files_to_process.append(path)
        elif path.is_dir():
            for ext in SUPPORTED_EXTENSIONS:
                # Recursive search for supported extensions
                files_to_process.extend(path.rglob(f"*{ext}"))
        
        if not files_to_process:
            print("[INFO] No supported source files found.")
            return

        print(f"[INFO] Found {len(files_to_process)} file(s) to review.")
        
        if self.model is None:
            self.load_model()

        for file_p in files_to_process:
            # Skip existing review files or diffs to avoid loops
            if file_p.name.endswith(".diff") or file_p.name.endswith("_r"):
                continue
            
            # Skip hidden files
            if any(part.startswith('.') for part in file_p.parts):
                continue

            print(f" -> Reviewing: {file_p}")
            reviewed_content = self.generate_review(file_p)
            
            if reviewed_content:
                output_path = file_p.parent / (file_p.name + ".diff")
                try:
                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(reviewed_content)
                    print(f"    Saved to: {output_path}")
                except Exception as e:
                    print(f"    [ERROR] Writing file: {e}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python codereview.py <file_or_folder>")
        sys.exit(1)
        
    target = sys.argv[1]
    reviewer = CodeReviewer()
    reviewer.process_path(target)

if __name__ == "__main__":
    main()