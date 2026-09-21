## **Auditoría bulldog de POLYDIM V762 (y del bloque V760 pegado)**

### Alcance

Leí los cuatro archivos y el bloque V760. El archivo 02 (el "monolito") solo contiene `polydim.h`. Kernel C++, Rust, Dart, orquestador Python, Triton y `test\_suite.cpp` aparecen como enlaces `file:///E:/...`. No pude auditar ese código ni lo ejecuté.

Lo que sí hice fue reproducir la matemática en el sandbox y recalcular toda la aritmética de tus tablas y logs. Usé numpy con referencia en long double de 80 bits, rangos sobre GF(2) y C++ con ThreadSanitizer. El sandbox tiene 1 núcleo, así que no saco conclusiones de rendimiento concurrente.

Etiquetas: **\[V\]** verificado aquí, **\[A\]** aritmética de tus documentos, **\[I\]** inferido, requiere ver el código.

**Lo que resiste el ataque:**

- La fórmula Cayley-SMW coincide con el Cayley denso (4.4e-16). 

- La ortogonalidad se mantiene (≤2.2e-15) incluso con pasos enormes, hasta escala de G ≈ 1e12. 

- La refutación del tribunal sobre ortogonalidad con G no tangente es correcta. 

- Rodrigues y la convención R(+θ) son correctos. 

- 64·2⁻⁵² = 1.42e-14. 

- Las 26 pruebas C++ y las 8 de Rust cuentan bien. 

- Los factores contra V761 son correctos. 

### Mapa de hallazgos

| **\#** | **Hallazgo** | **Severidad** | **Base** |
| :-: | :-: | :-: | :-: |
| E1 | El "monolito" no contiene el código | Crítica | A |
| E2 | Números de A1 contradictorios y prueba de progreso trivial | Alta | A |
| E3 | PMTP: carrera formal de datos, lector con hambre | Alta | V, I |
| E4 | Cayley-SMW: tangente vs gradiente euclídeo | Alta | V |
| E5 | Deriva en composición: el certificado es por llamada | Alta | V |
| E6 | Dos cotas, tolerancias de entrada no alineadas, ε mal definido | Media-alta | V, I |
| E7 | Betti-1 con DSU: se calcula otra cosa | Media | V |
| E8 | DPI, "O(1)" y "cero tokens" mal formulados | Media | lógica |
| E9 | Cobertura de pruebas y seguridad de memoria | Media | A |
| E10 | Umbral de pivote: falsos rechazos | Media-baja | V, I |
| E11 | Rendimiento: pierde 2 de 5 filas contra OpenBLAS | Media | A, I |
| E12 | Contrato ABI y cambio semántico | Media-baja | I |
| E13 | Higiene y credibilidad del dossier | Baja, visible | A |

### E1. El monolito no es un monolito (crítica, A)

El 02 promete "código completo y sin abreviar" y contiene 1 de 7 fuentes. Un auditor externo solo puede juzgar el resumen, como corregir un examen sin la hoja de respuestas.

**Solución:**

1. Incrustar los fuentes o adjuntar un zip. 

2. Añadir un `MANIFEST.sha256` con fuentes, binarios y logs. 

3. Poner tag git y commit SHA en el README. 

4. Dar a cada log una cabecera con CPU, núcleos, SO, compilador, flags, semilla y hash. 

### E2. A1: los números no cuadran (alta, A)

- README y tribunal dicen 0 desgarros en **218,417** lecturas. La telemetría dice 0 de **1,098**, una diferencia de 199 veces. 

- La línea "V761: 0,35% de 83646" usa un denominador que es exactamente 1,098 + 82,548, es decir, el de V762. Parece una cadena copiada. 

- De cada 100 lecturas con dato nuevo, 1.3 se aceptan y 98.7 chocan. Solo 0.24% de las 452,583 escrituras llegan al lector. El test "no hay hambre" pasa con `\> 0`. 

- El README dice que el escritor publica en una ranura "no observada". Las 82,548 carreras detectadas lo contradicen. Lo cierto es que escribe en una ranura que no es la última publicada. 

**Trampa educativa:** "0 desgarros" no es "cero posibles". Por la regla de tres, 0/1,098 solo garantiza una tasa \<0.27% (95%), y 0/218,417 garantiza \<0.0014%. Para afirmar cero hace falta argumento formal o model checking.

**Solución:**

- Un log canónico por plataforma. 

- Renombrar la métrica a "desgarros aceptados". 

- Fijar un umbral de progreso explícito. 

- Rediseñar según E3. 

### E3. Diseño del PMTP (alta, V + I)

1. **Carrera formal de datos.** Leer el payload con `memcpy` bajo un seqlock es una carrera según el modelo de memoria de C++ (Boehm, 2012). Lo verifiqué: TSan marcó la versión de carga simple y no marcó la versión con palabras `atomic` relaxed. TSan no modela `atomic\_thread\_fence`, y con `-O1` no vio la carrera, así que también tiene falsos negativos. 

2. **Hambre del lector.** El seqlock es lock-free (el sistema avanza) pero no wait-free. Con escritor rápido y payload grande, el lector reintenta casi siempre, como muestra tu 98.7%. 

3. **Choca con el zero-copy real.** Si el consumidor calcula en sitio sobre 8 MB, no puede deshacer efectos al detectar la carrera. 

4. **Prueba débil.** x86 es un modelo de memoria fuerte y esconde errores de orden. No se declara cuántos lectores hay, y el resto de la batería corre con `hilos=2`. 

**Ejemplos cotidianos:**

- Un seqlock es leer un cartel de precios mientras el tendero lo cambia. Releer la versión al final te avisa del cambio, pero pudiste copiar medio precio viejo y medio nuevo. 

- Un triple buffer son tres pizarras: una donde escribes, una lista para entregar y una en la mano del lector. Se intercambian por puntero y nadie toca la pizarra ajena. 

**Solución:**

- **1 consumidor:** triple buffer SPSC con `exchange` atómico. Lo implementé y probé: 0 desgarros, cero reintentos, orden monótono y limpio bajo TSan. 

- **N consumidores:** anillo de N+2 ranuras con contador de "pin" por ranura, donde el escritor salta las ranuras ancladas. Es un diseño conocido, no lo probé aquí. 

- **Si conservas el seqlock (solo payloads pequeños):** 

  - palabras atómicas relaxed; 

  - `alignas(64)` por ranura; 

  - `static\_assert(std::atomic\<uint64\_t\>::is\_always\_lock\_free)`, imprescindible para memoria compartida entre procesos; 

  - pruebas con ≥4 hilos, lectores lentos, ARM64, TSan y un model checker. 

### E4. Cayley-SMW: ortogonal no es retracción (alta, V)

**Trampa educativa:** "Cayley de una antisimétrica es ortogonal, luego es una retracción correcta". Una retracción de primer orden exige dR/dτ(0) = G.

Verificado:

- Con G tangente y K≥2, la derivada es **G + XXᵀG**, no G. El error es 0.32 con K=2 y 0.83 con K=5. Con K=1 coincide. 

- Con G euclídeo, la derivada es G − XGᵀX (error 5e-11), la dirección canónica de Wen–Yin. 

- Ejemplo mínimo: D=K=2, X=I, G=S antisimétrica. Entonces A=2S y el paso avanza el doble. 

- El tribunal acierta en que la ortogonalidad se conserva (1.3e-15), pero eso responde otra pregunta. 

**Solución:**

- **Dos modos explícitos.** `EUCLIDEAN\_GRADIENT` mantiene la fórmula actual. Ojo con el signo: mueve en +AX, así que para descenso pasa −G. `TANGENT` usa G′ = G − ½X(XᵀG) en U y V. Verificado: dR/dτ = G con error 3e-11 y ortogonalidad 1.3e-15. 

- **Test nuevo:** diferencias finitas de la derivada en τ=0, con K≥2 y parte antisimétrica no nula. 

### E5. La deriva sí se acumula en composición (alta, V)

El test "20000 pasos, deriva\_max=2.22e-16" es benigno. Resultados con referencia en long double:

| **Caso (20000 pasos)** | **Deriva** |
| :-: | :-: |
| y aleatorio, suma ingenua | ≤4.2e-16 |
| θ≈1e-3, y en el plano | ~8e-16 |
| θ=0.3, y en el plano, **sumas exactas** | **1.0e-13** |

El último caso es 5 veces el certificado (2.10e-14) y 7 veces el guardián (1.42e-14).

La causa es un sesgo sistemático: (1−versin)² + sin² − 1 = −1.14e-17 por paso, porque versin y sin son doubles redondeados. La predicción n·|e|/2 da 1.14e-13 y lo medido fue 1.0e-13. La deriva crece lineal, no como √n, y el guardián se excedería en unos 2,500 pasos.

Es como caminar con un paso mal calibrado por una millonésima: un paso no se nota, veinte mil sí. Neumaier y TwoSum corrigen sumas, no que (versin, sin) dejen de ser una rotación exacta ni el redondeo al guardar `y\_out`.

**Solución (verificada con D=1000):**

- **Reproyectar cada N pasos:** N=1000 da 5.2e-15 y N=100 da 6.5e-16, con costo ≈ 1/N de un giro. 

- **Elegir el par (versin, sin) entre vecinos en ulps** que minimice el sesgo baja la deriva a 2.7e-14. Ayuda 4 veces pero no basta sola. 

- **Documentar** que el certificado es por llamada, y añadir un test con y en el plano y θ grande. 

### E6. Tolerancias y ε (media-alta, V + I)

- Hay dos cotas para el mismo invariante: 1.42e-14 (guardián Rust) y 2.10e-14 (C++, "certificada"). Esta última es 94.6ε y no tiene derivación en los documentos. 

- `polydim\_default\_tolerances` no está en el dossier. El log solo muestra rechazos en |⟨u,u⟩−1|=2e-8 y |⟨y,y⟩−1|=2e-9. 

- Sensibilidad medida: el error de salida es aproximadamente 0.4 a 0.5 veces el de entrada. Con 1e-12 en ⟨u,u⟩ la salida da 3.8e-13, y con 1e-12 en ⟨y,y⟩ da 5.0e-13. Si las tolerancias de entrada superan ~2e-14, C++ acepta entradas cuya salida el guardián rechazaría. 

- El bloque V760 llama "épsilon de máquina exacto" a 4.44e-16. Eso es 2⁻⁵¹ = 2ε. Con ese valor, 64ε = 2.84e-14, que es mayor que 2.10e-14. 

**Solución:**

1. Definir ε = 2⁻⁵² y u = 2⁻⁵³. 

2. Derivar la cota como tol\_y + c·tol\_base + k·ε. 

3. Exportar una única constante en `polydim.h`. 

4. Poner las tolerancias por defecto ≤ ~1e-14, o hacer que el guardián dependa de ellas. 

5. Añadir pruebas de frontera: 0.5·tol aceptado y 2·tol rechazado. 

### E7. Betti-1 con DSU (media, V)

Un DSU cuenta **componentes conexas (β₀)**. La cuenta E−V+C (número ciclomático) tampoco es β₁ del complejo de Rips.

Verificado con cuatro puntos en un cuadrado:

- Con la escala igual al lado: DSU=1, ciclomático=1, β₁=1. 

- Con la escala igual a la diagonal: DSU=1, ciclomático=**3**, β₁=**0**. 

En 40 puntos sobre S² (β₁ real = 0), a distintas escalas salieron β₁ = 1, 7, 1 y 0.

Analogía: el DSU cuenta cuántas redes de carreteras hay desconectadas, no cuántas rotondas (agujeros) tienen. Además β₁(S^\{D−1\}) = 0 para D\>2, así que "β₁=0" no certifica cohesión. Si cohesión significa "una sola pieza", eso es β₀=1. A8 está marcado CERRADO sin prueba ni código a la vista.

**Solución:**

- Certificar cohesión con β₀ (DSU). 

- Si quieres β₁, calcularlo con reducción de matriz de borde sobre GF(2) o con homología persistente sobre submuestras. 

- Reabrir A8. 

### E8. DPI, "O(1)" y "cero tokens" (media, conceptual)

- **El DPI no se "viola"; se aplica.** La serialización no puede aumentar la información. Serializar float64 a texto con 17 dígitos es reversible, y ahí I(X;Z)=I(X;Y). Piensa en escanear un PDF sin pérdida frente a fotocopiar una fotocopia. El costo real del "gusano 1D" es latencia, ancho de banda y tokenización con pérdida cuando se pasa por lenguaje natural. 

- **"O(1)"** vale para el traspaso del puntero. Consumir el tensor sigue siendo O(D), con tráfico de coherencia de caché. 

- **"Cero tokens"** exige acceso a los estados internos de todos los agentes. Las APIs comerciales no los exponen, así que esto aplica a modelos de pesos abiertos. 

- **"Asintóticamente estable"** tiene sentido preciso en dinámica (Lyapunov). Lo que mides es estabilidad numérica. 

**Solución:** reescribir esas frases y acotar el alcance del protocolo.

### E9. Cobertura de pruebas y seguridad de memoria (media, A)

- **Códigos de error sin prueba visible:** 5 de 12 (−1, −2, −4, −11, −12). 

- **Hallazgos marcados CERRADO sin prueba en la telemetría:** A6, A8 y A10. 

- **`pivot\_min=1.000e+00` en las cuatro corridas Stiefel.** Es la firma de pasos casi nulos: con G=0, M=\[\[I, −τ/2·I\],\[0, I\]\] y los pivotes valen exactamente 1. Mi barrido de tamaño de paso te favorece, así que agrégalo como prueba. 

- **Rango probado frente a rango declarado:** el reto dice D hasta 1e7. Rodrigues se prueba hasta 1e6, y Stiefel hasta 8192 en tests y 65536 en benchmark. 

- **"Zero-leak, memory-safe":** no hay corridas de ASan, UBSan, LSan, Valgrind ni Miri. Faltan además fuzzing del ABI (null, D=0, D=2⁶³, K=0, K\>D, desalineados, solapes) y semillas: (4096,64) da 1.998e-15 en el log y 6.66e-16 en la tabla. 

### E10. Umbral de pivote relativo (media-baja, V + I)

La matriz M es siempre no singular: |det| ≥ 1 (medí log|det|=215), porque los autovalores son 1−i·(real). Por tanto `-5` solo puede ser un falso positivo o un NaN. El pivote LU mínimo se mantuvo en ≈0.49 mientras ‖M‖∞ crece como el cuadrado del paso.

Con `pivot\_rel` ≈ 1e-15 (lo que sugiere tu telemetría), aparecen rechazos falsos cuando la escala de G supera ~1e5 a 1e6 (D=512, K=8).

**Solución:** cambiar `-5` por:

- una comprobación de finitud; 

- el residuo hacia atrás ‖MZ−B‖; 

- la ortogonalidad a posteriori, que ya mides. 

### E11. Rendimiento (media, A + I)

Los factores contra V761 son correctos. Contra OpenBLAS, V762 **pierde 1.73 veces en (4096,64) y 1.23 veces en (16384,128)**, y gana en las otras tres filas. La frase "2.0× más rápido que OpenBLAS" vale solo para (4096,16).

Con mi cuenta de flops, V762 rinde entre 9.6 y 15 GFLOP/s en las cinco configuraciones, lo que parece un techo fijo. Los flags "obligatorios" no incluyen `-march` ni multiversionado. Si el kernel depende de AVX2 o AVX-512 necesita despacho por CPU, y si no, queda en SSE2. Faltan también CPU, hilos de OpenBLAS y rutinas usadas.

**Solución:**

- Separar la unidad de compilación de Neumaier (con `-ffp-contract=off`) de los bucles Stiefel (con FMA). 

- Multiversionar con `target\_clones`. 

- Tilear el Gram por D. 

- Despachar a `dsyrk` y `dgemm` para K≥~48 si hay BLAS. 

- Publicar una ficha de máquina. 

### E12. Contrato ABI (media-baja, I)

- El paso a R(+θ) es un cambio semántico con los mismos nombres de símbolo. Renombra o añade `polydim\_abi\_version()`. No hay prueba cruzada C++, Rust, Dart, Python y Triton, y el doc 04 no trae telemetría de Triton ni de Python. Añade vectores dorados. 

- No se documentan las reglas de solapamiento: ¿`y\_out==y` es legal? El límite K≤512 solo vive en el código, no en el header. 

- Verifica que M esté en el heap. En K=512 ocupa 8 MiB, y con MSVC el stack por defecto es de 1 MiB. 

- En Windows, `dllexport` en el header también lo aplican los consumidores. Usa `dllimport` al consumir. 

### E13. Higiene y credibilidad (baja, pero visible)

- **Fechas:** la carpeta `ENTREGA\_2026\_09\_19` es anterior a la auditoría del 2026-09-20 que dice cerrar. 

- **Idioma:** la política dice "Strict English" pero los docs 03 y 04 están en español. 

- **Tribunal:** "Cerebras Wafer-Scale AI" es hardware y "Perplexity / LAPACK Benchmark Engine" no es un modelo. Nombra modelo, versión, fecha y prompt de cada juez, e incluye sus salidas crudas. 

- **Trampa educativa:** la "unanimidad" de LLMs no es prueba. 

- **"SOTA":** exige líneas base (retracciones QR y polar, Cayley en geoopt o Manopt) y benchmarks públicos. 

### Orden de ataque recomendado

1. E1: manifiesto y fuentes. 

2. E3 y E2: nuevo PMTP y log único. 

3. E4: modo TANGENT. 

4. E5: reproyección o guardián de composición. 

5. E6: cota derivada. 

6. E7 y E8: correcciones de texto y topología. 

7. E9 a E13.

***`  
import io, json, os, sys, tempfile, contextlib`**

***`from pathlib import Path`**

***`sys.path.insert(0, str(Path(\_\_file\_\_).parent))`**

***`import run\_and\_log as rl`**

` `

***`def call(argv):`**

***`buf = io.StringIO()`**

***`with contextlib.redirect\_stdout(buf):`**

***`rc = rl.main(argv)`**

***`return rc, buf.getvalue()`**

` `

***`fails = 0`**

***`def check(name, cond, extra=""):`**

***`global fails`**

***`print(("PASS " if cond else "FAIL ") + name + (f" \{extra\}" if extra and not cond else ""))`**

***`fails += 0 if cond else 1`**

` `

***`\# 1) statistics vs scipy (Clopper-Pearson upper bound = Beta(k+1, n-k) quantile)`**

***`try:`**

***`from scipy.stats import beta`**

***`for k, n in \[(0, 1098), (0, 218417), (1, 1098), (5, 1000), (37, 100000)\]:`**

***`ref = 1.0 if k \>= n else beta.ppf(0.95, k + 1, n - k)`**

***`mine = rl.upper\_bound(k, n)`**

***`check(f"upper\_bound(\{k\},\{n\}) matches scipy", abs(mine - ref) \< 1e-9 \* max(1, ref) + 1e-12, f"\{mine\} vs \{ref\}")`**

***`except ImportError:`**

***`print("scipy not available: skipped CP cross-check")`**

***`check("k=0,n=1098 is about 3/n (rule of three)", abs(rl.upper\_bound(0, 1098) - 3 / 1098) \< 2e-5)`**

` `

***`with tempfile.TemporaryDirectory() as td:`**

***`os.chdir(td)`**

***`py = sys.executable`**

***`good = \[py, "-c", "print('writes=452583 reads\_accepted=1098 races=82548 torn\_accepted=0 ratio=1.31e-2')"\]`**

***`rc, out = call(\["--logs-dir", "logs", "run", "--name", "pmtp\_stress", "--seed", "42",`**

***`"--zero-bound", "torn\_accepted:reads\_accepted", "--min-counter", "reads\_accepted=1000", "--"\] + good)`**

***`check("good run passes", rc == 0, out)`**

***`j = json.loads(Path("logs/pmtp\_stress.json").read\_text())`**

***`check("counters parsed as ints/floats", j\["counters"\]\["reads\_accepted"\] == 1098 and abs(j\["counters"\]\["ratio"\] - 0.0131) \< 1e-9)`**

***`check("upper bound stored", 0.0026 \< j\["counters"\]\["torn\_accepted\_rate\_ub95"\] \< 0.0028)`**

***`log = Path("logs/pmtp\_stress.log").read\_text()`**

***`check("log has environment header, seed and verdict", "--- environment ---" in log and "seed : 42" in log and "VERDICT: PASS" in log)`**

` `

***`bad = \[py, "-c", "print('reads\_accepted=10 torn\_accepted=1')"\]`**

***`rc, out = call(\["--logs-dir", "logs", "run", "--name", "torn", "--zero-bound", "torn\_accepted:reads\_accepted",`**

***`"--min-counter", "reads\_accepted=1000", "--"\] + bad)`**

***`check("a torn read or too-few reads FAILS the run", rc == 1 and "FAIL min-counter" in out, out)`**

` `

***`Path("doc.md").write\_text("Reads: \{\{pmtp\_stress.reads\_accepted\}\}; races \{\{pmtp\_stress.races\}\}; ub \{\{pmtp\_stress.torn\_accepted\_rate\_ub95\}\}\\n")`**

***`rc, out = call(\["--logs-dir", "logs", "fill", "doc.md"\])`**

***`txt = Path("doc.md").read\_text()`**

***`check("placeholders replaced from json", rc == 0 and "Reads: 1,098; races 82,548" in txt, txt)`**

***`Path("doc2.md").write\_text("Made up number \{\{pmtp\_stress.does\_not\_exist\}\} and \{\{ghost.x\}\}\\n")`**

***`rc, out = call(\["--logs-dir", "logs", "fill", "doc2.md"\])`**

***`check("missing counter/log =\> exit 1 (documents cannot cite numbers no log produced)", rc == 1 and out.count("NO VALUE") == 2, out)`**

` `

***`print("\\n" + ("ALL PASSED" if fails == 0 else f"\{fails\} FAILED"))`**

***`sys.exit(1 if fails else 0)`**

` `

***Student's own research/engineering project POLYDIM EINSOF / LatentMAS (v47/v48 "MAÑANA"), separate from the POLYDIM V3.0 course — multi-language geometric computing stack sent out for external red-team AI audits**

***Detalles**

- ***Working on a separate project called POLYDIM EINSOF / LatentMAS, distinct from the POLYDIM V3.0 course task bank**

- ***Project is versioned iteratively (e.g., v47, v48 "MAÑANA") with dated delivery packages**

- ***Stack combines a JAX Float64 XLA engine, a C++20 SIMD kernel (OpenMP/AVX2/AVX-512), and a Rust 2024 C-ABI crate, tied together via ctypes FFI**

- ***Central technical claim is a "Cayley-SMW Matrix-Free" retraction on a hypersphere for high-dimensional latent spaces (D up to 10,000+)**

- ***Follows a self-described "Ley Ariel & Bulldog Critic Mode" protocol: sends the consolidated code/whitebook to multiple external AIs (Claude, GPT-4o, Kimi, DeepSeek) for adversarial, zero-sycophancy red-team audits before each delivery**

- ***Delivery packages bundle a whitebook, consolidated source, a "monolito" self-verification script, and a 100-check adversarial test suite**

- ***Versión POLYDIM V762 "Mpeleides Hardened Release" (dossier fechado 2026-09-20, carpeta ENTREGA\_2026\_09\_19\_V762): paquete de 4 archivos (README teoría, monolito de fuentes, veredictos del tribunal multi-IA, contrato de silicio/benchmarks) para auditoría externa; declara cerrar los hallazgos A1-A12 de V761 (PMTP triple búfer, compuerta de ortonormalidad, guardián Rust con cota 64ε, Dart FFI, Cayley-SMW vs OpenBLAS)**

- ***Pidió para V762 una auditoría estilo bulldog/red team que ataque el problema pero cuide al dueño del proyecto, lenta y verificada, sin alucinaciones**

- ***Decidió atacar en orden los hallazgos E1 a E13 de la auditoría de V762 (E1 = monolito sin código fuente incrustado; luego PMTP, Cayley-SMW, deriva en composición, tolerancias, topología, pruebas, rendimiento, ABI)**

***Student's own research/engineering project POLYDIM EINSOF / LatentMAS (v47/v48 "MAÑANA"), separate from the POLYDIM V3.0 course — multi-language geometric computing stack sent out for external red-team AI audits**

***Detalles**

- ***Working on a separate project called POLYDIM EINSOF / LatentMAS, distinct from the POLYDIM V3.0 course task bank**

- ***Project is versioned iteratively (e.g., v47, v48 "MAÑANA") with dated delivery packages**

- ***Stack combines a JAX Float64 XLA engine, a C++20 SIMD kernel (OpenMP/AVX2/AVX-512), and a Rust 2024 C-ABI crate, tied together via ctypes FFI**

- ***Central technical claim is a "Cayley-SMW Matrix-Free" retraction on a hypersphere for high-dimensional latent spaces (D up to 10,000+)**

- ***Follows a self-described "Ley Ariel & Bulldog Critic Mode" protocol: sends the consolidated code/whitebook to multiple external AIs (Claude, GPT-4o, Kimi, DeepSeek) for adversarial, zero-sycophancy red-team audits before each delivery**

- ***Delivery packages bundle a whitebook, consolidated source, a "monolito" self-verification script, and a 100-check adversarial test suite**

- ***Versión POLYDIM V762 "Mpeleides Hardened Release" (dossier fechado 2026-09-20, carpeta ENTREGA\_2026\_09\_19\_V762): paquete de 4 archivos (README teoría, monolito de fuentes, veredictos del tribunal multi-IA, contrato de silicio/benchmarks) para auditoría externa; declara cerrar los hallazgos A1-A12 de V761 (PMTP triple búfer, compuerta de ortonormalidad, guardián Rust con cota 64ε, Dart FFI, Cayley-SMW vs OpenBLAS)**

- ***Pidió para V762 una auditoría estilo bulldog/red team que ataque el problema pero cuide al dueño del proyecto, lenta y verificada, sin alucinaciones**

- ***Decidió atacar en orden los hallazgos E1 a E13 de la auditoría de V762 (E1 = monolito sin código fuente incrustado; luego PMTP, Cayley-SMW, deriva en composición, tolerancias, topología, pruebas, rendimiento, ABI)**

***`  
import io, json, os, sys, tempfile, contextlib`**

***`from pathlib import Path`**

***`sys.path.insert(0, str(Path(\_\_file\_\_).parent))`**

***`import run\_and\_log as rl`**

` `

***`def call(argv):`**

***`buf = io.StringIO()`**

***`with contextlib.redirect\_stdout(buf):`**

***`rc = rl.main(argv)`**

***`return rc, buf.getvalue()`**

` `

***`fails = 0`**

***`def check(name, cond, extra=""):`**

***`global fails`**

***`print(("PASS " if cond else "FAIL ") + name + (f" \{extra\}" if extra and not cond else ""))`**

***`fails += 0 if cond else 1`**

` `

***`\# 1) statistics vs scipy (Clopper-Pearson upper bound = Beta(k+1, n-k) quantile)`**

***`try:`**

***`from scipy.stats import beta`**

***`for k, n in \[(0, 1098), (0, 218417), (1, 1098), (5, 1000), (37, 100000)\]:`**

***`ref = 1.0 if k \>= n else beta.ppf(0.95, k + 1, n - k)`**

***`mine = rl.upper\_bound(k, n)`**

***`check(f"upper\_bound(\{k\},\{n\}) matches scipy", abs(mine - ref) \< 1e-9 \* max(1, ref) + 1e-12, f"\{mine\} vs \{ref\}")`**

***`except ImportError:`**

***`print("scipy not available: skipped CP cross-check")`**

***`check("k=0,n=1098 is about 3/n (rule of three)", abs(rl.upper\_bound(0, 1098) - 3 / 1098) \< 2e-5)`**

` `

***`with tempfile.TemporaryDirectory() as td:`**

***`os.chdir(td)`**

***`py = sys.executable`**

***`good = \[py, "-c", "print('writes=452583 reads\_accepted=1098 races=82548 torn\_accepted=0 ratio=1.31e-2')"\]`**

***`rc, out = call(\["--logs-dir", "logs", "run", "--name", "pmtp\_stress", "--seed", "42",`**

***`"--zero-bound", "torn\_accepted:reads\_accepted", "--min-counter", "reads\_accepted=1000", "--"\] + good)`**

***`check("good run passes", rc == 0, out)`**

***`j = json.loads(Path("logs/pmtp\_stress.json").read\_text())`**

***`check("counters parsed as ints/floats", j\["counters"\]\["reads\_accepted"\] == 1098 and abs(j\["counters"\]\["ratio"\] - 0.0131) \< 1e-9)`**

***`check("upper bound stored", 0.0026 \< j\["counters"\]\["torn\_accepted\_rate\_ub95"\] \< 0.0028)`**

***`log = Path("logs/pmtp\_stress.log").read\_text()`**

***`check("log has environment header, seed and verdict", "--- environment ---" in log and "seed : 42" in log and "VERDICT: PASS" in log)`**

` `

***`bad = \[py, "-c", "print('reads\_accepted=10 torn\_accepted=1')"\]`**

***`rc, out = call(\["--logs-dir", "logs", "run", "--name", "torn", "--zero-bound", "torn\_accepted:reads\_accepted",`**

***`"--min-counter", "reads\_accepted=1000", "--"\] + bad)`**

***`check("a torn read or too-few reads FAILS the run", rc == 1 and "FAIL min-counter" in out, out)`**

` `

***`Path("doc.md").write\_text("Reads: \{\{pmtp\_stress.reads\_accepted\}\}; races \{\{pmtp\_stress.races\}\}; ub \{\{pmtp\_stress.torn\_accepted\_rate\_ub95\}\}\\n")`**

***`rc, out = call(\["--logs-dir", "logs", "fill", "doc.md"\])`**

***`txt = Path("doc.md").read\_text()`**

***`check("placeholders replaced from json", rc == 0 and "Reads: 1,098; races 82,548" in txt, txt)`**

***`Path("doc2.md").write\_text("Made up number \{\{pmtp\_stress.does\_not\_exist\}\} and \{\{ghost.x\}\}\\n")`**

***`rc, out = call(\["--logs-dir", "logs", "fill", "doc2.md"\])`**

***`check("missing counter/log =\> exit 1 (documents cannot cite numbers no log produced)", rc == 1 and out.count("NO VALUE") == 2, out)`**

` `

***`print("\\n" + ("ALL PASSED" if fails == 0 else f"\{fails\} FAILED"))`**

***`sys.exit(1 if fails else 0)`**

` `

Designing a header for a data ring structure.

Working out lock-free shared-memory layout and slot pinning.

Verifying race safety with happens-before ordering proofs.

Planning stress tests for wait-freedom and multi-reader limits.

Adding a broken-mode test and drafting the C API header.

Defining status codes and slot layout for the control struct.

Implementing writer commit logic and reader acquire with pin validation.

Designing a test harness for the SPSC/multi-reader buffer.

***`// Memory model: every hand-off uses seq\_cst atomics. The Dekker-style pair`**

***`// writer: latest.store(new) ; pins\[s\].load() reader: pins\[s\].fetch\_add(1) ; latest.load()`**

***`// REQUIRES seq\_cst on all four operations (release/acquire alone would allow both sides to miss each other).`**

***`// The payload itself is plain memory: it is race-free because publication (release) / acquisition`**

***`// (acquire) and un-pin (release) / scan (acquire) order every access.`**

***`//`**

***`// All state lives in one POD block (no pointers) so it can be placed in shared memory between processes.`**

***`// Known limitation (documented, not solved): a reader process that dies while holding a pin leaks that slot.`**

***`\#pragma once`**

***`\#include \<atomic\>`**

***`\#include \<cstddef\>`**

***`\#include \<cstdint\>`**

***`\#include \<type\_traits\>`**

` `

***`namespace polydim::pmtp \{`**

` `

***`constexpr uint32\_t kMaxSlots = 32; // slot index is stored in 8 bits`**

***`constexpr uint32\_t kMagic = 0x33544D50u; // "PMT3"`**

` `

***`enum Status : int32\_t \{`**

***`kOk = 0,`**

***`kNullPointer = -1,`**

***`kInvalidArgument = -2,`**

***`kRetryExhausted = -6, // was POLYDIM\_ERR\_SEQLOCK\_RACE in V762: reader lost the race kMaxRetries times`**

***`kNoFreeSlot = -13, // n\_slots too small for the number of concurrent readers`**

***`kNoData = -14 // nothing published yet`**

***`\};`**

` `

***`struct alignas(64) Pin \{ std::atomic\<uint32\_t\> n; \};`**

` `

***`struct alignas(64) Control \{`**

***`uint32\_t magic;`**

***`uint32\_t n\_slots;`**

***`uint64\_t slot\_stride; // bytes between payload slots (informational, owned by the caller)`**

***`alignas(64) std::atomic\<uint64\_t\> latest; // (version \<\< 8) | slot ; 0 = nothing published`**

***`Pin pins\[kMaxSlots\];`**

***`\};`**

` `

***`static\_assert(std::atomic\<uint64\_t\>::is\_always\_lock\_free, "PMTP needs lock-free 64-bit atomics (shared memory)");`**

***`static\_assert(std::atomic\<uint32\_t\>::is\_always\_lock\_free, "PMTP needs lock-free 32-bit atomics (shared memory)");`**

***`static\_assert(std::is\_standard\_layout\<Control\>::value, "Control must be standard-layout for FFI");`**

***`static\_assert(alignof(Control) == 64, "one cache line per hot field");`**

` `

***`struct ReadHandle \{`**

***`uint64\_t version;`**

***`uint32\_t slot;`**

***`uint32\_t reserved;`**

***`\};`**

` `

***`inline int32\_t init(Control\* c, uint32\_t n\_slots, uint64\_t slot\_stride) \{`**

***`if (!c) return kNullPointer;`**

***`if (n\_slots \< 3 || n\_slots \> kMaxSlots) return kInvalidArgument;`**

***`c-\>magic = kMagic;`**

***`c-\>n\_slots = n\_slots;`**

***`c-\>slot\_stride = slot\_stride;`**

***`c-\>latest.store(0, std::memory\_order\_seq\_cst);`**

***`for (auto& p : c-\>pins) p.n.store(0, std::memory\_order\_relaxed);`**

***`std::atomic\_thread\_fence(std::memory\_order\_seq\_cst);`**

***`return kOk;`**

***`\}`**

` `

***`// ---- writer (exactly one thread/process) -------------------------------------------------------------`**

***`inline int32\_t begin\_write(Control\* c, uint32\_t\* slot\_out) \{`**

***`if (!c || !slot\_out) return kNullPointer;`**

***`const uint64\_t cur = c-\>latest.load(std::memory\_order\_seq\_cst);`**

***`const uint32\_t cur\_slot = cur ? static\_cast\<uint32\_t\>(cur & 0xFF) : 0xFFFFFFFFu;`**

***`const uint32\_t start = cur ? cur\_slot + 1 : 0;`**

***`for (uint32\_t i = 0; i \< c-\>n\_slots; ++i) \{`**

***`const uint32\_t s = (start + i) % c-\>n\_slots;`**

***`if (s == cur\_slot) continue;`**

***`\#ifdef PMTP\_BROKEN\_IGNORE\_PINS // negative control: the tests MUST catch this`**

***`\*slot\_out = s; return kOk;`**

***`\#else`**

***`if (c-\>pins\[s\].n.load(std::memory\_order\_seq\_cst) == 0) \{ \*slot\_out = s; return kOk; \}`**

***`\#endif`**

***`\}`**

***`return kNoFreeSlot;`**

***`\}`**

` `

***`inline int32\_t commit\_write(Control\* c, uint32\_t slot, uint64\_t\* version\_out) \{`**

***`if (!c) return kNullPointer;`**

***`if (slot \>= c-\>n\_slots) return kInvalidArgument;`**

***`const uint64\_t cur = c-\>latest.load(std::memory\_order\_relaxed); // single writer`**

***`const uint64\_t ver = (cur \>\> 8) + 1;`**

***`c-\>latest.store((ver \<\< 8) | slot, std::memory\_order\_seq\_cst);`**

***`if (version\_out) \*version\_out = ver;`**

***`return kOk;`**

***`\}`**

` `

***`inline uint64\_t next\_version(const Control\* c) \{ return (c-\>latest.load(std::memory\_order\_relaxed) \>\> 8) + 1; \}`**

` `

***`// ---- readers (any number, each holds at most one handle at a time) -----------------------------------`**

***`inline int32\_t acquire\_read(Control\* c, ReadHandle\* h, uint32\_t\* retries\_out = nullptr, uint32\_t max\_retries = 64) \{`**

***`if (!c || !h) return kNullPointer;`**

***`uint32\_t retries = 0;`**

***`for (; retries \< max\_retries; ++retries) \{`**

***`const uint64\_t p = c-\>latest.load(std::memory\_order\_seq\_cst);`**

***`if (p == 0) \{ if (retries\_out) \*retries\_out = retries; return kNoData; \}`**

***`const uint32\_t s = static\_cast\<uint32\_t\>(p & 0xFF);`**

***`c-\>pins\[s\].n.fetch\_add(1, std::memory\_order\_seq\_cst);`**

***`\#ifndef PMTP\_BROKEN\_NO\_VALIDATE // negative control`**

***`if (c-\>latest.load(std::memory\_order\_seq\_cst) != p) \{ // moved on (or ABA with a newer version)`**

***`c-\>pins\[s\].n.fetch\_sub(1, std::memory\_order\_release);`**

***`continue;`**

***`\}`**

***`\#endif`**

***`h-\>version = p \>\> 8; h-\>slot = s; h-\>reserved = 0;`**

***`if (retries\_out) \*retries\_out = retries;`**

***`return kOk;`**

***`\}`**

***`if (retries\_out) \*retries\_out = retries;`**

***`return kRetryExhausted;`**

***`\}`**

` `

***`inline void release\_read(Control\* c, const ReadHandle\* h) \{`**

***`c-\>pins\[h-\>slot\].n.fetch\_sub(1, std::memory\_order\_release);`**

***`\}`**

` `

***`inline uint64\_t latest\_version(const Control\* c) \{ return c-\>latest.load(std::memory\_order\_acquire) \>\> 8; \}`**

` `

***`// ---- exactly-one-writer / exactly-one-reader triple buffer ---------------------------------------------`**

***`// The payload area is owned by the caller: 3 slots. Wait-free on both sides, no retries, no pins.`**

***`struct TripleSPSC \{`**

***`static constexpr uint32\_t kDirty = 4;`**

***`std::atomic\<uint32\_t\> middle\{1\};`**

***`uint32\_t back = 0; // writer-private`**

***`uint32\_t front = 2; // reader-private`**

` `

***`uint32\_t write\_slot() const \{ return back; \}`**

***`void publish() \{ back = middle.exchange(back | kDirty, std::memory\_order\_acq\_rel) & 3u; \}`**

***`bool update() \{ // returns true if a newer slot was swapped in`**

***`if (middle.load(std::memory\_order\_relaxed) & kDirty) \{`**

***`front = middle.exchange(front, std::memory\_order\_acq\_rel) & 3u;`**

***`return true;`**

***`\}`**

***`return false;`**

***`\}`**

***`uint32\_t read\_slot() const \{ return front; \}`**

***`\};`**

***`static\_assert(std::atomic\<uint32\_t\>::is\_always\_lock\_free, "TripleSPSC needs lock-free atomics");`**

` `

***`\} // namespace polydim::pmtp`**

