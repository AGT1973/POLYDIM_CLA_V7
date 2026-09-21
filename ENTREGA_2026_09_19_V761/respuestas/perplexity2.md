# Auditoría POLYDIM V761 "MPELEIDES HARDENED": SOTA, mejoras, redundancias y anti-errores

## Resumen del veredicto

El álgebra es correcta. La certificación no lo es.

Los tres kernels fueron compilados y ejecutados sobre silicio real (GCC 15.2, x86-64, f64, OpenMP) contra una implementación de referencia en LAPACK. La fórmula de Rodrigues y la retracción Cayley–SMW son matemáticamente exactas y numéricamente sólidas en el camino feliz: se midió \(|\|y'\|-1| \le 2.22\times10^{-16}\) hasta \(D=10^6\), y \(\max|Y^\top Y - I| \le 6.9\times10^{-15}\) en Stiefel para \(K\) entre 16 y 128. El error de composición geodésica tras 20 000 pasos fue \(9.4\times10^{-15}\).

Lo que falla es la capa de garantía. La etiqueta "Silicio Certificado | Ortho Error \(\le 2.10\times10^{-14}\)" no está sostenida por ningún mecanismo del código: se identificaron cinco rutas por las que el kernel devuelve `POLYDIM_SUCCESS` con invariantes violados hasta \(1.47\times10^{-2}\) — doce órdenes de magnitud por encima de la cota declarada — y el sistema de IPC presentado como seqlock produjo **99,65 % de lecturas desgarradas** en prueba directa.

| Dimensión evaluada | Veredicto | Evidencia medida |
| --- | --- | --- |
| Corrección algebraica (Rodrigues, Cayley–SMW) | Sólida | \(2.2\times10^{-16}\) / \(6.9\times10^{-15}\) |
| Sumación compensada de Neumaier | Justificada, no redundante | naive falla la cota: \(4.3\times10^{-14}\) |
| Reproducibilidad multi-hilo | Casi exacta | \(\Delta = 2.2\times10^{-19}\) entre 1 y 8 hilos |
| Validación de invariantes (anti-errores) | **Deficiente** | 5 fallos silenciosos con `rc=0` |
| IPC "PMTP seqlock" | **Roto** | 198 584 / 199 280 lecturas corruptas |
| Guardián topológico Rust | **Ausente y mal calibrado** | umbral real \(4.4\times10^{-10}\); Betti-1 no existe |
| Rendimiento frente al SOTA | **4,4×–18,9× más lento** | vs LAPACK, misma fórmula |
| Posición en el estado del arte | SOTA de 2011–2013, no de 2020–2025 | ver sección de SOTA |
| Certificación por la capa Dart | **Vacía** | la función jamás se invoca |

---

## Metodología

Se extrajeron los kernels C++ a una biblioteca compartida (`g++ -O3 -fopenmp -fPIC -shared`, sin `-ffast-math`), se los expuso vía `ctypes` y se los sometió a nueve familias de pruebas: preservación de norma en el caso nominal, violación deliberada de ortonormalidad de la base, escalado de la base, validación de entradas, propagación de `NaN`/`Inf` en el parámetro angular, sentido de rotación contra la fórmula de Rodrigues canónica, ortogonalidad de la retracción de Stiefel con gradiente tangente y no tangente, deriva acumulada en 20 000 iteraciones, y coste comparado contra LAPACK. El protocolo PMTP se reimplementó verbatim en un banco productor/consumidor con carga útil de 65 536 doubles y un invariante verificable (todo el búfer contiene el mismo valor), que permite detectar desgarros sin ambigüedad.

La capa Rust no pudo compilarse: no había toolchain de Rust disponible en el entorno, de modo que su evaluación es estática y se apoya en documentación oficial del lenguaje. Los tiempos absolutos provienen de un entorno de 2 vCPU y no son comparables con la máquina de origen; los **cocientes** entre implementaciones sí lo son.

---

## Parte 1 — Lo que está bien y hay que preservar

### La retracción Cayley–SMW está bien derivada

La construcción por bloques del kernel es exactamente la aplicación de Sherman–Morrison–Woodbury a la transformada de Cayley con \(U=[G\ X]\), \(V=[X\ -G]\), lo que reduce la inversión de una matriz \(D\times D\) a un sistema denso \(2K\times2K\). Es la técnica que [Wen y Yin describen como esquema tipo Crank–Nicolson para preservar restricciones de ortogonalidad](https://link.springer.com/article/10.1007/s10107-012-0584-1) con menos flops que los métodos basados en proyecciones o geodésicas, y la reducción vía SMW aparece atribuida a Tagare en los [materiales suplementarios de la parametrización CWY](http://proceedings.mlr.press/v130/likhosherstov21a/likhosherstov21a-supp.pdf), que señalan que la retracción de Cayley directa requiere invertir una matriz \(N\times N\) y por tanto es cúbica en \(N\).

Los bloques del código verifican término a término: \(V^\top U = \begin{pmatrix} X^\top G & X^\top X \\ -G^\top G & -G^\top X\end{pmatrix}\) y \(V^\top X = \begin{pmatrix} X^\top X \\ -G^\top X\end{pmatrix}\), con \(M = I - \tfrac{\tau}{2}V^\top U\) y \(Y = X + \tau U M^{-1}V^\top X\). La diferencia máxima contra la misma fórmula evaluada en LAPACK fue de \(1.7\times10^{-16}\) en todos los casos probados, lo que confirma que no hay error de transcripción.

Un hallazgo favorable adicional: la ortogonalidad se conserva incluso alimentando el kernel con un gradiente euclídeo crudo, no proyectado al espacio tangente (\(\max|Y^\top Y-I| = 3.2\times10^{-15}\)). Esto es una propiedad estructural de la parametrización de Cayley, no un accidente, y hace al kernel robusto frente a un error frecuente en la capa que lo llame.

### La sumación de Neumaier gana su coste

Esta es la respuesta directa a la pregunta sobre redundancias, y es negativa: la compensación **no** es adorno. Con \(D=10^6\) y vectores unitarios realistas, la suma ingenua del producto escalar acumula un error relativo de \(4.3\times10^{-14}\) — es decir, **ya excede por sí sola la cota de \(2.10\times10^{-14}\) que el documento declara certificada**. La sumación pairwise con ocho acumuladores, que es 2,6× más rápida, tampoco alcanza: \(1.1\times10^{-14}\), sin margen. Neumaier baja a \(10^{-16}\)–\(10^{-17}\).

![Comparación de error relativo entre suma ingenua, pairwise y Neumaier](https://d2z0o16i8xm8ak.cloudfront.net/5a00fa2d-45ee-425f-a3d0-5147e37e2087/bc763d2b-6ec7-4b2e-b8dd-b8e668a5e72e/sumacion-compensada.png?Policy=eyJTdGF0ZW1lbnQiOlt7IlJlc291cmNlIjoiaHR0cHM6Ly9kMnowbzE2aTh4bThhay5jbG91ZGZyb250Lm5ldC81YTAwZmEyZC00NWVlLTQyNWYtYTNkMC01MTQ3ZTM3ZTIwODcvYmM3NjNkMmItNmVjNy00YjJlLWI4ZGQtYjhlNjY4YTVlNzJlL3N1bWFjaW9uLWNvbXBlbnNhZGEucG5nPyoiLCJDb25kaXRpb24iOnsiRGF0ZUxlc3NUaGFuIjp7IkFXUzpFcG9jaFRpbWUiOjE3OTA1MTM1MjB9fX1dfQ__&Signature=lw3ssXfruhXpmjf-RtK0lYD1vWIzMG7dIbyQTTEDxVvIjLkgFWZ5k8jaw8mrQnEfflfauB-FRojAptzPsy20P36A8BSF96udz8RYwLtT0E544-gJPrLlkopv2FYbERQTIj-PZiqnCXH~DKPXc5-72ObrO8sCtgRxZdWNPqg9CqbuxuH-s8V4MP0g-bCAcJZFq6GGmvIoWL4x~V98w7-uITUjawTbJF3lJHAERvTk2QvycgijAvS6iN7aLlMr-au8sFWPLVEMNn4dtiqLvB~ZI7clsdCizCjJqK6NTEWrC02PqOYVvBaShh9wJcTW3h-j455Z62nz~RxU1aimeLe4vA__&Key-Pair-Id=K1BF7XGXAIMYNX)

La propiedad se mantiene en los cinco regímenes de condicionamiento probados. El esquema de acumuladores por hilo combinados con un segundo nivel de Neumaier resultó además casi reproducible frente al número de hilos (\(\Delta=2.2\times10^{-19}\) entre 1 y 8 hilos), lo que es un logro real: la [no asociatividad del punto flotante es una causa conocida de irreproducibilidad corrida a corrida en algoritmos iterativos](https://arxiv.org/html/2408.05148v1), y este diseño la neutraliza casi por completo.

### Estabilidad geodésica en régimen iterativo

Comparar una rotación única de \(\theta=20\) rad contra 20 000 pasos de \(10^{-3}\) rad arrojó una discrepancia de \(9.4\times10^{-15}\), y la deriva de norma a lo largo de esas 20 000 iteraciones nunca superó \(2.22\times10^{-16}\). El kernel de Rodrigues es genuinamente estable cuando se lo alimenta correctamente.

---

## Parte 2 — Anti-errores: donde la coraza no existe

![Brecha entre la cota certificada y lo que el código acepta sin error](https://d2z0o16i8xm8ak.cloudfront.net/5a00fa2d-45ee-425f-a3d0-5147e37e2087/23386b60-6108-447a-8f3d-fe17437f769e/brecha-garantia.png?Policy=eyJTdGF0ZW1lbnQiOlt7IlJlc291cmNlIjoiaHR0cHM6Ly9kMnowbzE2aTh4bThhay5jbG91ZGZyb250Lm5ldC81YTAwZmEyZC00NWVlLTQyNWYtYTNkMC01MTQ3ZTM3ZTIwODcvMjMzODZiNjAtNjEwOC00NDdhLThmM2QtZmUxNzQzN2Y3NjllL2JyZWNoYS1nYXJhbnRpYS5wbmc~KiIsIkNvbmRpdGlvbiI6eyJEYXRlTGVzc1RoYW4iOnsiQVdTOkVwb2NoVGltZSI6MTc5MDUxMzUyMH19fV19&Signature=o1Bft0NJFjyy0IG~~tbGltbrXv5XsHTQ6z9Uz-duRU74icsNBK08OQl1Hn1VL~tftqEXGRj3ZWpxANEDBznQZJ8kc9I8magiEBC3qpGQktuWkaJljdke48Uu6tRjFY48GHOqVBrgIbj6MyW4aEVDs5szGxjx49i4UgmmRFoF9fbITtOK8Fg1~GRa3cOLvfWjIPD-1NFPmSoRXmME~rb~44e~G5sIpm4Wwkk8~6~b6wj6IiyOd-Pym53tKHQLZ96rNUR4ET4kt~qEHSWUDl2Gzdbwq5Z7ImEpmGoYah7LKIEOktDcbe~unA5En1Bv22L~7WX6CQxDruuDOaSVeNvnYg__&Key-Pair-Id=K1BF7XGXAIMYNX)

### A1 (crítico) — PMTP no es un seqlock; es un desgarro garantizado

`polydim_acquire_read` lee el estado empaquetado **una sola vez**, devuelve el índice de búfer y retorna `true`. No hay relectura del contador tras copiar la carga útil, no hay bit de "escritura en curso", y hay solo dos búferes alternantes. El escritor vuelve al búfer que el lector está recorriendo cada dos publicaciones.

Reimplementado verbatim y medido: de 199 280 lecturas validadas, **198 584 estaban desgarradas (99,65 %)**. El código de error `POLYDIM_ERR_SEQLOCK_RACE` está declarado en el enum y **no existe ninguna ruta de ejecución que lo devuelva**.

El contrato de un seqlock correcto es explícito en [la implementación de referencia de Erik Rigtorp](https://github.com/rigtorp/Seqlock): el lector carga el contador, copia los datos, **recarga el contador**, y reintenta salvo que ambos coincidan y el valor sea par; el paridad impar señaliza escritura en progreso. El diseño V761 omite los pasos 3 y 4 por completo. La primitiva está además [documentada en el comité de C++ como mecanismo para datos leídos con frecuencia y escritos rara vez](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2017/p0603r0.htm), un perfil que un kernel publicando estado en cada iteración no cumple.

Se implementó y midió también el seqlock canónico con paridad y revalidación: eliminó los desgarros (0 de 2), pero con un escritor publicando continuamente **inanició al lector**, con 194 millones de reintentos y solo dos lecturas exitosas. La conclusión operativa no es "añadir paridad" sino que este patrón de acceso exige **triple búfer con secuencia por ranura**, el mecanismo discutido precisamente para productores de alta frecuencia con consumidores lentos en [la discusión de triple buffering SPMC](https://users.rust-lang.org/t/spmc-buffer-triple-buffering-for-multiple-consumers/10118). Conviene notar que el patrón de triple búfer tiene trampas propias de invariante que han sido [señaladas en implementaciones concretas](https://www.reddit.com/r/programming/comments/p1zm5/triple_buffering_as_a_concurrency_mechanism/), de modo que el invariante "el búfer sucio nunca coincide con el búfer expuesto" debe demostrarse, no asumirse.

### A2 (crítico) — La compuerta de ortonormalidad se calcula y se tira a la basura

El kernel de Rodrigues acumula cinco productos escalares compensados: `yu`, `yv`, `uu`, `vv`, `uv`. Solo los dos primeros se usan. Los tres restantes — `uu`, `vv`, `uv` — son **exactamente los valores necesarios para verificar que \(\{u,v\}\) es ortonormal**, y se descartan sin leerlos.

La consecuencia medida, con \(D=10^5\):

| Perturbación de la base | Código devuelto | Deriva de norma resultante |
| --- | --- | --- |
| \(v \leftarrow \mathrm{norm}(v+0.3u)\) | `POLYDIM_SUCCESS` | \(1.47\times10^{-2}\) |
| \(\|u\|=2\) | `POLYDIM_SUCCESS` | \(1.48\times10^{-2}\) |
| \(\|u\|=1+10^{-8}\) | `POLYDIM_SUCCESS` | \(1.97\times10^{-10}\) |

El tercer caso es el peligroso: una base que se ha desviado en \(10^{-8}\) por acumulación normal de redondeo — algo esperable tras unos miles de reortogonalizaciones aproximadas — produce una deriva cuatro órdenes de magnitud por encima de la cota certificada, sin señal alguna.

Se midió el coste de usar los tres acumuladores ya calculados: **1 % del tiempo de reducción** a \(D=10^6\), porque el bucle está limitado por ancho de banda de memoria y no por flops. No hay argumento de rendimiento que justifique descartarlos.

### A3 (crítico) — `theta` y `tau` no se validan

La verificación de `NaN`/`Inf` recorre `y`, `u` y `v` elemento por elemento, con un coste de \(O(D)\), pero **omite el escalar**. Con \(\theta = \mathrm{NaN}\) o \(\theta = \mathrm{Inf}\), el kernel devuelve `POLYDIM_SUCCESS` y **el 100 % de las componentes de salida son `NaN`**. Lo mismo aplica a `tau` en la retracción de Stiefel. Es la comprobación más barata del kernel y es la única que falta.

### A4 (mayor) — La entrada nunca se valida contra la variedad

Con \(\|y\| = 1+10^{-6}\), el kernel propaga la violación intacta (\(1.00\times10^{-6}\) a la salida) y reporta éxito. Un kernel que declara \(S^{D-1}\) como dominio debe rechazar puntos fuera de él o proyectarlos, y elegir una de las dos políticas explícitamente. La práctica establecida en bibliotecas maduras es tener una operación de proyección dedicada: geoopt expone `projx(x)` precisamente para [inicialización de parámetros sobre la variedad y estabilización numérica tras actualizaciones](https://deepwiki.com/geoopt/geoopt/3-core-concepts).

### A5 (mayor) — El guardián Rust no puede certificar \(2.10\times10^{-14}\)

La tolerancia es `tol = 2*d*EPS + 50*EPS`, y la condición de fallo es `drift > tol && drift > 1e-12`. La conjunción convierte el umbral efectivo en \(\max(\mathrm{tol}, 10^{-12})\):

| \(D\) | `tol` de la fórmula | Umbral efectivo | Factor sobre la cota declarada |
| --- | --- | --- | --- |
| \(10^3\) | \(4.55\times10^{-13}\) | \(1.00\times10^{-12}\) | 48× |
| \(10^5\) | \(4.44\times10^{-11}\) | \(4.44\times10^{-11}\) | 2 115× |
| \(10^6\) | \(4.44\times10^{-10}\) | \(4.44\times10^{-10}\) | **21 143×** |

A \(D=10^6\), el guardián acepta silenciosamente una deriva veintiún mil veces mayor que la cifra que encabeza el documento de entrega. La cota lineal en \(d\) es defendible como cota pesimista de peor caso — el análisis clásico de estabilidad de [Higham](https://nhigham.com/wp-content/uploads/2023/10/high97t.pdf) sostiene términos polinómicos en la dimensión — pero es incoherente con una certificación de \(2.10\times10^{-14}\) publicada como propiedad del sistema. Con sumación compensada la deriva real observada fue \(O(\epsilon)\), independiente de \(D\), de modo que la tolerancia debería ser una constante pequeña multiplicada por \(\epsilon\), no lineal en \(d\). Y la cláusula `&& drift > 1e-12` no tiene justificación numérica: solo suaviza el guardián.

### A6 (mayor) — FTZ/DAZ contradice la cabecera y anula la comprobación de subnormales

El encabezado declara "IEEE-754 Strict Precision" mientras la primera línea de cada kernel activa FTZ y DAZ. El manual de Intel es inequívoco: [el modo flush-to-zero no es compatible con el estándar IEEE 754](https://xem.github.io/minix86/manual/intel-x86-and-64-manual-vol1/o_7281d5ea06a5b67a-241.html), dado que la respuesta obligada ante desbordamiento inferior es entregar el resultado desnormalizado. Intel documenta que [DAZ trata los valores subnormales de entrada como cero y FTZ fuerza a cero los resultados subnormales](https://www.intel.com/content/www/us/en/docs/fortran-compiler/developer-guide-reference/2023-1/set-the-ftz-and-daz-flags.html).

De aquí se sigue una incoherencia entre capas: el guardián Rust devuelve `ErrSubnormalDetected` ante cualquier componente subnormal, pero **ningún dato producido por el kernel C++ puede ser subnormal**, porque FTZ ya los convirtió en cero. La comprobación es código muerto en el flujo previsto, y en el flujo no previsto — datos que entran desde otra fuente — es un falso positivo: un vector unitario válido y muy disperso puede contener legítimamente componentes subnormales, y rechazarlo como error es una política demasiado agresiva que conviene degradar a advertencia.

Hay además una asimetría interna: `enable_ftz_daz()` se invoca dentro de la primera región paralela (correcto, MXCSR es por hilo) pero **no** en la segunda región `omp parallel for` que escribe `y_out`. Con el mismo equipo de hilos el estado persiste en la práctica, pero eso no está garantizado por el estándar.

### A7 (mayor) — La red de seguridad de Rust es ornamental y el archivo no compilará en edición 2024

Tres problemas acumulados en el mismo bloque:

El `catch_unwind` no protege nada. El cuerpo del closure no contiene ninguna operación que pueda entrar en pánico — sin indexación con límites, sin `unwrap`, sin asignaciones — de modo que la rama `Err(_) => ErrPanicCaught` es inalcanzable. Y si el perfil de release usa `panic = "abort"`, como es habitual en bibliotecas FFI, `catch_unwind` [nunca capturará nada y el programa terminará](https://users.rust-lang.org/t/catching-panic-at-ffi-boundary-iff-unwinding-enabled/14909). Vale la pena conservar la construcción como defensa en profundidad, pero no debe contarse como garantía: el Rustonomicon advierte que [la estrategia de desenrollado de Rust no es compatible por especificación con ningún otro lenguaje](https://doc.rust-lang.org/nomicon/ffi.html), y la disciplina correcta es marcar la función `extern "C-unwind"` o garantizar ausencia de pánico, no envolver y confiar.

El `slice::from_raw_parts` dentro del closure se apoya en que el cuerpo de una `unsafe fn` es implícitamente inseguro. En Rust 2024 ese comportamiento cambió: [el lint `unsafe_op_in_unsafe_fn` advierte por defecto](https://doc.rust-lang.org/edition-guide/rust-2024/unsafe-op-in-unsafe-fn.html), porque permitir operaciones inseguras sin bloque explícito se consideró demasiado riesgoso. El archivo necesita bloques `unsafe {}` explícitos.

Y `max_drift_out` solo se escribe en la ruta que llega al cálculo de la norma. En los retornos tempranos — puntero nulo, dimensión cero, `NaN` — el valor del llamante queda con su contenido anterior, indistinguible de una medición fresca.

### A8 (mayor) — El "Betti-1 Topological Guardian" no existe

El archivo Rust se titula "Guardián Topológico Betti-1 & Higham". No contiene ninguna construcción de complejo simplicial, ninguna filtración, ningún cálculo de homología persistente. La variante `ErrTopologyFragmented` está declarada y es inalcanzable. Lo que el archivo implementa es una verificación de norma con sumación compensada — útil, pero no topológica.

Esto conviene corregirlo en la documentación antes que en el código, porque construir el guardián real es costoso y su valor es dudoso a esta escala: los números de Betti [cuentan componentes conexas, túneles y cavidades](https://www.math.uni-hamburg.de/projekte/wiam16/slides/Rieck.pdf), y \(\beta_1\) de una esfera \(S^{D-1}\) con \(D>2\) es idénticamente cero, de modo que no aporta información sobre la deriva de un punto. Peor aún, la secuencia de Betti [es inestable bajo la métrica 1-Wasserstein frente a perturbaciones pequeñas del barcode](https://arxiv.org/html/2109.09218v1), lo que la descalifica como invariante de guardia numérica de alta sensibilidad.

### A9 (menor) — El umbral de pivote es absoluto, no relativo

`if (max_val < 1e-15) return POLYDIM_ERR_NUMERICAL_INSTABILITY;` compara contra una constante. Si \(\tau\) o la escala del gradiente hacen que \(\|M\|\) sea grande, una matriz efectivamente singular pasa el filtro; si \(\|M\|\) es pequeña, un sistema perfectamente resoluble se rechaza. El criterio debe escalarse: \(\max_{r}|M_{rk}| < c\,\epsilon\,\|M\|_\infty\). La detección de proximidad a la singularidad se mide por el recíproco del número de condición, no por una magnitud absoluta, como [formaliza Higham en los problemas de cercanía en álgebra lineal numérica](https://eprints.maths.manchester.ac.uk/2555/1/high85p.pdf).

### A10 (menor) — Dimensionado de los acumuladores por `omp_get_max_threads()`

Los vectores se dimensionan con `omp_get_max_threads()` y se indexan con `omp_get_thread_num()` sin cláusula `num_threads`. En presencia de paralelismo anidado o de cambios de configuración en tiempo de ejecución, un `tid` fuera de rango produce escritura fuera de límites. Añadir `num_threads(max_threads)` a la directiva cierra el hueco a coste cero.

### A11 (crítico, de compilación) — `-ffast-math` destruye silenciosamente la compensación

Toda la garantía numérica del sistema descansa en que el compilador **no** reasocie `(sum - t) + val`. Con `-ffast-math`, `-Ofast` o `/fp:fast`, esa expresión se simplifica algebraicamente a cero y los acumuladores de Neumaier degeneran en suma ingenua — es decir, el error salta a \(4.3\times10^{-14}\) y la cota declarada se pierde sin ningún síntoma visible. Intel documenta que [`-fp-model=precise` deshabilita las optimizaciones que pueden alterar los resultados de punto flotante](https://www.intel.com/content/www/us/en/docs/cpp-compiler/developer-guide-reference/2021-10/fp-model-fp.html). El repositorio debe fijar `-fno-fast-math -fno-associative-math` (GCC/Clang) y `/fp:precise` (MSVC), y añadir una prueba de regresión que falle si la compensación deja de funcionar.

### A12 (mayor) — La capa Dart no certifica nada

`main()` abre la biblioteca, resuelve el símbolo `polydim_apply_rodrigues_geodesic_f64` en una variable `rodrigues`, y **nunca la invoca**. No se asigna memoria nativa, no se libera nada, `const D = 1000000` no se usa, `import 'dart:math'` no se usa, y la cifra "46 ms on D=1,000,000 with 0.00 drift" es un comentario, no una medición. El archivo se titula "BENCHMARK" y no contiene ningún benchmark; el "Exit Code 0" que el documento presenta como evidencia de certificación es el código de salida de un programa que solo imprime una línea.

Dos observaciones adicionales sobre esta capa. La ruta `bin/polydim_kernel.so` no sigue la convención de nomenclatura de Linux (`libpolydim_kernel.so`) y no hay rama para macOS (`.dylib`). Y la vinculación no declara `isLeaf`, que para este kernel es la decisión correcta pero merece ser explícita y comentada: Dart documenta que una llamada nativa hoja cuesta **28 ns** frente a **235 ns** de una no hoja, pero [las llamadas hoja impiden que el GC de Dart se ejecute en todos los isolates](https://dart.googlesource.com/native/+/HEAD/doc/performance.md), lo que es inaceptable para un kernel OpenMP que puede tardar milisegundos. El mismo documento sitúa el umbral de relevancia del overhead FFI en llamadas por debajo de 1 µs, muy lejos de este caso.

---

## Parte 3 — Redundancias

| Redundancia | Coste medido o estimado | Recomendación |
| --- | --- | --- |
| Tres acumuladores Neumaier (`uu`, `vv`, `uv`) calculados y descartados | 1 % del tiempo (limitado por memoria) | **No eliminar: usarlos** como compuerta de ortonormalidad (A2) |
| `XTX` calculado en general cuando el invariante de Stiefel garantiza \(X^\top X = I\) | \(K^2D\) flops, un tercio del bucle Gram | Usarlo como compuerta de validación o sustituirlo por \(I\) tras verificar una vez |
| `VTX` materializado como copia de bloques ya presentes en `VTU` | \(2K^2\) doubles y una pasada de escritura | Indexar `VTU` directamente |
| Bucles Gram triples manuales en lugar de `dsyrk`/`dgemm` | 4,4×–18,9× de penalización total | Delegar a BLAS nivel 3 |
| `#pragma omp critical` para reducir tres matrices \(K^2\) por hilo | 25 MB por hilo con \(K=1024\); 403 MB con 16 hilos; serialización total de la reducción | Reducción por árbol, o `dsyrk` sobre bloques de filas |
| `enable_ftz_daz()` invocado en cada llamada y en cada región | Insignificante en tiempo | Consolidar en una inicialización por hilo, documentada |
| Cinco códigos de error declarados e inalcanzables (`DEGENERATE_NORM`, `SEQLOCK_RACE`, `BUFFER_OVERFLOW` en Rodrigues, `ErrTopologyFragmented`, `ErrPanicCaught`) | Deuda de documentación | Implementar las rutas o retirar los códigos |
| `catch_unwind` sin operaciones que puedan entrar en pánico | Rama inalcanzable | Conservar como defensa en profundidad, no contar como garantía |

El patrón de sustituir `critical` por una reducción apropiada está catalogado como mala práctica específica en las [guías de co-diseño de POP CoE](https://co-design.pop-coe.eu/best-practices/replace-critical-with-reduction.html), dado que la sección crítica permite la ejecución de un solo hilo a la vez y anula el paralelismo justo en el punto de agregación.

---

## Parte 4 — Posición frente al estado del arte

![Coste medido del kernel frente a LAPACK con la misma fórmula](https://d2z0o16i8xm8ak.cloudfront.net/5a00fa2d-45ee-425f-a3d0-5147e37e2087/3e7d0940-d0ef-4753-be40-6e41d2b91114/bench-kernel-vs-blas.png?Policy=eyJTdGF0ZW1lbnQiOlt7IlJlc291cmNlIjoiaHR0cHM6Ly9kMnowbzE2aTh4bThhay5jbG91ZGZyb250Lm5ldC81YTAwZmEyZC00NWVlLTQyNWYtYTNkMC01MTQ3ZTM3ZTIwODcvM2U3ZDA5NDAtZDBlZi00NzUzLWJlNDAtNmU0MWQyYjkxMTE0L2JlbmNoLWtlcm5lbC12cy1ibGFzLnBuZz8qIiwiQ29uZGl0aW9uIjp7IkRhdGVMZXNzVGhhbiI6eyJBV1M6RXBvY2hUaW1lIjoxNzkwNTEzNTIwfX19XX0_&Signature=DjYfXSnyjbJkx5mIWxY42Hm-1Cr7R5AAHafD3SFGbWNVCufFsOReQmeW5qPhe66D85U2HslaJlGTJr9EL2KHog8GZ462AEudjVZs-3CyBzhj7FFWlEaPBCI0ahQhxKJx4ItuxegFyAg301wAb-Hdq4h3jTKCbHEL0~U~YZQQQZ3ivs-ENtRZVIvlGE38AccMMN7g8NUCNrbtSabrB9qqE7y-D-55-GSvEDxJiwOYKtELIeIWnGWY7xWCf45uXPN7RMkkQzPwSYWxbknfPtE0V5U9C0dptlQvT2~gXv1ZCBlpSmfKy2PHblNNuZksKQZBnPhgPFDOSlJMmX5WeJBZdQ__&Key-Pair-Id=K1BF7XGXAIMYNX)

El resultado más incómodo de la auditoría es que la misma fórmula, implementada en unas veinte líneas de NumPy sobre LAPACK, corrió entre **4,4× y 18,9× más rápido** que el kernel "de silicio nativo", y con ortogonalidad ligeramente mejor (\(2.0\times10^{-15}\) frente a \(5.1\times10^{-15}\) en \(D{=}4096, K{=}64\)). La causa no es misteriosa: los bucles Gram triples escritos a mano no explotan bloqueo por caché ni registros vectoriales, y la brecha entre una multiplicación de matrices ingenua y una implementación BLAS ajustada es [un resultado clásico y bien documentado](https://stackoverflow.com/questions/14532169/why-is-a-na%C3%AFve-c-matrix-multiplication-100-times-slower-than-blas), abordado específicamente para `syrk` en la [literatura de implementación de BLAS nivel 3 de alto rendimiento](https://www.cs.utexas.edu/ftp/techreports/tr06-23.pdf).

En cuanto al algoritmo, V761 implementa fielmente el estado del arte de 2011–2013, no el de 2020–2025.

| Enfoque | Año | Coste dominante | Estado de V761 |
| --- | --- | --- | --- |
| Cayley + curvilinear search ([Wen y Yin](https://link.springer.com/article/10.1007/s10107-012-0584-1)) | 2013 | sistema denso \(2K\times2K\) | **implementado** |
| Reducción SMW de la inversa (Tagare, vía [CWY supp.](http://proceedings.mlr.press/v130/likhosherstov21a/likhosherstov21a-supp.pdf)) | 2011 | idem | **implementado** |
| Cayley iterativo sin inversa ([Li, Fuxin y Todorovic, ICLR 2020](https://arxiv.org/abs/2002.01113)) | 2020 | solo productos matriciales | ausente |
| Parametrización CWY / Householder paralelizable ([Likhosherstov et al.](https://proceedings.mlr.press/v130/likhosherstov21a.html)) | 2021 | productos, orientado a GPU/TPU | ausente |
| Landing flow, optimización sin retracción ([Ablin y Peyré](https://proceedings.mlr.press/v151/ablin22a/ablin22a.pdf)) | 2022 | solo productos matriciales | ausente |
| Landing determinista, estocástico y con reducción de varianza ([Ablin, Vary, Gao y Absil, JMLR](https://jmlr.org/papers/v25/23-0451.html)) | 2024 | idem | ausente |

La línea de trabajo de Li, Fuxin y Todorovic es directamente relevante: su contribución central es [una retracción basada en una transformada de Cayley iterativa que evita la inversión de matrices como actualización de parámetros](https://pdfs.semanticscholar.org/fa15/5943c583867ed09be5eb39a8feb8252355ee.pdf), es decir, elimina exactamente el componente que en V761 es el cuello de botella secuencial. Su implementación de referencia está [disponible públicamente](https://github.com/Ardo0115/Optimization-on-Stiefel-Manifold-via-Cayley-Transform).

La línea del landing es más radical y cuestiona la premisa del diseño. El método define el potencial \(N(X)=\tfrac14\|XX^\top-I\|^2\) y el campo \(\Lambda(X)=\psi(X)X+\lambda\nabla N(X)\), e itera \(X_{k+1}=X_k-\eta_k\Lambda(X_k)\) usando **solo multiplicaciones de matrices, sin inversión, sin raíz cuadrada matricial y sin factorización**. Es deliberadamente no factible: los iterados no están sobre la variedad, pero son empujados hacia ella y convergen a \(\|XX^\top-I\|=0\) hasta precisión numérica. Existe implementación como optimizador de PyTorch en los repositorios de [Vary](https://github.com/simonvary/landing-stiefel) y [Ablin](https://github.com/pierreablin/landing), y extensión reciente al [caso Stiefel generalizado estocástico](https://www.gaobin.cc/publication/2024-vary-landing/).

La tensión de diseño merece ser explícita: la filosofía de V761 es factibilidad estricta con certificación por invariante, que es una posición defendible y en ciertos dominios obligatoria. El landing renuncia a la factibilidad intermedia. La decisión no es obvia, pero debe tomarse a la vista de la alternativa y documentarse, no por omisión.

Sobre el límite de \(K\le1024\): es nominal, no operativo. Con \(K=1024\) el sistema denso es de \(2048\times2048\) (33,6 MB) y la eliminación gaussiana secuencial del kernel cuesta unos 5,7 GFLOP sin paralelizar, mientras la reducción `critical` consume 403 MB con 16 hilos. El `BUFFER_OVERFLOW` en \(K>1024\) sugiere una capacidad que el resto del código no puede sostener; el límite practicable real está más cerca de \(K\approx128\).

Como referencia de madurez de ingeniería, conviene mirar la superficie de API de [geoopt](https://github.com/geoopt/geoopt) y su [catálogo de variedades](https://geoopt.readthedocs.io/en/latest/manifolds.html): proyección explícita, `expmap`, `retr` y transporte vectorial como operaciones separadas y nombradas. V761 fusiona rotación, validación y publicación de estado en una sola función, lo que es precisamente lo que dificulta insertar las compuertas que faltan.

En cuanto a actividad reciente del campo, la optimización sobre Stiefel sigue en desarrollo activo en 2024–2025, con trabajo en [información de segundo orden sobre la variedad de Stiefel simpléctica](https://arxiv.org/html/2404.08463v2), [nuevos transportes vectoriales para gradiente conjugado sobre Stiefel generalizada](https://www.sciencedirect.com/science/article/abs/pii/S0377042724002747) y aplicaciones a adaptación de bajo rango como [LoRA sobre la variedad de Stiefel](https://arxiv.org/abs/2508.17901). Ninguna de estas líneas invalida el kernel de V761, pero sitúan su elección algebraica como una base sólida y conservadora más que como frontera.

---

## Parte 5 — Plan de mejora priorizado

### P0 — Bloqueantes de la certificación

El primer bloque de trabajo no mejora el rendimiento: hace verdadera la etiqueta del documento.

1. **Validar los escalares.** Dos líneas, coste nulo, cierra la vía de fallo más grave:

```cpp
if (!std::isfinite(theta)) return POLYDIM_ERR_NAN_OR_INF;   // idem tau en Stiefel
```

2. **Activar la compuerta de ortonormalidad con los acumuladores ya calculados** (coste medido: 1 %):

```cpp
double uu = total_uu.total(), vv = total_vv.total(), uv = total_uv.total();
const double gate = 8.0 * std::numeric_limits<double>::epsilon();
if (std::abs(uu - 1.0) > gate || std::abs(vv - 1.0) > gate || std::abs(uv) > gate)
    return POLYDIM_ERR_DEGENERATE_NORM;   // codigo ya declarado, hoy inalcanzable
```

3. **Validar la entrada contra la variedad.** Añadir el acumulador `yy` y rechazar (o proyectar, según política declarada) si \(|\,\|y\|^2-1| > \) tolerancia.

4. **Recalibrar el guardián Rust** a una constante pequeña por \(\epsilon\), eliminando la cláusula `&& drift > 1e-12`, y escribir `max_drift_out` en todas las rutas de retorno incluidas las tempranas.

5. **Reescribir PMTP como triple búfer con secuencia por ranura**, y demostrar el invariante de que la ranura en escritura nunca coincide con la ranura expuesta. Añadir al CI el banco productor/consumidor con invariante verificable usado en esta auditoría: hoy detecta 99,65 % de desgarros y debe detectar 0 %.

6. **Fijar las banderas de compilación** (`-fno-fast-math -fno-associative-math` / `/fp:precise`) y añadir una prueba de regresión que compare la sumación compensada contra una referencia en precisión extendida y falle si el compilador la ha reasociado.

7. **Corregir la documentación**: retirar "IEEE-754 Strict Precision" o desactivar FTZ/DAZ — ambas afirmaciones no pueden coexistir; retirar "Betti-1" o implementarlo; retirar la cifra de 46 ms hasta que exista un benchmark que la produzca.

8. **Hacer que la capa Dart ejecute realmente algo**: asignar memoria nativa, invocar el kernel, comprobar el código de retorno, medir con reloj monótono y varias repeticiones, y liberar. Sin esto no hay "Exit Code 0" que signifique nada.

### P1 — Rendimiento

9. **Delegar los productos Gram a `dsyrk`/`dgemm`** y el sistema \(2K\times2K\) a `dgetrf`/`dgetrs` de LAPACK. La evidencia medida sugiere un factor de 4×–19×, y la ortogonalidad no empeora sino que mejora ligeramente. Si el requisito de "silicio nativo sin dependencias" es firme, conviene al menos bloquear los bucles por caché y vectorizarlos explícitamente.

10. **Sustituir `#pragma omp critical` por una reducción en árbol** sobre las matrices \(K^2\).

11. **Añadir `num_threads(max_threads)`** a las regiones paralelas que indexan por `omp_get_thread_num()`.

12. **Escalar el umbral de pivote** por \(\|M\|_\infty\).

### P2 — Alcance y arquitectura

13. **Evaluar el Cayley iterativo de Li et al. y el landing de Ablin et al.** frente al solver denso actual, con un banco común. La decisión de mantener factibilidad estricta es legítima, pero debe ser una decisión medida y no heredada.

14. **Separar las responsabilidades**: `project`, `retract`, `verify` y `publish` como funciones distintas, siguiendo la convención de las bibliotecas maduras del dominio. Esto es lo que hace insertables las compuertas de P0 sin volver a tocar el bucle caliente.

15. **Documentar la convención de rotación.** El kernel implementa \(R(-\theta)\), no \(R(+\theta)\): la comprobación contra la fórmula de Rodrigues canónica dio \(\|out - R(-\theta)y\| = 5.6\times10^{-17}\) frente a \(2.95\times10^{-16}\) para \(R(+\theta)\). Es una rotación válida y autoconsistente, pero el signo debe estar en el contrato, porque cualquier capa que combine este kernel con un transporte vectorial de otra fuente heredará un error de signo silencioso.

---

## Límites de esta evaluación

La capa Rust no se compiló ni se ejecutó, por ausencia de toolchain en el entorno; sus hallazgos (A5, A6, A7, A8) son análisis estático apoyado en documentación oficial y no tienen respaldo empírico propio. Las rutas específicas de MSVC/Windows y la rama ARM64 de `enable_ftz_daz` no se ejercitaron, por lo que la corrección del acceso a FPCR y del comportamiento con `__cdecl` queda sin verificar. Los tiempos absolutos provienen de un entorno de 2 vCPU y no son comparables con la máquina de origen; solo los cocientes entre implementaciones lo son. El banco de desgarros usa un escritor publicando de forma continua, que es el peor caso: con publicaciones más espaciadas la tasa de corrupción bajaría, pero la ausencia de todo mecanismo de detección es estructural e independiente de la carga. Finalmente, no se auditó el comportamiento del kernel de Stiefel con \(K>128\) ni con \(D\) tal que la matriz no quepa en memoria, ni se evaluó la corrección bajo paralelismo anidado.
