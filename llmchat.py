#!/usr/bin/env python3
"""
LLM Chat Application
CLI chat interface using HuggingFace Transformers with openai/gpt-oss-120b
Optimized for NVIDIA DGX Spark (GB10)

See llmchat.md for full specification.
"""

import os
import sys
import re
import yaml
import logging
import threading
import warnings
from datetime import datetime
from pathlib import Path

import torch
from transformers import pipeline, AutoModelForCausalLM, AutoTokenizer, TextIteratorStreamer

# Suppress the attention mask warning
warnings.filterwarnings("ignore", message=".*attention mask.*")
logging.getLogger("transformers").setLevel(logging.ERROR)


def load_config(config_path: str = "llmchat_config.yaml") -> dict:
    """Load configuration from YAML file."""
    default_config = {
        "model": "openai/gpt-oss-120b",
        "system_prompt": "You are a helpful AI assistant.",
        "reasoning_level": "medium",
        "max_new_tokens": 32768,
        "max_history_tokens": None,
        "show_thinking": False,  # Show chain-of-thought reasoning
    }
    
    config_file = Path(config_path)
    if config_file.exists():
        with open(config_file, "r") as f:
            user_config = yaml.safe_load(f) or {}
            default_config.update(user_config)
    else:
        print(f"[INFO] Config file not found at {config_path}, using defaults.")
    
    return default_config


def build_system_prompt(base_prompt: str, reasoning_level: str) -> str:
    """Build system prompt with reasoning level."""
    return f"{base_prompt}\n\nReasoning: {reasoning_level}"


class LLMChat:
    """Main chat application class."""
    
    def __init__(self, config: dict):
        self.config = config
        self.model_id = config["model"]
        self.system_prompt = config["system_prompt"]
        self.reasoning_level = config["reasoning_level"]
        self.max_new_tokens = config["max_new_tokens"]
        self.max_history_tokens = config["max_history_tokens"]
        self.show_thinking = config.get("show_thinking", False)
        
        self.conversation_history = []
        self.model = None
        self.tokenizer = None
        self.streamer = None
    
    def parse_response(self, response: str) -> tuple:
        """
        Parse gpt-oss response to separate thinking from final answer.
        Returns (thinking, final_answer).
        """
        # Common patterns for gpt-oss chain-of-thought
        # Pattern: ...thinking...assistantfinal<answer>
        patterns = [
            r'(.*)assistantfinal(.*)$',
            r'(.*)\[FINAL\](.*)$',
            r'(.*)\n---\n(.*)$',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)
            if match:
                thinking = match.group(1).strip()
                final = match.group(2).strip()
                return thinking, final
        
        # No pattern matched, return as-is
        return "", response.strip()
        
    def load_model(self):
        """Load the model and tokenizer."""
        print(f"[INFO] Loading model: {self.model_id}")
        print("[INFO] This may take a few minutes...")
        
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_id)
        
        # Load model - try different strategies to avoid meta device issues
        try:
            # Strategy 1: Use device_map with offload disabled
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_id,
                torch_dtype=torch.bfloat16,
                device_map="cuda:0",  # Explicit single device instead of "auto"
                trust_remote_code=True,
            )
        except Exception as e:
            print(f"[WARN] Strategy 1 failed: {e}")
            print("[INFO] Trying alternative loading strategy...")
            # Strategy 2: Load without device_map, then move to GPU
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_id,
                torch_dtype=torch.bfloat16,
                trust_remote_code=True,
            )
            self.model = self.model.cuda()
        
        self.streamer = TextIteratorStreamer(
            self.tokenizer,
            skip_prompt=True,
            skip_special_tokens=True,
        )
        
        print("[INFO] Model loaded successfully!")
        print(f"[INFO] Reasoning level: {self.reasoning_level}")
        print(f"[INFO] Max tokens: {self.max_new_tokens}")
        print()
    
    def get_full_system_prompt(self) -> str:
        """Get system prompt with reasoning level."""
        return build_system_prompt(self.system_prompt, self.reasoning_level)
    
    def build_messages(self, user_input: str) -> list:
        """Build messages list for the model."""
        messages = [
            {"role": "system", "content": self.get_full_system_prompt()},
        ]
        messages.extend(self.conversation_history)
        messages.append({"role": "user", "content": user_input})
        return messages
    
    def generate_response(self, user_input: str):
        """Generate streaming response."""
        messages = self.build_messages(user_input)
        
        # Apply chat template
        inputs = self.tokenizer.apply_chat_template(
            messages,
            add_generation_prompt=True,
            return_tensors="pt",
        ).to(self.model.device)
        
        # Generation kwargs
        generation_kwargs = {
            "input_ids": inputs,
            "max_new_tokens": self.max_new_tokens,
            "streamer": self.streamer,
            "do_sample": True,
            "temperature": 0.7,
            "top_p": 0.9,
            "pad_token_id": self.tokenizer.eos_token_id,
        }
        
        # Run generation in a thread
        thread = threading.Thread(target=self.model.generate, kwargs=generation_kwargs)
        thread.start()
        
        # Collect full response (stream to buffer, not screen)
        full_response = ""
        if self.show_thinking:
            # Show everything as it streams
            print("Assistant: ", end="", flush=True)
            for token in self.streamer:
                print(token, end="", flush=True)
                full_response += token
            print()
        else:
            # Collect silently, then parse
            print("[Thinking...]", end="", flush=True)
            for token in self.streamer:
                full_response += token
            print("\r" + " " * 20 + "\r", end="")  # Clear "Thinking..."
        
        thread.join()
        
        # Parse response to separate thinking from final answer
        thinking, final_answer = self.parse_response(full_response)
        
        if not self.show_thinking:
            print(f"Assistant: {final_answer}")
            if thinking:
                # Store thinking for debugging but don't display
                pass
        
        # Update conversation history (store full response for context)
        self.conversation_history.append({"role": "user", "content": user_input})
        self.conversation_history.append({"role": "assistant", "content": full_response})
        
        return final_answer
    
    def handle_command(self, command: str) -> bool:
        """
        Handle special commands.
        Returns True if should continue, False if should exit.
        """
        parts = command.strip().split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""
        
        if cmd == "/bye":
            print("[INFO] Goodbye!")
            return False
        
        elif cmd == "/clear":
            self.conversation_history = []
            print("[INFO] Conversation history cleared.")
            return True
        
        elif cmd == "/system":
            if arg:
                self.system_prompt = arg
                print(f"[INFO] System prompt updated to: {arg}")
            else:
                print(f"[INFO] Current system prompt: {self.system_prompt}")
            return True
        
        elif cmd == "/save":
            filename = arg if arg else f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            self.save_conversation(filename)
            return True
        
        elif cmd == "/reason":
            if arg.lower() in ["low", "medium", "high"]:
                self.reasoning_level = arg.lower()
                print(f"[INFO] Reasoning level set to: {self.reasoning_level}")
            else:
                print(f"[INFO] Current reasoning level: {self.reasoning_level}")
                print("[INFO] Valid levels: low, medium, high")
            return True
        
        else:
            print(f"[WARN] Unknown command: {cmd}")
            print("[INFO] Available commands: /bye, /clear, /system, /save, /reason")
            return True
    
    def save_conversation(self, filename: str):
        """Save conversation history to file."""
        with open(filename, "w") as f:
            f.write(f"# LLM Chat Conversation\n")
            f.write(f"# Model: {self.model_id}\n")
            f.write(f"# Date: {datetime.now().isoformat()}\n")
            f.write(f"# System Prompt: {self.system_prompt}\n")
            f.write(f"# Reasoning Level: {self.reasoning_level}\n\n")
            
            for msg in self.conversation_history:
                role = msg["role"].upper()
                content = msg["content"]
                f.write(f"[{role}]\n{content}\n\n")
        
        print(f"[INFO] Conversation saved to: {filename}")
    
    def run(self):
        """Main chat loop."""
        import sys
        
        # Reconfigure stdin for UTF-8
        if hasattr(sys.stdin, 'reconfigure'):
            sys.stdin.reconfigure(encoding='utf-8', errors='replace')
        
        self.load_model()
        
        print("=" * 60)
        print("LLM Chat - Type '/bye' to exit, '/help' for commands")
        print("=" * 60)
        print()
        
        while True:
            try:
                print("You: ", end="", flush=True)
                user_input = sys.stdin.readline()
                if not user_input:  # EOF
                    print("\n[INFO] EOF received. Goodbye!")
                    break
                user_input = user_input.strip()
                
                if not user_input:
                    continue
                
                # Handle commands
                if user_input.startswith("/"):
                    if not self.handle_command(user_input):
                        break
                    continue
                
                # Generate response
                self.generate_response(user_input)
                print()
                
            except KeyboardInterrupt:
                print("\n[INFO] Interrupted. Type '/bye' to exit or continue chatting.")
            except EOFError:
                print("\n[INFO] EOF received. Goodbye!")
                break


def main():
    """Main entry point."""
    # Check for custom config path
    config_path = "llmchat_config.yaml"
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    
    # Load config and start chat
    config = load_config(config_path)
    chat = LLMChat(config)
    chat.run()


if __name__ == "__main__":
    main()
