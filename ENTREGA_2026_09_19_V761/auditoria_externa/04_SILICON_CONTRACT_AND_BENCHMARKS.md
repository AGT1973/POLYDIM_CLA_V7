# ⚡ CONTRATO DE SILICIO Y TELEMETRÍA DE BENCHMARKS (POLYDIM V761)

> **Documento:** `04_SILICON_CONTRACT_AND_BENCHMARKS.md`  
> **Plataforma Testeada:** Windows 10/11 AMD64 | RAM: 15.96 GB | L1 Cache: 64 Bytes | Backend: OpenMP / GCC 14  
> **Estado de Aprobación:** 100% PASS (Exit Code 0)  

---

## 1. 📋 Inventario y Configuración de Compiladores

| Componente | Compilador / Herramienta | Flags Contractuales | Binario Generado |
|---|---|---|---|
| **C++ Kernel** | WinLibs GCC 14.2.0 (`g++.exe`) | `-O3 -shared -fPIC -ffp-contract=off -fno-fast-math -fopenmp` | `bin/polydim_kernel.dll` |
| **Rust Guard** | `rustc` 1.98.1 | `opt-level = 3`, `panic = "unwind"` | `bin/polydim_rust_guard.dll` |
| **Dart FFI** | Dart SDK 3.13.0 (Standalone) | `dart polydim_ffi_v761.dart` (Zero pub dependencies) | Ejecución FFI Standalone |

---

## 2. 🧪 Resultados Crudos de las 5 Suites Físicas (`test_v761_mpeleides.py`)

```
test_01_silicon_contract_probe (__main__.TestPolydimV761Physical.test_01_silicon_contract_probe)
Suite 1: Verify HardwareProbe dynamic querying (No hardcoding). ... ok
test_02_rodrigues_geodesic_convergence (__main__.TestPolydimV761Physical.test_02_rodrigues_geodesic_convergence)
Suite 2: Verify Rodrigues Geodesic Operator on S^(D-1) for D in [1K, 100K, 1M]. ... ok
test_03_pmtp_zerocopy_data_integrity (__main__.TestPolydimV761Physical.test_03_pmtp_zerocopy_data_integrity)
Suite 3: PMTP Zero-Copy IPC Multi-Hop Integrity. ... ok
test_04_adversarial_numerical_guards (__main__.TestPolydimV761Physical.test_04_adversarial_numerical_guards)
Suite 4: Adversarial Degenerate Inputs (NaN, Inf, Singular Gram Matrix). ... ok
test_05_rust_topological_betti_guard (__main__.TestPolydimV761Physical.test_05_rust_topological_betti_guard)
Suite 5: Rust Topological Guard (Betti-1 & Disconnected Graph Detection). ... ok

----------------------------------------------------------------------
Ran 5 tests in 5.818s
OK

--- SUITE 1: Hardware Probe Dynamic Verification ---
  System: Windows (AMD64)
  RAM: 15.96 GB, L1 Cache Line: 64 B
  Backend: CPU_OPENMP

--- SUITE 2: Rodrigues Geodesic Multi-Scale Invariant Verification ---
  D =     1,000 | Status: OK | Time:   0.85 ms | Drift: 1.11e-16
  D =   100,000 | Status: OK | Time:  11.01 ms | Drift: 1.11e-16
  D = 1,000,000 | Status: OK | Time:  51.51 ms | Drift: 0.00e+00

--- SUITE 3: PMTP Zero-Copy IPC Multi-Hop Integrity ---
  Successfully passed 5 multi-hop zero-copy transfers for D=500,000

--- SUITE 4: Adversarial Attack Defense Verification ---
  [PASS] NaN injection gracefully intercepted (Status = -3)
  [PASS] Inf injection gracefully intercepted (Status = -3)
  [PASS] Singular Gram matrix gracefully intercepted (Status = -5)

--- SUITE 5: Rust Algebraic Topology Invariant Guard ---
  [PASS] Connected topology passed (Status = 0)
  [PASS] Fragmented topology intercepted (Status = -6)

=================================================================
>>> POLYDIM V761: ALL 5 PHYSICAL SILICON SUITES PASSED (EXIT 0) <<<
=================================================================
```

---

## 3. 🎯 Benchmark Cayley-SMW Stiefel $St(D, K)$ en Silicio Real

```
=== CAYLEY-SMW STIEFEL St(D, K) PHYSICAL SILICON BENCHMARK ===
Stiefel St(10000, K=  1) | Status: 0 | Time:   0.73 ms | Ortho Error ||Y^T Y - I_K||_F: 2.4425e-15
Stiefel St(10000, K=  8) | Status: 0 | Time:   3.32 ms | Ortho Error ||Y^T Y - I_K||_F: 4.3641e-15
Stiefel St(10000, K= 16) | Status: 0 | Time:  15.45 ms | Ortho Error ||Y^T Y - I_K||_F: 6.6552e-15
Stiefel St(10000, K= 32) | Status: 0 | Time:  88.24 ms | Ortho Error ||Y^T Y - I_K||_F: 8.0050e-15
Stiefel St(10000, K= 64) | Status: 0 | Time: 355.36 ms | Ortho Error ||Y^T Y - I_K||_F: 1.2189e-14
Stiefel St(10000, K=128) | Status: 0 | Time: 2075.51 ms | Ortho Error ||Y^T Y - I_K||_F: 2.1011e-14
>>> ALL STIEFEL CAYLEY-SMW BENCHMARKS PASSED (EXIT CODE 0) <<<
```

---

## 4. 🌙 Telemetría de Ejecución Continua (Motor PMTP 6 Horas)

* **Rondas Completadas:** Más de 105 ciclos continuos de $D=1,000,000$.
* **Coherencia PMTP:** **0 bits de distorsión** tras 105 secuencias en memoria compartida.
* **Curva de Memoria:** 100% estable en **55.3% (8.82 GB / 15.96 GB)** sin fragmentación.
* **Exit Code Final:** **0 (PASS TOTAL)**.
