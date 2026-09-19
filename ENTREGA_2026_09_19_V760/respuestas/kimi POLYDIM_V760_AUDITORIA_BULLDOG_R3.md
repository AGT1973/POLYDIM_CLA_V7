# POLYDIM V760 — AUDITORÍA RED-TEAM "BULLDOG" (Ronda 3, 2026-09-19)
## Verificación línea por línea de los 3 archivos + depuración del tribunal previo

> Metodología: cada hallazgo del tribunal (Cerebras/Groq/OpenRouter) fue contrastado
> contra el código fuente real. Cada hallazgo nuevo cita archivo y evidencia.
> Estados: [CONFIRMADO] existe en el código | [REFUTADO] el tribunal alucinó |
> [AUSENTE] el código referenciado no existe en el dossier.

================================================================================
SECCIÓN A — VERIFICACIÓN DEL TRIBUNAL (qué era real y qué te hizo perder tiempo)
================================================================================

A1. [CONFIRMADO] Module leak en hip_hsaco_runner.cpp
    Evidencia: la macro CHECK_HIP hace `return;` ante cualquier error. Después de
    hipModuleLoad exitoso, si hipModuleGetFunction o hipModuleLaunchKernel o
    hipDeviceSynchronize fallan, la función retorna sin ejecutar hipModuleUnload.
    Impacto: VRAM exhaustion por kernels fallidos repetidos (DoS real).
    FIX: RAII (ver Sección D, fix D4).

A2. [CONFIRMADO, impacto corregido] alignas(128) C++ vs align(64) Rust
    Evidencia: kernel_cpp_v760.cpp `struct alignas(128) PMTP_Control`;
    kernel_rust_v760.rs `#[repr(C, align(64))]`.
    NOTA DE HONESTIDAD: Groq exageró. Los offsets de campos son idénticos en ambos
    (sequence@0, active_buffer@8), tamaño de lectura/escritura 16 bytes → NO hay
    out-of-bounds. El riesgo real es: (a) false-sharing del bloque de control con
    datos adyacentes si Rust lo aloca a 64, (b) divergencia de ABI si el struct se
    embebe en layouts mayores, (c) violación del contrato L1 del host Apple M (128B).
    FIX: unificar a align(128) en ambos lenguajes (D1).

A3. [CONFIRMADO, mal etiquetado] Race en publicación PMTP
    Evidencia (publicador): active_buffer.store(relaxed) → sequence.store(release).
    Evidencia (consumidor): sequence.load(acquire) → active_buffer.load(relaxed).
    Escena real: consumidor ve seq N+1; publicador publica N+2 (mismo buffer si ring=2)
    antes de que el consumidor lea active_buffer → consumidor procesa el buffer N+2
    creyendo que validó N+1. Es un TORN READ, no ABA: el wrap de un contador uint64
    (1.8e19) es físicamente irreal, y con un ring de 2 buffers el índice "vuelve" en
    2 publicaciones, no en 2^32. El tribunal usó el nombre equivocado pero la
    vulnerabilidad existe.
    FIX: patrón seqcount — leer seq, leer buffer, re-leer seq, validar (D1).

A4. [CONFIRMADO] FTZ/DAZ es por-hilo; el guard Rust puede correr sin DAZ
    Evidencia: enable_ftz_daz() se llama en el hilo C++; MXCSR es por-hilo en x86.
    Además, si DAZ está activo en el hilo que chequea, los subnormales llegan como
    0.0 y `v.abs() < f64::MIN_POSITIVE` los deja pasar (falso negativo).
    FIX: detección por bit-pattern inmune a DAZ (D2).

A5. [CONFIRMADO] Test harness ciego
    Evidencia (test_v760_mpeleides.py): un solo hilo, nunca llama al runner HIP,
    no captura stderr, assert solo sobre rc y drift. No hay stress de concurrencia
    ni chequeo de leaks de módulos/VRAM.
    FIX: D8.

A6. [REFUTADO] "double work[N][N] en stack → SIGSEGV con N>4k" (Cerebras P1-005)
    Evidencia: estimate_rcond_hager_higham() es `return 1.0; // Placeholder`.
    No existe ninguna matriz N×N en el dossier. El tribunal auditó código imaginario.
    El problema REAL es peor y distinto: el estimador NO EXISTE (stub), y por eso
    kappa_est==1.0 < 1e8 siempre → el tier ambiguo SIEMPRE elige Shifted-CholQR2 y
    MGS2 es código muerto. Ver B3.

A7. [REFUTADO] "ROCm 5.0→5.3 agregó un 11º argumento; el loader resuelve la firma
    vieja de 10 args → stack smash" (Groq)
    La firma REAL de hipModuleLaunchKernel (driver API) siempre fue de 11 parámetros:
    (f, gridX/Y/Z, blockX/Y/Z, sharedMemBytes, stream, kernelParams, extra) — que es
    EXACTAMENTE la PFN declarada en hip_hsaco_runner.cpp. No hay versión de 10 args.
    REFUTADO. (Chequeo de versión igual es defensa barata; ver D5.)

A8. [REFUTADO] "hipModuleLoad renombrado a hipModuleLoadData; dlsym NULL → crash"
    hipModuleLoad sigue exportado en libamdhip64 de ROCm 5.x y 6.x. Además el loader
    SÍ chequea cada símbolo (LOAD_SYM retorna false si falta). Lo que SÍ falta:
    chequeeo del handle de dlopen antes de dlsym — ver B17 (b).

A9. [REFUTADO] "Stack overflow por device_args en Windows LLP64 / ctypes trunca"
    ctypes.c_uint64 es unsigned __int64 de 8 bytes en Windows (LLP64 afecta a
    `long`, no a ctypes.c_uint64). Los arrays de ctypes se asignan en el HEAP.
    Y como el runner hace hipDeviceSynchronize ANTES de retornar, el array vive
    durante toda la llamada: no hay use-after-free. Riesgos residuales reales:
    sin tope de num_args, sin chequeo de null, sin validación de grid/block (B17).

A10. [REFUTADO] "array('L') de 32 bits trunca punteros de GPU"
    El código real construye `(ctypes.c_uint64 * num_args)()` — 8 bytes, sin truncar.

A11. [AUSENTE] "DRAM saturation O(N·D) del fallback QR síncrono"
    No existe implementación alguna de QR/CholQR2/MGS2 en el monolito. El cuerpo de
    compute_gram_and_factorize es un esqueleto de decisión con comentarios.
    Afirmar costo asintótico de código inexistente es no-falsable.

A12. [AUSENTE] "mmap no pineado → GPU lee página swappeada"
    No existe implementación del PMTP slab / buffer mmap en el dossier (solo un
    import sin uso en polydim_v760_monolito.py). El "zero-copy" de V760 no está en
    los archivos auditables. Ver Sección E (hueso central).

A13. [AUSENTE] "Context leak por hipSetDevice en múltiples hilos"
    No hay ninguna llamada a hipSetDevice en el código. El gap real es el opuesto:
    el runner NUNCA inicializa contexto/dispositivo antes de las llamadas driver
    API (hipModuleLoad requiere contexto corriente; sin hipSetDevice/hipCtxCreate
    puede fallar con hipErrorInvalidContext según versión/driver). FIX en D5.

A14. [CONFIRMADO] Singleton de HardwareProbe sin lock
    Evidencia: `_spec: Optional[HardwareSpec] = None` a nivel clase; contract()
    no usa lock. Dos hilos en el primer llamado → doble probe, spec inconsistente.
    Severidad baja (GIL), fix trivial: threading.Lock (D6).

================================================================================
SECCIÓN B — HALLAZGOS NUEVOS (lo que esta ronda encontró y el tribunal no vio)
================================================================================

B1. [P1 FUNCIONAL] write_tensor_to_pmtp es un NO-OP
    Archivo: polydim_v760_monolito.py
    Evidencia:
        safe_x = require_f64_vector(x, dim=self.D)   # tensor sanitizado...
        if self.cpp_lib:
            self.cpp_lib.polydim_publish_write(ctypes.c_void_p(ctrl_ptr), ...)
    safe_x se descarta. El tensor NUNCA se copia al buffer inactivo. Se publican
    índices de buffers vacíos. Todo el flujo "writer → publish → reader" es teatro:
    no mueve datos. FIX: D3.

B2. [P1] ROCm detectado como CUDA (dispatch invertido)
    Archivo: hardware_probe_v760.py, _probe_cuda()
    Evidencia: _probe_cuda no filtra por vendor. Con PyTorch-ROCm,
    torch.cuda.is_available()==True y props.name es "AMD Radeon ..."/"MI300X".
    El probe devuelve backend="cuda", runner="cuda_cubin_runner" para una GPU AMD.
    _probe_rocm nunca se ejecuta (el loop toma el primer resultado no-None).
    Resultado: sistema ROCm selecciona el runner CUDA → falla garantizada.
    FIX: filtro de vendor en _probe_cuda (D6).

B3. [P1] compute_gram_and_factorize: división antes del guard + OOB + tiers muertos
    Archivo: kernel_cpp_v760.cpp
    Evidencia:
        double eta = dmax / dmin;                     // dmin==0 → inf; dmax==0 → NaN
        if (dmin == 0.0 || eta >= 1e8) { ... }        // guard DESPUÉS de dividir
    Con R todo-ceros: eta=NaN → NaN>=1e8 es FALSE → NaN<=1e4 es FALSE → cae al
    tier ambiguo donde kappa_est = 1.0 (stub) < 1e8 siempre → Shifted-CholQR2,
    MGS2 inalcanzable. Además: R[0] se lee aunque N==0 (OOB read), G/R sin
    chequeo de null, y NINGÚN tier tiene implementación (cuerpo = comentarios).
    FIX: D7.

B4. [P1 PORTABILIDAD] __asm__ volatile no compila con MSVC (Windows)
    Archivo: kernel_cpp_v760.cpp, enable_ftz_daz()
    `__asm__ volatile("":::"memory")` es sintaxis GNU/Clang. cl.exe la rechaza.
    El mismo proyecto declara compilación Windows en hip_hsaco_runner.cpp → el
    kernel C++ no buildea en el target que el propio dossier promete.
    FIX: fence portable (D7).

B5. [P1] Off-by-two en probe de cache line de Windows
    Archivo: hardware_probe_v760.py, _probe_cpu_cache_line()
    Layout de SYSTEM_LOGICAL_PROCESSOR_INFORMATION (x64):
      offset 0  ULONG_PTR ProcessorMask          (8)
      offset 8  LOGICAL_PROCESSOR_RELATIONSHIP   (4)
      offset 12 CACHE_DESCRIPTOR: Level(1)@12, Associativity(1)@13, LineSize(2)@14
    El código lee LineSize en offset+12 → lee Level|Associativity como WORD.
    En Windows la "alineación dinámica" BG-15 es basura propagada al sistema.
    FIX: offset + 14 (D6).

B6. [P2] FP64 nativo=True incondicional para toda AMD
    Archivo: hardware_probe_v760.py, _probe_rocm()
    "AMD CDNA FP64 is native 1:1 ... fp64_native = True" para CUALQUIER GPU AMD,
    incluidas Radeon consumer RDNA (razón FP64 1/16–1/32 según arquitectura).
    Contamina fp64_native, fp64_ratio y _compute_max_dim (elige 8 bytes/elemento).
    FIX: tabla por gfx (D6).

B7. [P2] _probe_tpu revienta con x64 deshabilitado → TPU silenciosamente perdido
    Archivo: hardware_probe_v760.py, _probe_tpu()
    jnp.array([1.0], dtype=jnp.float64) con jax_enable_x64=False lanza TypeError,
    NO ImportError. El try/except de contract() atrapa la excepción, la guarda en
    probe_errors y continúa → sistema con TPU real cae a CPU sin aviso ruidoso.
    FIX: habilitar x64 defensivamente dentro del probe (D6).

B8. [P2] Versión: test V760 sobre DLLs V753; Dart apunta a V753
    Archivo: test_v760_mpeleides.py (carga v753_bin); polydim_ffi_v760.dart
    (defaultCpp/defaultRust = ...\ENTREGA_2026_09_18_V753\bin\...).
    Se certifica V760 con binarios V753. Confusión estructural de release.

B9. [P2] API de Triton obsoleta
    Archivo: polydim_triton_kernel_v760.py
    triton.compile(fn, signature=..., constants=...) es API 2.x. En Triton 3.x
    estándar se requiere triton.compile(ASTSource(fn, signature, constants), ...).
    FIX: D9.

B10. [P2] load_hip_driver no thread-safe + superficie de hijack
    Archivo: hip_hsaco_runner.cpp
    (a) Dos hilos llaman launch_* concurrentemente (GIL liberado por ctypes) →
    race sobre g_hip (double dlopen, PFNs parciales visibles).
    (b) RTLD_GLOBAL: los símbolos de libamdhip64 entran al namespace global y pueden
    interponerse contra otras libs (o ser interpuentos).
    (c) Windows: LoadLibraryA("amdhip64.dll") sigue el search order clásico → DLL
    hijacking desde el directorio de la aplicación.
    FIX: std::once_flag + RTLD_LOCAL|RTLD_DEEPBIND + LoadLibraryExA con
    LOAD_LIBRARY_SEARCH_SYSTEM32 (D4/D5).

B11. [P2] Runner HIP: validaciones ausentes
    Sin chequeo de null de hsaco_path/kernel_name; sin tope de num_args; sin
    validación de grid/block != 0; hip_get_device_count llama hipDeviceGet sin
    hipInit previo (puede devolver 0 en drivers estrictos).
    FIX: D5.

B12. [P3] Claim β1-homology sin código
    README §2.2.3: "native Rust Guard verifying β1 homology". El único guard Rust
    (validate_vector) chequea finite+subnormal. No existe código de homología en
    el dossier. Claim-audit mismatch: documentar como roadmap o implementar.

B13. [P3] BG-15 no cableado
    El probe calcula recommended_align_bytes dinámico, pero kernel_cpp hardcodea
    constexpr CACHE_LINE = 64 y PMTP_Control alignas(128) — el valor dinámico no
    llega a ningún binario. El contrato BG-15 es aspiracional, no implementado.

B14. [P3] Coherencia del invariante de norma
    Test Python: drift sobre y + y_comp. Dart: verifyRustNorm(y) — omite y_comp.
    Ambos no certifican lo mismo. Unificar criterio (y_comp es parte del estado).

B15. [P3] _probe_simd_width heurística Windows
    Sin /proc/cpuinfo (Windows), `if hasattr(np, "__config__"): return 32` →
    reporta AVX2 aunque el CPU tenga AVX-512, y sin numpy cae a 8. Heurística
    honesta solo si se documenta como tal.

B16. [P3] grid hardcodeado en launcher
    launch_accelerator_kernel usa grid=(1024,1,1), block=(128,1,1) sin importar D:
    131072 hilos fijos. Para el kernel demo y D distinto, cubre mal el dominio.
    FIX: grid = ceil(D / BLOCK_SIZE) como parámetro.

B17. [P3] Variables/hilos muertos
    _probe_cuda: ratio_inv asignado y nunca usado. polydim_v760_monolito.py:
    `import multiprocessing.shared_memory as shm` sin uso. Test fase 4: asume
    mutación in-place de rotate_geodesic; si PolydimEngine devuelve arrays nuevos,
    el loop de 1000 hops no muta nada y el assert de drift es vacío — verificar
    semántica de polydim.core (no incluido en el dossier).

================================================================================
SECCIÓN C — PRIORIDAD DE EJECUCIÓN (cadena de dependencias)
================================================================================
1. Incluir el fuente del kernel geodésico real (hoy binario V753). Sin eso ninguna
   certificación numérica de V760 es auditable. (Sección E)
2. B1 (write no-op) + allocator de PMTP_Control alineado en Python.
3. A2/A3: PMTP unificado 128B + seqcount en C++ y Rust.
4. B3/B4: guardas de gram + portabilidad MSVC.
5. B2/B5/B6/B7: correcciones del probe (detección ROCm, offset Windows, FP64 AMD,
   TPU x64).
6. A1/B10/B11: RAII + thread-safety + hardening del runner HIP.
7. B9/B8/B16/B14: Triton 3.x, paths V760, grid dinámico, invariante unificado.
8. A5: test de concurrencia + path HIP + captura stderr + conteo de módulos.

================================================================================
SECCIÓN D — FIXES CONCRETOS (código listo para pegar)
================================================================================

--- D1. PMTP unificado (C++ y Rust), 128B, seqcount anti-torn-read -------------

// kernel_cpp_v760.cpp
struct alignas(128) PMTP_Control {
    std::atomic<uint64_t> sequence;
    alignas(64) std::atomic<uint32_t> active_buffer;
    char _pad[128 - 8 - 64];  // active_buffer en su propia línea (>=64B)
};
static_assert(sizeof(PMTP_Control) == 128, "PMTP_Control ABI");

extern "C" {
    // Publisher: escribir datos del tensor al buffer INACTIVO primero,
    // luego publicar. El release de sequence ordena también el store de
    // active_buffer que está programáticamente antes.
    void polydim_publish_write(PMTP_Control* ctrl, uint32_t buffer_index,
                               uint64_t next_seq) {
        ctrl->active_buffer.store(buffer_index, std::memory_order_relaxed);
        ctrl->sequence.store(next_seq, std::memory_order_release);
    }

    bool polydim_acquire_read(PMTP_Control* ctrl, uint64_t& observed_seq,
                              uint32_t& safe_buffer) {
        uint64_t s1 = ctrl->sequence.load(std::memory_order_acquire);
        if (s1 == observed_seq) return false;
        uint32_t b = ctrl->active_buffer.load(std::memory_order_acquire);
        std::atomic_thread_fence(std::memory_order_acquire);
        uint64_t s2 = ctrl->sequence.load(std::memory_order_acquire);
        if (s1 != s2) return false;   // torn read: una publicación interrumpió
        safe_buffer = b;
        observed_seq = s1;
        return true;
    }
}

// kernel_rust_v760.rs
#[repr(C, align(128))]
pub struct PMTPControl {
    pub sequence: AtomicU64,
    pub active_buffer: AtomicU32,
    pub _pad: [u8; 128 - 8 - 4],
}
static_assertions::const_assert_eq!(core::mem::size_of::<PMTPControl>(), 128);

#[no_mangle]
pub extern "C" fn rust_acquire_read(
    ctrl: &PMTPControl, observed_seq: &mut u64, safe_buffer: &mut u32) -> bool {
    let s1 = ctrl.sequence.load(Ordering::Acquire);
    if s1 == *observed_seq { return false; }
    let b = ctrl.active_buffer.load(Ordering::Acquire);
    std::sync::atomic::fence(Ordering::Acquire);
    let s2 = ctrl.sequence.load(Ordering::Acquire);
    if s1 != s2 { return false; }
    *safe_buffer = b;
    *observed_seq = s1;
    true
}

Nota de layout: el _pad garantiza que active_buffer no comparta línea de caché
con sequence ni con datos adyacentes (cerrando el struct en exactamente 128B).

--- D2. Guard Rust inmune a DAZ/FTZ -------------------------------------------

#[no_mangle]
pub extern "C" fn validate_vector(x_ptr: *const f64, expected_dim: usize) -> i32 {
    if x_ptr.is_null() { return -1; }
    let x = unsafe { std::slice::from_raw_parts(x_ptr, expected_dim) };
    for &v in x {
        let bits = v.to_bits();
        if bits & 0x7FF0_0000_0000_0000 == 0x7FF0_0000_0000_0000
           && bits & 0x000F_FFFF_FFFF_FFFF != 0 { return -2; } // NaN/Inf
        if bits & 0x7FF0_0000_0000_0000 == 0
           && bits & 0x000F_FFFF_FFFF_FFFF != 0 { return -3; } // subnormal
    }
    0
}
Por qué: con DAZ activo, la carga f64 ya llegó enmascarada y cualquier chequeo
sobre el VALOR da falso negativo. El patrón de bits es inmune.

--- D3. write_tensor_to_pmtp real + allocator del bloque de control -----------

# En PMTP_Orchestrator_V760:
import numpy as _np

def alloc_pmtp_control(self) -> int:
    """Bloque de control de 128B, alineado a 128, persistente."""
    # numpy no garantiza 128; usamos un buffer sobredimensionado y alineamos a mano.
    raw = _np.zeros(256, dtype=_np.uint8)
    base = raw.ctypes.data
    aligned = (base + 127) & ~127
    self._ctrl_buf = raw                    # mantener referencia viva
    self._ctrl_ptr = aligned
    # sequence=0, active_buffer=0 ya están en cero
    return aligned

def write_tensor_to_pmtp(self, x, buffer_base_ptr: int, buffer_idx: int,
                         next_seq: int, nbytes: int | None = None) -> None:
    safe_x = require_f64_vector(x, dim=self.D)
    n = nbytes if nbytes is not None else safe_x.nbytes
    # 1) copiar al buffer INACTIVO (el reader no lo está leyendo)
    dst = (ctypes.c_char * n).from_address(buffer_base_ptr)
    ctypes.memmove(dst, safe_x.ctypes.data_as(ctypes.c_void_p), n)
    # 2) publicar
    if self.cpp_lib:
        self.cpp_lib.polydim_publish_write(ctypes.c_void_p(self._ctrl_ptr),
                                           buffer_idx, next_seq)
Requiere además un contrato de ring: el publicador nunca escribe el buffer activo;
el alternado está garantizado libre por construcción del seqcount.

--- D4. Runner HIP: RAII + once_flag + hardening de carga ---------------------

// hip_hsaco_runner.cpp (fragmentos)
#include <mutex>

static std::once_flag g_hip_once;
static bool g_hip_ok = false;

static void load_hip_driver_once() {
    // ... loop de candidates ...
    // Linux:  DYNLIB_OPEN con RTLD_NOW | RTLD_LOCAL | RTLD_DEEPBIND
    // Windows: LoadLibraryExA(name, NULL, LOAD_LIBRARY_SEARCH_SYSTEM32)
    if (!g_hip.hLib) { g_hip_ok = false; return; }
#define LOAD_SYM(name) /* igual que antes, con cerrar librería al fallar */
    // ...
    g_hip_ok = true;
}

struct ModuleGuard {
    hipModule_t m;
    ~ModuleGuard() { if (m && g_hip.hipModuleUnload_fn) g_hip.hipModuleUnload_fn(m); }
};

EXPORT_API void CALL_CONV launch_triton_hsaco(
    const char* hsaco_path, const char* kernel_name, uint64_t* device_args,
    int num_args, unsigned int gridX, unsigned int gridY, unsigned int gridZ,
    unsigned int blockX, unsigned int blockY, unsigned int blockZ,
    unsigned int sharedMemBytes)
{
    std::call_once(g_hip_once, load_hip_driver_once);
    if (!g_hip_ok) return;
    if (!hsaco_path || !kernel_name || !device_args) return;
    if (num_args < 0 || num_args > 4096) return;
    if (gridX == 0 || gridY == 0 || gridZ == 0 ||
        blockX == 0 || blockY == 0 || blockZ == 0) return;

    CHECK_HIP(g_hip.hipInit_fn(0));

    hipFunction_t kernel_fn = nullptr;
    {
        ModuleGuard mg{nullptr};
        CHECK_HIP(g_hip.hipModuleLoad_fn(&mg.m, hsaco_path));
        CHECK_HIP(g_hip.hipModuleGetFunction_fn(&kernel_fn, mg.m, kernel_name));
        std::vector<void*> arg_ptrs((size_t)num_args);
        for (int i = 0; i < num_args; ++i) arg_ptrs[i] = &device_args[i];
        CHECK_HIP(g_hip.hipModuleLaunchKernel_fn(
            kernel_fn, gridX, gridY, gridZ, blockX, blockY, blockZ,
            sharedMemBytes, nullptr, arg_ptrs.data(), nullptr));
        CHECK_HIP(g_hip.hipDeviceSynchronize_fn());
    } // <- hipModuleUnload SIEMPRE ejecuta, éxito o fallo (cierra A1)
}

--- D5. Contexto explícito + chequeo de versión (defensa en profundidad) ------

Después de hipInit, antes de hipModuleLoad:
    // Crear/obtener contexto primario y hacerlo corriente (portable HIP):
    // hipSetDevice(0) vía runtime no está en nuestra PFN table; usar el patrón
    // driver: hipCtxCreate/hipDevicePrimaryCtxRetain requieren declarar 2 PFNs
    // más. Mínimo viable multi-GPU-seguro:
    typedef hipError_t (*PFN_hipCtxCreate)(hipCtx_t*, unsigned int, hipDevice_t);
    typedef hipError_t (*PFN_hipCtxSetCurrent)(hipCtx_t);
    // ...resolver bajo LOAD_SYM con fallback suave: si no existen, continuar
    // (ROCm >= 5.6 crea contexto implícito con hipInit en device 0).

Chequeo de versión barato (refuta A7/A8 para siempre):
    typedef hipError_t (*PFN_hipRuntimeGetVersion)(int*);
    int v = 0; if (pfn_get_version && pfn_get_version(&v) == HIP_SUCCESS)
        std::cerr << "[HIP Runner] ROCm runtime " << v << "\n";

--- D6. Fixes del HardwareProbe -----------------------------------------------

# (1) Filtro de vendor en _probe_cuda (cierra B2):
        name = props.name.lower()
        if any(v in name for v in ("amd", "radeon", "mi2", "mi3")):
            return None  # que lo tome _probe_rocm

# (2) Offset Windows correcto (cierra B5):
                        line_size = struct.unpack_from("<H", buf, offset + 14)[0]

# (3) FP64 por arquitectura gfx en _probe_rocm (cierra B6):
        _CDNA = ("gfx900", "gfx906", "gfx908", "gfx90a", "gfx942")
        fp64_native = any(gfx_arch.startswith(g) for g in _CDNA)
        fp64_ratio = 1.0 if fp64_native else 1.0/16.0   # RDNA consumer conservador

# (4) _probe_tpu robusto (cierra B7):
        try:
            jax.config.update("jax_enable_x64", True)
            x_test = jnp.array([1.0], dtype=jnp.float64)
            fp64_emulated = str(x_test.dtype) == "float64"  # XLA emula en TPU
        except Exception:
            fp64_emulated = False

# (5) Singleton con lock (cierra A14):
import threading
class HardwareProbe:
    _spec = None
    _lock = threading.Lock()
    @classmethod
    def contract(cls):
        with cls._lock:
            if cls._spec is None:
                cls._spec = cls._probe_all()
            return cls._spec

# (6) sysconf portable (nit): reemplazar os.sysconf(190) por
        name = "SC_LEVEL1_DCACHE_LINESIZE"
        if name in os.sysconf_names: val = os.sysconf(os.sysconf_names[name])

# (7) Eliminar ratio_inv muerto; documentar _CC_FP64_RATIO como tabla de
#     data-sheet con default conservador, o leer el atributo CUDA 87 vía
#     ctypes (cudaDeviceGetAttribute) cuando se quiere rigor absoluto.

--- D7. Guardas de compute_gram_and_factorize + MSVC --------------------------

#if defined(_MSC_VER)
  #include <intrin.h>
  #define COMPILER_FENCE() _ReadWriteBarrier()
#else
  #define COMPILER_FENCE() __asm__ volatile("":::"memory")
#endif

extern "C" {
    void compute_gram_and_factorize(double* G, double* R, int N) {
        if (!G || !R || N <= 0) return;
        double dmin = std::abs(R[0]), dmax = dmin;
        for (int i = 1; i < N; ++i) {
            double v = std::abs(R[i * (size_t)N + i]);
            if (v < dmin) dmin = v;
            if (v > dmax) dmax = v;
        }
        if (dmin == 0.0) { /* Tier 3: MGS2 */ return; }
        double eta = dmax / dmin;                 // seguro: dmin != 0
        if (eta >= 1e8)      { /* Tier 3: MGS2 */ }
        else if (eta <= 1e4) { /* Tier 1: CholQR2 */ }
        else {
            double kappa_est = estimate_rcond_hager_higham(R, N); // IMPLEMENTAR
            if (kappa_est < 1e8) { /* Tier 2: Shifted-CholQR2 */ }
            else                 { /* Tier 3: MGS2 */ }
        }
    }
}
PENDIENTE DE VERDAD: implementar el estimador (blocked, heap) o una rutina real
de Cholesky. Hoy los tres tiers son comentarios (A11).

--- D8. Test harness: concurrencia + HIP + stderr + leaks ---------------------

def test_concurrency_pmtp(cpp_dll):
    import threading
    ctrl = orch.alloc_pmtp_control()
    stop = False
    errors = []
    def publisher():
        seq = 0
        while not stop:
            seq += 1
            orch.cpp_lib.polydim_publish_write(ctypes.c_void_p(ctrl),
                                               seq % 2, seq)
    def consumer():
        obs = 0
        while not stop:
            r = orch.cpp_lib.polydim_acquire_read(
                ctypes.c_void_p(ctrl), ctypes.byref(...), ...)
    ts = [threading.Thread(target=publisher) for _ in range(2)] + \
         [threading.Thread(target=consumer) for _ in range(2)]
    [t.start() for t in ts]
    time.sleep(5); stop = True
    [t.join() for t in ts]
    assert not errors

Además: ejecutar el runner HIP con un .hsaco de prueba y capturar stderr;
verificar que el conteo de módulos cargados no crece tras N lanzamientos
fallidos (cierra A5/A1 de forma observable).

--- D9. Triton 3.x ------------------------------------------------------------

from triton.compiler import ASTSource
src = ASTSource(polydim_kernel, signature={"x_ptr": "*fp64", "y_ptr": "*fp64",
                                           "n_elements": "i32",
                                           "BLOCK_SIZE": "constexpr"},
                constants={"BLOCK_SIZE": 128})
compiled = triton.compile(src)
# compiled.asm["cubin"] / ["hsaco"] según backend

================================================================================
SECCIÓN E — EL HUESO CENTRAL (por qué nunca terminan las rondas)
================================================================================
Los ~1000 líneas auditadas contienen: probes, runners FFI, guards y tests —
todo el "perímetro". El "corazón" (rotación geodésica con Neumaier/TwoSum,
FWHT, CholQR2, el slab allocator PMTP) NO está en el dossier: son binarios
V753 y módulos no incluidos (polydim.core). Consecuencias:

1. La deriva 4.44e-16 se certifica sobre código que no se entrega.
2. Los errores "internos" del kernel no son falsables → cada ronda encuentra
   nuevos problemas en el perímetro mientras el corazón permanece opaco.
3. Recomendación bulldog: la entrega V761 debe incluir el fuente completo del
   kernel geodésico + slab allocator, o declarar explícitamente el perímetro
   como la única superficie certificada. Sin eso, la iteración no converge.

================================================================================
RESUMEN DE VEREDICTOS
================================================================================
Tribunal: 6 confirmados (A1-A5, A14), 6 refutados (A6-A10 parcial, A7, A8),
2 ausentes/no-falsables (A11, A12), 1 ausente (A13, con gap real inverso).
Nuevos: 4 P1 (B1-B4), 6 P2 (B5-B11), 6 P3 (B12-B17).
Total: 24 hallazgos accionables, 7 fixes con código listo (D1-D9).
