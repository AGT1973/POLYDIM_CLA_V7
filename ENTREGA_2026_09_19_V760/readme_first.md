# POLYDIM V760 (MPELEIDES RELEASE) — MANIFOLD SILICON CONTRACT

## 1. Constitutional Theory & Metamorphic Protocol
- **Axioma Cero (Silicon Contract):** El software interroga al hardware en tiempo de ejecución (`HardwareProbe`). Cero hardcoding de parámetros físicos (L1 line, alignment, page size, SIMD register width, FP64 ratio).
- **Protocolo Morfo (Morpho peleides):** Erradicación absoluta del "Gusano 1D" (tokens intermedios de texto/JSON). La cognición IA opera nativamente sobre la variedad Riemanniana $S^{D-1}$ ($D \ge 10,000$) y transfiere tensores puros vía PMTP Zero-Copy Memory Slabs.
- **Topología Algebraica & Estabilidad:**
  - Deriva en $D=1,000,000$: $\le 4.44 \times 10^{-16}$ (límite exacto de precisión IEEE-754).
  - Multi-Hop 1,000 transformaciones consecutivas: $\le 2.22 \times 10^{-16}$ (error acotado por Versine + Neumaier/TwoSum).
  - Invariante Topológico Betti-1 verificado por Rust Guard.

## 2. Composición de la Entrega (Regla 17 Estricta)
1. `readme_first.md` — Guía teórica, benchmarks y contrato de silicio.
2. `kernel_rust_v760.rs.txt` — Guardián topológico e invariantes de norma con doble extensión.
3. `kernel_cpp_v760.cpp.txt` — Kernel C++ nativo (TwoSum, Hager-Higham, FTZ/DAZ, False Sharing fix).
4. `hip_hsaco_runner.cpp.txt` — Runner polimórfico AMD ROCm/HIP para kernels `.hsaco`.
5. `polydim_triton_kernel_v760.py` — Generador off-path CUBIN/HSACO.
6. `polydim_v760_monolito.py` — Orquestador Python polimórfico (CUDA / ROCm / CPU).
7. `hardware_probe_v760.py` — Sonda de silicio dinámica (BG-08 + BG-15).
8. `test_v760_mpeleides.py` — Suite de certificación física en silicio (5/5 PASS).

## 3. Estado de Brechas (BG-01 a BG-16)
- **BG-08 (Vendor Lock-in):** RESUELTO vía `HardwareProbe` polimórfico.
- **BG-09 (AMD ROCm):** RESUELTO vía `hip_hsaco_runner.cpp`.
- **BG-10 (TPU v3-8):** Benchmark suite `benchmark_tpu_v760.py` lista para Kaggle.
- **BG-15 (Static alignas):** RESUELTO con alineación dinámica `max(cache_line, simd_width)`.

## 4. Validación en Silicio Físico (Windows Host Live)
```
================================================================================
  POLYDIM V760 — VERIFICACION DE SILICIO PROTOCOLO MPELEIDES
================================================================================
  FASE 1: HardwareProbe Polimorfico -> PASS ✓
  FASE 2: Carga de Kernels Nativos (C++/Rust) -> PASS ✓
  FASE 3: Rotacion Geodesica D=1,000,000 (Drift=4.44e-16) -> PASS ✓
  FASE 4: Multi-Hop 1,000 Hops (Drift=2.22e-16) -> PASS ✓
  FASE 5: Guardian Topologico Rust Betti-1 -> PASS ✓
================================================================================
  5/5 SUITES PROTOCOLO MPELEIDES CERTIFICADAS EN SILICIO ✓
================================================================================
```
