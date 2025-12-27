import torch
import sys
import os

def check_vram():
    print("Checking VRAM availability for Qwen/Qwen3-Coder-30B-A3B-Instruct...")
    
    if not torch.cuda.is_available():
        print("❌ CUDA is not available. Cannot run GPU inference.")
        return

    device_count = torch.cuda.device_count()
    print(f"Found {device_count} CUDA device(s).")

    # Assuming we use device 0
    device = torch.device("cuda:0")
    props = torch.cuda.get_device_properties(device)
    total_mem = props.total_memory
    
    # Get current usage (in case other things are running)
    current_allocated = torch.cuda.memory_allocated(device)
    current_reserved = torch.cuda.memory_reserved(device)
    
    total_gb = total_mem / (1024**3)
    free_gb = (total_mem - current_reserved) / (1024**3)
    
    print(f"\nGPU 0: {props.name}")
    print(f"  Total VRAM: {total_gb:.2f} GB")
    print(f"  Free VRAM:  {free_gb:.2f} GB")
    
    # Model Estimation
    # Model: Qwen3-Coder-30B
    # Parameters: ~30 Billion
    params_b = 30
    
    # Standard Precision (BF16/FP16) - 2 bytes per param
    size_bf16_gb = params_b * 2
    
    # 4-bit Quantization (MXFP4 / INT4) - 0.5 bytes per param
    # Note: MXFP4 might have slight overhead or specific layout, but 0.5 is good baseline
    size_fp4_gb = params_b * 0.5
    
    # Context / KV Cache overhead
    # For coding tasks, we often need large context.
    # 32k context can take 5-10GB depending on implementation (GQA helps).
    # Let's be safe and reserve 10GB for runtime overhead + long context.
    runtime_overhead_gb = 10.0
    
    print(f"\nModel Requirement Estimation (30B Params):")
    print(f"  Base Weights (BF16/FP16): ~{size_bf16_gb:.1f} GB")
    print(f"  Base Weights (4-bit/MXFP4): ~{size_fp4_gb:.1f} GB")
    print(f"  Runtime Buffer (KV Cache, Activation): ~{runtime_overhead_gb:.1f} GB")
    
    req_bf16 = size_bf16_gb + runtime_overhead_gb
    req_fp4 = size_fp4_gb + runtime_overhead_gb
    
    print("\nFeasibility Analysis:")
    
    # Scenario 1: Standard Loading
    print(f"  [Scenario 1] Standard BF16 Loading (~{req_bf16:.1f} GB)")
    if free_gb >= req_bf16:
        print("  -> ✅ SUFFICIENT. You can load this model in native BF16.")
    else:
        print(f"  -> ❌ INSUFFICIENT. Missing {req_bf16 - free_gb:.1f} GB.")
        
    # Scenario 2: 4-bit Loading (MXFP4)
    print(f"  [Scenario 2] 4-bit / MXFP4 Loading (~{req_fp4:.1f} GB)")
    if free_gb >= req_fp4:
        print("  -> ✅ SUFFICIENT. You can load this model with 4-bit quantization.")
    else:
        print(f"  -> ❌ INSUFFICIENT. Missing {req_fp4 - free_gb:.1f} GB.")

if __name__ == "__main__":
    check_vram()
