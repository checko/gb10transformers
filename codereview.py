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
            self.tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=True)
            
            # Using device_map="cuda:0" and bfloat16 as per spec
            self.model = AutoModelForCausalLM.from_pretrained(
                MODEL_ID,
                torch_dtype=torch.bfloat16,
                device_map=self.device,
                trust_remote_code=True,
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

    def generate_review(self, file_path: Path) -> str:
        """Read file and generate review content."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"[WARN] Could not read {file_path}: {e}")
            return ""

        comment_prefix = self.get_comment_style(file_path.suffix)
        
        # Construct Prompt
        system_prompt = (
            "You are an expert Senior Software Engineer and Security Auditor.\n"
            "Your task is to review the provided source code and insert inline comments where issues are found.\n"
            "\n"
            "OUTPUT INSTRUCTIONS:\n"
            "1. Output the COMPLETE original code. DO NOT TRUNCATE any part of the file.\n"
            f"2. Insert review comments using the prefix '{comment_prefix}'.\n"
            "3. Insert comments immediately BEFORE the line they refer to.\n"
            "4. Do not remove or modify any original code.\n"
            "5. Do not wrap the output in Markdown code blocks (like ```python). Just output raw code.\n"
            "6. IGNORE existing comments in the code that look like issue tags (e.g. '[CRITICAL-1]').\n"
            "   You must generate your OWN review comments with the correct prefix.\n"
            "\n"
            "CRITICAL INSTRUCTION: You MUST comment on missing headers.\n"
            "If the file lacks SPDX, Copyright, or Author headers, insert a comment at the very top of the file.\n"
            "\n"
            "REVIEW RULES:\n"
            "PART 1: HEADERS (MANDATORY CHECKS)\n"
            "- [HEADER-1] Check for SPDX-License-Identifier.\n"
            "- [HEADER-2] Check for Copyright notice (ensure year is current).\n"
            "- [HEADER-3] Check for Author information.\n"
            "   -> IF MISSING: Insert a comment at line 1: '{comment_prefix}[HEADER-X] Missing header...'\n"
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
            "- [LOW-1] Naming: Use standard conventions (CamelCase for Java/C++, snake_case for Python).\n"
            "- [LOW-3] Structure: Keep classes in separate files where appropriate.\n"
            "\n"
            "Example Comment Format:\n"
            f"{comment_prefix}[CRITICAL-9] Hard-coded secret detected. Move to environment variable.\n"
            "String secret = \"123456\";"
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content}
        ]

        # Prepare inputs
        text = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )
        
        model_inputs = self.tokenizer([text], return_tensors="pt").to(self.device)

        # Generate
        # We need a large token limit to accommodate the full file rewrite + comments
        # 8192 is a safe default for modern coding models, but Qwen3 can handle more.
        generated_ids = self.model.generate(
            model_inputs.input_ids,
            max_new_tokens=8192,
            temperature=0.2, # Low temperature for more deterministic/faithful code reproduction
            do_sample=True 
        )
        
        # Decode
        generated_ids = [
            output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
        ]
        response = self.tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
        
        return self._clean_response(response)

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
            # Skip existing review files to avoid loops
            if file_p.name.endswith("_r"):
                continue
            
            # Skip hidden files
            if any(part.startswith('.') for part in file_p.parts):
                continue

            print(f" -> Reviewing: {file_p}")
            reviewed_content = self.generate_review(file_p)
            
            if reviewed_content:
                output_path = file_p.parent / (file_p.name + "_r")
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
