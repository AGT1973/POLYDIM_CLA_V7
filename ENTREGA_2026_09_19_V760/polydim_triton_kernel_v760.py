import triton
import triton.language as tl
import json
import os

# ============================================================================
# POLYDIM V760 — TRITON S^{D-1} KERNEL (OFF-PATH COMPILER)
# ============================================================================

@triton.jit
def polydim_kernel(
    x_ptr, y_ptr, n_elements,
    BLOCK_SIZE: tl.constexpr
):
    pid = tl.program_id(axis=0)
    block_start = pid * BLOCK_SIZE
    offsets = block_start + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask)
    tl.store(y_ptr + offsets, x * 2.0, mask=mask)

def compile_off_path(backend="cuda"):
    """
    Off-path kernel compilation: generates .cubin (NVIDIA) or .hsaco (AMD ROCm).
    """
    signature = "*fp64,*fp64,i32"
    compiled = triton.compile(
        polydim_kernel,
        signature=signature,
        constants={"BLOCK_SIZE": 128}
    )
    
    out_dir = "E:/POLYDIM_EINSOF/ENTREGA_2026_09_19_V760/"
    kernel_name = compiled.metadata.name
    
    if backend == "cuda" and "cubin" in compiled.asm:
        cubin_data = compiled.asm["cubin"]
        bin_path = os.path.join(out_dir, f"kernel_{kernel_name}.cubin")
        with open(bin_path, "wb") as f:
            f.write(cubin_data)
        print(f"[OK] CUBIN generated: {bin_path}")
    elif backend == "rocm" and "hsaco" in compiled.asm:
        hsaco_data = compiled.asm["hsaco"]
        bin_path = os.path.join(out_dir, f"kernel_{kernel_name}.hsaco")
        with open(bin_path, "wb") as f:
            f.write(hsaco_data)
        print(f"[OK] HSACO generated: {bin_path}")
        
    manifest = {
        "kernel_name": kernel_name,
        "signature": signature,
        "backend": backend,
        "num_warps": compiled.metadata.num_warps,
        "num_ctas": compiled.metadata.num_ctas,
        "shared_bytes": compiled.metadata.shared,
    }
    manifest_path = os.path.join(out_dir, f"kernel_{kernel_name}_manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=4)
    print(f"[OK] Manifest generated: {manifest_path}")

if __name__ == "__main__":
    compile_off_path()
