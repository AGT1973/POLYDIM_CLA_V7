/**
 * POLYDIM V760 — hip_hsaco_runner.cpp
 * AMD ROCm/HIP Backend: Zero-Copy Tensor Runner (BG-09)
 *
 * Mirrors cuda_cubin_runner_v759.cpp architecture but targets the HIP runtime
 * and loads pre-compiled .hsaco (AMD GPU binary) instead of .cubin.
 *
 * Design constraints (Silicon Contract):
 *   - Dynamic linking via dlopen/LoadLibrary — no compile-time HIP SDK dependency.
 *   - Zero hardcoded GFX arch (e.g., "gfx90a") — arch is embedded in the .hsaco.
 *   - ABI identical to CUDA runner: Python ctypes can swap the DLL transparently.
 *   - FP64 native on AMD CDNA (MI250X/MI300X): 1:1 FP64/FP32 throughput.
 *
 * Compilation:
 *   Linux:
 *     g++ -O3 -fPIC -shared -o hip_hsaco_runner.so hip_hsaco_runner.cpp -ldl
 *   Windows (ROCm 6.x):
 *     cl /O2 /LD /DWINDOWS_PLATFORM hip_hsaco_runner.cpp amdhip64.lib
 *
 * Usage from Python (via HardwareProbe):
 *   runner = ctypes.CDLL("hip_hsaco_runner.so")
 *   runner.launch_triton_hsaco(hsaco_path, kernel_name, args_ptr, n, gx,gy,gz, bx,by,bz, smem)
 */

#include <iostream>
#include <cstdint>
#include <cstring>
#include <vector>

#ifdef WINDOWS_PLATFORM
  #include <windows.h>
  #define DYNLIB_OPEN(path)         LoadLibraryA(path)
  #define DYNLIB_SYM(h, sym)        GetProcAddress((HMODULE)(h), sym)
  #define DYNLIB_CLOSE(h)           FreeLibrary((HMODULE)(h))
  #define DYNLIB_HANDLE             HMODULE
  #define EXPORT_API                __declspec(dllexport)
  #define CALL_CONV                 __cdecl
#else
  #include <dlfcn.h>
  #define DYNLIB_OPEN(path)         dlopen(path, RTLD_NOW | RTLD_GLOBAL)
  #define DYNLIB_SYM(h, sym)        dlsym(h, sym)
  #define DYNLIB_CLOSE(h)           dlclose(h)
  #define DYNLIB_HANDLE             void*
  #define EXPORT_API                __attribute__((visibility("default")))
  #define CALL_CONV
#endif

// ---------------------------------------------------------------------------
// HIP Driver API types (subset required for .hsaco loading)
// We declare these locally to avoid compile-time dependency on ROCm headers.
// ---------------------------------------------------------------------------

typedef int hipError_t;
typedef int hipDevice_t;
typedef void* hipCtx_t;       // HIP does not use explicit contexts (CUDA compat shim)
typedef void* hipModule_t;
typedef void* hipFunction_t;
typedef void* hipStream_t;

#define HIP_SUCCESS 0

// HIP driver API function signatures
typedef hipError_t (*PFN_hipInit)(unsigned int flags);
typedef hipError_t (*PFN_hipDeviceGet)(hipDevice_t* dev, int ordinal);
typedef hipError_t (*PFN_hipModuleLoad)(hipModule_t* module, const char* fname);
typedef hipError_t (*PFN_hipModuleUnload)(hipModule_t module);
typedef hipError_t (*PFN_hipModuleGetFunction)(hipFunction_t* hfunc, hipModule_t hmod, const char* name);
typedef hipError_t (*PFN_hipModuleLaunchKernel)(
    hipFunction_t f,
    unsigned int gridDimX, unsigned int gridDimY, unsigned int gridDimZ,
    unsigned int blockDimX, unsigned int blockDimY, unsigned int blockDimZ,
    unsigned int sharedMemBytes, hipStream_t stream,
    void** kernelParams, void** extra
);
typedef hipError_t (*PFN_hipDeviceSynchronize)(void);
typedef const char* (*PFN_hipGetErrorString)(hipError_t error);

// ---------------------------------------------------------------------------
// Driver state (module-level singleton — matches cuda_cubin_runner pattern)
// ---------------------------------------------------------------------------

struct HIPDriverState {
    DYNLIB_HANDLE hLib = nullptr;
    bool          loaded = false;

    PFN_hipInit                  hipInit_fn                  = nullptr;
    PFN_hipDeviceGet             hipDeviceGet_fn             = nullptr;
    PFN_hipModuleLoad            hipModuleLoad_fn            = nullptr;
    PFN_hipModuleUnload          hipModuleUnload_fn          = nullptr;
    PFN_hipModuleGetFunction     hipModuleGetFunction_fn     = nullptr;
    PFN_hipModuleLaunchKernel    hipModuleLaunchKernel_fn    = nullptr;
    PFN_hipDeviceSynchronize     hipDeviceSynchronize_fn     = nullptr;
    PFN_hipGetErrorString        hipGetErrorString_fn        = nullptr;
};

static HIPDriverState g_hip;

// ---------------------------------------------------------------------------
// Dynamic loader — tries candidate library names in order
// ---------------------------------------------------------------------------

static bool load_hip_driver() {
    if (g_hip.loaded) return true;

    // Candidate library names (ROCm 5.x/6.x on Linux, Windows ROCm preview)
    static const char* candidates[] = {
        "libamdhip64.so",       // ROCm 6.x Linux canonical
        "libamdhip64.so.6",     // ROCm 6.x versioned
        "libamdhip64.so.5",     // ROCm 5.x versioned
        "amdhip64.dll",         // Windows ROCm
        nullptr
    };

    for (const char** cand = candidates; *cand != nullptr; ++cand) {
        g_hip.hLib = DYNLIB_OPEN(*cand);
        if (g_hip.hLib) {
            std::cerr << "[HIP Runner] Loaded: " << *cand << "\n";
            break;
        }
    }

    if (!g_hip.hLib) {
        std::cerr << "[HIP Runner] FATAL: libamdhip64.so not found. "
                     "Install ROCm 5.x or 6.x and set LD_LIBRARY_PATH.\n";
        return false;
    }

#define LOAD_SYM(name) \
    g_hip.name##_fn = (PFN_##name)DYNLIB_SYM(g_hip.hLib, #name); \
    if (!g_hip.name##_fn) { \
        std::cerr << "[HIP Runner] Missing symbol: " #name "\n"; \
        return false; \
    }

    LOAD_SYM(hipInit)
    LOAD_SYM(hipDeviceGet)
    LOAD_SYM(hipModuleLoad)
    LOAD_SYM(hipModuleUnload)
    LOAD_SYM(hipModuleGetFunction)
    LOAD_SYM(hipModuleLaunchKernel)
    LOAD_SYM(hipDeviceSynchronize)
    LOAD_SYM(hipGetErrorString)

#undef LOAD_SYM

    g_hip.loaded = true;
    return true;
}

// ---------------------------------------------------------------------------
// Error check macro (prints and aborts — matches CUDA runner severity)
// ---------------------------------------------------------------------------

#define CHECK_HIP(call)                                                         \
    do {                                                                         \
        hipError_t _err = (call);                                                \
        if (_err != HIP_SUCCESS) {                                               \
            const char* msg = g_hip.hipGetErrorString_fn                         \
                              ? g_hip.hipGetErrorString_fn(_err) : "unknown";    \
            std::cerr << "[HIP Runner] FATAL Error " << _err << " (" << msg     \
                      << ") at " << __FILE__ << ":" << __LINE__ << "\n";         \
            std::cerr.flush();                                                   \
            /* Return instead of abort to let Python handle the failure */       \
            return;                                                              \
        }                                                                        \
    } while (0)

// ---------------------------------------------------------------------------
// PUBLIC ABI — identical signature to cuda_cubin_runner for transparent swap
// ---------------------------------------------------------------------------

extern "C" {

/**
 * launch_triton_hsaco
 *
 * Load a pre-compiled AMD .hsaco (equivalent to CUDA .cubin) and launch
 * the specified kernel with the provided arguments.
 *
 * Parameters (ABI-identical to launch_triton_cubin):
 *   hsaco_path   : path to the .hsaco file on disk
 *   kernel_name  : mangled kernel name (from Triton manifest JSON)
 *   device_args  : array of 64-bit device pointers / scalar args (BG-07: no LLP64 truncation)
 *   num_args     : length of device_args
 *   gridX/Y/Z    : HIP grid dimensions
 *   blockX/Y/Z   : HIP block dimensions
 *   sharedMemBytes: dynamic shared memory in bytes
 */
EXPORT_API void CALL_CONV launch_triton_hsaco(
    const char* hsaco_path,
    const char* kernel_name,
    uint64_t*   device_args,
    int         num_args,
    unsigned int gridX,  unsigned int gridY,  unsigned int gridZ,
    unsigned int blockX, unsigned int blockY, unsigned int blockZ,
    unsigned int sharedMemBytes
) {
    // --- 1. Lazy driver load ---
    if (!g_hip.loaded) {
        if (!load_hip_driver()) {
            std::cerr << "[HIP Runner] Cannot proceed: HIP driver unavailable.\n";
            return;
        }
    }

    // --- 2. Initialize HIP runtime ---
    CHECK_HIP(g_hip.hipInit_fn(0));

    // HIP does not require explicit device context management like CUDA.
    // The device is selected via hipSetDevice (not needed if device 0 is default).
    // Omit cuDevicePrimaryCtxRetain — HIP manages context internally.

    // --- 3. Load .hsaco module ---
    hipModule_t   module   = nullptr;
    hipFunction_t kernel_fn = nullptr;

    CHECK_HIP(g_hip.hipModuleLoad_fn(&module, hsaco_path));
    CHECK_HIP(g_hip.hipModuleGetFunction_fn(&kernel_fn, module, kernel_name));

    // --- 4. ABI-safe pointer packing (BG-07: all args are uint64_t, never truncated) ---
    std::vector<void*> arg_ptrs(static_cast<size_t>(num_args));
    for (int i = 0; i < num_args; ++i) {
        arg_ptrs[i] = &device_args[i];
    }

    // --- 5. Kernel launch ---
    CHECK_HIP(g_hip.hipModuleLaunchKernel_fn(
        kernel_fn,
        gridX, gridY, gridZ,
        blockX, blockY, blockZ,
        sharedMemBytes,
        nullptr,            // stream (nullptr = default stream)
        arg_ptrs.data(),    // kernelParams (pointer array)
        nullptr             // extra (HIP extra launch params)
    ));

    // --- 6. Anti-Tautology synchronization barrier ---
    // Mandatory: ensures kernel completes and traps any async memory faults
    // before Python reads back results. No optional sync allowed (Regla 16-a).
    CHECK_HIP(g_hip.hipDeviceSynchronize_fn());

    // --- 7. Module unload (avoid VRAM leaks on repeated calls) ---
    if (g_hip.hipModuleUnload_fn && module) {
        g_hip.hipModuleUnload_fn(module);
    }
}

/**
 * hip_get_device_name
 * Utility: returns device name string for HardwareProbe integration.
 * Called once during HardwareProbe._probe_rocm() if rocminfo is unavailable.
 */
EXPORT_API int CALL_CONV hip_get_device_count() {
    if (!load_hip_driver()) return 0;
    // hipGetDeviceCount is exposed in libamdhip64 as a runtime (not driver) API.
    // Use hipDeviceGet probe: try ordinals 0..7, count how many succeed.
    int count = 0;
    hipDevice_t dev;
    for (int i = 0; i < 8; ++i) {
        if (g_hip.hipDeviceGet_fn(&dev, i) == HIP_SUCCESS)
            ++count;
        else
            break;
    }
    return count;
}

} // extern "C"

// ---------------------------------------------------------------------------
// Optional: standalone smoke-test (compiled as executable, not DLL)
// g++ -DHIP_RUNNER_STANDALONE -o hip_runner_test hip_hsaco_runner.cpp -ldl
// ---------------------------------------------------------------------------

#ifdef HIP_RUNNER_STANDALONE
int main(int argc, char** argv) {
    if (argc < 3) {
        std::cerr << "Usage: hip_runner_test <path/to/kernel.hsaco> <kernel_name>\n";
        return 1;
    }

    std::cout << "[HIP Smoke Test] Loading driver...\n";
    if (!load_hip_driver()) return 1;

    std::cout << "[HIP Smoke Test] Device count: " << hip_get_device_count() << "\n";

    // Dummy args (null pointers = kernel will fault, but confirms ABI layer is intact)
    uint64_t dummy_args[3] = {0ULL, 0ULL, 1024ULL};
    std::cout << "[HIP Smoke Test] Attempting launch (expect ABI layer trace)...\n";
    launch_triton_hsaco(
        argv[1], argv[2],
        dummy_args, 3,
        1, 1, 1,   // grid
        64, 1, 1,  // block
        0          // shared mem
    );
    std::cout << "[HIP Smoke Test] Done.\n";
    return 0;
}
#endif // HIP_RUNNER_STANDALONE
