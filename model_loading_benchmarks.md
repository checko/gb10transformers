# Qwen3-Coder-30B Loading Benchmarks on NVIDIA GB10

## Overview
This document records the performance testing results for loading the **Qwen/Qwen3-Coder-30B-A3B-Instruct** model on the **NVIDIA GB10 (Blackwell)** architecture.

The goal was to determine the optimal loading strategy balancing loading time, VRAM usage, and model quality for code review tasks.

## System Specifications
- **GPU**: NVIDIA GB10
- **VRAM**: ~120 GB
- **Driver/CUDA**: CUDA 12.1+ capability (detected as 12.1 compatible)
- **PyTorch**: 2.9.1+cu130

## Benchmark Results

| Configuration | Precision | Loading Time | VRAM Usage (Est.) | Pros | Cons |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Quantized** | 4-bit (NF4) | 7m 26s | ~15-25 GB | Low VRAM usage | Slower load (CPU overhead), minor quality loss |
| **Native** | bfloat16 | 7m 03s | ~70 GB | **Faster load**, Max quality | High VRAM usage |

## Analysis
1.  **Loading Speed**: Native `bfloat16` loading was **faster** (~23 seconds) than 4-bit loading. This is likely because the 4-bit quantization process ("on-the-fly" quantization) incurs CPU overhead that outweighs the I/O benefits of reading smaller weights, or simply because the I/O bottleneck remains dominant for this model size.
2.  **VRAM Capacity**: The GB10 has 120 GB of VRAM. The full `bfloat16` model requires approximately 70 GB. This leaves ~50 GB of free memory, which is more than sufficient for the Operating System, context window (KV cache), and other overheads.
3.  **Quality**: 4-bit quantization can introduce minor precision loss. For a code review tool where detecting subtle bugs and security vulnerabilities is critical, maintaining full 16-bit precision is preferred.

## Conclusion & Configuration
**Winner: Native `bfloat16`**

We have configured `codereview.py` to use the following settings for maximum performance and quality:
- **Precision**: `torch.bfloat16`
- **Attention**: `attn_implementation="sdpa"` (Scaled Dot Product Attention)
- **Format**: `use_safetensors=True`
- **Optimization**: `low_cpu_mem_usage=True`
- **Loading**: `local_files_only=True` (assumes model is cached)

This configuration provides the best balance of quality and speed for this specific hardware setup.
