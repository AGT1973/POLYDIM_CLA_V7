# ============================================================================
# POLYDIM V761 — GPU TRITON GEODESIC KERNEL (S^(D-1) RODRIGUES ENGINE)
# AMD ROCm / NVIDIA CUDA Compatible | 2-Pass Compensated Geodesic Stream
# ============================================================================

import math
import numpy as np

try:
    import torch
    import triton
    import triton.language as tl
    HAS_TRITON = True
except ImportError:
    HAS_TRITON = False

if HAS_TRITON:
    @triton.jit
    def _rodrigues_reduction_kernel(
        y_ptr, u_ptr, v_ptr,
        partial_yu_ptr, partial_yv_ptr,
        partial_uu_ptr, partial_vv_ptr,
        D,
        BLOCK_SIZE: tl.constexpr
    ):
        pid = tl.program_id(axis=0)
        block_start = pid * BLOCK_SIZE
        offsets = block_start + tl.arange(0, BLOCK_SIZE)
        mask = offsets < D

        y = tl.load(y_ptr + offsets, mask=mask, other=0.0)
        u = tl.load(u_ptr + offsets, mask=mask, other=0.0)
        v = tl.load(v_ptr + offsets, mask=mask, other=0.0)

        yu_sum = tl.sum(y * u, axis=0)
        yv_sum = tl.sum(y * v, axis=0)
        uu_sum = tl.sum(u * u, axis=0)
        vv_sum = tl.sum(v * v, axis=0)

        tl.store(partial_yu_ptr + pid, yu_sum)
        tl.store(partial_yv_ptr + pid, yv_sum)
        tl.store(partial_uu_ptr + pid, uu_sum)
        tl.store(partial_vv_ptr + pid, vv_sum)

    @triton.jit
    def _rodrigues_stream_update_kernel(
        y_ptr, u_ptr, v_ptr, y_out_ptr,
        alpha, beta,
        D,
        BLOCK_SIZE: tl.constexpr
    ):
        pid = tl.program_id(axis=0)
        block_start = pid * BLOCK_SIZE
        offsets = block_start + tl.arange(0, BLOCK_SIZE)
        mask = offsets < D

        y = tl.load(y_ptr + offsets, mask=mask, other=0.0)
        u = tl.load(u_ptr + offsets, mask=mask, other=0.0)
        v = tl.load(v_ptr + offsets, mask=mask, other=0.0)

        y_out = y + alpha * u + beta * v
        tl.store(y_out_ptr + offsets, y_out, mask=mask)

def execute_gpu_rodrigues(
    y_tensor: 'torch.Tensor',
    u_tensor: 'torch.Tensor',
    v_tensor: 'torch.Tensor',
    theta: float
) -> 'torch.Tensor':
    """Executes S^(D-1) Rodrigues rotation on GPU via Triton."""
    if not HAS_TRITON:
        raise RuntimeError("Triton not installed on current execution node.")

    D = y_tensor.numel()
    BLOCK_SIZE = 1024
    num_blocks = triton.cdiv(D, BLOCK_SIZE)

    partial_yu = torch.empty((num_blocks,), dtype=torch.float64, device=y_tensor.device)
    partial_yv = torch.empty((num_blocks,), dtype=torch.float64, device=y_tensor.device)
    partial_uu = torch.empty((num_blocks,), dtype=torch.float64, device=y_tensor.device)
    partial_vv = torch.empty((num_blocks,), dtype=torch.float64, device=y_tensor.device)

    # Pass 1: Reduction
    grid = (num_blocks,)
    _rodrigues_reduction_kernel[grid](
        y_tensor, u_tensor, v_tensor,
        partial_yu, partial_yv, partial_uu, partial_vv,
        D, BLOCK_SIZE=BLOCK_SIZE
    )

    yu = partial_yu.sum().item()
    yv = partial_yv.sum().item()

    # Pass 2: Exact Versine Geodesic Computation
    half_theta = 0.5 * theta
    sn_half = math.sin(half_theta)
    vers = 2.0 * sn_half * sn_half
    sn = math.sin(theta)

    alpha = -vers * yu + sn * yv
    beta = -vers * yv - sn * yu

    y_out = torch.empty_like(y_tensor)
    _rodrigues_stream_update_kernel[grid](
        y_tensor, u_tensor, v_tensor, y_out,
        alpha, beta,
        D, BLOCK_SIZE=BLOCK_SIZE
    )
    return y_out
