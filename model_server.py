#!/usr/bin/env python3
"""
AI Code Review Model Server
Loads Qwen3-Coder-30B once and serves review requests via HTTP.
"""

import os
import sys
import json
import torch
from http.server import BaseHTTPRequestHandler, HTTPServer
from transformers import AutoModelForCausalLM, AutoTokenizer

# Configuration
MODEL_ID = "Qwen/Qwen3-Coder-30B-A3B-Instruct"
PORT = 8000
HOST = "localhost"

class ModelWrapper:
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.device = "cuda:0" if torch.cuda.is_available() else "cpu"

    def load(self):
        print(f"[SERVER] Loading model: {MODEL_ID}")
        print(f"[SERVER] Target Device: {self.device}")
        
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=True, local_files_only=True)
            
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
            
            # Ensure pad_token is set
            if self.tokenizer.pad_token_id is None:
                self.tokenizer.pad_token_id = self.tokenizer.eos_token_id
                
            print("[SERVER] Model loaded successfully!")
        except Exception as e:
            print(f"[SERVER] CRITICAL FAILURE: {e}")
            sys.exit(1)

    def generate(self, code_content, system_prompt):
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Filename: input_file\n\n{code_content}"}
        ]

        text = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )
        
        model_inputs = self.tokenizer([text], return_tensors="pt").to(self.device)

        generated_ids = self.model.generate(
            model_inputs.input_ids,
            attention_mask=model_inputs.attention_mask,
            max_new_tokens=4096,
            temperature=0.2, 
            do_sample=True,
            pad_token_id=self.tokenizer.eos_token_id
        )
        
        generated_ids = [
            output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
        ]
        
        response = self.tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
        return self._clean_response(response)

    def _clean_response(self, response: str) -> str:
        lines = response.splitlines()
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        return "\n".join(lines)

# Global model instance
model_wrapper = ModelWrapper()

class ReviewHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != '/review':
            self.send_error(404, "Not Found")
            return

        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data)
            code = data.get('code', '')
            prompt = data.get('prompt', '')
            
            if not code or not prompt:
                self.send_error(400, "Missing 'code' or 'prompt'")
                return

            print(f"[SERVER] Processing review request ({len(code)} bytes)...")
            
            diff = model_wrapper.generate(code, prompt)
            
            response = {'diff': diff}
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode('utf-8'))
            
        except (BrokenPipeError, ConnectionResetError):
            print("[SERVER] Client disconnected before response could be sent.")
        except Exception as e:
            print(f"[SERVER] Error processing request: {e}")
            try:
                self.send_error(500, str(e))
            except (BrokenPipeError, ConnectionResetError):
                pass # Client is already gone

    def log_message(self, format, *args):
        # Suppress default logging to keep console clean
        pass

def run_server():
    model_wrapper.load()
    server_address = (HOST, PORT)
    httpd = HTTPServer(server_address, ReviewHandler)
    print(f"[SERVER] Listening on http://{HOST}:{PORT}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[SERVER] Shutting down...")
        httpd.server_close()

if __name__ == "__main__":
    run_server()
