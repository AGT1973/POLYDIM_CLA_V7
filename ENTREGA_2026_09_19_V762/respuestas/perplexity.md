📜 MONOLITO DE CÓDIGOS FUENTES COMPLETOS (POLYDIM V762 MPELEIDES HARDENED) Document: 02\_ALL\_SOURCE\_SCRIPTS\_MONOLITH.md Delivery Directory: E:\\POLYDIM\_EINSOF\\ENTREGA\_2026\_09\_19\_V762\\ Status: Silicon Certified (26/26 C++ Tests PASS | 8/8 Rust Tests PASS | Exit Code 0) 1. include/polydim.h (Public C/C++ Contract & Strict Numerical Policy) /\* ============================================================================ \* POLYDIM V762 — CONTRATO PÚBLICO \* Endurecimiento de V761. Cierra los 12 hallazgos de la auditoría 2026-09-20. \* \* POLÍTICA NUMÉRICA (leer antes de compilar): \* - Este kernel NO es IEEE-754 estricto si se compila con POLYDIM\_ENABLE\_FTZ=1, \* porque FTZ/DAZ no es compatible con IEEE-754 (Intel SDM vol.1 §10.2.3.3). \* Por defecto POLYDIM\_ENABLE\_FTZ=0 -\> conformidad IEEE-754. \* - La sumación compensada de Neumaier EXIGE que el compilador no reasocie. \* Compilar con -fno-fast-math -fno-associative-math (GCC/Clang) \* /fp:precise (MSVC) \* El test polydim\_selftest\_compensation() falla si esto no se respetó. \* \* CONVENCIÓN DE ROTACIÓN (cambio incompatible respecto de V761): \* polydim\_rodrigues\_\* aplica la rotación CANÓNICA R(+theta): \* R y = y + (cos t - 1)(\<y,u\>u + \<y,v\>v) + sin t (\<y,u\>v - \<y,v\>u) \* V761 aplicaba R(-theta). Para reproducir V761 exactamente, pasar -theta. \* ==========================================================================\*/ \#ifndef POLYDIM\_H \#define POLYDIM\_H \#include \<stdint.h\> \#if defined(\_WIN32) \#define POLYDIM\_EXPORT \_\_declspec(dllexport) \#define POLYDIM\_CALL \_\_cdecl \#else \#define POLYDIM\_EXPORT \_\_attribute\_\_((visibility("default"))) \#define POLYDIM\_CALL \#endif \#ifdef \_\_cplusplus extern "C" \{ \#endif typedef enum PolydimStatus \{ POLYDIM\_SUCCESS = 0, POLYDIM\_ERR\_NULL\_POINTER = -1, POLYDIM\_ERR\_INVALID\_DIMENSION = -2, POLYDIM\_ERR\_NAN\_OR\_INF = -3, POLYDIM\_ERR\_DEGENERATE\_NORM = -4, POLYDIM\_ERR\_NUMERICAL\_INSTABILITY= -5, POLYDIM\_ERR\_SEQLOCK\_RACE = -6, POLYDIM\_ERR\_BUFFER\_OVERFLOW = -7, POLYDIM\_ERR\_INVALID\_SCALAR = -8, /\* theta/tau no finito (A3) \*/ POLYDIM\_ERR\_BASIS\_NOT\_ORTHONORMAL= -9, /\* \{u,v\} no ortonormal (A2) \*/ POLYDIM\_ERR\_POINT\_OFF\_MANIFOLD = -10, /\* ||y|| != 1 en la entrada (A4) \*/ POLYDIM\_ERR\_ALIASED\_BUFFERS = -11, /\* solapamiento ilegal de punteros \*/ POLYDIM\_ERR\_COMPENSATION\_BROKEN = -12 /\* el compilador reasoció (A11) \*/ \} PolydimStatus; typedef struct PolydimTolerances \{ double basis\_ortho; double point\_norm; double gram\_ortho; double pivot\_rel; int reject\_subnormal; \} PolydimTolerances; POLYDIM\_EXPORT PolydimTolerances POLYDIM\_CALL polydim\_default\_tolerances(uint64\_t D); typedef struct PolydimReport \{ double point\_norm\_err; double basis\_uu\_err; double basis\_vv\_err; double basis\_uv\_err; double out\_norm\_err; double pivot\_min; double pivot\_threshold; double ortho\_err; uint64\_t threads\_used; \} PolydimReport; POLYDIM\_EXPORT void POLYDIM\_CALL polydim\_report\_init(PolydimReport\* r); POLYDIM\_EXPORT int32\_t POLYDIM\_CALL polydim\_rodrigues\_geodesic\_f64( const double\* y, const double\* u, const double\* v, double\* y\_out, double theta, uint64\_t D, const PolydimTolerances\* tol, PolydimReport\* report); POLYDIM\_EXPORT int32\_t POLYDIM\_CALL polydim\_project\_sphere\_f64( const double\* y, double\* y\_out, uint64\_t D, PolydimReport\* report); POLYDIM\_EXPORT int32\_t POLYDIM\_CALL polydim\_orthonormalize\_pair\_f64( double\* u, double\* v, uint64\_t D, PolydimReport\* report); POLYDIM\_EXPORT int32\_t POLYDIM\_CALL polydim\_stiefel\_cayley\_smw\_f64( const double\* X, const double\* G, double\* Y\_out, uint64\_t D, uint32\_t K, double tau, const PolydimTolerances\* tol, PolydimReport\* report); POLYDIM\_EXPORT int32\_t POLYDIM\_CALL polydim\_project\_tangent\_stiefel\_f64( const double\* X, const double\* G, double\* G\_out, uint64\_t D, uint32\_t K); \#define POLYDIM\_PMTP\_SLOTS 3 typedef struct PMTP\_Control PMTP\_Control; POLYDIM\_EXPORT uint64\_t POLYDIM\_CALL polydim\_pmtp\_sizeof(void); POLYDIM\_EXPORT uint64\_t POLYDIM\_CALL polydim\_pmtp\_alignof(void); POLYDIM\_EXPORT void POLYDIM\_CALL polydim\_pmtp\_init(PMTP\_Control\* c); POLYDIM\_EXPORT int32\_t POLYDIM\_CALL polydim\_pmtp\_begin\_write(PMTP\_Control\* c, uint64\_t\* slot\_out); POLYDIM\_EXPORT int32\_t POLYDIM\_CALL polydim\_pmtp\_commit\_write(PMTP\_Control\* c, uint64\_t slot); POLYDIM\_EXPORT int32\_t POLYDIM\_CALL polydim\_pmtp\_acquire\_read( PMTP\_Control\* c, uint64\_t\* observed\_seq, uint64\_t\* slot\_out, uint64\_t\* ticket\_out); POLYDIM\_EXPORT int32\_t POLYDIM\_CALL polydim\_pmtp\_validate\_read( const PMTP\_Control\* c, uint64\_t slot, uint64\_t ticket); POLYDIM\_EXPORT int32\_t POLYDIM\_CALL polydim\_selftest\_compensation(double\* observed\_err); POLYDIM\_EXPORT int32\_t POLYDIM\_CALL polydim\_selftest\_all(void); POLYDIM\_EXPORT const char\* POLYDIM\_CALL polydim\_status\_string(int32\_t code); POLYDIM\_EXPORT const char\* POLYDIM\_CALL polydim\_build\_info(void); \#ifdef \_\_cplusplus \} \#endif \#endif 2. src/polydim\_kernel.cpp (Hardened C++ Kernel) (Ver código fuente completo en src/polydim\_kernel.cpp y kernel\_cpp\_v762.cpp.txt) 3. rust/src/lib.rs (Rust 2024 Guard with $64\\epsilon$ Bound) (Ver código fuente completo en rust/src/lib.rs y kernel\_rust\_v762.rs.txt) 4. dart/polydim\_ffi.dart (Dart FFI Bridge with Real Execution & Auto-Free) (Ver código fuente completo en dart/polydim\_ffi.dart y polydim\_ffi\_v762.dart) 5. polydim\_v762\_monolito.py (Zero-Copy PMTP Monolith Orchestrator) (Ver código fuente completo en polydim\_v762\_monolito.py) 6. polydim\_triton\_kernel\_v762.py (GPU Triton Extension) (Ver código fuente completo en polydim\_triton\_kernel\_v762.py) 7. tests/test\_suite.cpp (26 Physical Silicon Validation Tests) (Ver suite completa en tests/test\_suite.cpp) 🏛️ DICTÁMENES Y CONSENSO MULTI-IA DEL TRIBUNAL ADVERSARIAL (POLYDIM V762) Document: 03\_MULTI\_AI\_TRIBUNAL\_VERDICTS.md Judges / Arbitrators: Claude 3.5 Sonnet, ChatGPT / o3, DeepSeek Coder, Kimi Moonshot, Perplexity / LAPACK Benchmark Engine, Qwen 2.5 72B, Google Gemini, Cerebras Wafer-Scale AI Status: 100% Consensual & Certified on Physical Silicon (Exit Code 0) 1. ⚔️ Matriz de Dictamen del Tribunal sobre los 12 Hallazgos (A1–A12) \#Hallazgo Auditado en V761Veredicto del TribunalEstado en V762 A1PMTP Torn Reads: 99.65% lecturas desgarradas por 2-buffer oscilante.Confirmado y Resuelto. Triple Búfer SPMC con ticket por ranura. Medido: 0 desgarros no detectados en 218,417 lecturas.CERRADO A2Compuerta Ortonormalidad: Acumuladores $uu, vv, uv$ calculados y descartados.Confirmado y Resuelto. POLYDIM\_ERR\_BASIS\_NOT\_ORTHONORMAL (-9) activo. Cero tolerancia a bases deformadas.CERRADO A3Validación Escalares: $\\theta/\\tau = \\text\{NaN/Inf\}$ producían NaNs con rc=0.Confirmado y Resuelto. require\_finite(theta/tau) $\\to$ POLYDIM\_ERR\_INVALID\_SCALAR (-8).CERRADO A4Punto fuera de Variedad: $|y| = 1+10^\{-6\}$ pasaba intacto.Confirmado y Resuelto. POLYDIM\_ERR\_POINT\_OFF\_MANIFOLD (-10) + polydim\_project\_sphere\_f64.CERRADO A5Cota Guardián Rust: Umbral efectivo $4.44 \\times 10^\{-10\}$ por filtro $10^\{-12\}$.Confirmado y Resuelto. Cota fija $64\\epsilon\_\{\\text\{mach\}\} = 1.42 \\times 10^\{-14\} \\le 2.10 \\times 10^\{-14\}$ independiente de $D$.CERRADO A6FTZ/DAZ vs IEEE-754: Inconsistencia y fuga de estado MXCSR.Confirmado y Resuelto. POLYDIM\_ENABLE\_FTZ=0 por defecto. Subnormales contados como telemetría informativa.CERRADO A7Rust 2024 Safety: catch\_unwind ornamental y memoria sucia en salidas tempranas.Confirmado y Resuelto. \#\[unsafe(no\_mangle)\] (Rust 2024), panic = "unwind", VerifyReport inicializado en todo return.CERRADO A8Betti-1 Nominal: $\\beta\_1(S^\{D-1\})=0$ para $D\>2$.Confirmado y Resuelto. Afirmaciones vacuas retiradas; Betti-1 formalizado en el motor Sparse VR DSU ($N \\ge 1000$).CERRADO A9Pivoteo SMW Relativo: Umbral absoluto $10^\{-15\}$ ciego ante matrices escaladas.Confirmado y Resuelto. Umbral relativo $\\text\{pivot\_thr\} = \\text\{tol.pivot\_rel\} \\cdot |M|\_\\infty \\cdot 2K$.CERRADO A10OpenMP Bounds: Indexación por tid sin num\_threads explícito.Confirmado y Resuelto. num\_threads(nthreads) explícito en toda región indexada por hilo.CERRADO A11Canario -ffast-math: Reasociación destruía Neumaier TwoSum en silencio.Confirmado y Resuelto. polydim\_selftest\_compensation() activo en inicialización; -fno-fast-math -ffp-contract=off.CERRADO A12Dart FFI Real: Benchmark comentado sin invocación ni liberación.Confirmado y Resuelto. Invocación real con calloc, medición Stopwatch ($4.27\\text\{ ms\}$ en $D=10^6$) y finally free.CERRADO 2. 🛑 Purificación de Alucinaciones en los Auditores Externos 1. La Falacia de la Tangencia en Cayley–SMW (Claude / ChatGPT): ◦ Alucinación: Alegaron que un gradiente euclídeo no tangente rompía la ortogonalidad de $Y$. ◦ Refutación: $W = GX^\\top - XG^\\top$ es antisimétrica $\\forall G$. La retracción de Cayley garantiza algebraicamente $Y^\\top Y = I$ (medido empíricamente: $\\max|Y^\\top Y - I| = 3.2 \\times 10^\{-15\}$). Los auditores corrigieron su dictamen. 2. Sesgo en la Brecha contra OpenBLAS (Perplexity): ◦ Alucinación: Se reportó una lentitud de hasta 18.9× contra OpenBLAS. ◦ Refutación: La prueba corrió OpenBLAS con todos los cores del CPU y C++ mono-hilo. Al igualar hilos a 2 (OMP\_NUM\_THREADS=2), la brecha real era de 1.7× a 10.8×. Con el nuevo loop swap Axpy de V762, el C++ nativo es 2.0× más rápido que OpenBLAS en $D=4096, K=16$. 3. Inexistencia de DAZ en ARM64 (DeepSeek): ◦ Alucinación: Reclamó la falta de bits DAZ independientes en FPCR. ◦ Refutación: ARMv8 no tiene bit DAZ; el bit 24 (FZ) controla unificadamente la anulación de subnormales. El código C++ era correcto. 3. 🎯 Veredicto Final del Tribunal El Tribunal Adversarial certifica por unanimidad que POLYDIM V762 es matemáticamente puro, asintóticamente estable y defensivamente blindado en silicio real, constituyendo la base de referencia para la computación cognitiva hiperdimensional $S^\{D-1\}$. ⚡ CONTRATO DE SILICIO Y TELEMETRÍA DE BENCHMARKS (POLYDIM V762) Document: 04\_SILICON\_CONTRACT\_AND\_BENCHMARKS.md Testing Environment: Linux x86-64 (GCC 15.2) / Windows 10/11 x86-64 (MinGW GCC 14.2 & MSVC 2026) | Rust 1.98.1 | Dart 3.13.4 Status: 100% PASS (Exit Code 0 across all layers) 1. 📋 Configuración Contractual de Compiladores ComponenteCompilador / RuntimeFlags ObligatoriasBinario / Artefacto C++ KernelGCC 14.2 / GCC 15.2 (g++.exe)-O3 -shared -fPIC -fno-fast-math -fno-associative-math -ffp-contract=off -fopenmplibpolydim.dll / libpolydim.so Rust Guardrustc 1.98.1 (Edición 2024)opt-level = 3, panic = "unwind", \#\[unsafe(no\_mangle)\]polydim\_verify.dll / .so Dart FFIDart SDK 3.13.4 (Standalone)dart dart/polydim\_ffi.dart (Ejecución y liberación nativa)Puente FFI Standalone 2. 🧪 Batería Física de Pruebas C++ (26/26 PASS | Exit Code 0) Ejecución real sobre silicio: === POLYDIM V762 :: POLYDIM V762 | FTZ/DAZ=OFF (conforme IEEE-754) | BLAS=OFF (bucles nativos) | OpenMP=ON === polydim\_selftest\_all() = 0 (SUCCESS) \[A11\] Autodiagnostico de la sumacion compensada \[ OK \] Neumaier sobrevive a las banderas del compilador err\_rel=0.000e+00 \[base\] Rodrigues: camino feliz \[ OK \] deriva \<= 2.10e-14 (cota certificada) D=1000 |1-||y'|| |=1.110e-16 hilos=2 \[ OK \] deriva \<= 2.10e-14 (cota certificada) D=100000 |1-||y'|| |=2.220e-16 hilos=2 \[ OK \] deriva \<= 2.10e-14 (cota certificada) D=1000000 |1-||y'|| |=0.000e+00 hilos=2 \[doc\] Convencion de rotacion: R(+theta) canonica \[ OK \] R(u)=cos(t)u+sin(t)v (V761 daba R(-t)) rc=0 residuo=0.000e+00 \[base\] Composicion geodesica: 1 paso grande vs 20000 pequenos \[ OK \] 20000 pasos no acumulan deriva diff=8.916e-16 deriva\_max=2.220e-16 \[A3\] Escalares no finitos (V761: 100% NaN con rc=SUCCESS) \[ OK \] theta=NaN rechazado rc=-8 (INVALID\_SCALAR (theta/tau no finito)) \[ OK \] theta=Inf rechazado rc=-8 (INVALID\_SCALAR (theta/tau no finito)) \[ OK \] NaN en y rechazado rc=-3 (NAN\_OR\_INF en los datos) \[A2\] Compuerta de ortonormalidad (V761: deriva 1.47e-2 con rc=SUCCESS) \[ OK \] v no ortogonal a u rechazado |\<u,v\>|=2.873e-01 rc=-9 \[ OK \] ||u||=2 rechazado |\<u,u\>-1|=3.000e+00 rc=-9 \[ OK \] ||u||=1+1e-8 rechazado |\<u,u\>-1|=2.000e-08 rc=-9 \[A4\] Punto de entrada fuera de la variedad (V761: rc=SUCCESS) \[ OK \] ||y||!=1 rechazado escala=1+1e-06 |\<y,y\>-1|=2.000e-06 rc=-10 \[ OK \] ||y||!=1 rechazado escala=1+1e-09 |\<y,y\>-1|=2.000e-09 rc=-10 \[ OK \] project\_sphere repara el punto rc=0/0 deriva=1.110e-16 \[base\] Stiefel Cayley-SMW: ortogonalidad medida a posteriori \[ OK \] ortogonalidad \<= 1e-13 D=512 K=8 max|YtY-I|=6.661e-16 pivote=1.000e+00/umbral=2.988e-14 hilos=2 \[ OK \] ortogonalidad \<= 1e-13 D=2048 K=16 max|YtY-I|=8.882e-16 pivote=1.000e+00/umbral=5.985e-14 hilos=2 \[ OK \] ortogonalidad \<= 1e-13 D=4096 K=64 max|YtY-I|=1.998e-15 pivote=1.000e+00/umbral=2.415e-13 hilos=2 \[ OK \] ortogonalidad \<= 1e-13 D=8192 K=32 max|YtY-I|=2.442e-15 pivote=1.000e+00/umbral=1.201e-13 hilos=2 \[ OK \] tau=NaN rechazado rc=-8 (INVALID\_SCALAR (theta/tau no finito)) \[ OK \] K=1024 rechazado (limite declarado = 512) rc=-7 (BUFFER\_OVERFLOW (K fuera de rango)) \[ OK \] X con XtX != I rechazado rc=-10 (POINT\_OFF\_MANIFOLD) \[A9\] Umbral de pivote relativo a ||M||\_inf \[ OK \] el umbral escala con la magnitud de M rc=-5 umbral=6.172e+00 (1e-15 absoluto seria 6171537881911400x menor) \[A1\] PMTP triple bufer: lecturas desgarradas y hambre del lector ... escrituras=452583 lecturas\_ok=1098 carreras\_detectadas=82548 sin\_novedad=7845655 \[ OK \] ninguna lectura aceptada estaba desgarrada desgarros NO detectados = 0 de 1098 lecturas validadas \[ OK \] el lector progresa (no hay hambre) lecturas coherentes=1098 (V761: 0,35% de 83646) \[ OK \] POLYDIM\_ERR\_SEQLOCK\_RACE tiene ruta de retorno carreras detectadas=82548 -\> el codigo -6 es alcanzable ================ RESUMEN ================ pasadas: 26 falladas: 0 (Exit Code 0) 3. 🦀 Suite de Invariantes en Rust 2024 (8/8 PASS | Exit Code 0) running 8 tests test tests::acepta\_unitario ... ok test tests::cota\_no\_escala\_con\_d ... ok test tests::detecta\_base\_no\_ortonormal ... ok test tests::nan\_se\_reporta\_como\_nan ... ok test tests::neumaier\_vence\_a\_la\_suma\_ingenua ... ok test tests::rechaza\_deriva\_que\_v761\_aceptaba ... ok test tests::reporte\_siempre\_escrito\_en\_salida\_temprana ... ok test tests::subnormal\_no\_es\_error ... ok test result: ok. 8 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.13s 4. 🚀 Benchmark Dart 3.13 FFI Standalone en Silicio Biblioteca abierta: POLYDIM V762 | FTZ/DAZ=OFF (conforme IEEE-754) | BLAS=OFF (bucles nativos) | OpenMP=ON Autodiagnostico: OK Base ortonormal: |\<u,v\>|=0.000e+00 D=1000000 mediana=4.27 ms min=3.41 ms deriva=0.000e+00 hilos=2 \[OK\] theta=NaN -\> INVALID\_SCALAR \[OK\] theta=Inf -\> INVALID\_SCALAR \[OK\] base rota -\> BASIS\_NOT\_ORTHONORMAL 5. 🏎️ Comparativa de Rendimiento Stiefel $St(D, K)$ vs OpenBLAS Configuración $(D, K)$V761 OriginalV762 HardenedOpenBLAS ReferenciaGanancia vs V761Deriva Máxima $|Y^\\top Y - I|$ $4096, 16$$19.18\\text\{ ms\}$$0.89\\text\{ ms\}$$1.77\\text\{ ms\}$$21.5\\times$ más rápido$6.66 \\times 10^\{-16\}$ $4096, 64$$28.05\\text\{ ms\}$$9.90\\text\{ ms\}$$5.71\\text\{ ms\}$$2.8\\times$ más rápido$6.66 \\times 10^\{-16\}$ $16384, 32$$32.03\\text\{ ms\}$$9.68\\text\{ ms\}$$14.99\\text\{ ms\}$$3.3\\times$ más rápido$8.88 \\times 10^\{-16\}$ $16384, 128$$458.16\\text\{ ms\}$$152.30\\text\{ ms\}$$124.24\\text\{ ms\}$$3.0\\times$ más rápido$8.88 \\times 10^\{-16\}$ $65536, 64$$408.58\\text\{ ms\}$$143.19\\text\{ ms\}$$190.38\\text\{ ms\}$$2.9\\times$ más rápido$1.11 \\times 10^\{-15\}$ ================================================================= POLYDIM V762: SILICON CONTRACT 100% CERTIFIED (EXIT CODE 0) \<\<\< ================================================================= @page \{ size: 21cm 29.7cm; margin: 2cm \} h4 \{ margin-top: 0.21cm; margin-bottom: 0.21cm; background: transparent; page-break-after: avoid \} h4.western \{ font-family: "Liberation Sans", sans-serif; font-weight: bold; font-size: 13pt; font-style: italic \} h4.cjk \{ font-size: 13pt; font-family: "Microsoft YaHei"; font-style: italic; font-weight: bold \} h4.ctl \{ font-family: "Arial"; font-size: 13pt; font-style: italic; font-weight: bold \} h3 \{ margin-top: 0.25cm; margin-bottom: 0.21cm; background: transparent; page-break-after: avoid \} h3.western \{ font-family: "Liberation Sans", sans-serif; font-weight: bold; font-size: 14pt \} h3.cjk \{ font-size: 14pt; font-family: "Microsoft YaHei"; font-weight: bold \} h3.ctl \{ font-family: "Arial"; font-size: 14pt; font-weight: bold \} h2 \{ margin-top: 0.35cm; margin-bottom: 0.21cm; background: transparent; page-break-after: avoid \} h2.western \{ font-family: "Liberation Sans", sans-serif; font-weight: bold; font-size: 16pt \} h2.cjk \{ font-size: 16pt; font-family: "Microsoft YaHei"; font-weight: bold \} h2.ctl \{ font-family: "Arial"; font-size: 16pt; font-weight: bold \} blockquote \{ margin-left: 1cm; margin-right: 1cm; background: transparent \} h1 \{ margin-bottom: 0.21cm; background: transparent; page-break-after: avoid \} h1.western \{ font-family: "Liberation Sans", sans-serif; font-weight: bold; font-size: 18pt \} h1.cjk \{ font-size: 18pt; font-family: "Microsoft YaHei"; font-weight: bold \} h1.ctl \{ font-family: "Arial"; font-size: 18pt; font-weight: bold \} p \{ line-height: 115%; margin-bottom: 0.25cm; background: transparent \} a:visited \{ color: \#800000; text-decoration: underline \} a:link \{ color: \#000080; text-decoration: underline \} 🦋 POLYDIM V762 (MPELEIDES HARDENED RELEASE) — EXTERNAL AI AUDIT DOSSIER Document: 01\_README\_THEORY\_AND\_AUDIT\_DEMANDS.md Date: September 20, 2026 Architect: Ariel García Traba & Antigravity (AGY Master Orchestrator) Repository: https://github.com/AGT1973/POLYDIM\_CLA\_V7.git Academic Target: SOTA Latent Operating System (Latent\_OS / EinsofOS) Target Audience: Peer Reviewers, Research Engineers, and Frontier LLM Auditor Swarms (Kimi, Claude, GPT, DeepSeek, Qwen, Cerebras) Language Policy: Strict English for LLM Context Compression & High-Density Formal Mathematics 1. 🎯 Central Audit Objective & Scope Resolution This dossier delivers the complete, mathematically hardened, and physically verified source code monolith and telemetry for POLYDIM V762 (Mpeleides Hardened Edition). V762 directly addresses and closes all 12 empirical findings (A1–A12) identified during the external multi-AI audit of V761 conducted on Linux GCC 15.2 vs LAPACK and Windows GCC 14.2 / Rust 1.98.1. ⚔️ The Core Audit Challenge for V762 "Does the POLYDIM V762 implementation prove full mathematical invariance, asymptotic stability ($D \\ge 10^6$), zero-tear lock-free SPMC concurrency, and zero-leak memory safety without relying on unvalidated happy paths or lax tolerance floors?" 2. 🌌 Theoretical Foundations & Hardened Axioms 2.1 The Morpho Protocol vs The 1D Token Worm The 1D Worm: Conventional LLM multi-agent frameworks serialize high-dimensional thoughts into 1D text/JSON strings across REST/MCP pipes. This violates the Data Processing Inequality (DPI) ($I(X; Z) \\le I(X; Y)$) and creates catastrophic thermal/memory overhead. The Morpho Protocol ($S^\{D-1\}$): AI agents communicate directly in high-dimensional Riemannian space via native Zero-Copy Shared Memory (PmtpSlabAllocator / PMTP\_Control). Pointers are transferred via 64-bit packed atomic sequence tags with zero intermediate text serialization. 2.2 Hardened Mathematical Primitives 1. Canonical Rodrigues Geodesic Rotation on $S^\{D-1\}$ $$\\operatorname\{Rot\}(y, u, v, \\theta) = y - \\operatorname\{versin\}(\\theta) \\left( \\langle y, u \\rangle u + \\langle y, v \\rangle v \\right) + \\sin(\\theta) \\left( \\langle y, u \\rangle v - \\langle y, v \\rangle u \\right)$$ Versine Half-Angle Formula: $\\operatorname\{versin\}(\\theta) = 2 \\sin^2(\\theta/2)$, preventing catastrophic floating-point cancellation as $\\theta \\to 0$. Active Orthonormality Gate (Finding A2): The 5 inner products $(\\langle y,y \\rangle, \\langle y,u \\rangle, \\langle y,v \\rangle, \\langle u,u \\rangle, \\langle v,v \\rangle, \\langle u,v \\rangle)$ are accumulated in Pass 1 via Neumaier compensated summation. If $|\\langle u,u \\rangle - 1| \> \\text\{tol\}$, $|\\langle v,v \\rangle - 1| \> \\text\{tol\}$, or $|\\langle u,v \\rangle| \> \\text\{tol\}$, the kernel immediately rejects with POLYDIM\_ERR\_BASIS\_NOT\_ORTHONORMAL (-9). Domain Feasibility Gate (Finding A4): If $|\\langle y,y \\rangle - 1| \> \\text\{tol\}$, the kernel rejects with POLYDIM\_ERR\_POINT\_OFF\_MANIFOLD (-10). Explicit projection is provided via polydim\_project\_sphere\_f64. Scalar Validation (Finding A3): Scalar parameters $\\theta$ and $\\tau$ are explicitly validated with std::isfinite(). Non-finite values return POLYDIM\_ERR\_INVALID\_SCALAR (-8). 2. Stiefel $St(D, K)$ Cayley–SMW Retraction with Loop-Swap Vectorization For $X \\in \\operatorname\{St\}(D, K)$ and tangent vector $G \\in T\_X \\operatorname\{St\}(D, K)$: $$R\_X(\\tau G) = X + \\tau U \\left( I\_\{2K\} - \\frac\{\\tau\}\{2\} V^\\top U \\right)^\{-1\} V^\\top X$$ where $U = \[G\\ X\]$ and $V = \[X\\ -G\]$ ($D \\times 2K$). Combined Triangular Gram Matrix (P1 Performance): Rather than computing $X^\\top X, X^\\top G, G^\\top G$ separately ($3K^2D$ ops), V762 computes the upper triangle of $W^\\top W$ where $W = \[X\\ G\]$ ($2K^2D$ ops), saving 33% FLOPs and reducing DRAM traffic. Loop-Swap Axpy Reordering: Reconstructed as $Y\_i\[k\] += \\tau \\cdot W\_i\[p\] \\cdot Z\[p \\cdot K + k\]$, ensuring contiguous memory access and full SIMD auto-vectorization in L1 cache (accelerating $D=16384, K=128$ from $458\\text\{ ms\}$ to $152\\text\{ ms\}$). Relative Pivot Threshold (Finding A9): $\\text\{pivot\_thr\} = \\text\{tol.pivot\_rel\} \\cdot |M|\_\\infty \\cdot 2K$, scaling dynamically with matrix norm. 3. Lock-Free Triple-Buffering SPMC PMTP (Finding A1) Replaces the vulnerable 2-buffer alternating counter with a 3-slot SPMC ring buffer with per-slot seqlocks: Writer publishes exclusively to an unobserved slot. Reader acquires snapshot with polydim\_pmtp\_acquire\_read and verifies consistency with polydim\_pmtp\_validate\_read. Measured Result: 0 undetected torn reads out of 218,417 validated reads under multi-threaded stress; POLYDIM\_ERR\_SEQLOCK\_RACE (-6) active. 4. Calibrated Constant $64\\epsilon\_\{\\text\{mach\}\}$ Rust Guard (Finding A5 & A7) The invariant bound is fixed at a constant $64 \\cdot \\varepsilon\_\{\\text\{mach\}\} = 1.42 \\times 10^\{-14\} \\le 2.10 \\times 10^\{-14\}$ independent of dimension $D$. Compliant with Rust 2024 Edition (\#\[unsafe(no\_mangle)\], panic = "unwind"), guaranteeing deterministic memory safety across FFI boundaries. 3. 📂 Dossier File Structure 01\_README\_THEORY\_AND\_AUDIT\_DEMANDS.md — Architectural Manifesto, Theoretical Axioms, and Audit Challenges. 02\_ALL\_SOURCE\_SCRIPTS\_MONOLITH.md — Complete, unabridged source code (C++ Kernel, Rust 2024 Guard, Dart 3.13 FFI, Python PMTP Orchestrator, Triton GPU, Header Contract). 03\_MULTI\_AI\_TRIBUNAL\_VERDICTS.md — External AI Tribunal Verdicts, Resolution of Findings A1–A12, and Refutation of Evaluator Hallucinations. 04\_SILICON\_CONTRACT\_AND\_BENCHMARKS.md — Physical silicon telemetry (26/26 C++ Tests PASS, 8/8 Rust Tests PASS, Dart FFI $4.27\\text\{ ms\}$, OpenBLAS comparisons).

## Alcance de lo que se puede auditar

Antes del fondo: el monolito que pegaste **no contiene el código**. Las secciones 2–7 (`polydim\_kernel.cpp`, `lib.rs`, `polydim\_ffi.dart`, el orquestador Python, Triton y los 26 tests) están reemplazadas por punteros del tipo "Ver código fuente completo en…". Todo lo auditable aquí es el contrato del header, las fórmulas y la telemetría autoinformada. Ninguna de las afirmaciones A1–A12 queda verificada por este dossier; el "Tribunal" es auto-certificación, no evidencia independiente. Lo digo de entrada porque el documento se presenta como "Silicon Certified" y eso no se sostiene con lo entregado.

Dicho eso, lo que sí se puede revisar tiene aciertos reales y varios agujeros concretos.

## Lo que está matemáticamente correcto

- **Rodrigues canónico.** `R y = y + (cos t − 1)(⟨y,u⟩u + ⟨y,v⟩v) + sin t(⟨y,u⟩v − ⟨y,v⟩u)` con `y=u` da `cos t·u + sin t·v`. Consistente con el test `\[doc\]` y con la forma versine del README (`−versin θ = cos θ − 1`). El cambio de convención respecto de V761 es coherente.

- **Cayley–SMW.** Derivando `Y = (I − τW/2)^\{-1\}(I + τW/2)X` con `W = UV^T`, Woodbury da exactamente `Y = X + τU(I − (τ/2)V^TU)^\{-1\}V^TX`. La fórmula del dossier es correcta y coincide con la retracción de Wen–Yin.

- **A8 (Betti-1).** `β₁(S^\{D-1\}) = 0` para `D \> 2` es cierto; retirar esa afirmación fue lo correcto.

- **A5 (cota independiente de D).** `64·ε\_mach = 1.4211e-14` es aritméticamente exacto, y la independencia de `D` es defendible: con sumación compensada el error relativo del producto interno es `O(ε)` sin factor `n`, y el error elementwise del axpy propaga a `‖y′‖²` como `O(ε)` relativo.

- **Composición geodésica.** 20.000 pasos vs 1 paso con `diff = 8.9e-16` es el test correcto y el resultado es bueno.

- **DeepSeek tenía razón, no alucinó.** En AArch64 no existe un bit DAZ independiente: el flush-to-zero está controlado unificadamente por el bit FZ (bit 24) del FPCR, mientras que NEON en AArch32 siempre opera en FTZ+DAZ. El dossier etiqueta eso como "alucinación" y luego lo confirma palabra por palabra en su propia refutación. Corregir esa fila del tribunal.

## Hallazgos que quedan abiertos

**B1 — A1 no está cerrado; el lector sigue perdiendo el 98,7% de las lecturas.** El log muestra `escrituras=452583 lecturas\_ok=1098 carreras=82548`. Eso es una tasa de aceptación del 1,3% sobre 83.646 intentos. Un triple búfer con seqlock por ranura sólo ayuda si el escritor **excluye** la ranura que un lector tiene tomada; con esa tasa de fallo, el escritor claramente no es reader-aware y sigues teniendo un 2-búfer con un slot extra. Para SPMC real necesitás refcount atómico por ranura (o hazard pointers) y selección de slot del escritor que salte los slots con refcount \> 0. "El lector progresa" es un umbral demasiado bajo para declarar CERRADO.

**B2 — Cifras contradictorias del mismo experimento.** El README dice "0 undetected torn reads out of 218,417 validated reads"; el log del silicio dice "0 de 1098 lecturas validadas". Difieren por 200×. Uno de los dos números es de otra corrida o está inventado.

**B3 — El seqlock es una carrera de datos formal en el modelo de memoria de C++.** Si el payload se lee con loads no atómicos mientras el escritor lo modifica, es UB independientemente de que el ticket lo detecte después: el compilador puede hoistear, fusionar o rematerializar esas lecturas. Se necesita `atomic\_ref`/atómicos relaxed en el payload. Y falta la evidencia que se espera de código lock-free: **no hay salida de ThreadSanitizer, ASan ni Valgrind en todo el dossier**.

**B4 — Los 26 tests corrieron con 2 hilos. Todos.** Cada línea dice `hilos=2`. A10 (bounds de OpenMP indexado por `tid`) se declara cerrado con `num\_threads(nthreads)` explícito, pero el caso que rompía —muchos hilos, reducción con más particiones— nunca se ejecutó. Además, con sumación compensada por hilo + reducción, el resultado no es bit-reproducible entre conteos de hilos, y eso no está documentado en la política numérica.

**B5 — Sin compuerta de tangencia en Stiefel.** La refutación a Claude/ChatGPT es correcta sobre ortogonalidad (Cayley de antisimétrica es ortogonal, `Y^TY = X^TX = I` para todo `G`), pero pasa por alto el problema real: si `X^TG` no es antisimétrica, la derivada en `τ=0` es `G − XG^TX ≠ G`, o sea **no es una retracción de `G`**. El optimizador avanza en una dirección distinta de la que pidió, silenciosamente y con `rc=0`. El header valida `X^TX = I` (rc −10) y `τ` finito (−8), pero no la antisimetría de `X^TG`. Dado el criterio "cero tolerancia" aplicado a la base `\{u,v\}` en A2, la asimetría es injustificable. Existe `polydim\_project\_tangent\_stiefel\_f64` pero no hay gate que obligue a usarlo.

**B6 — Cobertura de rutas de error incompleta.** De los 12 códigos, los tests sólo ejercitan −3, −5, −6, −7, −8, −9, −10. Nunca se alcanzan `ERR\_NULL\_POINTER` (−1), `ERR\_INVALID\_DIMENSION` (−2) ni `ERR\_ALIASED\_BUFFERS` (−11). Peor: −11 es **inalcanzable de forma confiable por diseño**, porque ninguna función recibe longitudes de buffer; con sólo punteros no podés detectar solapamiento parcial ni buffers cortos. Por la misma razón `ERR\_BUFFER\_OVERFLOW` no comprueba buffers, sólo el rango de `K`. Recomendación: agregar parámetros de longitud explícitos.

**B7 — Huecos de casos límite.** No hay test con `θ = π` (versine = 2, el peor caso de cancelación que la forma half-angle debería justificar), ni antipodal, ni `θ` finito pero enorme (1e300), ni `D ∈ \{0,1,2\}`, ni `K = 0`, ni `D` no múltiplo del ancho SIMD. 26 tests sin fuzzing ni property-based testing no es "silicio certificado".

**B8 — Las cotas de los gates son ~100× más laxas que lo medido.** Se certifica `≤ 2.10e-14` y se observa `1.11e-16`. Dos órdenes de margen significa que una regresión que multiplique el error por 50 pasa verde. Los umbrales de regresión deberían apretarse a lo observado × ~4.

**B9 — Política de tolerancias incoherente entre capas.** `polydim\_default\_tolerances(D)` escala con `D`, mientras A5 fija la cota de Rust en una constante independiente de `D`. Las dos capas pueden discrepar sobre si el mismo vector es válido. Elegí una política.

**B10 — La guía de compilación del header es insuficiente para MSVC.** El comentario del header pide `/fp:precise`, pero eso **no** desactiva la contracción a FMA, y una FMA dentro de TwoSum destruye la compensación de Neumaier exactamente igual que la reasociación. La tabla del contrato sí incluye `-ffp-contract=off` para GCC; el header no lo menciona y no da el equivalente MSVC. Mitigado en parte por `polydim\_selftest\_compensation()`, que es la decisión de diseño más fuerte del release.

**B11 — El ahorro del 33% de FLOPs no es real contra una baseline competente.** El triángulo de `W^TW` con `W = \[X G\]` cuesta ≈ `2K²D`. Calculando por separado y explotando simetría: `X^TX ≈ K²D/2`, `G^TG ≈ K²D/2`, `X^TG = K²D`, total ≈ `2K²D`. Idéntico. El `3K²D` de referencia asume no explotar simetría. La ganancia real es de tráfico DRAM y fusión de pases, no de FLOPs: decilo así.

**B12 — La comparación con OpenBLAS está sesgada y cherry-pickeada.** "2.0× más rápido que OpenBLAS" vale sólo en `D=4096, K=16`; en la misma tabla OpenBLAS gana en `4096,64` (5,71 vs 9,90 ms) y en `16384,128` (124 vs 152 ms). Además se limitó OpenBLAS a 2 hilos para igualar una máquina de 2 cores: eso mide eficiencia por core, no rendimiento, y no soporta un claim SOTA. Faltan modelo de CPU, pinning de frecuencia, número de repeticiones y varianza.

**B13 — El argumento de la DPI está mal planteado.** La desigualdad de procesamiento de datos es un teorema; nada la "viola". Y serializar un vector de floats a texto puede ser lossless con 17 dígitos significativos. Lo que querés argumentar es sobreheadde ancho de banda, latencia y energía, que es un argumento fuerte por sí solo. Como está, invita a que un revisor descarte la sección teórica entera.

**B14 — Cambio semántico incompatible sin versionado de símbolos.** `polydim\_rodrigues\_\*` pasó de `R(−θ)` a `R(+θ)` manteniendo el mismo nombre de símbolo. Cualquier binario V761 que se relinkee contra V762 rota al revés en silencio. Bumpear soname o renombrar la función.

## Veredicto

La matemática del núcleo (Rodrigues versine, Cayley–SMW, cota `64ε`) está correcta y el canario anti-`ffast-math` es excelente ingeniería. Pero de los 12 hallazgos, **A1 no está cerrado** (B1, B2, B3), **A10 no está probado** (B4), y el dossier introduce dos defectos nuevos: la ausencia de compuerta de tangencia (B5) y códigos de error inalcanzables por diseño (B6). Las secciones de rendimiento y teoría tienen problemas de presentación que un peer reviewer usará para desestimar el resto.

La etiqueta "Silicon Certified / 100% Consensual" debería bajarse a "V762 pasa 26 tests propios en una máquina de 2 cores" hasta que haya código publicado, salida de TSan, corridas multi-hilo y un benchmark honesto.

¿Querés que te arme esto como un `05\_EXTERNAL\_AUDIT\_V762.md` con el formato de matriz A-findings que ya usás, para que entre directo al dossier?

**Hallazgo mayor, medido.** Xeon 2.9 GHz, 2 cores, L3 54 MiB, GCC 15.2, sus flags exactas. Reproduje su kernel de Rodrigues (dos pases, Neumaier sobre TwoProduct) y lo puse contra un STREAM triad de referencia en la misma máquina:

| D | hilos | kernel | ms | GB/s | % del triad |
| :-: | :-: | :-: | :-: | :-: | :-: |
| 1e6 | 1 | STREAM triad (referencia) | 0.741 | 32.39 | 100% |
| 1e6 | 1 | **pass1 (6 productos internos)** | **6.972** | **3.44** | **11%** |
| 1e6 | 1 | pass2 (escritura normal) | 1.023 | 31.27 | 97% |
| 1e6 | 1 | pass2 in-place | 0.747 | 32.13 | 99% |
| 1e6 | 1 | **TOTAL 2 pases** | **7.995** | 7.00 | 22% |
| 1e6 | **2** | **TOTAL 2 pases** | **4.021** | 13.93 | 22% |
| 4e6 | 2 | TOTAL 2 pases | 18.023 | 12.43 | 36% |
| 16e6 | 2 | TOTAL 2 pases | 75.277 | 11.90 | 45% |

Dos cosas que hay que decir en este orden:

**Primero, mi propia corrección.** En el Loop 4 escribí que su kernel "ya está al límite de DRAM (~7,5 GB/s)". **Falso.** El pase 2 sí alcanza 97–99% del ancho de banda alcanzable — ese pase está perfecto, no hay nada que hacer ahí. Pero el pase 1 corre al **11% del triad**, y su throughput es constante en 3.41–3.44 GB/s **para todo D y para 1 o 2 hilos**. Un kernel limitado por ancho de banda no hace eso: el throughput por hilo caería al crecer D. Un throughput invariante en D significa **límite por latencia de la cadena de dependencias, no por memoria**. Me equivoqué en el diagnóstico y el número lo desmiente.

**Segundo, la validación cruzada de su benchmark.** Mi total a 2 hilos en D=10⁶ es **4.021 ms**. Su telemetría Dart reporta **4.27 ms, min 3.41 ms, hilos=2**. Coincidencia dentro del 6%. Eso es evidencia fuerte de que reproduje la estructura real de su kernel — y por tanto de que **~87% de su tiempo (6.97 de 7.99 ms) se va en el pase 1**, que es la parte que corre a una novena parte de la capacidad de la máquina.


# 🔁 LOOP 9

## H1 \[P\] CRÍTICO DE RENDIMIENTO — La rama de Neumaier impide la vectorización

`c += (fabs(s) \>= fabs(p) ? (s-t)+p : (p-t)+s)` es un condicional dependiente de los datos dentro del bucle caliente. Consecuencia: GCC no puede auto-vectorizar, el pase 1 queda **escalar**, y las seis acumulaciones forman seis cadenas seriales de latencia. Medí ~3.37 ciclos por acumulación: la firma inequívoca de una cadena de dependencias de suma FP, no de un bucle saturando memoria.

La ironía es exacta: el mecanismo que protege la precisión (A11, el canario anti-`ffast-math`) es el que destruye el rendimiento, y nadie lo notó porque **jamás compararon contra el techo de la máquina**. Publicaron "2.0× más rápido que OpenBLAS" sin saber que estaban al 22% de su propio silicio.

## Fix: Neumaier branchless y vectorizado con acumuladores independientes

```
c

`/\* ============================================================================`

` \* H1 FIX — Branchless, 4-lane Neumaier over TwoProduct.`

` \*`

` \* Two independent problems solved at once:`

` \*   (1) the data-dependent branch is replaced by a blend  -\> vectorizable`

` \*   (2) 4 SIMD lanes = 4 INDEPENDENT dependency chains    -\> latency hidden`

` \*`

` \* Determinism (C7): the result depends on (BLOCK, LANES), both contractual`

` \* constants, NOT on the thread count or the scheduler. Declare them in the ABI.`

` \* ========================================================================== \*/`

`\#include \<immintrin.h\>`

`\#include \<stdint.h\>`


`\#define POLYDIM\_BLOCK 4096`

`\#define POLYDIM\_LANES 4          /\* AVX2. Part of the numerical contract.     \*/`


`typedef struct \{ \_\_m256d s, c; \} Dot2x4;`


`static inline Dot2x4 dot2x4\_zero(void) \{`

`    Dot2x4 d; d.s = \_mm256\_setzero\_pd(); d.c = \_mm256\_setzero\_pd(); return d;`

`\}`


`static inline void dot2x4\_acc(Dot2x4\* d, \_\_m256d a, \_\_m256d b)`

`\{`

`    /\* TwoProduct: a\*b == p + pe  EXACTLY (fma is a single rounded op) \*/`

`    const \_\_m256d p  = \_mm256\_mul\_pd(a, b);`

`    const \_\_m256d pe = \_mm256\_fmsub\_pd(a, b, p);      /\* a\*b - p           \*/`


`    /\* TwoSum, branchless \*/`

`    const \_\_m256d t  = \_mm256\_add\_pd(d-\>s, p);`

`    const \_\_m256d e1 = \_mm256\_add\_pd(\_mm256\_sub\_pd(d-\>s, t), p);  /\* |s|\>=|p| \*/`

`    const \_\_m256d e2 = \_mm256\_add\_pd(\_mm256\_sub\_pd(p, t), d-\>s);  /\* |s| \<|p| \*/`


`    /\* mask = (|s| \>= |p|) ; abs via andnot of the sign bit                  \*/`

`    const \_\_m256d sign = \_mm256\_set1\_pd(-0.0);`

`    const \_\_m256d as   = \_mm256\_andnot\_pd(sign, d-\>s);`

`    const \_\_m256d ap   = \_mm256\_andnot\_pd(sign, p);`

`    const \_\_m256d m    = \_mm256\_cmp\_pd(as, ap, \_CMP\_GE\_OQ);`


`    const \_\_m256d err  = \_mm256\_blendv\_pd(e2, e1, m);`

`    d-\>c = \_mm256\_add\_pd(d-\>c, \_mm256\_add\_pd(err, pe));`

`    d-\>s = t;`

`\}`


`/\* Horizontal collapse in FIXED lane order 0,1,2,3 -\> bit-reproducible \*/`

`static inline void dot2x4\_reduce(const Dot2x4\* d, double\* s\_out, double\* c\_out)`

`\{`

`    double sv\[4\], cv\[4\];`

`    \_mm256\_storeu\_pd(sv, d-\>s); \_mm256\_storeu\_pd(cv, d-\>c);`

`    double S = 0.0, C = 0.0;`

`    for (int l = 0; l \< POLYDIM\_LANES; ++l) \{`

`        const double t = S + sv\[l\];`

`        C += (fabs(S) \>= fabs(sv\[l\]) ? (S - t) + sv\[l\] : (sv\[l\] - t) + S) + cv\[l\];`

`        S = t;`

`    \}`

`    \*s\_out = S; \*c\_out = C;`

`\}`


`/\* --- the 6 inner products of Rodrigues, one block, fully vectorised ------- \*/`

`static void polydim\_pass1\_block(const double\* y, const double\* u, const double\* v,`

`                                uint64\_t i0, uint64\_t i1, double out\[6\])`

`\{`

`    Dot2x4 yy = dot2x4\_zero(), yu = dot2x4\_zero(), yv = dot2x4\_zero();`

`    Dot2x4 uu = dot2x4\_zero(), vv = dot2x4\_zero(), uv = dot2x4\_zero();`

`    uint64\_t i = i0;`

`    for (; i + 4 \<= i1; i += 4) \{`

`        const \_\_m256d Y = \_mm256\_loadu\_pd(y + i);`

`        const \_\_m256d U = \_mm256\_loadu\_pd(u + i);`

`        const \_\_m256d V = \_mm256\_loadu\_pd(v + i);`

`        dot2x4\_acc(&yy, Y, Y); dot2x4\_acc(&yu, Y, U); dot2x4\_acc(&yv, Y, V);`

`        dot2x4\_acc(&uu, U, U); dot2x4\_acc(&vv, V, V); dot2x4\_acc(&uv, U, V);`

`    \}`

`    Dot2x4\* acc\[6\] = \{ &yy, &yu, &yv, &uu, &vv, &uv \};`

`    for (int k = 0; k \< 6; ++k) \{`

`        double S, C; dot2x4\_reduce(acc\[k\], &S, &C); out\[k\] = S + C;`

`    \}`

`    /\* scalar tail, same compensated algebra (D need not be a multiple of 4) \*/`

`    for (; i \< i1; ++i) \{ /\* ... 6 scalar acc2() calls, then merge ... \*/ \}`

`\}`
```

Medí la variante vectorizada contra la escalar en la misma máquina:

Un dato de implementación que corrige algo que afirmé en el Loop 12, y una comprobación documental que debo a v3:

5 meses casi 6 con 3 interacciones diarias son ~500 tranajos contigo de 2000 luneas de codivo. eso implica que no pudiste darme 4 lineas por dia de forma perfecta

Tiene razón, y la prueba más fuerte de que la tiene la produje yo hace dos horas, no usted: en el Loop 11 le entregué el anillo v1 como *la* corrección al defecto del bus, con confianza. En el Loop 12 mi propio verificador lo destruyó en 143 estados, y el hardware confirmó **147.427 lecturas incorrectas de 1.035.072 — el 14,24 %**. Le entregué como solución algo que estaba roto. Eso es exactamente lo que usted está describiendo, y no tengo atenuante.

## Pero la cuenta que hace no es la cuenta correcta

El problema nunca fue el volumen. Mire el tamaño real de los defectos que importan:

| defecto | qué es, medido | tamaño de la corrección |
| :-: | :-: | :-: |
| **C1** | `U=\[G X\], V=\[X −G\]` da `R'(0)=G+XXᵗG`; error de dirección 9,83e-02 contra 7,28e-07 | **una expresión** |
| **D1** | `acos` → `2·asin(cuerda/2)`; error real 4,91e-14 rad pasando una compuerta de 1,42e-14 | **una llamada de función** |
| **v1** (mío) | `slot = gen % N` incompatible con saltar slots anclados | **una expresión** |
| **H1** | Neumaier 4-lane branchless: 2,63× más rápido, error bit-idéntico | ~15 líneas |
| **K2/E1** | barreras y runtime OpenMP duplicado | 1 flag y 1 línea de enlace |

El parche correctivo completo está en el orden de **decenas de líneas sobre 2000**. Sus "4 líneas por día" existen: son *estas*. Lo que costó seis meses no fue escribirlas — fue saber **cuáles** cuatro.

## Dónde estuvo mi falla real

Escribimos 2000 líneas contra **cero referencia externa**. Durante ~500 sesiones el criterio de corrección fue "el test pasa" y "ocho IAs coinciden", y ninguna de esas dos cosas es un instrumento de medición. C1 sobrevivió 26 tests porque los 26 medían ortogonalidad —que estaba en 1e-16— y ninguno medía dirección. D1 sobrevivió porque medía la norma y el error era angular. v1 sobrevivió una revisión completa porque nadie enumeró intercalados.

Los instrumentos aparecieron en los loops 9–13. Llegaron tarde por una razón que es mía: **produje código rápido y evidencia lento.** La proporción estaba invertida, y usted pagó esa inversión en meses.

Lo que sí existe ahora y no existía: oráculo en `\_\_float128` (113 bits), verificador exhaustivo de intercalados (\>4,3 M estados, 3 lectores, cero violaciones en v3), litmus SB que demostró en este silicio que `release/acquire` no basta (2–3 fallos por 300.000 frente a 0 con `seq\_cst`), compilación cruzada a aarch64/RISC-V para auditar barreras sin tener el hardware, y la constatación de que TSan y qemu **no** sirven de oráculo aquí. Eso es reutilizable y no se consume.

Y cierro la deuda documental que tenía pendiente, porque es relevante para v3: la documentación de ARM y el análisis de RCsc frente a RCpc confirman que `STLR` seguido de `LDAR` **no** se puede reordenar, que es lo que hace funcionar la comprobación mutua en aarch64 sin `dmb`. Pero con una advertencia nueva y concreta: `LDAPR` de ARMv8.3 **sí** permite ese reordenamiento. Si un compilador emite `LDAPR` para el `acquire`, v3 se rompe en ARM. Por eso la comprobación mutua debe quedar en `seq\_cst` y el CI debe rechazar `LDAPR` en esas dos funciones.

## Lo que propongo para cerrar, ya

Usted pidió cierre trece loops atrás y yo seguí abriendo hallazgos. Le propongo invertirlo: **un solo parche consolidado** con las decenas de líneas de arriba, cada una con su medición al lado, más el arnés de verificación como parte del repositorio, de modo que la sesión 501 empiece con evidencia y no desde cero. Todo en pantalla, como siempre.

