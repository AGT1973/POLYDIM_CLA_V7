## **Auditoría Redteam Exhaustiva**


# 🐕 \***AUDITORÍA RED TEAM — POLYDIM V762 (Mpeleides Hardened)**

\***He leído los cuatro documentos línea por línea, recalculé cada constante, contrasté cada número de telemetría contra los dictámenes, y verifiqué el repositorio externo. Abajo va todo, ordenado por severidad, con evidencia citada y solución concreta. Distingo siempre entre hecho verificado, inferencia razonada y no verificable.**

## \***VERIFICACIÓN PREVIA**

\***El repositorio `github.com/AGT1973/POLYDIM\\\_CLA\\\_V7` existe (no es 404), pero muestra 0 estrellas, 0 forks, sin descripción y no pude enumerar su contenido desde aquí. Es decir: el código no es comprobable de forma independiente en este momento.**

## 🔴 \***CRÍTICO-1 — El "monolito de código fuente" no contiene código**

\***Evidencia: `02\\\_ALL\\\_SOURCE\\\_SCRIPTS\\\_MONOLITH.md` promete en su título *"Complete, unabridged source code"* (C++ Kernel, Rust Guard, Dart FFI, Python, Triton), pero las secciones 2–7 contienen únicamente stubs con punteros a rutas locales inaccesibles (`file:///E:/POLYDIM\\\_EINSOF/...`).**

\***Por qué es crítico: La pregunta central de auditoría es *"does the POLYDIM V762 implementation prove..."*. Sin el código, ningún de los cierres A1–A12 es verificable por un revisor independiente. Los dictámenes del tribunal (doc 03) juzgan código que el dossier no muestra. Es el agujero estructural del paquete.**

\***Solución (la mejor):**

1. \***Incluir el código inlined en el monolito (el archivo se llama literalmente `ALL\\\_SOURCE\\\_SCRIPTS\\\_MONOLITH`), o**

2. \***Como mínimo: hash SHA-256 de cada archivo fuente + commit SHA del repo + tag firmado, para que el tribunal pueda verificar integridad. Idealmente ambas.**

## 🔴 \***CRÍTICO-2 — Contradiccción numérica en el hallazgo estrella (A1)**

\***Evidencia:**

- \***Doc 01 y doc 03: *"0 undetected torn reads out of 218,417 validated reads"*.**

- \***Doc 04 (telemetría real): `lecturas\\\_ok=1098`, y el propio test dice *"desgarros NO detectados = 0 de 1098 lecturas validadas"*.**

\***Discrepancia: 218,417 vs 1,098. No hay derivación posible de uno desde otro (ni siquiera sumando carreras: 1,098 + 82,548 = 83,646). El número de marketing del tribunal no aparece en la telemetría. Un revisor adversario descalifica el dictamen entero por esto.**

\***Solución: Publicar el log completo de la corrida de estrés (o el contador acumulado de varias corridas con su metodología). Si 218,417 viene de N corridas, decirlo y mostrarlo.**

## 🔴 \***CRÍTICO-3 — La prueba insignia de D = 10⁶ parece ser vacía**

\***Evidencia (doc 04, sección `\\\[base\\\] Rodrigues`):**

\***plain**

```
\*\*\*\`D=1000    |1-||y'|| |=1.110e-16\`\*\*  
  
\*\*\*\`D=100000  |1-||y'|| |=2.220e-16\`\*\*  
  
\*\*\*\`D=1000000 |1-||y'|| |=0.000e+00   ← deriva EXACTAMENTE cero\`\*\*
```

\***Inferencia razonada: Una deriva exactamente 0.0 en punto flotante doble, en una operación que involucra `sin`, `cos` y productos internos a D = 10⁶, es la firma de un vector `y` construido ortogonal al plano \{u,v\} (o con soporte disjunto): la rotación es la identidad sobre sus componentes y todo el trabajo numérico ocurre en coordenadas exactas. El "happy path" de la escala insignia no ejercita la rotación.**

\***Por qué importa: El claim central es estabilidad asintótica en D = 10⁶–10⁷. La prueba que lo sostiene puede estar midiendo la identidad.**

\***Solución (la mejor): Rehacer el test con `y = (u + v)/√2` (máxima componente en el plano de rotación) en D = 10⁶ y D = 10⁷, y reportar deriva. Exigir `deriva \\\> 0` como sanity check de no-vacuidad del test. La prueba de composición geodésica (20,000 pasos, diff = 8.9e-16) es la buena del grupo — replicar ese criterio de construcción en el happy path.**

## 🔴 \***CRÍTICO-4 — El claim asintótico cubre hasta D = 10⁷; la evidencia llega a 10⁶ (y 65,536 en Stiefel)**

\***Evidencia:**

- \***Doc 01/objetivo: `D ≥ 10^6`, target hasta `D = 10,000,000`.**

- \***Telemetría real: Rodrigues máx D = 1,000,000; Stiefel máx (65536, 64); Dart D = 10⁶.**

\***La estabilidad asintótica no se demuestra extrapolando; se demuestra midiendo. A D = 10⁷ los buffers son ~320 MB solo para \{y, u, v, y\_out\} — el régimen de caché/NUMA cambia cualitativamente y es exactamente donde un error de indexación OpenMP (A10) o un ordenamiento de bucles (P1) se manifiesta.**

\***Solución: Correr la batería completa en D = 10⁷ (Linux, ≥ 2 nodos NUMA si aplica) y publicar. Sin eso, reformular el claim a "demostrado hasta D = 10⁶, diseñado para 10⁷".**

## 🔴 \***CRÍTICO-5 — Dos cotas de deriva incompatibles sin derivación**

\***Evidencia:**

- \***Doc 01/doc 03 (Rust Guard, A5): cota fija 64·ε = 1.42×10⁻¹⁴, "independiente de D".**

- \***Doc 04 (tests C++): cada test exige `deriva \\\<= 2.10e-14 (cota certificada)`.**

\***Verificación aritmética: 64 × 2.220446e-16 = 1.4211e-14 ✓ (correcto). Pero 2.10e-14 / ε ≈ 94.6ε — una constante sin justificación en ningún documento. ¿Es 2.10e-14 la cota contractual o 1.42e-14? Si el kernel C++ certifica 2.10e-14 pero el guardián Rust rechaza con 1.42e-14, hay una ventana (1.42–2.10)×10⁻¹⁴ donde C++ declara éxito y Rust fallo: inconsistencia de contrato entre capas.**

\***Solución (la mejor): Derivar 2.10e-14 formalmente (probablemente 64ε + margen de la compensación TwoSum del Pass 2 — si es eso, escríbalo), o unificar ambas capas a una sola cota. Documentar la constante en `polydim.h` junto al enum de errores.**

## 🟠 \***ALTO-6 — PMTP: "sin hambre" está mal soportada; y es pérdida de mensajes, no solo retry**

\***Evidencia (doc 04):**

\***plain**

```
\*\*\*\`escrituras=452583  lecturas\\\_ok=1098  carreras\\\_detectadas=82548  sin\\\_novedad=7845655\`\*\*
```

- \***Éxito del lector: 1,098 / (1,098 + 82,548) = 1.31 % de los intentos (el dato "0.35 % de 83646" de V761 en el mismo log lo confirma: 83,646 = 1,098 + 82,548).**

- \***El escritor publicó 452,583 estados; el lector validó 1,098. ~99.8 % de los estados publicados jamás fueron leídos.**

\***Análisis: El diseño 3-slot con seqlock tiene semántica de *latest-state snapshot* (correcto y estándar), pero el dossier lo presenta como bus de telemetría donde "el lector progresa". Con 1.31 % de tasa de captura, si el escritor publica más rápido que el lector, los mensajes intermedios se pierden por construcción. Además, 82,548 carreras → `rc=-6` significa que el camino de retry está muy caliente. Nada de esto es un bug por sí mismo; es una característica no declarada.**

\***Solución (la mejor): (a) Declarar explícitamente la semántica *snapshot/latest-wins* en `polydim.h` y el README. (b) Añadir telemetría de *message loss* (seqs saltados por el lector). (c) Si algún consumidor necesita entrega, añadir contador de lectores activos por slot (RCU-style) o secuencias monótonas con buffer de reordenamiento. (d) Re-explicar "sin hambre" con tasa de éxito, no solo con "progresa".**

## 🟠 \***ALTO-7 — Cherry-picking en el claim de OpenBLAS**

\***Evidencia: El tribunal (doc 03, §2.2) afirma: *"el C++ nativo es 2.0× más rápido que OpenBLAS en D=4096, K=16"*. Verificado: 1.77/0.89 ≈ 1.99 ✓ — para ese único punto. Pero la propia tabla del doc 04 muestra:**

\***Table**

| **Config** | **V762** | **OpenBLAS** | **¿Quién gana?** |
| :-: | :-: | :-: | :-: |
| (4096, 16) | 0.89 ms | 1.77 ms | V762, 2.0× |
| (4096, 64) | 9.90 ms | 5.71 ms | **OpenBLAS, 1.7×** |
| (16384, 32) | 9.68 ms | 14.99 ms | V762, 1.5× |
| (16384, 128) | 152.30 ms | 124.24 ms | **OpenBLAS, 1.23×** |
| (65536, 64) | 143.19 ms | 190.38 ms | V762, 1.3× |


\***Hecho verificado: V762 pierde contra OpenBLAS en 2 de 5 configuraciones (las de K grande). El dictamen selecciona el único punto favorable para la frase contundente. Los auditores que corrigieron su "sesgo de brecha" cometen el mismo sesgo en dirección opuesta.**

\***Solución: Reformular honestamente: *"V762 supera a OpenBLAS en 3 de 5 configuraciones, hasta 2.0× en (4096,16); OpenBLAS retiene ventaja en K ≥ 64"*. La tabla ya es honesta — el texto del tribunal no.**

## 🟠 \***ALTO-8 — Incoherencia de versión en el propio documento de objetivos**

\***Evidencia: El texto del objetivo central que usted me entrega dice *"POLYDIM V760"*; el dossier completo es V762 (con cierre de hallazgos de V761). Si el documento de objetivos/glosario que circula entre los jueces dice V760, hay material de auditoría mezclado entre versiones.**

\***Solución: Congelar un `VERSION` único en el encabezado de los 4 documentos y en `polydim\\\_build\\\_info()`, y regenerar el documento de objetivos.**

## 🟡 \***MEDIO-9 — Cobertura contractual vs. evidencia por plataforma**

\***La tabla de compiladores (doc 04) compromete GCC 15.2 Linux, MinGW GCC 14.2, MSVC 2026 y Rust 1.98.1. La telemetría mostrada corresponde a una sola corrida (banner de una sola plataforma, `hilos=2`). No hay evidencia de MSVC, ni de Windows, ni de LAPACK (mencionado en doc 01). Solución: publicar un log por plataforma comprometida o acotar el contrato.**

## 🟡 \***MEDIO-10 — "Zero-leak memory safety" sin evidencia de sanitizer**

\***En ningún documento aparece ASan/LSan/valgrind, ni `Miri` para el Rust. Los tests 26/26 prueban corrección numérica, no higiene de memoria; el claim de zero-leak es no verificable con lo entregado. Solución: añadir `-fsanitize=address,undefined` (GCC/Clang) y una corrida de Miri a la batería, publicar resultados.**

## 🟡 \***MEDIO-11 — A6 y A8 "cerrados" sin telemetría**

\***A6 (FTZ/DAZ) y A8 (Betti-1 en motor Sparse VR DSU con N ≥ 1000) se declaran resueltos, pero la batería de 26 tests no contiene ningún test de subnormales ni de homología (el test Rust `subnormal\\\_no\\\_es\\\_error` existe, ok, pero el motor VR DSU no aparece en la telemetría C++). Solución: incluir el test de conteo de subnormales y un test β₁ con N ≥ 1000 en `polydim\\\_selftest\\\_all()`.**

## 🟡 \***MEDIO-12 — Semántica de `panic = "unwind"` sobrevendida**

\***Doc 01: *"panic = 'unwind', guaranteeing deterministic memory safety across FFI boundaries"*. Precisión: `panic=unwind` habilita `catch\\\_unwind` para contención en la frontera FFI; no "garantiza" memory safety (eso lo dan las reglas de ownership + ausencia de `unsafe` malicioso, no verificable sin el código — ver CRÍTICO-1). Solución: corregir la redacción.**

## 🟡 \***MEDIO-13 — Tolerancias por defecto no publicadas**

\***`polydim\\\_default\\\_tolerances(D)` existe, pero ningún documento da los valores numéricos de `basis\\\_ortho`, `point\\\_norm`, `gram\\\_ortho`, `pivot\\\_rel`. Los tests implican `basis\\\_ortho \\\< 2e-8` (rechaza |⟨u,u⟩−1| = 2e-8) y `point\\\_norm \\\< 2e-9`. Un revisor no puede razonar si `point\\\_norm` por defecto es seguro en D = 10⁷ sin el valor. Solución: tabla de defaults en el README con justificación por dimensión.**

## 🟡 \***MEDIO-14 — Metodología de benchmarks V761 vs V762**

\***Las ganancias "21.5×, 2.8×, 3.3×..." comparan contra números de V761 presumiblemente de una corrida anterior, sin declarar si el hardware es idéntico. Y `hilos=2` es una elección arbitraria no justificada (¿por qué no 1, no 8, no nproc?). Solución: declarar hardware, versión de OpenBLAS, `OMP\\\_NUM\\\_THREADS` para ambos lados, y justificar o barrer el número de hilos.**

## 🟡 \***MEDIO-15 — `pivot\\\_min = 1.000e+00` en todos los tests Stiefel**

\***En las 4 corridas Stiefel el pivote mínimo es exactamente 1.0: las matrices nunca ejercitan el solver cerca del umbral. Solo el test sintético A9 ejerce el umbral relativo. Solución: añadir un caso con M mal condicionada (pivote ~ umbral) probando tanto el rechazo correcto como el éxite marginal.**

## 🟢 \***BAJOS**

- \***B-16: Política de idioma *"Strict English"* (doc 01) vs. docs 03/04 íntegramente en español. Para peer review internacional, elegir una política.**

- \***B-17: Benchmark Dart: mediana 4.27 ms, mín 3.41 ms → dispersión ~25 % sin explicación (JIT warmup debería estabilizar; declarar número de warmups).**

- \***B-18: En el banner, `BLAS=OFF (bucles nativos)`: dado ALTO-7, conviene aclarar si OpenBLAS referencia usó hilos = 2 o todos los cores (el tribunal dice que ahora se igualó a 2, pero el doc 04 no lo documenta).**

## ✅ \***Lo que sí verifiqué y está bien (crédito donde corresponde)**

1. \***La fórmula de Rodrigues con versine es correcta: con ⟨u,u⟩=⟨v,v⟩=1, ⟨u,v⟩=0, expandir −versin(θ) = cos θ − 1 reproduce la rotación canónica en el plano \{u,v\}. ✔**

2. \***La retracción de Cayley–SMW: W = GXᵀ − XGᵀ es antisimétrica ∀G ✔, y el Cayley de una matriz antisimétrica es ortogonal, luego YᵀY = XᵀQᵀQX = I algebraicamente ✔ (consistente con las mediciones ≤ 2.4e-15).**

3. \***64ε = 1.4211e-14 ✔ aritméticamente exacto.**

4. \***A9: 6.172 / 1e-15 = 6.172e15 ✔ coincide con el factor 6,171,537,881,911,400 citado.**

5. \***Aritmética del claim 2.0×: 1.77/0.89 = 1.99 ✔.**

6. \***Las refutaciones de alucinaciones del tribunal (§2.3 de doc 03) son correctas: β₁(S^\{D−1\}) = 0 para D \> 2 ✔; ARMv8 no tiene bit DAZ independiente ✔.**

7. \***La convención de rotación R(+θ) con nota de breaking change respecto a V761 está bien documentada en el header.**

## 🎯 \***PLAN DE ACCIÓN PRIORIZADO (lo que haría, en orden)**

\***Table**

| **\#** | **Acción** | **Cierra** |
| :-: | :-: | :-: |
| 1 | Inlinear el código real en el doc 02 + SHA-256 por archivo + commit SHA | CRÍTICO-1, MEDIO-10, MEDIO-12 |
| 2 | Reconciliar 218,417 vs 1,098 con log completo de estrés PMTP | CRÍTICO-2 |
| 3 | Rehacer happy path con y ∈ span\{u,v\} en D = 10⁶ **y 10⁷**; exigir deriva \> 0 | CRÍTICO-3, CRÍTICO-4 |
| 4 | Derivar o unificar las cotas 1.42e-14 / 2.10e-14; documentar en `polydim.h` | CRÍTICO-5 |
| 5 | Declarar semántica snapshot del PMTP + métrica de pérdida; reformular "sin hambre" | ALTO-6 |
| 6 | Corregir el claim OpenBLAS: "3 de 5 configuraciones" | ALTO-7 |
| 7 | Unificar versión V762 en todos los docs | ALTO-8 |
| 8 | Añadir ASan/UBSan/Miri a la batería; publicar logs por plataforma | MEDIO-9, MEDIO-10 |
| 9 | Publicar tabla de tolerancias default + tests de subnormal/β₁ con telemetría | MEDIO-11, MEDIO-13 |


\***Mi recomendación única si solo puede hacer una cosa: la \#1. Todo lo demás es secundario mientras el código no sea verificable — los 12 dictámenes "CERRADO" del tribunal son, hoy, actos de fe bien redactados.**

\***¿Quieres que profundice en alguno de estos (por ejemplo, rediseñar el test de D = 10⁷, o escribir la declaración de semántica del PMTP), o que prepare el checklist de verificación para cuando el código real esté disponible?**

\***necesito todo lo que proponers y luego mostrame sota en que mejorar confirmas que no son alucinaciones? luego si a todas las opciones que me puedas dar. una detrás de otra en bucle hasta el limite de tus entregas o no encontrar mas errores. el  propósito es darle cierre  a los problema sota no encontrados. continua evaluando problemas y soluciones en bucles cada vez mas profundamente. Hay mucho sota. no solo evalúa con tus conocimientos y sesgos. busca errores mas allá de tu programación básica, dame soluciones. se un bulldog que ataca al problema pero ayuda al dueño. se un redteam que ataca el problema pero respeta y cuida el que les da el trabajo. /goal busca todo problema, encuentra soluciones dame la mejor continua con el siguiente error. muestras los códigos en pantalla, nunca por adjuntos. /goal profundiza ciclos necesarios para pasar a industria \#\#atención\#\# evalúa las respuestas para no dar alucinaciones. Nuestro debe ser "matemáticamente SOTA en papel" a ser industrialmente inquebrantable en silicio real. --------------------------. confirmas que no son alucinaciones?"continua profundiza, se sota, evalua alucinaciones, entiende el contexto"**

\***Edit**

\***Copy**

\***Share**

\***Documenting PMTP API Payload Location and PolydimTolerances Flag Semantics**

\***Python**

\***c**

\***cpp**

\***Python**

\***c**

\***c**

\***yaml**

\***Python**

\***cpp**

\***cpp**

\***c**

# ✅ \***CONFIRMACIÓN ANTI-ALUCINACIÓN (primero, como exiges)**

\***Antes de entregar, clasifico cada hallazgo anterior por su clase epistémica, porque esa es la única forma honesta de confirmar:**

\***Table**

| **Hallazgo** | **Clase** | **Base** |
| :-: | :-: | :-: |
| CRÍTICO-1 (monolito sin código) | **Evidencia directa** | El doc 02 contiene solo stubs `file:///E:/...` — lo cité literalmente |
| CRÍTICO-2 (218,417 vs 1,098) | **Evidencia directa** | Ambos números están impresos en los docs; la aritmética no los relaciona |
| CRÍTICO-3 (deriva 0.0 en D=10⁶) | **Inferencia razonada** (declarada como tal) | La conclusión "test vacío" es inferencia; el hecho "deriva exactamente 0.0" es evidencia |
| CRÍTICO-4 (D=10⁷ no probado) | **Evidencia directa** | Telemetría máx = 10⁶ (Rodrigues), 65,536 (Stiefel) |
| CRÍTICO-5 (1.42e-14 vs 2.10e-14) | **Evidencia + aritmética verificada** | 64ε = 1.4211e-14 ✔; 2.10e-14 = 94.6ε sin derivación ✔ |
| ALTO-6 (1.31% captura PMTP) | **Evidencia + aritmética** | 1098+82548 = 83,646 ✔; 1098/83,646 = 1.31% ✔ |
| ALTO-7 (cherry-picking OpenBLAS) | **Evidencia directa** | La propia tabla del doc 04 muestra 2 configs donde V762 pierde |
| ALTO-8 / MEDIO-9..15 / BAJOS | **Evidencia directa** | Citas textuales de los documentos |


\***Límite declarado de mi auditoría: no he visto el código fuente real (no está en el dossier). Todo lo que propongo a continuación es parche de referencia contra la API pública documentada en `polydim.h`, nunca una afirmación sobre lo que "su código hace" internamente. Donde un riesgo requiere verificación interna, lo marco `\\\[VERIFICAR EN CÓDIGO\\\]`. Esa es mi garantía contra alucinación: no afirmo hechos sobre código que no puedo leer.**

# ═══ \***ENTREGA 1 — Manifest de integridad (cierra CRÍTICO-1) ═══**

\***Python**

```
\*\*\*\`\\\#!/usr/bin/env python3\`\*\*\*  
  
\*\*\*\`\\\# tools/manifest.py — genera y verifica el manifest de integridad V762\`\*\*\*  
  
\*\*\*\`\\\# Uso:  python tools/manifest.py make   (antes de publicar)\`\*\*\*  
  
\*\*\*\`\\\#       python tools/manifest.py verify (en CI del revisor)\`\*\*\*  
  
\*\*\*\`import hashlib, json, pathlib, subprocess, sys\`\*\*  
  
  
\*\*\*\`ROOT = pathlib.Path(\\\_\\\_file\\\_\\\_).resolve().parent.parent\`\*\*  
  
\*\*\*\`PATTERNS = \\\["include/\\\*\\\*/\\\*.h", "src/\\\*\\\*/\\\*.cpp", "rust/src/\\\*\\\*/\\\*.rs",\`\*\*  
  
\`            \*\*\*"dart/\\\*\\\*/\\\*.dart", "tests/\\\*\\\*/\\\*.cpp", "polydim\\\_\\\*.py"\\\]\`\*\*  
  
  
\*\*\*\`def sha256(p: pathlib.Path) -\\\> str:\`\*\*  
  
\`    \*\*\*h = hashlib.sha256()\`\*\*  
  
\`    \*\*\*h.update(p.read\\\_bytes())\`\*\*  
  
\`    \*\*\*return h.hexdigest()\`\*\*  
  
  
\*\*\*\`def git\\\_commit() -\\\> str:\`\*\*  
  
\`    \*\*\*return subprocess.run(\\\["git", "rev-parse", "HEAD"\\\],\`\*\*  
  
\`                          \*\*\*capture\\\_output=True, text=True, cwd=ROOT).stdout.strip()\`\*\*  
  
  
\*\*\*\`def collect():\`\*\*  
  
\`    \*\*\*files = \\\{\\\}\`\*\*  
  
\`    \*\*\*for pat in PATTERNS:\`\*\*  
  
\`        \*\*\*for p in sorted(ROOT.glob(pat)):\`\*\*  
  
\`            \*\*\*if p.is\\\_file():\`\*\*  
  
\`                \*\*\*files\\\[str(p.relative\\\_to(ROOT)).replace("\\\\\\\\", "/")\\\] = sha256(p)\`\*\*  
  
\`    \*\*\*return files\`\*\*  
  
  
\*\*\*\`if sys.argv\\\[1\\\] == "make":\`\*\*  
  
\`    \*\*\*manifest = \\\{"version": "V762", "commit": git\\\_commit(), "files": collect()\\\}\`\*\*  
  
\`    \*\*\*(ROOT / "INTEGRITY\\\_MANIFEST.json").write\\\_text(json.dumps(manifest, indent=2))\`\*\*  
  
\`    \*\*\*print(f"Manifest escrito: \\\{len(manifest\\\['files'\\\])\\\} archivos, commit \\\{manifest\\\['commit'\\\]\\\[:12\\\]\\\}")\`\*\*  
  
\*\*\*\`elif sys.argv\\\[1\\\] == "verify":\`\*\*  
  
\`    \*\*\*m = json.loads((ROOT / "INTEGRITY\\\_MANIFEST.json").read\\\_text())\`\*\*  
  
\`    \*\*\*assert m\\\["commit"\\\] == git\\\_commit(), f"commit drift: \\\{m\\\['commit'\\\]\\\} vs \\\{git\\\_commit()\\\}"\`\*\*  
  
\`    \*\*\*now = collect()\`\*\*  
  
\`    \*\*\*assert set(now) == set(m\\\["files"\\\]), "conjunto de archivos driftó"\`\*\*  
  
\`    \*\*\*bad = \\\[f for f in m\\\["files"\\\] if now\\\[f\\\] != m\\\["files"\\\]\\\[f\\\]\\\]\`\*\*  
  
\`    \*\*\*if bad:\`\*\*  
  
\`        \*\*\*print("ARCHIVOS MODIFICADOS:"); \\\[print(" ", f) for f in bad\\\]; sys.exit(1)\`\*\*  
  
\`    \*\*\*print(f"INTEGRIDAD OK: \\\{len(now)\\\} archivos verificados contra commit \\\{m\\\['commit'\\\]\\\[:12\\\]\\\}")\`\*\*
```

\***Además: el repo debe llevar tag firmado (`git tag -s v762.0`) y el doc 03 debe citar el commit. Hasta que esto exista, ningún dictamen es reproducible.**

# ═══ \***ENTREGA 2 — PMTP: semántica declarada + contadores reconciliados + implementación libre de data-race (cierra CRÍTICO-2, ALTO-6) ═══**

\***Texto a insertar en `polydim.h` (semántica contractual):**

\***c**

```
\*\*\*\`/\\\* SEMÁNTICA PMTP (obligatoria, V762):\`\*\*\*  
  
\` \*\*\*\\\*   - Latest-state snapshot, NO message stream. El escritor puede sobrescribir\`\*\*\*  
  
\` \*\*\*\\\*     una ranura antes de que cualquier lector la observe: los estados\`\*\*\*  
  
\` \*\*\*\\\*     intermedios se pierden POR DISEÑO.\`\*\*\*  
  
\` \*\*\*\\\*   - El lector debe tolerar POLYDIM\\\_ERR\\\_SEQLOCK\\\_RACE (-6) como evento normal\`\*\*\*  
  
\` \*\*\*\\\*     de retry, no como error fatal.\`\*\*\*  
  
\` \*\*\*\\\*   - Métricas obligatorias de telemetría (ver PMTP\\\_Metrics): seqs\\\_saltados\`\*\*\*  
  
\` \*\*\*\\\*     mide la pérdida de estados; su umbral aceptable es decisión del\`\*\*\*  
  
\` \*\*\*\\\*     consumidor, no del kernel. \\\*/\`\*\*\*
```

\***Referencia endurecida — race-free bajo el estándar C++20. `\\\[VERIFICAR EN CÓDIGO\\\]` que el kernel real cumple esto; un seqlock clásico con lectura de datos no-atómica es *data race* = UB en C++ abstracto aunque "funcione" en x86:**

\***cpp**

```
\*\*\*\`// reference/pmtp\\\_seqlock\\\_ref.hpp — SPMC 3-slot, race-free, C++20\`\*\*\*  
  
\*\*\*\`\\\#include \\\<atomic\\\>\`\*\*  
  
\*\*\*\`\\\#include \\\<cstdint\\\>\`\*\*  
  
\*\*\*\`\\\#include \\\<cstring\\\>\`\*\*  
  
\*\*\*\`\\\#include \\\<thread\\\>\`\*\*  
  
  
\*\*\*\`namespace polydim\\\_ref \\\{\`\*\*  
  
  
\*\*\*\`constexpr uint64\\\_t PMTP\\\_WORDS = 1024;            \*// 8 KiB de payload por ranura\`\*\*\*  
  
\*\*\*\`constexpr uint64\\\_t PMTP\\\_SLOTS = 3;\`\*\*  
  
  
\*\*\*\`struct alignas(64) Slot \\\{\`\*\*  
  
\`    \*\*\*alignas(64) std::atomic\\\<uint64\\\_t\\\> words\\\[PMTP\\\_WORDS\\\];\`\*\*  
  
\`    \*\*\*alignas(64) std::atomic\\\<uint64\\\_t\\\> seq\\\{0\\\};    \*// par = estable, impar = escribiendo\`\*\*\*  
  
\*\*\*\`\\\};\`\*\*  
  
  
\*\*\*\`class Pmtp \\\{\`\*\*  
  
\*\*\*\`public:\`\*\*  
  
\`    \*\*\*// ---- escritor (único) ----\`\*\*\*  
  
\`    \*\*\*uint64\\\_t begin\\\_write() \\\{\`\*\*  
  
\`        \*\*\*uint64\\\_t s = wr\\\_.fetch\\\_add(2, std::memory\\\_order\\\_relaxed) + 2;\`\*\*  
  
\`        \*\*\*slot\\\_ = (s / 2) % PMTP\\\_SLOTS;\`\*\*  
  
\`        \*\*\*slots\\\_\\\[slot\\\_\\\].seq.store(s + 1, std::memory\\\_order\\\_relaxed); \*// impar: en progreso\`\*\*\*  
  
\`        \*\*\*return slot\\\_;\`\*\*  
  
\`    \*\*\*\\\}\`\*\*  
  
\`    \*\*\*void write\\\_word(uint64\\\_t i, uint64\\\_t w) \\\{\`\*\*  
  
\`        \*\*\*slots\\\_\\\[slot\\\_\\\].words\\\[i\\\].store(w, std::memory\\\_order\\\_relaxed);\`\*\*  
  
\`    \*\*\*\\\}\`\*\*  
  
\`    \*\*\*void commit() \\\{\`\*\*  
  
\`        \*\*\*std::atomic\\\_thread\\\_fence(std::memory\\\_order\\\_release);       \*// datos antes que seq\`\*\*\*  
  
\`        \*\*\*slots\\\_\\\[slot\\\_\\\].seq.store(wr\\\_.load(std::memory\\\_order\\\_relaxed),\`\*\*  
  
\`                                \*\*\*std::memory\\\_order\\\_release);          \*// par: publicado\`\*\*\*  
  
\`    \*\*\*\\\}\`\*\*  
  
  
\`    \*\*\*// ---- lectores (muchos) ----\`\*\*\*  
  
\`    \*\*\*// Devuelve true si la snapshot es consistente; false si debe reintentar.\`\*\*\*  
  
\`    \*\*\*bool read(uint64\\\_t\\\* out \*/\\\* PMTP\\\_WORDS de salida \\\*/\*, uint64\\\_t\\\* seq\\\_out) \\\{\`\*\*  
  
\`        \*\*\*for (;;) \\\{\`\*\*  
  
\`            \*\*\*uint64\\\_t s1 = head\\\_seq\\\_.load(std::memory\\\_order\\\_acquire);\`\*\*  
  
\`            \*\*\*if (s1 & 1) \\\{ backoff(); continue; \\\}                     \*// escritor activo\`\*\*\*  
  
\`            \*\*\*uint64\\\_t sl = (s1 / 2) % PMTP\\\_SLOTS;\`\*\*  
  
\`            \*\*\*Slot& S = slots\\\_\\\[sl\\\];\`\*\*  
  
\`            \*\*\*if (S.seq.load(std::memory\\\_order\\\_acquire) != s1) \\\{ backoff(); continue; \\\}\`\*\*  
  
\`            \*\*\*for (uint64\\\_t i = 0; i \\\< PMTP\\\_WORDS; i++)\`\*\*  
  
\`                \*\*\*out\\\[i\\\] = S.words\\\[i\\\].load(std::memory\\\_order\\\_relaxed); \*// race-free: atómicas\`\*\*\*  
  
\`            \*\*\*std::atomic\\\_thread\\\_fence(std::memory\\\_order\\\_acquire);     \*// barrera de validación\`\*\*\*  
  
\`            \*\*\*uint64\\\_t s2 = S.seq.load(std::memory\\\_order\\\_relaxed);\`\*\*  
  
\`            \*\*\*if (s2 != s1) continue;                                  \*// tocado durante lectura\`\*\*\*  
  
\`            \*\*\*\\\*seq\\\_out = s1;\`\*\*  
  
\`            \*\*\*return true;\`\*\*  
  
\`        \*\*\*\\\}\`\*\*  
  
\`    \*\*\*\\\}\`\*\*  
  
\*\*\*\`private:\`\*\*  
  
\`    \*\*\*static void backoff() \\\{ std::this\\\_thread::yield(); \\\}\`\*\*  
  
\`    \*\*\*Slot slots\\\_\\\[PMTP\\\_SLOTS\\\];\`\*\*  
  
\`    \*\*\*std::atomic\\\<uint64\\\_t\\\> wr\\\_\\\{0\\\};\`\*\*  
  
\`    \*\*\*std::atomic\\\<uint64\\\_t\\\> head\\\_seq\\\_\\\{0\\\};   \*// cache del último seq publicado (opcional)\`\*\*\*  
  
\`    \*\*\*uint64\\\_t slot\\\_ = 0;\`\*\*  
  
\*\*\*\`\\\};\`\*\*  
  
  
\*\*\*\`\\\} \*// namespace\`\*\*\*
```

\***Arnes de estrés con contadores reconciliados (el 218,417 vs 1,098 no vuelve a ocurrir porque cada contador tiene definición única y se imprime junto):**

\***cpp**

```
\*\*\*\`// tests/pmtp\\\_stress\\\_metrics.cpp — contadores canónicos (definiciones cerradas)\`\*\*\*  
  
\*\*\*\`struct PmtpMetrics \\\{\`\*\*  
  
\`    \*\*\*std::atomic\\\<uint64\\\_t\\\> writes\\\_committed\\\{0\\\};  \*// commit\\\_write que devolvieron 0\`\*\*\*  
  
\`    \*\*\*std::atomic\\\<uint64\\\_t\\\> reads\\\_validated\\\{0\\\};   \*// validate\\\_read == 0 (snapshot buena)\`\*\*\*  
  
\`    \*\*\*std::atomic\\\<uint64\\\_t\\\> reads\\\_raced\\\{0\\\};       \*// validate\\\_read == -6\`\*\*\*  
  
\`    \*\*\*std::atomic\\\<uint64\\\_t\\\> polls\\\_no\\\_news\\\{0\\\};     \*// acquire sin novedad (seq repetido)\`\*\*\*  
  
\`    \*\*\*std::atomic\\\<uint64\\\_t\\\> torn\\\_detected\\\{0\\\};     \*// datos cambiaron entre acquire y validate\`\*\*\*  
  
\`    \*\*\*std::atomic\\\<uint64\\\_t\\\> max\\\_seq\\\_gap\\\{0\\\};       \*// max(s\\\_nuevo - s\\\_previo observado)\`\*\*\*  
  
\`    \*\*\*std::atomic\\\<uint64\\\_t\\\> last\\\_seq\\\{0\\\};\`\*\*  
  
\*\*\*\`\\\};\`\*\*  
  
\*\*\*\`// Invariantes que el test debe IMPRIMIR y ASERTAR:\`\*\*\*  
  
\*\*\*\`//   reads\\\_validated + reads\\\_raced == total de intentos con novedad\`\*\*\*  
  
\*\*\*\`//   seqs\\\_saltados   == writes\\\_committed - reads\\\_validated  (pérdida, aceptada pero MEDIDA)\`\*\*\*  
  
\*\*\*\`//   torn\\\_detected   == 0  (nunca se aceptó una lectura desgarrada)\`\*\*\*  
  
\*\*\*\`// Regla de publicación: el número que va al tribunal es reads\\\_validated, con su log.\`\*\*\*
```

\***Y la corrección textual al tribunal (doc 03, A1), verificable contra telemetría:**

> ***"Confirmado y Resuelto. 0 lecturas desgarradas aceptadas en 1,098 snapshots validados (corrida única, log completo archivado). El lector capturó el 1.31% de los estados publicados; la semántica del bus es latest-state snapshot y la pérdida de estados intermedios es por diseño (métrica `seqs\\\_saltados` expuesta)."***

# ═══ \***ENTREGA 3 — Happy path NO vacío + cobertura D = 10⁷ (cierra CRÍTICO-3, CRÍTICO-4) ═══**

\***cpp**

```
\*\*\*\`// tests/rodrigues\\\_nonvacuous\\\_v762.cpp — contra la API pública de polydim.h\`\*\*\*  
  
\*\*\*\`\\\#include "polydim.h"\`\*\*  
  
\*\*\*\`\\\#include \\\<cmath\\\>\`\*\*  
  
\*\*\*\`\\\#include \\\<cstdio\\\>\`\*\*  
  
\*\*\*\`\\\#include \\\<vector\\\>\`\*\*  
  
\*\*\*\`\\\#include \\\<algorithm\\\>\`\*\*  
  
  
\*\*\*\`int main() \\\{\`\*\*  
  
\`    \*\*\*const double EPS   = 0x1p-52;                 \*// 2.220446049250313e-16\`\*\*\*  
  
\`    \*\*\*const double BOUND = 64.0 \\\* EPS;              \*// 1.4211e-14 (única cota, ver Entrega 4)\`\*\*\*  
  
\`    \*\*\*const uint64\\\_t Ds\\\[\\\] = \\\{1000, 100000, 1000000, 10000000\\\}; \*// 10^7: ~320 MB de buffers\`\*\*\*  
  
  
\`    \*\*\*for (uint64\\\_t D : Ds) \\\{\`\*\*  
  
\`        \*\*\*std::vector\\\<double\\\> u(D, 0.0), v(D, 0.0), y(D), yp(D);\`\*\*  
  
\`        \*\*\*u\\\[0\\\] = 1.0; v\\\[1\\\] = 1.0;                   \*// base canónica: ortonormalidad EXACTA\`\*\*\*  
  
\`        \*\*\*// y DENTRO del plano \\\{u,v\\\}: ejercita versin, sin, y ambos coeficientes\`\*\*\*  
  
\`        \*\*\*const double s2 = std::sqrt(2.0);\`\*\*  
  
\`        \*\*\*for (uint64\\\_t i = 0; i \\\< D; i++) y\\\[i\\\] = (u\\\[i\\\] + v\\\[i\\\]) / s2;\`\*\*  
  
  
\`        \*\*\*PolydimReport rep; polydim\\\_report\\\_init(&rep);\`\*\*  
  
\`        \*\*\*if (polydim\\\_project\\\_sphere\\\_f64(y.data(), y.data(), D, &rep) != 0) return 2;\`\*\*  
  
\`        \*\*\*PolydimTolerances tol = polydim\\\_default\\\_tolerances(D);\`\*\*  
  
\`        \*\*\*const double theta = 0.7;\`\*\*  
  
\`        \*\*\*int rc = polydim\\\_rodrigues\\\_geodesic\\\_f64(y.data(), u.data(), v.data(),\`\*\*  
  
\`                                                \*\*\*yp.data(), theta, D, &tol, &rep);\`\*\*  
  
\`        \*\*\*if (rc != 0) \\\{ printf("D=%llu rc=%d\\\\n",(unsigned long long)D, rc); return 3; \\\}\`\*\*  
  
  
\`        \*\*\*// --- ASERCION DE NO-VACUIDAD: la rotación DEBE haber movido el punto ---\`\*\*\*  
  
\`        \*\*\*double moved = 0.0;\`\*\*  
  
\`        \*\*\*for (uint64\\\_t i = 0; i \\\< D; i++) moved = std::max(moved, std::fabs(yp\\\[i\\\] - y\\\[i\\\]));\`\*\*  
  
\`        \*\*\*// teórico: |y'-y| = sqrt(versin^2 + sin^2) ~ 0.688 para theta=0.7\`\*\*\*  
  
\`        \*\*\*if (moved \\\< 0.1) \\\{\`\*\*  
  
\`            \*\*\*printf("D=%llu TEST VACIO (moved=%.3e) — la rotación no tocó a y\\\\n",\`\*\*  
  
\`                   \*\*\*(unsigned long long)D, moved); return 4;\`\*\*  
  
\`        \*\*\*\\\}\`\*\*  
  
\`        \*\*\*// --- cota compuesta: deriva de entrada (puerta) + cota certificada ---\`\*\*\*  
  
\`        \*\*\*double gate = rep.point\\\_norm\\\_err;         \*// error de norma ADMITIDO por la puerta\`\*\*\*  
  
\`        \*\*\*double drift = std::fabs(rep.out\\\_norm\\\_err);\`\*\*  
  
\`        \*\*\*bool ok = (drift \\\<= gate + BOUND);\`\*\*  
  
\`        \*\*\*printf("D=%-9llu deriva=%.3e gate=%.3e ratio=%.1fe movio=%.3e %s\\\\n",\`\*\*  
  
\`               \*\*\*(unsigned long long)D, drift, gate, drift/EPS, moved, ok?"\\\[OK\\\]":"\\\[FAIL\\\]");\`\*\*  
  
\`        \*\*\*if (!ok) return 5;\`\*\*  
  
\`    \*\*\*\\\}\`\*\*  
  
\`    \*\*\*printf("NOTA ejecucion D=1e7: numactl --interleave=all ./test "\`\*\*  
  
\`           \*\*\*"(buffers ~320 MB; first-touch NUMA del caller)\\\\n");\`\*\*  
  
\`    \*\*\*return 0;\`\*\*  
  
\*\*\*\`\\\}\`\*\*
```

\***Puntos clave: `moved \\\< 0.1` falla el test si la rotación es la identidad (mata el vacuidad de D=10⁶); la cota es compuesta `gate + 64ε` (fundamentado en la Entrega 4 / hallazgo L3-3 más abajo); D=10⁷ queda dentro de la batería.**

# ═══ \***ENTREGA 4 — Cota unificada con derivación escrita (cierra CRÍTICO-5) ═══**

\***Parche al contrato público:**

\***c**

```
\*\*\*\`/\\\* ---- Cota certificada única (fuente de verdad para C++, Rust, Dart, Python) ---- \\\*/\`\*\*\*  
  
\*\*\*\`\\\#define POLYDIM\\\_EPS64          0x1p-52                    \*/\\\* 2.220446049250313e-16      \\\*/\`\*\*\*  
  
\*\*\*\`\\\#define POLYDIM\\\_DRIFT\\\_BOUND    (64.0 \\\* POLYDIM\\\_EPS64)    \*/\\\* 1.4211e-14, indep. de D    \\\*/\`\*\*\*  
  
\*\*\*\`/\\\* Borrar del codebase la constante 2.10e-14 (= 94.6e, sin derivación).            \\\*/\`\*\*\*
```

\***Derivación (la que debe ir en el README, §2.2.1): sea ε = 2⁻⁵². Para vectores unitarios:**

1. \***Productos `x\\\_i = fl(y\\\_i·u\\\_i)`: `|x\\\_i − y\\\_i u\\\_i| ≤ ε|y\\\_i u\\\_i|`; por Cauchy–Schwarz `Σ|y\\\_i u\\\_i| ≤ ‖y‖‖u‖ = 1` → error de productos ≤ ε.**

2. \***Neumaier sobre `x\\\_i`: `|S − Σx\\\_i| ≤ 2ε·Σ|x\\\_i| + O(Dε²)·max|x\\\_i|` → ≤ 2ε + despreciable (a D=10⁷, Dε² ≈ 5×10⁻²⁵).**

3. \***Dot total: ⟨y,u⟩ con error ≤ 3ε; idem ⟨y,v⟩.**

4. \***Coeficientes: `versin(θ)=2·sin²(θ/2)` (2ε), dos productos y dos sumas con |coef| ≤ 2.2 → error ≤ 6ε por coeficiente.**

5. \***Pass 2 elementwise con TwoSum: residual exacto absorbido → ≤ 2ε por componente en norma.**

\***Total teórico ≈ 11ε; certificado = 64ε (margen ≈ 5.8×). Rust y C++ usan la MISMA macro vía FFI constant `polydim\\\_certified\\\_drift\\\_bound()`. Test guardián:**

\***rust**

```
\*\*\*\`\\\#\\\[test\\\]\`\*\*  
  
\*\*\*\`fn cota\\\_empirica\\\_no\\\_escala\\\_con\\\_d() \\\{   \*// refuerza la derivación, no la reemplaza\`\*\*\*  
  
\`    \*\*\*for d in \\\[1\\\_000usize, 100\\\_000, 1\\\_000\\\_000, 10\\\_000\\\_000\\\] \\\{\`\*\*  
  
\`        \*\*\*let worst = max\\\_drift\\\_over\\\_random\\\_trials(d, 200); \*// f(seed) fijo y publicado\`\*\*\*  
  
\`        \*\*\*assert!(worst \\\<= 64.0 \\\* f64::EPSILON);\`\*\*  
  
\`        \*\*\*eprintln!("D=\\\{d:\\\>9\\\}  worst=\\\{worst:.3e\\\}  ratio=\\\{:.1\\\}e", worst / f64::EPSILON);\`\*\*  
  
\`    \*\*\*\\\}\`\*\*  
  
\*\*\*\`\\\}\`\*\*
```

# ═══ \***ENTREGA 5 — Texto corregido del tribunal OpenBLAS (cierra ALTO-7) ═══**

\***Texto de reemplazo verbatim para doc 03 §2.2:**

> ***"Refutación corregida: con hilos igualados (OMP\_NUM\_THREADS=2 en ambos lados), V762 supera a OpenBLAS en 3 de 5 configuraciones, con ventaja máxima de 2.0× en (D=4096, K=16). OpenBLAS retiene ventaja en K elevado: 1.7× en (4096,64) y 1.2× en (16384,128). La tabla completa (doc 04 §5) es la fuente de verdad; la frase 'el C++ nativo es 2.0× más rápido que OpenBLAS' sin calificativo de configuración se retira."***

# ═══ \***ENTREGA 6 — Freeze de versión (cierra ALTO-8) ═══**

\***c**

```
\*\*\*\`// polydim.h — junto al banner del kernel\`\*\*\*  
  
\*\*\*\`\\\#define POLYDIM\\\_VERSION\\\_MAJOR 7\`\*\*  
  
\*\*\*\`\\\#define POLYDIM\\\_VERSION\\\_MINOR 62\`\*\*  
  
\*\*\*\`\\\#define POLYDIM\\\_VERSION\\\_PATCH 0\`\*\*  
  
\*\*\*\`POLYDIM\\\_EXPORT uint32\\\_t POLYDIM\\\_CALL polydim\\\_version(void); \*/\\\* 0x00076200 \\\*/\`\*\*\*
```

\***Regla de publicación: los 4 documentos, el banner del kernel y `INTEGRITY\\\_MANIFEST.json` deben derivar la versión de esta única macro (script de release que falla si difieren).**

# ═══ \***ENTREGA 7 — Sanitizers + Miri/Loom en CI (cierra MEDIO-9, MEDIO-10) ═══**

\***yaml**

```
\*\*\*\`\\\# .github/workflows/silicon.yml (extracto)\`\*\*\*  
  
\*\*\*\`jobs:\`\*\*  
  
\`  \*\*\*hardened:\`\*\*  
  
\`    \*\*\*runs-on: ubuntu-24.04\`\*\*  
  
\`    \*\*\*steps:\`\*\*  
  
\`      \*\*\*- uses: actions/checkout@v4\`\*\*  
  
\`      \*\*\*- name: C++ ASan+UBSan (zero-leak exigido, no opcional)\`\*\*  
  
\`        \*\*\*run: |\`\*\*  
  
\`          \*\*\*g++ -O1 -g -fsanitize=address,undefined -fno-sanitize-recover=all \\\\\`\*\*  
  
\`              \*\*\*-shared -fPIC -fno-fast-math -fno-associative-math -ffp-contract=off \\\\\`\*\*  
  
\`              \*\*\*-fopenmp src/polydim\\\_kernel.cpp -o libpolydim.so\`\*\*  
  
\`          \*\*\*g++ -O1 -g -fsanitize=address,undefined -fno-sanitize-recover=all \\\\\`\*\*  
  
\`              \*\*\*-fno-fast-math -fno-associative-math -ffp-contract=off -fopenmp \\\\\`\*\*  
  
\`              \*\*\*tests/test\\\_suite.cpp -Iinclude -L. -lpolydim -Wl,-rpath,. -o test\\\_asan\`\*\*  
  
\`          \*\*\*ASAN\\\_OPTIONS=detect\\\_leaks=1 UBSAN\\\_OPTIONS=halt\\\_on\\\_error=1 ./test\\\_asan\`\*\*  
  
\`      \*\*\*- name: Rust Miri (UB de unsafe) y Loom (permutaciones de atomics PMTP)\`\*\*  
  
\`        \*\*\*run: |\`\*\*  
  
\`          \*\*\*cargo +nightly miri test\`\*\*  
  
\`          \*\*\*RUSTFLAGS="--cfg loom" cargo test --release --features loom\`\*\*  
  
\`      \*\*\*- name: Windows (MSVC 2026) — obligatorio porque está en el contrato\`\*\*  
  
\`        \*\*\*runs-on: windows-2025\`\*\*
```

\***Sin este job en verde, los claims "memory-safe" y "multiplataforma" son retórica. Nota honesta: hoy el dossier no contiene evidencia de ninguna de estas tres corridas.**

# ═══ \***ENTREGA 8 — Tolerancias default publicadas (cierra MEDIO-13) ═══**

\***Tabla que debe ir en el README (los valores actuales no aparecen en ningún documento; estos son los propuestos con su justificación):**

\***Table**

| **campo** | **default propuesto** | **justificación** |
| :-: | :-: | :-: |
| `basis\\\_ortho` | `1e-8` | rechaza el caso de test documentado (2e-8); admite bases QR reales a D=10⁷ (err ~ nε ≈ 2e-9) |
| `point\\\_norm` | `1e-9` | admite ‖y‖−1 = 2e-9?? **conflicto**: el test rechaza 2e-9 → default debe ser \< 2e-9, propongo `1e-9` |
| `gram\\\_ortho` | `1e-13` | coherente con telemetría medida (máx 2.4e-15, margen 40×) |
| `pivot\\\_rel` | `1e-12` | coherente con umbrales impresos en doc 04 |
| `reject\\\_subnormal` | `0` | conforme A6 (subnormales = telemetría, no error) |


\***Y la advertencia obligatoria que hoy no existe (ver L3-3 abajo): la cota certificada 64ε solo vale para entradas en precisión de máquina; la puerta admite errores hasta `basis\\\_ortho`, así que la cota real por llamada es compuesta — publicarla es lo que separa "SOTA en papel" de "marketing".**

# ═══ \***ENTREGA 9 — Metodología de benchmark auditable (cierra MEDIO-14, B-18) ═══**

\***Python**

```
\*\*\*\`\\\#!/usr/bin/env python3\`\*\*\*  
  
\*\*\*\`\\\# tools/bench\\\_matrix.py — mediana ± IQR, barrido de hilos, hardware sellado\`\*\*\*  
  
\*\*\*\`import subprocess, statistics, json, platform, os\`\*\*  
  
  
\*\*\*\`CONFIGS = \\\[(4096,16),(4096,64),(16384,32),(16384,128),(65536,64)\\\]\`\*\*  
  
\*\*\*\`THREADS  = sorted(\\\{1, 2, 4, os.cpu\\\_count() or 1\\\})\`\*\*  
  
\*\*\*\`REPS     = 30\`\*\*  
  
  
\*\*\*\`def bench(D, K, threads, binary):\`\*\*  
  
\`    \*\*\*env = dict(os.environ, OMP\\\_NUM\\\_THREADS=str(threads),\`\*\*  
  
\`               \*\*\*OPENBLAS\\\_NUM\\\_THREADS=str(threads))  \*\\\# igualación explícita, ambos lados\`\*\*\*  
  
\`    \*\*\*ts = \\\[float(subprocess.run(\\\[binary, str(D), str(K)\\\], env=env,\`\*\*  
  
\`              \*\*\*capture\\\_output=True, text=True).stdout.split()\\\[-1\\\]) for \\\_ in range(REPS)\\\]\`\*\*  
  
\`    \*\*\*return \\\{"median\\\_ms": statistics.median(ts), "iqr\\\_ms": statistics.quantiles(ts, n=4)\\\[2\\\]\`\*\*  
  
\`            \*\*\*- statistics.quantiles(ts, n=4)\\\[0\\\]\\\}\`\*\*  
  
  
\*\*\*\`manifest = \\\{"cpu": platform.processor(), "machine": platform.machine(),\`\*\*  
  
\`            \*\*\*"governor": open("/sys/devices/system/cpu/cpu0/cpufreq/scaling\\\_governor").read().strip()\`\*\*  
  
\`            \*\*\*if os.path.exists("/sys/devices/system/cpu/cpu0/cpufreq/scaling\\\_governor") else "n/a",\`\*\*  
  
\`            \*\*\*"openblas": subprocess.run(\\\["sh","-c","ldconfig -p | grep openblas"\\\],\`\*\*  
  
\`                                        \*\*\*capture\\\_output=True, text=True).stdout.strip(),\`\*\*  
  
\`            \*\*\*"results": \\\{\\\}\\\}\`\*\*  
  
\*\*\*\`for impl, binary in \\\[("v762", "./bench\\\_v762"), ("openblas", "./bench\\\_oblas")\\\]:\`\*\*  
  
\`    \*\*\*for D, K in CONFIGS:\`\*\*  
  
\`        \*\*\*for t in THREADS:\`\*\*  
  
\`            \*\*\*manifest\\\["results"\\\]\\\[f"\\\{impl\\\}|\\\{D\\\}|\\\{K\\\}|t\\\{t\\\}"\\\] = bench(D, K, t, binary)\`\*\*  
  
\*\*\*\`json.dump(manifest, open("bench\\\_manifest.json", "w"), indent=2)\`\*\*  
  
\*\*\*\`\\\# Regla: ningún claim del tribunal cita un número que no exista en este JSON.\`\*\*\*
```

# ═══ \***ENTREGA 10 — Stiefel: test de pivote con M realmente mal condicionada (cierra MEDIO-15) ═══**

\***cpp**

```
\*\*\*\`// tests/stiefel\\\_pivot\\\_domain.cpp — ejerce el umbral relativo lejos de pivote=1.0\`\*\*\*  
  
\*\*\*\`\\\#include "polydim.h"\`\*\*  
  
\*\*\*\`\\\#include \\\<cmath\\\>\`\*\*  
  
\*\*\*\`\\\#include \\\<cstdio\\\>\`\*\*  
  
\*\*\*\`\\\#include \\\<vector\\\>\`\*\*  
  
  
\*\*\*\`int main() \\\{\`\*\*  
  
\`    \*\*\*const uint64\\\_t D = 4096; const uint32\\\_t K = 2;\`\*\*  
  
\`    \*\*\*// X = \\\[e1 e2\\\] (ortonormal exacta), G = sigma \\\* \\\[e3 e4\\\]-combinación tangente\`\*\*\*  
  
\`    \*\*\*std::vector\\\<double\\\> X(D\\\*K, 0.0), G(D\\\*K, 0.0), Y(D\\\*K);\`\*\*  
  
\`    \*\*\*X\\\[0\\\*D + 0\\\] = 1.0; X\\\[1\\\*D + 1\\\] = 1.0;          \*// columnas e1, e2\`\*\*\*  
  
\`    \*\*\*G\\\[0\\\*D + 2\\\] = 1.0;  G\\\[1\\\*D + 3\\\] = 1.0;          \*// tangente: X^T G = 0 exacto\`\*\*\*  
  
  
\`    \*\*\*PolydimTolerances tol = polydim\\\_default\\\_tolerances(D);\`\*\*  
  
\`    \*\*\*PolydimReport rep; polydim\\\_report\\\_init(&rep);\`\*\*  
  
  
\`    \*\*\*// (a) tau moderado: éxito, pivote ~1\`\*\*\*  
  
\`    \*\*\*int rc = polydim\\\_stiefel\\\_cayley\\\_smw\\\_f64(X.data(), G.data(), Y.data(),\`\*\*  
  
\`                                            \*\*\*D, K, 0.1, &tol, &rep);\`\*\*  
  
\`    \*\*\*printf("(a) rc=%d pivot\\\_min=%.3e thr=%.3e ortho=%.3e\\\\n",\`\*\*  
  
\`           \*\*\*rc, rep.pivot\\\_min, rep.pivot\\\_threshold, rep.ortho\\\_err);\`\*\*  
  
  
\`    \*\*\*// (b) tau grande: el test documentado NUNCA ejerce esto (pivot siempre 1.0).\`\*\*\*  
  
\`    \*\*\*//     Exigimos comportamiento DOCUMENTADO: éxito con ortho \\\<= gram\\\_ortho,\`\*\*\*  
  
\`    \*\*\*//     o rechazo limpio rc=-5. Lo prohibido: rc=0 con ortho \\\> gram\\\_ortho.\`\*\*\*  
  
\`    \*\*\*rc = polydim\\\_stiefel\\\_cayley\\\_smw\\\_f64(X.data(), G.data(), Y.data(),\`\*\*  
  
\`                                        \*\*\*D, K, 1e6, &tol, &rep);\`\*\*  
  
\`    \*\*\*bool silent\\\_bad = (rc == 0 && rep.ortho\\\_err \\\> tol.gram\\\_ortho);\`\*\*  
  
\`    \*\*\*printf("(b) tau=1e6 rc=%d ortho=%.3e thr=%.3e %s\\\\n", rc, rep.ortho\\\_err,\`\*\*  
  
\`           \*\*\*rep.pivot\\\_threshold, silent\\\_bad ? "\\\[FALLA SILENCIOSA\\\]" : "\\\[OK\\\]");\`\*\*  
  
\`    \*\*\*return silent\\\_bad ? 1 : 0;\`\*\*  
  
\*\*\*\`\\\}\`\*\*
```

\***Este test conecta directamente con el hallazgo profundo L3-4 (abajo): para τ·σ grande el Cayley–SMW pierde dígitos por condición, y la única defensa documentada es la compuerta a posteriori. El test verifica que la compuerta existe y dispara.**

# ═══ \***ENTREGA 11 — Subnormales: test con MXCSR save/restore (cierra parte de MEDIO-11) ═══**

\***cpp**

```
\*\*\*\`// tests/subnormal\\\_mxcsr.cpp — A6 exigible en silicio, no solo en el enum\`\*\*\*  
  
\*\*\*\`\\\#include "polydim.h"\`\*\*  
  
\*\*\*\`\\\#include \\\<xmmintrin.h\\\>     \*// \\\_MM\\\_GET/SET\\\_FLUSH\\\_ZERO\\\_MODE (x86; en ARM64: FPCR bit FZ)\`\*\*\*  
  
\*\*\*\`\\\#include \\\<pmmintrin.h\\\>     \*// DAZ\`\*\*\*  
  
\*\*\*\`\\\#include \\\<cstdio\\\>\`\*\*  
  
\*\*\*\`\\\#include \\\<vector\\\>\`\*\*  
  
\*\*\*\`\\\#include \\\<cmath\\\>\`\*\*  
  
  
\*\*\*\`int main() \\\{\`\*\*  
  
\`    \*\*\*const uint64\\\_t D = 100000;\`\*\*  
  
\`    \*\*\*std::vector\\\<double\\\> u(D,0.0), v(D,0.0), y(D,0.0), yp(D);\`\*\*  
  
\`    \*\*\*u\\\[0\\\]=1.0; v\\\[1\\\]=1.0;\`\*\*  
  
\`    \*\*\*for (uint64\\\_t i=2; i\\\<D; i++) y\\\[i\\\] = (i & 1) ? 0x1p-1074 : -0x1p-1074; \*// subnormales puros\`\*\*\*  
  
\`    \*\*\*double nrm = std::sqrt((double)(D-2)) \\\* 0x1p-1074;   \*// norma subnormal ~3e-320\`\*\*\*  
  
\`    \*\*\*for (uint64\\\_t i=2; i\\\<D; i++) y\\\[i\\\] /= nrm;            \*// y normalizado (componentes ~1e-3)\`\*\*\*  
  
\`    \*\*\*y\\\[0\\\] = 1.0;                                          \*// ahora ||y|| ~ 1\`\*\*\*  
  
\`    \*\*\*polydim\\\_project\\\_sphere\\\_f64(y.data(), y.data(), D, nullptr);\`\*\*  
  
  
\`    \*\*\*unsigned old\\\_mxcsr = \\\_mm\\\_getcsr();\`\*\*  
  
\`    \*\*\*\\\_MM\\\_SET\\\_FLUSH\\\_ZERO\\\_MODE(\\\_MM\\\_FLUSH\\\_ZERO\\\_ON);          \*// forzamos el caso hostil\`\*\*\*  
  
\`    \*\*\*\\\_MM\\\_SET\\\_DENORMALS\\\_ZERO\\\_MODE(\\\_MM\\\_DENORMALS\\\_ZERO\\\_ON);\`\*\*  
  
  
\`    \*\*\*PolydimTolerances tol = polydim\\\_default\\\_tolerances(D);\`\*\*  
  
\`    \*\*\*PolydimReport rep; polydim\\\_report\\\_init(&rep);\`\*\*  
  
\`    \*\*\*int rc = polydim\\\_rodrigues\\\_geodesic\\\_f64(y.data(), u.data(), v.data(),\`\*\*  
  
\`                                            \*\*\*yp.data(), 0.3, D, &tol, &rep);\`\*\*  
  
\`    \*\*\*\\\_mm\\\_setcsr(old\\\_mxcsr);                               \*// restauración obligatoria\`\*\*\*  
  
\`    \*\*\*bool restored = (\\\_mm\\\_getcsr() == old\\\_mxcsr);\`\*\*  
  
\`    \*\*\*bool finite\\\_out = std::isfinite(yp\\\[0\\\]) && std::isfinite(yp\\\[2\\\]);\`\*\*  
  
\`    \*\*\*printf("rc=%d finite=%d mxcsr\\\_restored=%d\\\\n", rc, finite\\\_out, restored);\`\*\*  
  
\`    \*\*\*return (rc == 0 && finite\\\_out && restored) ? 0 : 1;\`\*\*  
  
\`    \*\*\*// Nota: con FTZ/DAZ ON la deriva puede exceder 64e legitimanente;\`\*\*\*  
  
\`    \*\*\*// este test exige solo finite + no-cola-sucia. La deriva estricta se mide con FTZ OFF.\`\*\*\*  
  
\*\*\*\`\\\}\`\*\*
```

# ═══ \***ENTREGA 12 — Redacción Rust corregida (cierra MEDIO-12) ═══**

\***Reemplazo verbatim en doc 01 §2.2.4:**

> ***"Compliant with Rust 2024 Edition (`\\\#\\\[unsafe(no\\\_mangle)\\\]`, `panic = "unwind"`): `panic = "unwind` enables `catch\\\_unwind` containment at the FFI boundary, so a panicking guard never unwinds across the C ABI. Memory safety itself is provided by ownership semantics and the absence of `unsafe` outside the FFI shim — verifiable only with the source published (see CRÍTICO-1)."***

# ═══ \***ENTREGA 13 — Betti-1: precisión matemática obligatoria (cierra A8 de verdad) ═══**

\***El motor Sparse VR DSU con `N ≥ 1000` debe declarar exactamente qué calcula. Un DSU sobre el grafo da la ciclicidad del 1-esqueleto:**

> \***β₁(1-esqueleto) = E − V + C (V = vértices, E = aristas VR bajo umbral, C = componentes DSU)**

\***Eso no es H₁ del complejo de Vietoris–Rips completo: los 2-símplices llenan ciclos. Texto correcto para el doc 03:**

> ***"A8 cerrado con precisión: el guardián certifica β₁ del 1-esqueleto (rango cíclico E − V + C por DSU, N ≥ 1000). Se retira cualquier lectura como H₁ del VR completo; si se requiere H₁ persistente, la vía es reducción de matrices de borde (complejidad O(N³) peor caso), fuera del alcance del guardián runtime."***

\***Validación con nubes sintéticas de geometría conocida (S¹ → β₁\_grafo ≈ 1 en el rango de escala correcto; toro → 2), contra este micro-referencia:**

\***Python**

```
\*\*\*\`\\\# tools/ref\\\_betti1.py — referencia por reducción de borde (solo para validar el DSU)\`\*\*\*  
  
\*\*\*\`import numpy as np\`\*\*  
  
\*\*\*\`def betti1\\\_vr(points, eps):\`\*\*  
  
\`    \*\*\*from scipy.spatial.distance import pdist, squareform\`\*\*  
  
\`    \*\*\*Dm = squareform(pdist(points)); n = len(points)\`\*\*  
  
\`    \*\*\*edges = \\\[(i,j) for i in range(n) for j in range(i+1,n) if Dm\\\[i,j\\\] \\\<= eps\\\]\`\*\*  
  
\`    \*\*\*\\\# matriz de borde d1: aristas -\\\> vértices ; H1 = ker d1 / im d2 (d2: triángulos-\\\>aristas)\`\*\*\*  
  
\`    \*\*\*import itertools\`\*\*  
  
\`    \*\*\*tris = \\\[(i,j,k) for i,j,k in itertools.combinations(range(n),3)\`\*\*  
  
\`            \*\*\*if max(Dm\\\[i,j\\\],Dm\\\[i,k\\\],Dm\\\[j,k\\\]) \\\<= eps\\\]\`\*\*  
  
\`    \*\*\*d1 = np.zeros((n, len(edges))); idx = \\\{e:k for k,e in enumerate(edges)\\\}\`\*\*  
  
\`    \*\*\*for k,(i,j) in enumerate(edges): d1\\\[i,k\\\]=1; d1\\\[j,k\\\]=1\`\*\*  
  
\`    \*\*\*\\\# rango sobre GF(2) vía eliminación gaussiana espartana:\`\*\*\*  
  
\`    \*\*\*def gf2\\\_rank(A):\`\*\*  
  
\`        \*\*\*A = A.copy() % 2; r = 0\`\*\*  
  
\`        \*\*\*for c in range(A.shape\\\[1\\\]):\`\*\*  
  
\`            \*\*\*p = np.where(A\\\[r:,c\\\])\\\[0\\\]\`\*\*  
  
\`            \*\*\*if len(p)==0: continue\`\*\*  
  
\`            \*\*\*A\\\[\\\[r, r+p\\\[0\\\]\\\]\\\] = A\\\[\\\[r+p\\\[0\\\], r\\\]\\\]; A\\\[r+1:\\\] ^= A\\\[r\\\] & A\\\[r+1:,c,None\\\]; r += 1\`\*\*  
  
\`            \*\*\*if r == A.shape\\\[0\\\]: break\`\*\*  
  
\`        \*\*\*return r\`\*\*  
  
\`    \*\*\*rank\\\_d1 = gf2\\\_rank(d1)\`\*\*  
  
\`    \*\*\*beta0 = n - rank\\\_d1\`\*\*  
  
\`    \*\*\*beta1\\\_skel = len(edges) - rank\\\_d1 - 0  \*\\\# rango cíclico del grafo\`\*\*\*  
  
\`    \*\*\*return beta0, beta1\\\_skel, len(tris)   \*\\\# len(tris)\\\>0 advierte: H1 del VR lleno \\\<= beta1\\\_skel\`\*\*\*
```

# ══════════ \***CICLO PROFUNDO 2 — hallazgos que el ciclo 1 no alcanzó ══════════**

## 🟠 \***L2-A — El seqlock clásico es *data race* = UB en C++ (industrial, no cosmético)**

\***Evidencia: el header expone `acquire\\\_read`/`validate\\\_read` sobre un control opaco; la técnica seqlock canónica lee el payload con loads comunes mientras el escritor escribe. En el modelo de memoria C++ eso es carrera de datos formal (UB), aunque x86 lo "resuelva" de facto. Con optimizadores agresivos (LTO + alias analysis) es una bomba de reloj.**

\***Solución: ya entregada arriba — payload como array de `std::atomic\\\<uint64\\\_t\\\>` leído relaxed + fence acquire de validación (Entrega 2). Costo: cero en x86 (los movs son los mismos), ganancia: well-defined. `\\\[VERIFICAR EN CÓDIGO\\\]` que el kernel real no lee el payload con punteros crudos.**

\***Crédito donde corresponde: ABA no es un riesgo aquí (contador de 64 bits monótono; el wrap necesita 2⁶³ escrituras). Lo comprobé explícitamente para no regalarle una crítica falsa al tribunal.**

## 🟠 \***L2-B — La vía GPU/Triton (f32) invalida la cota 64ε sin que nadie lo diga**

\***Evidencia: doc 02 lista `polydim\\\_triton\\\_kernel\\\_v762.py` como componente, pero ningún documento fija la precisión del path GPU. Si el kernel Triton corre en f32 (ε\_f32 = 1.19e-7), la cota certificada pasa de 1.42e-14 a 64·ε\_f32 ≈ 7.6e-6 — cinco órdenes de magnitud peor, y el `PolydimReport` no distingue la vía.**

\***Solución (mejor): compuerta de precisión por construcción:**

\***Python**

```
\*\*\*\`\\\# polydim\\\_triton\\\_kernel\\\_v762.py — extracto del parche\`\*\*\*  
  
\*\*\*\`import triton.language as tl\`\*\*  
  
  
\*\*\*\`POLYDIM\\\_BOUND\\\_F64 = 1.4211e-14          \*\\\# 64 \\\* eps64\`\*\*\*  
  
\*\*\*\`POLYDIM\\\_BOUND\\\_F32 = 7.63e-6             \*\\\# 64 \\\* eps32 — NUNCA publicar como 64e\`\*\*\*  
  
  
\*\*\*\`def rodrigues\\\_geodesic(y, u, v, theta, out\\\_path\\\_report):\`\*\*  
  
\`    \*\*\*if y.dtype == tl.float32:\`\*\*  
  
\`        \*\*\*out\\\_path\\\_report\\\["precision\\\_path"\\\] = "f32\\\_gpu"\`\*\*  
  
\`        \*\*\*out\\\_path\\\_report\\\["certified\\\_bound"\\\] = POLYDIM\\\_BOUND\\\_F32\`\*\*  
  
\`        \*\*\*\\\# y opcionalmente: raise PrecisionError si el caller exigió f64\`\*\*\*  
  
\`    \*\*\*else:\`\*\*  
  
\`        \*\*\*out\\\_path\\\_report\\\["precision\\\_path"\\\] = "f64\\\_gpu"\`\*\*  
  
\`        \*\*\*out\\\_path\\\_report\\\["certified\\\_bound"\\\] = POLYDIM\\\_BOUND\\\_F64\`\*\*
```

\***Regla contractual: el reporte lleva `precision\\\_path` siempre; el README publica ambas cotas. Hoy el dossier tiene un claim de cota única sobre un sistema de dos precisiones.**

## 🟠 \***L2-C — Agujero ABI: structs por FFI sin `struct\\\_size` y sin APIs `sizeof`**

\***Evidencia: `polydim.h` expone `polydim\\\_pmtp\\\_sizeof()` y `polydim\\\_pmtp\\\_alignof()` — reconociendo el riesgo ABI — pero no existe `polydim\\\_report\\\_sizeof()` ni `polydim\\\_tolerances\\\_sizeof()`. Dart/Rust/Python hardcodean el layout de `PolydimReport` (4 doubles + 6 doubles + uint64 + padding, packing dependiente de compilador). Un campo añadido en V763 rompe FFI en silencio o con corrupción de pila.**

\***Solución (mejor):**

\***c**

```
\*\*\*\`POLYDIM\\\_EXPORT uint32\\\_t POLYDIM\\\_CALL polydim\\\_report\\\_sizeof(void);\`\*\*  
  
\*\*\*\`POLYDIM\\\_EXPORT uint32\\\_t POLYDIM\\\_CALL polydim\\\_tolerances\\\_sizeof(void);\`\*\*  
  
\*\*\*\`typedef struct PolydimReport \\\{\`\*\*  
  
\`    \*\*\*uint32\\\_t struct\\\_size;   \*/\\\* PRIMER campo: caller lo fija a polydim\\\_report\\\_sizeof();\`\*\*\*  
  
\`                               \*\*\*el kernel rechaza (rc=-2) si difiere -\\\> forward-compat \\\*/\`\*\*\*  
  
\`    \*\*\*double point\\\_norm\\\_err;  \*/\\\* ... resto idéntico ... \\\*/\`\*\*\*  
  
\*\*\*\`\\\} PolydimReport;\`\*\*
```

\***En Dart: `assert(sizeOf\\\<PolydimReport\\\>() == polydim\\\_report\\\_sizeof());` en la inicialización del FFI.**

## 🟡 \***L2-D — Reproducibilidad bitwise vs OpenMP**

\***Evidencia: los tests exigen deriva ≤ cota, pero si las regiones paralelas usan `schedule(dynamic)` o reducciones sin orden fijo, los resultados varían corrida a corrida en los bits bajos — la composición de 20,000 pasos (doc 04) no es reproducible entre máquinas. `\\\[VERIFICAR EN CÓDIGO\\\]`.**

\***Solución: `schedule(static)` en toda región de reducción + orden de combinación por thread fijo + test gemelo: correr `test\\\_suite` dos veces y asertar igualdad bitwise de los `PolydimReport` impresos. Una línea en CI:**

\***bash**

```
\*\*\*\`./test\\\_suite \\\> run1.txt && ./test\\\_suite \\\> run2.txt && diff run1.txt run2.txt || exit 1\`\*\*
```

## 🟡 \***L2-E — PMTP expone control pero no payload: la API está incompleta para el Morpho Protocol**

\***Evidencia: el header define begin/commit/acquire/validate pero ninguna función de payload. ¿Dónde vive el tensor? ¿Quién fija dtype/D/K del contenido de la ranura? El "protocolo Morpho" pasa tags de 64 bits, pero el contrato no fija el encabezado del tensor que el tag referencia.**

\***Solución: cabecera canónica en el slab, versionada:**

\***c**

```
\*\*\*\`typedef struct PolydimTensorHeader \\\{  \*/\\\* vive al inicio de cada slot PMTP \\\*/\`\*\*\*  
  
\`    \*\*\*uint64\\\_t magic;        \*/\\\* 0x504D5450 'PMTP' \\\*/\`\*\*\*  
  
\`    \*\*\*uint32\\\_t version;      \*/\\\* 1 \\\*/\`\*\*\*  
  
\`    \*\*\*uint32\\\_t dtype;        \*/\\\* 0=f64 1=f32 2=f16 \\\*/\`\*\*\*  
  
\`    \*\*\*uint64\\\_t D, K;\`\*\*  
  
\`    \*\*\*uint64\\\_t seq;          \*/\\\* debe coincidir con el seqlock del slot \\\*/\`\*\*\*  
  
\*\*\*\`\\\} PolydimTensorHeader;\`\*\*
```

## 🟡 \***L2-F — `panic = "abort"` del consumidor tumba la frontera FFI**

\***Evidencia: A7 corrige el lado del guardián, pero si la crate consumidora compila con `panic = "abort"` en su `\\\[profile.release\\\]`, el unwind desaparece y un panic en el guardián aborta el proceso host entero (el kernel C++ muere con él). Esto es comportamiento estándar de Cargo, no un bug del código.**

\***Solución: documentar en `rust/README.md` con prueba de inyección:**

\***rust**

```
\*\*\*\`\\\#\\\[test\\\]\`\*\*  
  
\*\*\*\`fn panic\\\_en\\\_frontera\\\_no\\\_aborta\\\_al\\\_host() \\\{\`\*\*  
  
\`    \*\*\*let r = std::panic::catch\\\_unwind(|| polydim\\\_verify::entry\\\_panicking\\\_test\\\_hook());\`\*\*  
  
\`    \*\*\*assert!(r.is\\\_err());   \*// si el profile del consumidor es abort, ESTE test aborta -\\\> se detecta\`\*\*\*  
  
\*\*\*\`\\\}\`\*\*
```

## 🟢 \***L2-G — Precisiones de redacción matemática (doc 01 / objetivo)**

1. ***"4.44×10⁻¹⁶ (Exact IEEE-754 machine ε)"* → falso como redacción: 4.44e-16 = 2ε (ε = 2.22e-16). Escribir "2ε (unit roundoff 2u)".**

2. ***"The 1D Worm violates DPI"* → la DPI nunca se viola; la serialización la satura con desigualdad estricta (I(X;g(Y)) \< I(X;Y) cuando g pierde información). La redacción correcta es más fuerte, no más débil: *"the 1D worm is a lossy channel that saturates the Data Processing Inequality with strict inequality"*.**

3. \***Doc 01 §2.2 cita `I(X; Z) \\\\le I(X; Y)` sin definir Z := g(Y) — una línea de definición cierra el formalismo.**

# ══════════ \***CICLO PROFUNDO 3 — capa de derivación numérica ══════════**

## 🔴 \***L3-1 — La cota certificada 64ε es inválida tal como se declara: la puerta admite entradas 5 órdenes de magnitud peor que la cota**

\***Este es el hallazgo más profundo de este ciclo, y es teorema, no opinión:**

\***Hechos del dossier: (a) la compuerta A2 rechaza `|\\\<u,u\\\>−1| = 2e-8` → `basis\\\_ortho` default \< 2e-8; (b) la compuerta A4 admite `||y||−1 ≈ 2e-9`; (c) la cota publicada es 1.42e-14.**

\***Derivación: perturbe la base `u' = u + δu`, `v' = v + δv` con `‖δu‖, ‖δv‖ ≤ δ` (admisible si δ ≤ basis\_ortho). Entonces `a = ⟨y,u'⟩ = a\\\* + ⟨y,δu⟩` con `|⟨y,δu⟩| ≤ δ`. Los coeficientes de la rotación cambian en `≤ (versin+sin)·δ ≤ 2δ` cada uno, y `y'` se perturba en `≤ 4δ`. Con δ = 1e-8 (puerta real), la salida puede desviarse ~4e-8 — ¡2800× la cota certificada!**

\***Conclusión: la certificación de 64ε solo vale sobre entradas en precisión de máquina (δ ~ ε). Tal como está redactada, la promesa es falsa en su dominio completo.**

\***Solución (la mejor — ya aplicada en Entrega 3): publicar la cota compuesta por contrato:**

\***c**

```
\*\*\*\`/\\\* polydim.h — certificación honesta \\\*/\`\*\*\*  
  
\*\*\*\`/\\\* deriva\\\_salida \\\<= 8 \\\* max(basis\\\_ortho, point\\\_norm\\\_err\\\_entrada) + POLYDIM\\\_DRIFT\\\_BOUND\`\*\*\*  
  
\` \*\*\*\\\* El término 64e solo domina cuando las entradas están a precisión de máquina.\`\*\*\*  
  
\` \*\*\*\\\* Alternativa estricta: fijar basis\\\_ortho default = 1e-12 y exigir bases compensadas. \\\*/\`\*\*\*
```

\***Decisión de diseño que le pertenece al dueño: (i) cota compuesta (flexible, honesta), o (ii) endurecer la puerta a ~1e-12 (rompe bases QR reales a D=10⁷, cuyo error de ortonormalidad es ~nε ≈ 2e-9 — no caben en 1e-12, así que (ii) exigiría orthonormalización compensada en el pipeline). Mi recomendación: (i) compuesta, con el factor 8 derivado arriba.**

## 🟠 \***L3-2 — Dominio de estabilidad del Cayley–SMW: τ·σ grande degrada la ortogonalidad *aunque* el pivote relativo pase**

\***Derivación (K=1 exacta, K≥2 por bloques): con G tangente, `VᵀU = \\\[\\\[0, I\\\],\\\[−GᵀG, 0\\\]\\\]` y M = I − τ/2·VᵀU es bloques 2×2 `\\\[\\\[1, −τ/2\\\],\\\[τσ\\\_j²/2, 1\\\]\\\]` por valor singular σ\_j de G. El bloque con σ\_j = 1 es una rotación escalada (cond = 1 ✓), pero para σ\_j ≠ 1:**

- \***cond₂ del bloque ~ (1 + τσ\_j/2)² / min(1, σ\_j²) en el peor caso (analizable directamente del determinante `1 + τ²σ\\\_j²/4`).**

\***Con LU backward-stable, el error de ortogonalidad resultante escala como cond(M)·ε. Zona de clíff: τ·σ\_max ≳ 1/√ε ≈ 6.7×10⁷ pierde todos los dígitos; y para G anisotrópico el daño empieza mucho antes contra `gram\\\_ortho = 1e-13`.**

\***Por qué el pivote relativo NO salva esto: el pivoteo detecta M singular en precisión finita, pero aquí M es genuinamente mal condicionada, no singular: los pivotes pasan el umbral relativo y el solve devuelve basura con buena cara.**

\***Solución (ya codificada en Entrega 10): asertar el contrato (b): `rc=0 ⟹ ortho\\\_err ≤ gram\\\_ortho`, siempre; `rc=-5` en caso contrario. Más: para pasos agresivos, documentar la retracción alternativa estable (QR de X + τG — ortonormalización explícita, costo mayor, dominio ilimitado en τ) y dejar la elección al caller vía flag en `PolydimTolerances`. La batería actual — pivote = 1.000e+00 en los 4 tests — jamás entró a esta zona.**

## 🟡 \***L3-3 — Combinación de reducciones OpenMP: el factor `threads` en la cota**

\***Si los parciales por thread se combinan con suma ingenua (`part\\\[0\\\] + part\\\[1\\\]`), el error de Neumaier gana un término ~ ε·nthreads·max|parcial| — a 2 hilos es 2ε, despreciable, pero la cota publicada debe declararlo: con la compensación de combinación (sumar los `comp` de cada thread con otro TwoSum) el término desaparece del bound. `\\\[VERIFICAR EN CÓDIGO\\\]` + una línea en la derivación de la Entrega 4: *"los parciales por hilo se combinan con compensación; sin eso la cota lleva +nthreads·ε"*.**

## 🟡 \***L3-4 — Reducción de argumento de θ no especificada**

\***La cota asume `sin(θ)`, `cos(θ)` con error ~ε. Eso solo vale para θ reducido al rango fundamental. Para `|θ|` grande (el caller pasa θ = 1e9), la reducción mod 2π de libm introduce error ~ε·|θ| en el argumento → el error de sin/cos ya no es ε sino ~ulp(θ). La certificación debe declarar dominio: `|θ| ≤ Θ\\\_max` (p. ej. Θ\_max = 2π·2¹⁰ con reducción Cody–Waite documentada) o exigir θ pre-reducido. `\\\[VERIFICAR EN CÓDIGO\\\]` + línea contractual en el README. Test: θ = 1e9, comparar contra θ reducido por el caller.**

## 🟡 \***L3-5 — Stress dinámico rotate→project (el ciclo que el sistema real vivirá)**

\***Ningún test evalúa el sistema como dinámica iterada. Propuesta:**

\***cpp**

```
\*\*\*\`// tests/rotate\\\_project\\\_dynamics.cpp — 1e6 ciclos rotate→project, deriva acotada\`\*\*\*  
  
\*\*\*\`double worst = 0;\`\*\*  
  
\*\*\*\`for (int t = 0; t \\\< 1000000; t++) \\\{\`\*\*  
  
\`    \*\*\*rc = polydim\\\_rodrigues\\\_geodesic\\\_f64(y.data(), u.data(), v.data(), yp.data(),\`\*\*  
  
\`                                        \*\*\*1e-4, D, &tol, &rep);\`\*\*  
  
\`    \*\*\*assert(rc == 0);\`\*\*  
  
\`    \*\*\*polydim\\\_project\\\_sphere\\\_f64(yp.data(), y.data(), D, &rep); \*// re-normalización\`\*\*\*  
  
\`    \*\*\*worst = std::max(worst, std::fabs(rep.out\\\_norm\\\_err));\`\*\*  
  
\*\*\*\`\\\}\`\*\*  
  
\*\*\*\`// contrato: worst \\\<= gate + BOUND en cada paso; la proyección evita deriva acumulada\`\*\*\*  
  
\*\*\*\`// y debería mantener worst plano en t (si crece ~sqrt(t), hay sesgo sistemático)\`\*\*\*
```

## 🟢 \***L3-6 — Semillas y determinismo de la batería**

\***Los tests con datos aleatorios (si los hay) deben correr con seed fijo archivado + una corrida con seed temporal. `\\\[VERIFICAR EN CÓDIGO\\\]` — el dossier no menciona RNG en ningún lado, lo cual para tests de Stiefel (¿cómo se construyeron X, G?) es una laguna de reproducibilidad.**

## 🟢 \***L3-7 — Runbook operativo D = 10⁷**

\***Documento de ejecución obligatoria: `numactl --interleave=all` (los buffers de 320 MB cruzan nodos si el allocator del caller hace first-touch en un solo nodo), governor `performance`, pinning de hilos. Sin esto, dos laboratorios obtienen números distintos y el "silicon contract" no es transferible.**

# ══════════ \***AUTO-VERIFICACIÓN DE ESTE CICLO (tu exigencia \#anti-alucinación) ══════════**

\***Table**

| **Afirmación nueva** | **Estado** |
| :-: | :-: |
| 64ε = 1.4211e-14; 2.10e-14 = 94.6ε | **aritmética verificada** |
| 1098/83,646 = 1.31%; 1098+82,548 = 83,646 | **aritmética verificada** |
| β₁(grafo) = E − V + C | **teorema estándar** |
| Cayley de matriz antisimétrica es ortogonal; M nunca singular para τ real, G tangente | **demostrado arriba** (eigen ±iσ) |
| cond del bloque 2×2 ~~ (1+τσ/2)²/… y zona de clíff ~~ ε^\{-1/2\} | **derivación mostrada; constantes exactas dependen del espectro de σ\_j — marcado como derivación, no medición** |
| Seqlock con payload no-atómico = UB C++ | **hecho estándar del modelo de memoria** |
| ε\_f32 = 1.19e-7 → 64ε\_f32 ≈ 7.63e-6 | **aritmética verificada** |
| Cota compuesta de L3-1 con factor 8 | **derivación mostrada; el factor exacto es 4 en norma con margen 2× — lo declaré como tal** |
| "El código de V762 hace X internamente" | **ninguna afirmación de este tipo fue hecha; todo riesgo interno lleva `\\\[VERIFICAR EN CÓDIGO\\\]`** |



\***El ciclo 4 ya no es "leer más": es herramientas — (a) fuzzer libFuzzer/AFL++ sobre la API pública con oráculo de cota compuesta, (b) mutation testing de la batería 26/26 (¿los tests matan mutantes reales o son decorativos? — la deriva 0.0 de D=10⁶ sugiere lo segundo), (c) verificación formal acotada de la compensación (Frama-C/Why3 sobre el TwoSum), (d) soak test PMTP de 24 h con histograma de latencias de validación, (e) análisis de `cargo-geiger` y SBOM completo para la frontera FFI.**

