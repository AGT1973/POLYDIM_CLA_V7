// ============================================================================
// POLYDIM V761 — AMD ROCm/HIP DYNAMIC RUNNER
// Dynamic Loader for .hsaco binary code objects on AMD CDNA/RDNA architectures
// ============================================================================

#include <cstdint>
#include <cstring>
#include <cstdio>
#include <string>
#include <vector>
#include <mutex>

#if defined(_WIN32)
  #include <windows.h>
  #define DYNLIB_HANDLE HMODULE
  #define DYNLIB_OPEN(p) LoadLibraryExA((p), NULL, LOAD_WITH_ALTERED_SEARCH_PATH)
  #define DYNLIB_SYM(h,s) GetProcAddress((HMODULE)(h), (s))
  #define DYNLIB_CLOSE(h) FreeLibrary((HMODULE)(h))
  #define POLYDIM_EXPORT __declspec(dllexport)
  #define POLYDIM_CALL __cdecl
#else
  #include <dlfcn.h>
  #define DYNLIB_HANDLE void*
  #define DYNLIB_OPEN(p) dlopen((p), RTLD_NOW | RTLD_LOCAL)
  #define DYNLIB_SYM(h,s) dlsym((h), (s))
  #define DYNLIB_CLOSE(h) dlclose((h))
  #define POLYDIM_EXPORT __attribute__((visibility("default")))
  #define POLYDIM_CALL
#endif

enum HipRunnerStatus {
    HIP_RUNNER_SUCCESS = 0,
    HIP_RUNNER_ERR_DRIVER_NOT_FOUND = -1001,
    HIP_RUNNER_ERR_INIT_FAILED = -1002,
    HIP_RUNNER_ERR_MODULE_LOAD = -1003,
    HIP_RUNNER_ERR_FUNC_LOOKUP = -1004,
    HIP_RUNNER_ERR_LAUNCH_FAILED = -1005,
    HIP_RUNNER_ERR_BAD_ARGUMENT = -1006
};

typedef int hipError_t;
typedef void* hipModule_t;
typedef void* hipFunction_t;
typedef void* hipStream_t;
typedef int hipDevice_t;

typedef hipError_t (*PFN_hipInit)(unsigned int);
typedef hipError_t (*PFN_hipDeviceGet)(hipDevice_t*, int);
typedef hipError_t (*PFN_hipModuleLoad)(hipModule_t*, const char*);
typedef hipError_t (*PFN_hipModuleUnload)(hipModule_t);
typedef hipError_t (*PFN_hipModuleGetFunction)(hipFunction_t*, hipModule_t, const char*);
typedef hipError_t (*PFN_hipModuleLaunchKernel)(hipFunction_t, unsigned, unsigned, unsigned, unsigned, unsigned, unsigned, unsigned, hipStream_t, void**, void**);
typedef hipError_t (*PFN_hipDeviceSynchronize)();

class HipDriverBridge {
private:
    DYNLIB_HANDLE handle;
    std::mutex mtx;
    bool initialized;

    PFN_hipInit hipInit_fn;
    PFN_hipDeviceGet hipDeviceGet_fn;
    PFN_hipModuleLoad hipModuleLoad_fn;
    PFN_hipModuleUnload hipModuleUnload_fn;
    PFN_hipModuleGetFunction hipModuleGetFunction_fn;
    PFN_hipModuleLaunchKernel hipModuleLaunchKernel_fn;
    PFN_hipDeviceSynchronize hipDeviceSynchronize_fn;

    HipDriverBridge() : handle(nullptr), initialized(false) {}

public:
    static HipDriverBridge& instance() {
        static HipDriverBridge inst;
        return inst;
    }

    int init() {
        std::lock_guard<std::mutex> lock(mtx);
        if (initialized) return HIP_RUNNER_SUCCESS;

        const char* lib_name = 
#if defined(_WIN32)
            "amdhip64.dll";
#else
            "libamdhip64.so";
#endif
        handle = DYNLIB_OPEN(lib_name);
        if (!handle) {
            return HIP_RUNNER_ERR_DRIVER_NOT_FOUND;
        }

        hipInit_fn = (PFN_hipInit)DYNLIB_SYM(handle, "hipInit");
        hipDeviceGet_fn = (PFN_hipDeviceGet)DYNLIB_SYM(handle, "hipDeviceGet");
        hipModuleLoad_fn = (PFN_hipModuleLoad)DYNLIB_SYM(handle, "hipModuleLoad");
        hipModuleUnload_fn = (PFN_hipModuleUnload)DYNLIB_SYM(handle, "hipModuleUnload");
        hipModuleGetFunction_fn = (PFN_hipModuleGetFunction)DYNLIB_SYM(handle, "hipModuleGetFunction");
        hipModuleLaunchKernel_fn = (PFN_hipModuleLaunchKernel)DYNLIB_SYM(handle, "hipModuleLaunchKernel");
        hipDeviceSynchronize_fn = (PFN_hipDeviceSynchronize)DYNLIB_SYM(handle, "hipDeviceSynchronize");

        if (!hipInit_fn || !hipModuleLoad_fn || !hipModuleLaunchKernel_fn) {
            DYNLIB_CLOSE(handle);
            handle = nullptr;
            return HIP_RUNNER_ERR_INIT_FAILED;
        }

        if (hipInit_fn(0) != 0) {
            return HIP_RUNNER_ERR_INIT_FAILED;
        }

        initialized = true;
        return HIP_RUNNER_SUCCESS;
    }

    int launch(const char* hsaco_path, const char* kernel_name, void** kernel_args, unsigned gx, unsigned gy, unsigned gz, unsigned bx, unsigned by, unsigned bz) {
        if (!hsaco_path || !kernel_name || !kernel_args) return HIP_RUNNER_ERR_BAD_ARGUMENT;
        int status = init();
        if (status != HIP_RUNNER_SUCCESS) return status;

        hipModule_t mod = nullptr;
        if (hipModuleLoad_fn(&mod, hsaco_path) != 0) return HIP_RUNNER_ERR_MODULE_LOAD;

        hipFunction_t func = nullptr;
        if (hipModuleGetFunction_fn(&func, mod, kernel_name) != 0) {
            hipModuleUnload_fn(mod);
            return HIP_RUNNER_ERR_FUNC_LOOKUP;
        }

        hipError_t err = hipModuleLaunchKernel_fn(func, gx, gy, gz, bx, by, bz, 0, nullptr, kernel_args, nullptr);
        if (err != 0) {
            hipModuleUnload_fn(mod);
            return HIP_RUNNER_ERR_LAUNCH_FAILED;
        }

        hipDeviceSynchronize_fn();
        hipModuleUnload_fn(mod);
        return HIP_RUNNER_SUCCESS;
    }
};

extern "C" {
    POLYDIM_EXPORT int POLYDIM_CALL polydim_hip_launch_hsaco(
        const char* hsaco_path,
        const char* kernel_name,
        void** kernel_args,
        unsigned gx, unsigned gy, unsigned gz,
        unsigned bx, unsigned by, unsigned bz
    ) {
        return HipDriverBridge::instance().launch(hsaco_path, kernel_name, kernel_args, gx, gy, gz, bx, by, bz);
    }
}
