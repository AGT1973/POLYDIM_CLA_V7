## \***0. La verdad incómoda primero (bulldog con el dueño, no contra él)**

\***El problema de las "600 rondas" no es que falten errores por encontrar. Es que el tribunal anterior te reportó errores que NO EXISTEN en este código, y te dejó de reportar el error más grave: el núcleo numérico de V760 no está en el dossier. El monolito contiene stubs y esqueletos; el kernel geodésico real vive en DLLs binarias de V753. Estás corrigiendo un archivo de ~1000 líneas cuya mitad funcional no está auditable. Ese es el hueso.**

\***Lo que el tribunal ACERTÓ (confirmado en el código):**

\***Table**

| **\#** | **Hallazgo** | **Veredicto** |
| :-: | :-: | :-: |
| 1 | Module leak en `hip\\\_hsaco\\\_runner.cpp`: `CHECK\\\_HIP` hace `return` temprano → `hipModuleUnload` nunca se ejecuta en fallos. **Confirmado, línea por línea.** | ✅ REAL |
| 2 | `alignas(128)` (C++) vs `\\\#\\\[repr(C, align(64))\\\]` (Rust). **Confirmado.** Los offsets internos son idénticos (0 y 8), así que NO hay out-of-bounds como dijo Groq, pero sí false-sharing y divergencia de ABI. | ✅ REAL (impacto corregido) |
| 3 | Torn-read race en publicación PMTP: el consumidor puede leer `active\\\_buffer` de la publicación N+2 creyendo que es la N+1. Es un **torn read, no ABA** (el wrap de 64 bits es irreal). | ✅ REAL (mal etiquetado) |
| 4 | Test harness ciego: un solo hilo, nunca prueba el path HIP, no captura stderr, solo chequea rc. | ✅ REAL |
| 5 | FTZ/DAZ es **por hilo** en x86: el guard de Rust puede correr sin DAZ activado → fuga de subnormales no detectada. | ✅ REAL |


\***Lo que el tribunal INVENTÓ (alucinaciones que te hicieron perder rondas):**

\***Table**

| **\#** | **Afirmación falsa** | **La realidad en el código** |
| :-: | :-: | :-: |
| 1 | "`double work\\\[N\\\]\\\[N\\\]` en stack desborda con N\>4k" | **Ese código no existe.** `estimate\\\_rcond\\\_hager\\\_higham` es `return 1.0;`. No hay matriz N×N en ningún archivo. |
| 2 | "ROCm 5.0→5.3 cambió `hipModuleLaunchKernel` de 10 a 11 args" | **Falso.** La firma de 11 parámetros (f, 3 grid, 3 block, smem, stream, params, extra) es la que siempre tuvo y la que el código declara correctamente. |
| 3 | "`hipModuleLoad` renombrado a `hipModuleLoadData`, retorna NULL en sistemas endurecidos" | **Falso.** `hipModuleLoad` sigue existiendo en ROCm 5/6. |
| 4 | "Stack overflow por `device\\\_args` en Windows LLP64" | **Falso para este código.** `ctypes.c\\\_uint64` es 8 bytes en Windows, y los arrays de ctypes se asignan en el **heap**, no en el stack. Además el runner sincroniza antes de retornar → no hay use-after-free. |
| 5 | "`array('L')` de 32 bits trunca punteros" | El código usa `(ctypes.c\\\_uint64 \\\* num\\\_args)()` — 8 bytes siempre. |
| 6 | "O(N·D) DRAM saturation del fallback QR" | **No verificable: no existe implementación de QR en el monolito.** El cuerpo de `compute\\\_gram\\\_and\\\_factorize` es puro pseudocódigo-comentario. |


## \***1. Errores NUEVOS que el tribunal NO vio (los importantes de esta ronda)**

\***P1 — Funcional: `write\\\_tensor\\\_to\\\_pmtp` es un no-op.**

\***Python**

```
\*\*\*\`def write\\\_tensor\\\_to\\\_pmtp(self, x, ctrl\\\_ptr, buffer\\\_idx, next\\\_seq):\`\*\*  
  
\`    \*\*\*safe\\\_x = require\\\_f64\\\_vector(x, dim=self.D)   \*\\\# sanitiza...\`\*\*\*  
  
\`    \*\*\*if self.cpp\\\_lib:\`\*\*  
  
\`        \*\*\*self.cpp\\\_lib.polydim\\\_publish\\\_write(...)   \*\\\# ...y descarta safe\\\_x. NUNCA copia el tensor al buffer.\`\*\*\*
```

\***El tensor jamás llega al buffer. Publicás índices de buffers vacíos. Esto solo, destruye todo el "zero-copy PMTP" hasta que se arregle.**

\***P1 — Detector de hardware: una máquina ROCm se autodetecta como CUDA. `\\\_probe\\\_cuda` se ejecuta primero y no filtra por vendor. Con PyTorch-ROCm, `torch.cuda.is\\\_available()` es `True` y el device se llama "AMD Radeon..." → el sistema selecciona `cuda\\\_cubin\\\_runner` para una GPU AMD. Falla garantizada. Y `\\\_probe\\\_rocm` nunca llega a ejecutarse.**

\***P1 — `compute\\\_gram\\\_and\\\_factorize`: división antes del chequeo + OOB + tiers muertos.**

\***cpp**

```
\*\*\*\`double eta = dmax / dmin;                    \*// ← dmin puede ser 0 → eta=inf; si dmax=0 → NaN\`\*\*\*  
  
\*\*\*\`if (dmin == 0.0 || eta \\\>= 1e8) \\\{ ... \\\}       \*// el chequeo llega DESPUÉS de la división\`\*\*\*
```

\***Con `R` todo ceros: `eta=NaN` → `NaN \\\>= 1e8` es false → `NaN \\\<= 1e4` es false → cae al tier ambiguo con comparaciones NaN → `kappa\\\_est=1.0` (stub) → siempre Shifted-CholQR2, nunca MGS2. Además: `R\\\[0\\\]` se lee aunque `N==0`, no hay chequeo de null, y ninguno de los tres tiers tiene implementación.**

\***P1 — El código no compila en Windows con MSVC: `\\\_\\\_asm\\\_\\\_ volatile("":::"memory")` en `enable\\\_ftz\\\_daz()` es sintaxis GNU, rechazada por `cl`.**

\***P1 — Off-by-two en el probe de cache line de Windows: lee `LineSize` en `offset+12`, pero el campo está en `offset+14` (Number=8, Relationship=4, Level=1, Associativity=1). En Windows estás leyendo Level+Associativity como si fueran el tamaño de línea → alineación basura propagada a todo el sistema.**

\***P2 — `\\\_probe\\\_rocm` reporta FP64 nativo para TODA GPU AMD, incluidas Radeon consumer RDNA (razón FP64 ~1/16–1/32), contradiciendo tu propio Silicon Contract y contaminando `max\\\_safe\\\_dim`.**

\***P2 — `\\\_probe\\\_tpu` lanza excepción no capturada (`jnp.float64` con x64 deshabilitado → `TypeError`, no `ImportError`) → en TPU real con x64 off, el probe revienta, se traga el error el loop de `contract()`, y caés a CPU silenciosamente.**

\***P2 — Test V760 certificado con DLLs V753 y `polydim\\\_ffi\\\_v760.dart` con defaults hardcodeados a `...\\\\ENTREGA\\\_2026\\\_09\\\_18\\\_V753\\\\bin\\\\...`. Confusión de versión estructural.**

\***P2 — `polydim\\\_triton\\\_kernel\\\_v760.py` usa la API de Triton 2.x. `triton.compile(fn, signature=..., constants=...)` fue reemplazado por `ASTSource` en Triton 3.x (estándar actual). En instalación moderna tira `TypeError`.**

\***P2 — `hip\\\_hsaco\\\_runner`: `load\\\_hip\\\_driver` no es thread-safe (race sobre `g\\\_hip` con GIL liberado por ctypes), usa `RTLD\\\_GLOBAL` (superficie de hijack de símbolos), y en Windows `LoadLibraryA` sin `LOAD\\\_LIBRARY\\\_SEARCH\\\_SYSTEM32` (DLL hijacking clásico). `hip\\\_get\\\_device\\\_count` llama `hipDeviceGet` sin `hipInit` previo.**

\***P3 — Coherencia de claims: el README promete "Rust guard verifica homología β1" — ese código no existe en ningún archivo (solo `validate\\\_vector`). El contrato BG-15 de alineación dinámica no está cableado: el kernel C++ hardcodea `CACHE\\\_LINE = 64` mientras el probe recomienda 64. El Dart valida norma sobre `y` solo, mientras el test Python valida `y + y\\\_comp`.**

## \***2. Correcciones concretas (las que desbloquean todo lo demás)**

\***PMTP C++ — seqcount pattern, elimina el torn read:**

\***cpp**

```
\*\*\*\`bool polydim\\\_acquire\\\_read(PMTP\\\_Control\\\* ctrl, uint64\\\_t& observed\\\_seq, uint32\\\_t& safe\\\_buffer) \\\{\`\*\*  
  
\`    \*\*\*uint64\\\_t s1 = ctrl-\\\>sequence.load(std::memory\\\_order\\\_acquire);\`\*\*  
  
\`    \*\*\*if (s1 == observed\\\_seq) return false;\`\*\*  
  
\`    \*\*\*uint32\\\_t b  = ctrl-\\\>active\\\_buffer.load(std::memory\\\_order\\\_acquire);\`\*\*  
  
\`    \*\*\*std::atomic\\\_thread\\\_fence(std::memory\\\_order\\\_acquire);\`\*\*  
  
\`    \*\*\*uint64\\\_t s2 = ctrl-\\\>sequence.load(std::memory\\\_order\\\_acquire);\`\*\*  
  
\`    \*\*\*if (s1 != s2) return false;          \*// publicación interrumpida: reintentar\`\*\*\*  
  
\`    \*\*\*safe\\\_buffer = b; observed\\\_seq = s1; return true;\`\*\*  
  
\*\*\*\`\\\}\`\*\*
```

\***Y en Rust: `\\\#\\\[repr(C, align(128))\\\]` + misma lógica + chequeo de subnormal inmune a DAZ por bits:**

\***rust**

```
\*\*\*\`let bits = v.to\\\_bits();\`\*\*  
  
\*\*\*\`let subnormal = (bits & 0x7FF0\\\_0000\\\_0000\\\_0000) == 0 && (bits & 0x000F\\\_FFFF\\\_FFFF\\\_FFFF) != 0;\`\*\*
```

\***Gram/factorize — guardas primero, implementación después:**

\***cpp**

```
\*\*\*\`void compute\\\_gram\\\_and\\\_factorize(double\\\* G, double\\\* R, int N) \\\{\`\*\*  
  
\`    \*\*\*if (!G || !R || N \\\<= 0) return;\`\*\*  
  
\`    \*\*\*double dmin = std::abs(R\\\[0\\\]), dmax = dmin;\`\*\*  
  
\`    \*\*\*for (int i = 1; i \\\< N; ++i) \\\{ \*/\\\* ... \\\*/\* \\\}\`\*\*  
  
\`    \*\*\*if (dmin == 0.0) \\\{ \*/\\\* Tier 3 MGS2 \\\*/\* return; \\\}\`\*\*  
  
\`    \*\*\*double eta = dmax / dmin;   \*// ahora es seguro\`\*\*\*  
  
\`    \*\*\*...\`\*\*  
  
\*\*\*\`\\\}\`\*\*
```

\***Probe — vendor filter (arregla lo P1 de detección):**

\***Python**

```
\*\*\*\`def \\\_probe\\\_cuda() -\\\> Optional\\\[dict\\\]:\`\*\*  
  
\`    \*\*\*...\`\*\*  
  
\`    \*\*\*name = props.name.lower()\`\*\*  
  
\`    \*\*\*if any(v in name for v in ("amd", "radeon", "mi2", "mi3")):\`\*\*  
  
\`        \*\*\*return None          \*\\\# dejar que \\\_probe\\\_rocm lo tome\`\*\*\*
```

\***Probe Windows: `line\\\_size = struct.unpack\\\_from("\\\<H", buf, offset + 14)\\\[0\\\]`**

\***HIP runner — RAII + once\_flag: envolver el módulo en un guard cuyo destructor llama `hipModuleUnload`, resolver símbolos bajo `std::once\\\_flag`, y cambiar a `RTLD\\\_LOCAL | RTLD\\\_DEEPBIND` / `LoadLibraryExA(..., LOAD\\\_LIBRARY\\\_SEARCH\\\_SYSTEM32)`.**

## \***3. El plan para que no vuelvas 600 veces**

\***El orden importa, y te lo doy como cadena de dependencias:**

1. \***Incluir el código fuente del kernel geodésico real (hoy: binario V753) en el dossier. Sin eso, ninguna certificación de deriva 4.44e-16 es auditable — es el hueso más grande.**

2. \***Arreglar `write\\\_tensor\\\_to\\\_pmtp` (no-op) y agregar un allocator de `PMTP\\\_Control` con alineación 128 en Python.**

3. \***Unificar PMTP a 128 bytes + seqcount en C++ y Rust.**

4. \***Guardas en `compute\\\_gram\\\_and\\\_factorize` + implementar al menos un tier real (CholQR2).**

5. \***Vendor filter + offset Windows + tabla FP64 por arquitectura gfx en el probe.**

6. \***RAII/thread-safety/hijack-hardening en el runner HIP.**

7. \***API Triton 3.x + paths V760 en Dart + tests de concurrencia y path HIP con captura de stderr.**

\***El informe completo, con cada hallazgo citado contra su archivo/línea, el veredicto del tribunal correspondiente (real/refutado), y el código corregido listo para pegar, está acá:**

\***Used 1 tool**

\***Execute Python code**

\***Thinking complete**

\***Informe completo escrito: 557 líneas, 24 hallazgos accionables (4 P1 nuevos, 6 P2, 6 P3), 7 refutados del tribunal, 7 fixes con código listo para pegar.**

\***Para cerrar la idea central: no necesitás 600 rondas más. Necesitás una entrega que incluya el corazón. El perímetro ya está mapeado casi completo: lo que queda descubierto cada vez que volvés no es que "falta revisar" — es que el kernel geodésico real y el slab allocator PMTP no están en el dossier, y sin ellos cada ronda solo puede re-raspar la superficie. Traé el fuente de `polydim.core` y del kernel V753 en la próxima entrega, y esto converge en una o dos rondas.**

\***El orden exacto de arreglo (cadena de dependencias) está en la Sección C del informe: empezá por B1 (`write\\\_tensor\\\_to\\\_pmtp` no copia nada — eso solo invalida todo el flujo PMTP), después la unificación del bloque de control a 128B con seqcount, después el probe (detección ROCm rota + offset Windows +14), y recién entonces el runner HIP. Cada fix tiene el código en la Sección D.**

\***Si querés, en la próxima ronda puedo redactar los archivos completos ya corregidos (kernel\_cpp, kernel\_rust, probe, runner HIP) como entrega lista, no solo parches.**

![](data:image/svg+xml;base64,PHN2ZyB3aWR0aD0nNTInIGhlaWdodD0nNjgnIHZpZXdCb3g9JzAgMCA1MiA2OCcgZmlsbD0nbm9uZScgeG1sbnM9J2h0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnJz48cGF0aCBkPSdNMzkuNjI3IDkuMTExMzNDMzkuNjQ2MSAxMC40ODU5IDQwLjc3MTggMTEuNTg3OCA0Mi4xNDY1IDExLjU3NzFMNTAuMDAxIDExLjUxNTZMMzkuNTI1NCAxLjg0NTdMMzkuNjI3IDkuMTExMzNaJyBmaWxsPScjMTIxMjEyJy8+PHBhdGggZD0nTTQ2IDY3QzQ4Ljc2MTQgNjcgNTEgNjQuNzYxNCA1MSA2MlYxMi41MDY4TDQyLjE1NDMgMTIuNTc2MkM0MC4yMjk3IDEyLjU5MTIgMzguNjUzNyAxMS4wNDk0IDM4LjYyNyA5LjEyNUwzOC41MTM3IDFINkMzLjIzODU4IDEgMSAzLjIzODU4IDEgNlY2MkMxIDY0Ljc2MTQgMy4yMzg1OCA2NyA2IDY3SDQ2WicgZmlsbD0nd2hpdGUnIGZpbGwtb3BhY2l0eT0nMC4xMicvPjxwYXRoIGQ9J000NiA2N0M0OC43NjE0IDY3IDUxIDY0Ljc2MTQgNTEgNjJWMTIuNTA2OEw0Mi4xNTQzIDEyLjU3NjJDNDAuMjI5NyAxMi41OTEyIDM4LjY1MzcgMTEuMDQ5NCAzOC42MjcgOS4xMjVMMzguNTEzNyAxSDZDMy4yMzg1OCAxIDEgMy4yMzg1OCAxIDZWNjJDMSA2NC43NjE0IDMuMjM4NTggNjcgNiA2N0g0NlonIGZpbGw9JyMxMjEyMTInLz48cGF0aCBkPSdNNDYgNjdDNDguNzYxNCA2NyA1MSA2NC43NjE0IDUxIDYyVjEyLjUwNjhMNDIuMTU0MyAxMi41NzYyQzQwLjIyOTcgMTIuNTkxMiAzOC42NTM3IDExLjA0OTQgMzguNjI3IDkuMTI1TDM4LjUxMzcgMUg2QzMuMjM4NTggMSAxIDMuMjM4NTggMSA2VjYyQzEgNjQuNzYxNCAzLjIzODU4IDY3IDYgNjdINDZaJyBmaWxsPSd1cmwoI3BhaW50MF9saW5lYXJfMzI0ODhfMzE2MTgpJy8+PHBhdGggZmlsbC1ydWxlPSdldmVub2RkJyBjbGlwLXJ1bGU9J2V2ZW5vZGQnIGQ9J00wIDZWNjJDMCA2NS4zMTM3IDIuNjg2MjkgNjggNiA2OEw2IDY3QzMuMjM4NTggNjcgMSA2NC43NjE0IDEgNjJWNkMxIDMuMjM4NTggMy4yMzg1OCAxIDYgMUgzOC41MTM3TDM4LjYyNyA5LjEyNUMzOC42NTM3IDExLjA0OTQgNDAuMjI5NyAxMi41OTEyIDQyLjE1NDMgMTIuNTc2Mkw1MSAxMi41MDY4VjYyQzUxIDY0Ljc2MTQgNDguNzYxNCA2NyA0NiA2N1Y2OEM0OS4zMTM3IDY4IDUyIDY1LjMxMzcgNTIgNjJWMTJMMzkgMEg2QzIuNjg2MjkgMCAwIDIuNjg2MjkgMCA2Wk00Mi4xNDY1IDExLjU3NzFDNDAuNzcxOCAxMS41ODc4IDM5LjY0NjEgMTAuNDg1OSAzOS42MjcgOS4xMTEzM0wzOS41MjU0IDEuODQ1N0w1MC4wMDEgMTEuNTE1Nkw0Mi4xNDY1IDExLjU3NzFaJyBmaWxsPScjMzUzNTM1Jy8+PHBhdGggZD0nTTYgNjhINDZWNjdINkw2IDY4WicgZmlsbD0nIzM1MzUzNScvPjxwYXRoIGQ9J00yOC4zNjEzIDM0LjcxNjhDMjguNzQ3OCAzNC43MTY4IDI5LjA2MTMgMzUuMDI5NiAyOS4wNjE1IDM1LjQxNkMyOS4wNjE1IDM1LjgwMjYgMjguNzQ3OSAzNi4xMTYyIDI4LjM2MTMgMzYuMTE2MkgxOC4xNjAyQzE3Ljc3MzYgMzYuMTE2MiAxNy40NiAzNS44MDI2IDE3LjQ2IDM1LjQxNkMxNy40NjAxIDM1LjAyOTYgMTcuNzczNyAzNC43MTY4IDE4LjE2MDIgMzQuNzE2OEgyOC4zNjEzWicgZmlsbD0nd2hpdGUnIGZpbGwtb3BhY2l0eT0nMC41NicvPjxwYXRoIGQ9J00zMy44Mzk4IDI5LjI5OThDMzQuMjI2NCAyOS4yOTk4IDM0LjU0IDI5LjYxMzQgMzQuNTQgMzBDMzQuNTM5OCAzMC4zODYzIDM0LjIyNzEgMzAuNjk5IDMzLjg0MDggMzAuNjk5MkgxOC4xNjAyQzE3Ljc3MzcgMzAuNjk5MiAxNy40NjAyIDMwLjM4NjQgMTcuNDYgMzBDMTcuNDYgMjkuNjEzNCAxNy43NzM2IDI5LjI5OTggMTguMTYwMiAyOS4yOTk4SDMzLjgzOThaJyBmaWxsPSd3aGl0ZScgZmlsbC1vcGFjaXR5PScwLjU2Jy8+PHBhdGggZD0nTTMzLjgzOTggMjMuODgyOEMzNC4yMjY0IDIzLjg4MjggMzQuNTQgMjQuMTk2NCAzNC41NCAyNC41ODNDMzQuNTQgMjQuOTY5NiAzNC4yMjY0IDI1LjI4MzIgMzMuODM5OCAyNS4yODMySDE4LjE2MDJDMTcuNzczNiAyNS4yODMyIDE3LjQ2IDI0Ljk2OTYgMTcuNDYgMjQuNTgzQzE3LjQ2IDI0LjE5NjQgMTcuNzczNiAyMy44ODI4IDE4LjE2MDIgMjMuODgyOEgzMy44Mzk4WicgZmlsbD0nd2hpdGUnIGZpbGwtb3BhY2l0eT0nMC41NicvPjxkZWZzPjxsaW5lYXJHcmFkaWVudCBpZD0ncGFpbnQwX2xpbmVhcl8zMjQ4OF8zMTYxOCcgeDE9JzI2JyB5MT0nMCcgeDI9JzI2JyB5Mj0nNjgnIGdyYWRpZW50VW5pdHM9J3VzZXJTcGFjZU9uVXNlJz48c3RvcCBzdG9wLWNvbG9yPSd3aGl0ZScgc3RvcC1vcGFjaXR5PScwLjAzJy8+PHN0b3Agb2Zmc2V0PScxJyBzdG9wLWNvbG9yPSd3aGl0ZScgc3RvcC1vcGFjaXR5PScwJy8+PC9saW5lYXJHcmFkaWVudD48L2RlZnM+PC9zdmc+)

\***POLYDIM\_V760\_AUDITORIA\_BULLDOG\_R3.md**

\***Preview file**

**InstantStandard**



