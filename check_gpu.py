import torch
import sys

print(f"Python: {sys.version.split()[0]}")
print(f"PyTorch: {torch.__version__}")

if torch.cuda.is_available():
    print(f"\nSUCCESS: CUDA is available.")
    print(f"Device Name: {torch.cuda.get_device_name(0)}")
    print(f"Device Capability: {torch.cuda.get_device_capability(0)}")
    
    # Simple tensor test
    try:
        x = torch.tensor([1.0, 2.0]).cuda()
        print(f"Tensor on GPU: {x}")
        print("Basic GPU computation verification passed.")
    except Exception as e:
        print(f"FAILED to move tensor to GPU: {e}")
else:
    print("\nWARNING: CUDA is NOT available. PyTorch is using CPU.")
    print("Please ensure you have installed the correct version of PyTorch for your CUDA drivers.")

