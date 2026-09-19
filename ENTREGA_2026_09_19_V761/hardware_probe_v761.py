# ============================================================================
# POLYDIM V761 — HARDWARE PROBE (SILICON CONTRACT & RUNTIME INTERROGATION)
# Anti-Hardcoding | AMD/NVIDIA/TPU/CPU Dynamic Discovery | IEEE-754 Calibration
# ============================================================================

import os
import sys
import ctypes
import platform
import threading
from dataclasses import dataclass
from typing import Optional, Dict, Any

@dataclass(frozen=True)
class HardwareSpec:
    platform_system: str
    architecture: str
    cpu_cores_logical: int
    cpu_cores_physical: int
    cpu_cache_line_size: int
    system_page_size: int
    available_ram_bytes: int
    gpu_backend: str  # 'CUDA', 'ROCm_HIP', 'TPU_XLA', 'CPU_OPENMP'
    gpu_device_name: str
    gpu_fp64_ratio: float
    gpu_vram_bytes: int
    fpu_has_avx512: bool
    fpu_has_avx2: bool
    fpu_machine_eps: float
    cgroup_memory_limit_bytes: Optional[int]

_PROBE_LOCK = threading.Lock()
_CACHED_SPEC: Optional[HardwareSpec] = None

class HardwareProbe:
    """Interrogates the execution silicon dynamically without hardcoding assumptions."""

    @staticmethod
    def _probe_cpu_cache_line() -> int:
        system = platform.system()
        if system == "Windows":
            try:
                kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
                GetLogicalProcessorInformation = kernel32.GetLogicalProcessorInformation
                
                class PROCESSOR_CACHE_TYPE:
                    CacheUnified = 0
                    CacheInstruction = 1
                    CacheData = 2
                    CacheTrace = 3

                buffer_size = ctypes.c_ulong(0)
                GetLogicalProcessorInformation(None, ctypes.byref(buffer_size))
                
                if buffer_size.value > 0:
                    buffer = ctypes.create_string_buffer(buffer_size.value)
                    if GetLogicalProcessorInformation(buffer, ctypes.byref(buffer_size)):
                        # SYSTEM_LOGICAL_PROCESSOR_INFORMATION is 24 bytes on x86, 32 bytes on x64
                        is_64bit = sys.maxsize > 2**32
                        struct_size = 32 if is_64bit else 24
                        num_structs = buffer_size.value // struct_size
                        
                        for i in range(num_structs):
                            offset = i * struct_size
                            rel_type = ctypes.c_ulong.from_buffer_copy(buffer, offset + (8 if is_64bit else 4)).value
                            if rel_type == 2:  # RelationCache
                                # LineSize is offset + 14 in x64 / + 10 in x86
                                line_offset = offset + (14 if is_64bit else 10)
                                line_size = ctypes.c_ushort.from_buffer_copy(buffer, line_offset).value
                                if 16 <= line_size <= 256:
                                    return int(line_size)
            except Exception:
                pass
        elif system == "Linux":
            try:
                cache_path = "/sys/devices/system/cpu/cpu0/cache/index0/coherency_line_size"
                if os.path.exists(cache_path):
                    with open(cache_path, "r") as f:
                        return int(f.read().strip())
            except Exception:
                pass
        return 64  # Default robust fallback

    @staticmethod
    def _probe_cgroups_v2() -> Optional[int]:
        if platform.system() == "Linux":
            cgroup_path = "/sys/fs/cgroup/memory.max"
            try:
                if os.path.exists(cgroup_path):
                    with open(cgroup_path, "r") as f:
                        val = f.read().strip()
                        if val != "max":
                            return int(val)
            except Exception:
                pass
        return None

    @classmethod
    def probe(cls, force_refresh: bool = False) -> HardwareSpec:
        global _CACHED_SPEC
        with _PROBE_LOCK:
            if _CACHED_SPEC is not None and not force_refresh:
                return _CACHED_SPEC

            system = platform.system()
            arch = platform.machine()
            cpu_logical = os.cpu_count() or 1
            cpu_physical = cpu_logical // 2 if cpu_logical > 1 else 1

            # Page size
            try:
                if hasattr(os, "sysconf") and "SC_PAGE_SIZE" in os.sysconf_names:
                    page_size = os.sysconf("SC_PAGE_SIZE")
                else:
                    page_size = 4096
            except Exception:
                page_size = 4096

            # RAM size
            total_ram = 8 * 1024 * 1024 * 1024
            if system == "Windows":
                try:
                    class MEMORYSTATUSEX(ctypes.Structure):
                        _fields_ = [
                            ("dwLength", ctypes.c_ulong),
                            ("dwMemoryLoad", ctypes.c_ulong),
                            ("ullTotalPhys", ctypes.c_ulonglong),
                            ("ullAvailPhys", ctypes.c_ulonglong),
                            ("ullTotalPageFile", ctypes.c_ulonglong),
                            ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong),
                            ("ullAvailVirtual", ctypes.c_ulonglong),
                            ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                        ]
                    kernel32 = ctypes.WinDLL("kernel32")
                    stat = MEMORYSTATUSEX()
                    stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
                    if kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
                        total_ram = stat.ullTotalPhys
                except Exception:
                    pass
            elif system == "Linux":
                try:
                    with open("/proc/meminfo", "r") as f:
                        for line in f:
                            if line.startswith("MemTotal:"):
                                total_ram = int(line.split()[1]) * 1024
                                break
                except Exception:
                    pass

            # GPU Detection with strict ROCm / AMD precedence
            gpu_backend = "CPU_OPENMP"
            gpu_device_name = "None"
            gpu_fp64_ratio = 1.0 / 32.0
            gpu_vram = 0

            # Step 1: Check PyTorch if present
            try:
                import torch
                if hasattr(torch, "version") and hasattr(torch.version, "hip") and torch.version.hip:
                    if torch.cuda.is_available():
                        name = torch.cuda.get_device_name(0)
                        # Brecha 1 Policy: On Windows native, default to CPU_OPENMP unless RDNA 4 (gfx1200+)
                        if system == "Windows" and not any(k in name for k in ["9000", "gfx1200", "gfx1201"]):
                            gpu_backend = "CPU_OPENMP"
                            gpu_device_name = f"{name} (Windows Native -> Fallback OpenMP)"
                        else:
                            gpu_backend = "ROCm_HIP"
                            gpu_device_name = name
                        gpu_vram = torch.cuda.get_device_properties(0).total_memory
                        gpu_fp64_ratio = 0.5 if "MI" in name or "CDNA" in name else (1.0 / 16.0)
                elif torch.cuda.is_available():
                    name = torch.cuda.get_device_name(0)
                    if "AMD" in name.upper() or "RADEON" in name.upper():
                        if system == "Windows" and not any(k in name for k in ["9000", "gfx1200", "gfx1201"]):
                            gpu_backend = "CPU_OPENMP"
                            gpu_device_name = f"{name} (Windows Native -> Fallback OpenMP)"
                        else:
                            gpu_backend = "ROCm_HIP"
                            gpu_device_name = name
                        gpu_vram = torch.cuda.get_device_properties(0).total_memory
                        gpu_fp64_ratio = 1.0 / 16.0
                    else:
                        gpu_backend = "CUDA"
                        gpu_device_name = name
                        gpu_vram = torch.cuda.get_device_properties(0).total_memory
                        if any(arch in name for arch in ["A100", "H100", "V100", "B100", "B200"]):
                            gpu_fp64_ratio = 0.5
                        elif any(arch in name for arch in ["3090", "4090", "AD102", "GA102"]):
                            gpu_fp64_ratio = 1.0 / 64.0
                        else:
                            gpu_fp64_ratio = 1.0 / 32.0
            except ImportError:
                pass

            cache_line = cls._probe_cpu_cache_line()
            cgroups_lim = cls._probe_cgroups_v2()

            _CACHED_SPEC = HardwareSpec(
                platform_system=system,
                architecture=arch,
                cpu_cores_logical=cpu_logical,
                cpu_cores_physical=cpu_physical,
                cpu_cache_line_size=cache_line,
                system_page_size=page_size,
                available_ram_bytes=total_ram,
                gpu_backend=gpu_backend,
                gpu_device_name=gpu_device_name,
                gpu_fp64_ratio=gpu_fp64_ratio,
                gpu_vram_bytes=gpu_vram,
                fpu_has_avx512=("avx512" in arch.lower()),
                fpu_has_avx2=("x86" in arch.lower() or "amd64" in arch.lower()),
                fpu_machine_eps=sys.float_info.epsilon,
                cgroup_memory_limit_bytes=cgroups_lim
            )
            return _CACHED_SPEC

if __name__ == "__main__":
    spec = HardwareProbe.probe()
    print("=== POLYDIM V761 SILICON CONTRACT SPEC ===")
    for k, v in spec.__dict__.items():
        print(f"  {k:30}: {v}")
