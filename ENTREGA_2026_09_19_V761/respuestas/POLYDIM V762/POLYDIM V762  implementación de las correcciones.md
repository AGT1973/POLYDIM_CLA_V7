# POLYDIM V762 — implementación de las correcciones de la auditoría V761

Cierra los hallazgos A1–A12 de la auditoría del 2026-09-20. Todo lo que sigue
está **medido en este repositorio**, no declarado: `./ci.sh` reproduce cada cifra.

Entorno de medición: GCC 15.2.0, x86-64, 2 vCPU, `OMP_NUM_THREADS=2`,
Rust 1.98.1 (edición 2024), Dart 3.13.4, OpenBLAS 0.3.34 vía numpy.

```
./ci.sh          # C++ (26 pruebas) + Rust (8) + Dart (ejecución real) + rendimiento
make verify      # sólo C++, incluida la prueba negativa de -ffast-math
```

---

## 1. Estado de los 12 hallazgos

| # | Hallazgo V761 | Estado | Evidencia reproducible |
|---|---|---|---|
| A1 | PMTP sin relectura del contador: **99,65 %** de lecturas desgarradas; `SEQLOCK_RACE` inalcanzable | **Cerrado** | Triple búfer con seqlock por ranura. Medido: **0 desgarros no detectados** en 218 417 lecturas aceptadas; 345 516 carreras detectadas y reportadas; el lector progresa (la corrección canónica odd/even lo dejaba en hambre con 194 M de reintentos) |
| A2 | `uu`/`vv`/`uv` calculados y descartados; deriva 1,47e-2 con `rc=0` | **Cerrado** | `POLYDIM_ERR_BASIS_NOT_ORTHONORMAL`. Los 3 casos de la auditoría rechazados, incluido el sutil `‖u‖=1+1e-8` |
| A3 | `theta`/`tau` sin validar: 100 % de NaN con `rc=0` | **Cerrado** | `POLYDIM_ERR_INVALID_SCALAR` |
| A4 | `‖y‖=1+1e-6` pasaba intacto | **Cerrado** | `POLYDIM_ERR_POINT_OFF_MANIFOLD` + `polydim_project_sphere_f64` para repararlo |
| A5 | Guardián Rust con umbral efectivo 4,44e-10 en D=10⁶ (21 143× la cota certificada) | **Cerrado** | Cota fija `64·eps = 1,42e-14`, **no escalada en D**, ≤ el 2,10e-14 publicado. Test `rechaza_deriva_que_v761_aceptaba` |
| A6 | FTZ/DAZ contradecía "IEEE-754 Strict"; ausente en la 2.ª región paralela | **Cerrado** | `POLYDIM_ENABLE_FTZ=0` por defecto; `polydim_build_info()` declara el modo; MXCSR se fija en **toda** región paralela |
| A7 | `catch_unwind` ornamental; `max_drift_out` sin escribir en salidas tempranas | **Cerrado** | `panic="unwind"` fijado en `Cargo.toml`; el reporte se inicializa antes de cualquier `return`; test dedicado |
| A8 | "Guardián Topológico Betti-1" y `ErrTopologyFragmented` inexistentes en el código | **Cerrado por eliminación** | β₁(S^(D-1))=0 para D>2: la cantidad era vacua. Se retira en vez de sustituirla por un placebo |
| A9 | Umbral de pivote `1e-15` absoluto | **Cerrado** | Umbral relativo `pivot_rel · ‖M‖∞ · 2K`. Con G∼1e6 el umbral medido es 6,17, o sea 6,2e15 veces el valor absoluto anterior |
| A10 | Acumuladores dimensionados por `omp_get_max_threads()` sin `num_threads` | **Cerrado** | `num_threads(nthreads)` en toda región indexada por `tid` |
| A11 | `-ffast-math` habría destruido Neumaier en silencio | **Cerrado** | `polydim_selftest_compensation()` + prueba **negativa** en CI: el binario con `-ffast-math` devuelve `COMPENSATION_BROKEN (-12)` y el build falla |
| A12 | Dart nunca invocaba el kernel; "46 ms" era un comentario; `.so` mal nombrado; sin liberar memoria | **Cerrado** | El puente ejecuta: **4,27 ms** medidos en D=10⁶ con deriva 0,00e+00; `libpolydim.so`/`.dylib`/`.dll` por plataforma; `finally` libera siempre |

Extra descubierto al compilar el Rust (que en la auditoría no fue posible):
la edición 2024 exige `#[unsafe(no_mangle)]`, no sólo bloques `unsafe` internos.
V761 fallaba por **dos** motivos, no uno.

---

## 2. Rendimiento

Misma fórmula, mismos (D,K), 2 hilos en todos los casos. `ms` por retracción, mediana de 3.

| D,K | V761 | **V762 nativo** | OpenBLAS (referencia) | V762 vs V761 | V762 vs OpenBLAS |
|---|---|---|---|---|---|
| 4096,16 | 19,18 | **0,89** | 1,77 | 21,5× más rápido | 2,0× más rápido |
| 4096,64 | 28,05 | **9,90** | 5,71 | 2,8× | 1,7× más lento |
| 16384,32 | 32,03 | **9,68** | 14,99 | 3,3× | 1,5× más rápido |
| 16384,128 | 458,16 | **152,30** | 124,24 | 3,0× | 1,2× más lento |
| 65536,64 | 408,58 | **143,19** | 190,38 | 2,9× | 1,3× más rápido |

V762 es más rápido que OpenBLAS en 3 de 5 puntos, y lo hace **midiendo además**
`max‖YᵀY−I‖` a posteriori, trabajo que V761 no hacía. Tres cambios lo explican:

1. **Gram simétrico combinado.** En vez de XᵀX, XᵀG y GᵀG por separado (3K²D),
   un solo barrido del triángulo superior de `[X G]ᵀ[X G]` (2K²D): −33 % de flops
   y localidad contigua en K.
2. **Inversión de bucles en el producto final.** `Y = X + τ·U·Z` acumulaba sobre
   `p` con `k` fijo, recorriendo `Z` con salto K. Reordenado como axpy sobre `k`,
   ambos accesos son contiguos y vectorizables. **Éste fue el cambio dominante**:
   por sí solo llevó 16384,128 de 367 ms a 152 ms.
3. **Reducción en árbol** en lugar de `#pragma omp critical`, que serializaba K²
   sumas por hilo.

Aviso sobre la corrección de mi propia auditoría: la brecha de **4,4×–18,9×** que
reporté se midió sin fijar el número de hilos de OpenBLAS. Con los hilos igualados
la brecha real de V761 era de **1,7×–10,8×**. La conclusión cualitativa se sostiene,
la magnitud estaba inflada.

Esfera, D=10⁶: V762 tarda 4,25 ms frente a 3,38 ms de V761, es decir **+24 %**.
Ése es el precio completo de la compuerta de ortonormalidad más la verificación
a posteriori. La compuerta sola costaba ~1 %; el resto es el tercer barrido.

BLAS de referencia (netlib, `-DPOLYDIM_USE_BLAS` con `libblas.so.3`) resultó
**más lento** que la ruta nativa (780 ms vs 143 ms en 65536,64). La ruta BLAS
existe y funciona, pero sólo vale la pena con OpenBLAS o MKL.

---

## 3. Precisión

`max‖YᵀY−I‖` del Y producido, medido de forma independiente con OpenBLAS:

| D,K | V761 | V762 |
|---|---|---|
| 4096,16 | 6,66e-16 | 6,66e-16 |
| 16384,128 | 8,88e-16 | 8,88e-16 |
| 65536,64 | 8,88e-16 | 1,11e-15 |

La precisión no se degradó. Con Rodrigues, la deriva es **0,00e+00** en D=10⁶.

**Advertencia sobre `report.ortho_err`.** El verificador interno usa suma plana
y por tanto **sobreestima** el error real 4–7× (2,22e-15 interno vs 6,66e-16 real
en 4096,16). El sesgo es conservador: la compuerta nunca acepta algo peor de lo
que declara. Es la única dirección aceptable para un umbral de certificación.

---

## 4. Cambios incompatibles al migrar desde V761

1. **Signo de rotación.** V761 aplicaba R(−θ); V762 aplica la R(+θ) canónica
   (`R u = cos θ·u + sin θ·v`). **Para reproducir V761 exactamente, pasar −θ.**
   V761 no documentaba esto en ningún sitio.
2. **Firmas nuevas.** `polydim_rodrigues_geodesic_f64` y
   `polydim_stiefel_cayley_smw_f64` toman ahora `PolydimTolerances*` y
   `PolydimReport*` (ambos aceptan `NULL`). El nombre `..._retraction_f64` desapareció.
3. **Normalización compensada obligatoria.** La cota por defecto es `64·eps` y
   **no** crece con D. Una normalización ingenua en D=10⁶ deja un error relativo
   de ~4,3e-14 y será **rechazada con `POINT_OFF_MANIFOLD`**, con razón. Usar
   `polydim_project_sphere_f64` y `polydim_orthonormalize_pair_f64`.
4. **`K ≤ 512`, no 1024.** El límite nominal de V761 era inviable: el sistema
   denso 2K×2K son 33 MB y ~5,7 GFLOP secuenciales. K=1024 devuelve
   `BUFFER_OVERFLOW` en vez de arrastrar al proceso.
5. **Códigos de error nuevos** (−8 a −12). Código que hacía `if (rc != 0)` sigue
   funcionando; código que enumeraba los códigos hay que actualizarlo.
6. **Banderas de compilación no negociables.** `-fno-fast-math
   -fno-associative-math -ffp-contract=off`. Sin ellas el autodiagnóstico
   aborta la carga de la biblioteca.

### Ejemplo mínimo de migración

```c
/* V761 */
int32_t rc = polydim_apply_rodrigues_geodesic_f64(y, u, v, out, theta, D);

/* V762 */
PolydimReport rep;
int32_t rc = polydim_orthonormalize_pair_f64(u, v, D, NULL);   /* nuevo */
if (rc == POLYDIM_SUCCESS) rc = polydim_project_sphere_f64(y, y_n, D, NULL);
if (rc == POLYDIM_SUCCESS)
    rc = polydim_rodrigues_geodesic_f64(y_n, u, v, out, -theta, D, NULL, &rep);
    /*                                                  ^ signo, ver punto 1  */
if (rc != POLYDIM_SUCCESS) abortar(polydim_status_string(rc));
/* rep.out_norm_err contiene la deriva REAL de esta llamada */
```

---

## 5. Lo que sigue abierto

Honestidad sobre el alcance:

- **La "certificación" sigue siendo un conjunto de pruebas, no una prueba.** Lo
  que hay es verificación en tiempo de ejecución con cotas explícitas y una
  batería reproducible. No hay demostración formal de error hacia atrás al
  estilo Higham para la composición completa Cayley-SMW.
- **PMTP sólo está probado con un escritor y un lector.** El diseño de triple
  búfer no cubre múltiples escritores. Con varios lectores debería funcionar
  (cada uno mantiene su propio `observed_seq`), pero no está medido.
- **El Gram de Stiefel no está compensado.** Compensarlo duplicaría la arena de
  memoria. La consecuencia está expuesta en `tol.gram_ortho`, que **sí** escala
  como √D·eps, y documentada en `polydim.h` en lugar de disimulada.
- **SOTA sin tocar.** V762 endurece el algoritmo de 2011–2013 (Wen & Yin). No
  implementa el Cayley iterativo sin inversa de
  [Li, Fuxin & Todorovic (ICLR 2020)](https://arxiv.org/abs/2002.01113) ni el
  flujo de aterrizaje de
  [Ablin & Peyré (2022)](https://proceedings.mlr.press/v151/ablin22a/ablin22a.pdf)
  / [Ablin, Vary, Gao & Absil (JMLR 2024)](https://jmlr.org/papers/v25/23-0451.html),
  que eliminan por completo la resolución densa 2K×2K. Ésa sigue siendo la mejora
  algorítmica de mayor impacto pendiente.
- **Un solo microarquitectura y 2 vCPU.** Los números de escalado con más hilos,
  y el comportamiento de la arena de memoria con K=512 y 16 hilos, no están medidos.

---

## Árbol

```
include/polydim.h            contrato público, con la política numérica escrita
src/polydim_kernel.cpp       kernel + PMTP + autodiagnóstico
tests/test_suite.cpp         26 pruebas, una por hallazgo
tests/bench.cpp              retracción Stiefel
tests/bench_sphere.cpp       rotación en la esfera
rust/src/lib.rs              verificador de invariantes, edición 2024, 8 tests
dart/polydim_ffi.dart        puente FFI que sí invoca, mide y libera
Makefile                     banderas numéricas obligatorias + `make verify`
ci.sh                        las tres capas en un comando
```
