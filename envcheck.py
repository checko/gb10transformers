import torch
import transformers

print(f"CUDA Available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"GPU Name: {torch.cuda.get_device_name(0)}")
    # Check if you have enough memory for the 120B model
    total_mem = torch.cuda.get_device_properties(0).total_memory / (1024**3)
    print(f"Total Unified Memory: {total_mem:.2f} GB")

    if total_mem < 80:
        print("⚠️ Warning: You might need heavy quantization for the 120B model.")
    else:
        print("✅ Hardware looks great for large models!")
else:
    print("❌ CUDA is not available. Check your installation.")
