# **ROUND 1 — EL PRIMER PROBLEMA GRAVE: EL DPI ESTÁ MAL UTILIZADO**

El dossier afirma:

> “The 1D Worm ... violates the Data Processing Inequality (DPI)”

y escribe:

I(X;Z)≤I(X;Y)

Esto **no demuestra ninguna violación**. De hecho, esa desigualdad **es precisamente la Data Processing Inequality** cuando

X→Y→Z

forma una cadena de procesamiento.

Si:

Z=g(Y)

entonces:

I(X;g(Y))≤I(X;Y)

es lo esperado.

### **Qué significa realmente**

Si un vector hiperdimensional se serializa:

Y∈RD

a JSON:

Z=JSON(Y)

hay varios casos.

### **Caso A — codificación reversible**

En principio:

Y↔Z

puede ser reversible.

Entonces idealmente:

I(X;Z)=I(X;Y)

La serialización puede ser **terriblemente ineficiente**, pero no necesariamente destruye información.

### **Caso B — cuantización**

Por ejemplo:

Y→Q(Y)

sí puede reducir información.

### **Caso C — truncamiento**

Y→(y1​,…,yk​)

puede perder información.

### **Caso D — generación autoregresiva**

Aquí sí aparece un cuello de botella radicalmente distinto:

Y→tokens→decoding→Y′

pero hay que medir la pérdida y el coste.

## **Corrección SOTA**

No hay que defender POLYDIM diciendo:

> “JSON viola DPI”.

Eso es matemáticamente incorrecto.

La formulación fuerte y defendible sería:

La serializacioˊn no necesariamente viola DPI; introduce un canal de representacioˊn que puede ser​lossy, cuantizado, secuencial, costoso en memoria y desacoplado de la geometrıˊa original.​

Y entonces demostrar experimentalmente:

distortion(Y,Y^)latencybandwidthallocation countenergymutual-information retention

en lugar de atribuirlo incorrectamente al DPI.

**Estado:** 🔴 **ERROR MATEMÁTICO REAL.**

# **ROUND 2 — “O(1) TENSOR TRANSFER” NO SIGNIFICA O(1) TRANSFERENCIA DEL TENSOR**

El dossier afirma que PMTP obtiene:

> “O(1) tensor transfer”

mediante punteros/tags.

Esto requiere una distinción fundamental.

Si el tensor tiene:

D=107

y ocupa:

80MB

aproximadamente en FP64,

pasar un descriptor:

```
\*\*\`slot\\\_id\`\*\*  
  
\*\*\`offset\`\*\*  
  
\*\*\`length\`\*\*  
  
\*\*\`sequence\`\*\*  
  
\*\*\`generation\`\*\*
```

puede ser O(1).

Pero **el tensor no ha sido transferido**.

Se ha transferido el **descriptor del tensor**.

El consumidor posteriormente tiene que leer:

O(D)

datos.

Por tanto:

Tpublish​=O(1)​

puede ser correcto.

Pero:

Tconsume​=O(D)​

y el tráfico de memoria sigue siendo:

Θ(D)

si el consumidor procesa el vector completo.

Esto no es una objeción contra POLYDIM. Es precisamente cómo debe formularse correctamente la ventaja.

### **Mejor formulación**

Separar:

Tmetadata​

de:

Tpayload access​

y demostrar:

Tmetadata​≈O(1)

mientras:

Tpayload​≈BWeffective​D⋅sizeof(float)​

Eso convierte una afirmación vulnerable en una afirmación sólida.

**Estado:** 🟠 **CLAIM SOBRECOMPRIMIDO / MAL DEFINIDO.**

# **ROUND 3 — HAY UN PROBLEMA MUCHO MÁS SERIO: “POINTERS” ENTRE PROCESOS**

El README dice:

> “Pointers are transferred via 64-bit packed atomic sequence tags”

Esto es peligrosísimo si se interpreta literalmente como **punteros virtuales**.

Un puntero:

```
\*\*\`0x7f1234560000\`\*\*
```

de proceso A **no tiene por qué significar nada** en proceso B.

Con:

```
\*\*\`mmap()\`\*\*
```

el mismo segmento puede mapearse como:

```
\*\*\`Process A:\`\*\*  
  
\*\*\`0x7f1000000000\`\*\*  
  
  
\*\*\`Process B:\`\*\*  
  
\*\*\`0x7f9000000000\`\*\*
```

El offset físico dentro del segmento puede ser idéntico, pero el puntero virtual no.

## **Por tanto**

Para IPC robusto no debe viajar:

pointer

sino algo equivalente a:

(segment\_id, offset, length, generation, type, checksum/version)​

y cada proceso reconstruye:

ptr=baselocal​+offset

Esto es particularmente importante porque POLYDIM pretende:

- Zero-copy

- SharedMemory

- IPC

- FFI

- múltiples agentes

- eventualmente RDMA

La representación correcta es un **capability/handle**, no un puntero crudo.

### **Solución**

Definir un descriptor ABI explícito:

```
\*\*\`PMTP\\\_Handle \\\{\`\*\*  
  
\`    \*\*uint32 segment\\\_id;\`\*\*  
  
\`    \*\*uint32 generation;\`\*\*  
  
\`    \*\*uint64 byte\\\_offset;\`\*\*  
  
\`    \*\*uint64 byte\\\_length;\`\*\*  
  
\`    \*\*uint64 sequence;\`\*\*  
  
\`    \*\*uint32 dtype;\`\*\*  
  
\`    \*\*uint32 rank;\`\*\*  
  
\*\*\`\\\}\`\*\*
```

y prohibir semánticamente:

```
\*\*\`raw\\\_pointer\\\_across\\\_process\\\_boundary\`\*\*
```

Esto además permite detectar:

- stale handles

- ABA

- use-after-recycle

- tamaño incorrecto

- dtype mismatch

- generación antigua.

**Estado:** 🔴 **BRECHA ARQUITECTÓNICA CRÍTICA.**

Esta es una de las primeras cosas que yo corregiría antes de llamar al sistema “industrial”.

# **ROUND 4 — EL “LOCK-FREE” TODAVÍA NO ESTÁ DEMOSTRADO**

El dossier dice:

> “Lock-Free Triple-Buffering SPMC”

y presenta:

> 0 torn reads / 218,417 validated reads.

Eso demuestra una cosa mucho más pequeña:

en esa ejecucioˊn no se observaron lecturas desgarradas

No demuestra:

lock-free

La propiedad lock-free es una propiedad del algoritmo bajo el modelo de memoria y las operaciones atómicas.

Necesitamos demostrar, entre otras cosas:

### **Writer progress**

Si un reader queda bloqueado/pausado:

writer→progress

### **Reader progress**

Si el writer sigue produciendo:

reader→eventual observation

### **ABA**

Si:

slot=A→B→A

el reader debe poder distinguir:

Ageneration1​=Ageneration2​

### **Memory ordering**

Necesitamos ver realmente:

```
\*\*\`memory\\\_order\\\_release\`\*\*  
  
\*\*\`memory\\\_order\\\_acquire\`\*\*  
  
\*\*\`memory\\\_order\\\_acq\\\_rel\`\*\*
```

etc.

No basta con afirmar “seqlock”.

### **Más importante todavía**

El benchmark dice:

```
\*\*\`escrituras=452583\`\*\*  
  
\*\*\`lecturas\\\_ok=1098\`\*\*  
  
\*\*\`carreras\\\_detectadas=82548\`\*\*  
  
\*\*\`sin\\\_novedad=7845655\`\*\*
```

Eso muestra que el sistema está experimentando una enorme cantidad de intentos de lectura sin novedad/races respecto de sólo 1098 lecturas aceptadas.

Eso no prueba hambre cero.

La métrica correcta debe distinguir:

attemptssuccessful acquisitionsretry countmax retry streakmax reader latencywriter latencyfairnessstarvation probability

El test actual sólo demuestra ausencia de torn reads **entre las lecturas finalmente validadas**.

**Estado:** 🔴 **LOCK-FREE NO DEMOSTRADO.**

# **ROUND 5 — LA AFIRMACIÓN DE 64ϵ INDEPENDIENTE DE D ES EL PUNTO MATEMÁTICO MÁS DELICADO**

El dossier dice:

64ϵmach​=1.42×10−14

independiente de D.

La frase:

> “invariant bound ... independent of dimension D”

no puede salir simplemente de haber ejecutado:

D=1000,105,106

Eso es una **observación experimental**, no una demostración asintótica.

Además, para una suma FP convencional, el error clásico está ligado a:

γn​=1−nϵnϵ​

aunque la compensación puede mejorar drásticamente la dependencia.

Pero hay que demostrar exactamente qué algoritmo se está utilizando y qué error residual queda.

### **Y hay otro problema**

El dossier dice:

> “TwoSum compensation to eliminate floating-point drift”

“eliminate” es demasiado fuerte.

TwoSum no elimina el error de redondeo.

Permite representar:

a+b=s+e

de forma exacta bajo las condiciones correspondientes, pero luego el algoritmo completo debe demostrar cómo se propaga:

e1​,e2​,…

La compensación puede **acotar** el error.

No significa automáticamente:

error=0

ni:

error≤64ϵ

para todo:

D≤107.

### **Solución correcta**

Separar tres niveles:

**Nivel 1 — theorem**

Probar una cota:

∥y^​−y∥≤f(D,ϵ,θ,κ,…)

**Nivel 2 — adversarial numerical validation**

Probar:

D=103,…,107

con datos específicamente construidos para maximizar error.

**Nivel 3 — measured bound**

Reportar:

Dmax​ED​

sin convertirlo automáticamente en teorema.

**Estado:** 🔴 **LA CERTIFICACIÓN ASINTÓTICA NO ESTÁ JUSTIFICADA POR LA EVIDENCIA PRESENTADA.**

# **ROUND 6 — EL TEST DE D=106 NO CERTIFICA D=107**

El objetivo declarado incluye:

D≤107

pero el benchmark principal de Rodrigues muestra:

```
\*\*\`D=1000\`\*\*  
  
\*\*\`D=100000\`\*\*  
  
\*\*\`D=1000000\`\*\*
```

No:

```
\*\*\`D=10000000\`\*\*
```

Eso importa.

Para FP64:

107×8=80MB

por vector.

Para:

y,u,v,yout​

tenemos aproximadamente:

320MB

sólo en cuatro arrays.

Y eso sin:

- temporales

- allocator

- buffers PMTP

- páginas

- cache effects

- thread-private state

- Rust reports

- guard buffers.

El sistema debe probar explícitamente:

D=107

y, si el objetivo es escalabilidad, idealmente una curva:

103,104,105,106,107.

**Estado:** 🔴 **COBERTURA INCOMPLETA DEL DOMINIO DECLARADO.**

# **ROUND 7 — EL CLAIM “BETTI-1 VERIFICADO MEDIANTE DSU” NO CIERRA MATEMÁTICAMENTE**

Este es otro problema serio.

El dossier afirma:

> “Betti-1 formalizado en el motor Sparse VR DSU”

Un **DSU / Union-Find** permite calcular esencialmente:

β0​

número de componentes conexas.

Pero:

β1​

es otra cosa.

Para un complejo simplicial:

β1​=dimker∂1​−rank∂2​.

Necesitas información sobre:

- vértices

- aristas

- 2-simplices

- ciclos

- fronteras de triángulos.

Union-Find por sí solo no calcula:

rank∂2​.

Para un grafo 1-dimensional sí puedes obtener:

β1​=E−V+C

pero eso es el primer Betti del **grafo**, no automáticamente del complejo Vietoris–Rips completo.

Y en un VR complex:

triangles

pueden matar ciclos.

## **Ejemplo conceptual**

Un triángulo:

v1​−v2​−v3​−v1​

como grafo tiene:

β1​=1

pero como complejo simplicial que contiene el 2-simplex:

\[v1​,v2​,v3​\]

tiene:

β1​=0.

DSU no detecta esa diferencia.

### **Solución**

Si realmente quieren certificar β1​:

β1​=dimker∂1​−rank∂2​​

y deben implementar o verificar algebraicamente el rango de ∂2​, posiblemente con:

- sparse GF(2)

- persistent homology

- boundary matrix reduction

- sparse rank

- filtración VR.

Si lo único que quieren demostrar es conectividad, llamarlo:

β0​

y retirar la afirmación sobre β1​.

**Estado:** 🔴 **ERROR MATEMÁTICO REAL.**

# **ROUND 8 — SD−1 NO ES LO MISMO QUE “LA COHESIÓN DEL SISTEMA MULTIAGENTE”**

El dossier mezcla:

β1​(SD−1)=0,D\>2

con:

> “cohesion of the multi-agent manifold”

Eso no se deduce.

Que el espacio matemático subyacente sea:

SD−1

no significa que el conjunto de estados de los agentes tenga necesariamente la misma topología.

Si tienes:

\{x1​,…,xN​\}⊂SD−1

la topología inducida por:

- un grafo de comunicación,

- un Vietoris-Rips complex,

- un kernel,

- un umbral de distancia,

- una filtración,

puede tener:

β1​\>0.

Por tanto:

β1​(SD−1)=0

no certifica:

β1​(agent communication complex)=0.

Son objetos matemáticos diferentes.

**Estado:** 🔴 **CONFUSIÓN ENTRE ESPACIO AMBIENTE Y TOPOLOGÍA DE LA MUESTRA/COMPLEJO.**

# **ROUND 9 — LA “TANGENCIA” NO ES NECESARIA PARA LA ORTOGONALIDAD DE CAYLEY, PERO ESO NO RESUELVE TODO**

Aquí el tribunal externo tiene parcialmente razón.

Si:

W=GXT−XGT

entonces:

WT=−W

para cualquier G.

Por tanto la transformación de Cayley asociada puede ser ortogonal independientemente de que G sea tangente.

Así que decir:

> “un G euclídeo no tangente rompe necesariamente YTY=I”

sí sería incorrecto.

Pero el dossier va demasiado lejos al usar eso como:

> “todo está resuelto”.

La cuestión correcta es:

### **Ortogonalidad**

YTY=I

puede mantenerse.

### **Pero retracción de Stiefel**

Para que sea una retraction adecuada de la variedad, necesitas las condiciones correspondientes sobre el vector tangente / dirección y la propiedad:

RX​(0)=XDRX​(0)\[ξ\]=ξ

según la definición de retraction utilizada.

Por tanto hay que separar:

orthogonality preservation​

de:

valid manifold retraction​

y de:

descent direction / optimization correctness​.

El tribunal mezcla estas propiedades.

**Estado:** 🟠 **CONCLUSIÓN EXCESIVA, aunque la objeción original de tangencia puede estar mal formulada.**

# **ROUND 10 — “33% MENOS FLOPS” NECESITA UNA REVISIÓN**

El documento dice:

> 3K2D → 2K2D

y:

> “saving 33% FLOPs”

Eso es demasiado simplificado.

Construir:

W=\[X,G\]

y obtener:

WTW

no significa automáticamente exactamente:

2K2D

operaciones relevantes.

Hay:

(2K)×(2K)

productos.

Si explotas simetría:

2(2K)(2K+1)​≈2K2

sí aparece esa magnitud.

Pero el coste real incluye:

- multiplicaciones

- sumas

- diagonal

- simetría

- almacenamiento

- acceso a X/G

- reconstrucción

- resolución 2K×2K

- operaciones posteriores.

Y además la afirmación:

> “reducing DRAM traffic”

no sale sólo de contar FLOPs.

Para demostrarlo hay que medir:

bytes readbytes writtenL1 missesL2 missesLLC missesmemory bandwidth

y/o usar hardware performance counters.

**Estado:** 🟠 **CLAIM DE PERFORMANCE NO DEMOSTRADO COMO ESTÁ FORMULADO.**

# **ROUND 11 — EL PIVOT THRESHOLD NO ESTÁ MATEMÁTICAMENTE JUSTIFICADO**

Se usa:

pivotthr​=tolpivot​∥M∥∞​2K.

Que sea relativo es una mejora respecto de:

10−15

absoluto.

Pero:

∥M∥∞​2K

no es automáticamente la escala correcta para decidir singularidad/numerical stability.

El criterio debería relacionarse con:

- escala de M

- condición

- backward error

- precisión

- algoritmo de factorización

- crecimiento de pivote.

Además, un threshold demasiado grande puede rechazar matrices perfectamente válidas.

Necesitamos test:

κ(M)

controlado, por ejemplo:

100,102,104,…

y medir:

∥M∥∥Z^∥+∥B∥∥MZ^−B∥​

en lugar de simplemente comprobar:

```
\*\*\`pivot != 0\`\*\*
```

**Estado:** 🟠 **HEURÍSTICA RAZONABLE, NO CERTIFICACIÓN MATEMÁTICA.**

# **ROUND 12 — “IEEE-754 CONFORME” ES DEMASIADO AMPLIO**

El contrato dice:

> FTZ/DAZ=OFF (conforme IEEE-754)

Eso sólo demuestra una parte del problema.

IEEE-754 tiene muchas dimensiones:

- rounding mode

- subnormals

- NaN propagation

- signed zero

- infinities

- FMA

- exception flags

- signaling NaNs

- underflow behavior

- overflow

- reproducibility.

Además:

```
\*\*\`-fno-fast-math\`\*\*  
  
\*\*\`-fno-associative-math\`\*\*  
  
\*\*\`-ffp-contract=off\`\*\*
```

no convierte automáticamente todo el programa en una implementación formalmente reproducible IEEE-754.

Y:

```
\*\*\`OpenMP\`\*\*
```

introduce otro problema:

orden de reduccioˊn

que puede cambiar resultados.

### **Especialmente importante**

Si:

i∑​xi​

se distribuye entre threads:

S=S1​+S2​+⋯+Sp​

el orden de combinación puede variar.

Para una certificación numérica fuerte hay que distinguir:

accuracy

de:

bitwise reproducibility.

**Estado:** 🟠 **CERTIFICACIÓN DEMASIADO AMPLIA.**

# **ROUND 13 — “EXACT IEEE MACHINE EPSILON” YA APARECE MAL EXPRESADO**

En el dossier original aparece la idea de:

4.44×10−16

como:

> “Exact IEEE-754 machine ε”

Pero para FP64:

ϵmach​=2−52≈2.220446049250313×10−16.

Por tanto:

4.44×10−16≈2ϵ.

No es “la epsilon exacta”.

Posteriormente V762 usa:

64ϵ≈1.421×10−14

que sí es aproximadamente correcto.

Pero hay una evolución semántica:

```
\*\*\`4.44e-16 = machine epsilon\`\*\*
```

es incorrecto.

**Estado:** 🟠 **ERROR NUMÉRICO DE DEFINICIÓN.**

# **ROUND 14 — LOS BENCHMARKS NO PERMITEN DECIR “SILICON CERTIFIED”**

Esto es importante porque el dossier lo repite varias veces.

El benchmark proporciona:

```
\*\*\`Linux GCC 15.2\`\*\*  
  
\*\*\`Windows GCC 14.2\`\*\*  
  
\*\*\`MSVC\`\*\*  
  
\*\*\`Rust\`\*\*  
  
\*\*\`Dart\`\*\*
```

pero no especifica de manera suficiente:

- modelo exacto de CPU

- microarquitectura

- frecuencia

- turbo

- affinity

- NUMA

- RAM

- DDR5/DDR4

- governor

- temperatura

- warm-up

- número de muestras

- desviación

- percentiles

- pinning de threads

- estado de caches

- SMT

- versión exacta OpenMP runtime.

Por tanto:

“tested on silicon”​

sí puede decirse.

Pero:

“silicon certified”​

no se desprende de esos datos.

La certificación industrial necesita una matriz de plataforma.

# **ROUND 15 — EL BENCHMARK DE D=106 TIENE UNA MÉTRICA QUE PUEDE ENGAÑAR**

Se reporta:

```
\*\*\`D=1000000\`\*\*  
  
\*\*\`mediana=4.27 ms\`\*\*  
  
\*\*\`min=3.41 ms\`\*\*  
  
\*\*\`hilos=2\`\*\*
```

Para cuatro vectores FP64:

4×106×8=32MB

aproximadamente.

Entonces sólo el streaming mínimo de:

y,u,v,yout​

ya implica del orden de decenas de MB.

La métrica realmente interesante es:

BWeffective​=Tbytes moved​.

Con 32 MB y 4.27 ms:

≈7.5GB/s

como orden de magnitud.

Eso no prueba todavía rendimiento extraordinario.

Hay que medir:

BWread​BWwrite​FLOP/stextarithmeticintensity

y determinar si el kernel es:

memory-bound

o:

compute-bound.

# **ROUND 16 — LA COMPARACIÓN CON OPENBLAS NO ES TODAVÍA APPLES-TO-APPLES**

La tabla es interesante:

| D,K | POLYDIM | OpenBLAS |
| :-: | :-: | :-: |
| 4096,16 | 0.89 ms | 1.77 ms |
| 4096,64 | 9.90 ms | 5.71 ms |
| 16384,32 | 9.68 ms | 14.99 ms |
| 16384,128 | 152.3 ms | 124.24 ms |
| 65536,64 | 143.19 ms | 190.38 ms |


Y aquí aparece algo importante:

**POLYDIM no gana consistentemente.**

En:

K=64,D=4096

OpenBLAS:

5.71ms

POLYDIM:

9.90ms

En:

D=16384,K=128

OpenBLAS:

124.24ms

POLYDIM:

152.30ms.

Esto no es malo. Al contrario: revela dónde está el trabajo SOTA pendiente.

La conclusión correcta no es:

> “POLYDIM es superior a OpenBLAS”.

La conclusión correcta es:

> El kernel especializado presenta ventajas en determinadas regiones de (D,K), pero pierde en otras y requiere un modelo de rendimiento por régimen.

Eso es mucho más útil.

# **ROUND 17 — HAY UNA INCONSISTENCIA EN LAS CIFRAS DEL PMTP**

README:

> 0 torn reads / **218,417** validated reads

Benchmark:

```
\*\*\`lecturas\\\_ok=1098\`\*\*
```

Puede ser que sean dos experimentos distintos, pero el dossier no lo especifica.

Por lo tanto un auditor externo no puede saber si:

218417

es:

- total de intentos,

- total de validaciones,

- otro benchmark,

- acumulación de ejecuciones.

### **Solución**

Cada benchmark debe llevar un ID:

```
\*\*\`RUN\\\_ID\`\*\*  
  
\*\*\`COMMIT\\\_SHA\`\*\*  
  
\*\*\`DATE\`\*\*  
  
\*\*\`CPU\`\*\*  
  
\*\*\`OS\`\*\*  
  
\*\*\`THREADS\`\*\*  
  
\*\*\`ITERATIONS\`\*\*  
  
\*\*\`WRITES\`\*\*  
  
\*\*\`READ\\\_ATTEMPTS\`\*\*  
  
\*\*\`READ\\\_SUCCESS\`\*\*  
  
\*\*\`READ\\\_RETRY\`\*\*  
  
\*\*\`TEAR\\\_DETECTED\`\*\*  
  
\*\*\`MAX\\\_RETRY\\\_STREAK\`\*\*
```

y la tabla debe ser reproducible.

**Estado:** 🟠 **AUDIT TRAIL INSUFICIENTE.**

# **ROUND 18 — 26/26 TESTS PASS NO SIGNIFICA QUE EL SISTEMA ESTÉ CERRADO**

Este es un principio importante del red team.

Los tests prueban:

P(bug bajo suite)

no:

P(bug en todo dominio)=0.

Más aún, varios tests parecen comprobar explícitamente los A1-A12 que el propio equipo ya conocía.

Eso produce:

known-bug regression testing

pero no necesariamente:

unknown-bug discovery.

Falta una capa de **property-based / metamorphic / adversarial testing**.

# **ROUND 19 — FALTA TESTING DE ALIASING EN EL CONTRATO PÚBLICO**

Existe:

```
\*\*\`POLYDIM\\\_ERR\\\_ALIASED\\\_BUFFERS = -11\`\*\*
```

Eso es bueno.

Pero el dossier no muestra evidencia de pruebas como:

```
\*\*\`y\\\_out == y\`\*\*  
  
\*\*\`y\\\_out == u\`\*\*  
  
\*\*\`y\\\_out == v\`\*\*  
  
\*\*\`y\\\_out = y + 1 byte\`\*\*  
  
\*\*\`u/v partially overlap\`\*\*  
  
\*\*\`unaligned pointer\`\*\*  
  
\*\*\`buffer too short\`\*\*  
  
\*\*\`D inconsistent with allocation\`\*\*
```

Especialmente:

yout​=y

puede ser legal o ilegal según el contrato.

El API debe decirlo explícitamente.

### **Solución**

Definir:

alias policy

por función:

| Función | Exact alias | Partial overlap |
| :-: | :-: | :-: |
| Rodrigues | reject/allow explícito | reject |
| project | ... | ... |
| Stiefel | ... | ... |


Y probarlo con ASan/UBSan.

# **ROUND 20 — FALTA LA PRUEBA DE “BUFFER LENGTH”**

El API recibe:

```
\*\*\`const double\\\* y\`\*\*  
  
\*\*\`...\`\*\*  
  
\*\*\`uint64\\\_t D\`\*\*
```

pero no recibe:

```
\*\*\`size\\\_t y\\\_len\`\*\*
```

El kernel no puede saber si el caller realmente proporcionó:

D

elementos.

Por tanto:

```
\*\*\`D = 10,000,000\`\*\*
```

con un buffer de:

```
\*\*\`1000 doubles\`\*\*
```

es un posible out-of-bounds salvo que exista una capa superior que lo impida.

El C API **no tiene forma de verificarlo**.

Esto es fundamental para la afirmación:

> “zero-leak memory safety”.

Memory safety no es sólo liberar memoria.

Incluye:

- bounds

- lifetime

- alignment

- aliasing

- initialization

- race freedom

- ownership.

### **Solución**

API de producción:

```
\*\*\`const double\\\* y,\`\*\*  
  
\*\*\`uint64\\\_t y\\\_len,\`\*\*  
  
\*\*\`...\`\*\*
```

o un descriptor:

```
\*\*\`PolydimBuffer \\\{\`\*\*  
  
\`    \*\*void\\\* data;\`\*\*  
  
\`    \*\*uint64\\\_t elements;\`\*\*  
  
\`    \*\*uint64\\\_t bytes;\`\*\*  
  
\`    \*\*uint32\\\_t dtype;\`\*\*  
  
\`    \*\*uint32\\\_t alignment;\`\*\*  
  
\*\*\`\\\}\`\*\*
```

**Estado:** 🔴 **BRECHA ABI DE SEGURIDAD.**

# **ROUND 21 — `uint64\\\_t D` NO GARANTIZA QUE LAS OPERACIONES DE TAMAÑO SEAN SEGURAS**

Aunque:

```
\*\*\`D\`\*\*
```

sea **`uint64\\\_t`**, expresiones como:

```
\*\*\`D \\\* sizeof(double)\`\*\*
```

pueden tener problemas si se convierten o almacenan en tipos menores.

También hay que controlar:

D⋅sizeof(T)

contra:

SIZE\_MAX.

Para D=107 no hay problema práctico, pero una API industrial no debe depender del rango actual.

Debe existir una función de checked arithmetic:

checked\_mul(D,sizeof(T)).

# **ROUND 22 — `K\\\<=512` NO ES UNA PRUEBA DE ESCALABILIDAD DE STIEFEL**

El test:

```
\*\*\`K=1024 rejected\`\*\*
```

demuestra el límite declarado.

Pero no demuestra que:

K=512

sea seguro/óptimo.

El coste del sistema contiene términos aproximadamente:

O(DK2)

y:

O(K3)

para las operaciones densas pequeñas.

Para:

D=107,K=512

el término:

DK2

es enorme.

Hay que definir el dominio operacional:

(D,K)

no sólo:

D.

# **ROUND 23 — FALTA UN TEST CRÍTICO: θ EXTREMADAMENTE PEQUEÑO**

El dossier celebra:

versin(θ)=2sin2(θ/2).

Correcto como forma para evitar:

1−cosθ.

Pero hay que probar:

θ=10−1,10−4,10−8,10−12,10−16,10−20,10−100,subnormal.

Porque:

sin(θ/2)

puede llegar a límites de representación.

Y hay que comparar contra una referencia de alta precisión.

### **Test obligatorio**

R(y,u,v,θ)

contra:

RMPFR​

para un barrido logarítmico.

No sólo comprobar:

∥y′∥≈1.

Porque una transformación puede conservar norma y estar equivocada angularmente.

Este punto es crucial.

# **ROUND 24 — CONSERVAR NORMA NO DEMUESTRA CORRECCIÓN GEODÉSICA**

Este es un error de validación muy importante.

Actualmente se reporta:

∣∥y′∥−1∣

Eso sólo verifica aproximadamente:

y′∈SD−1.

No verifica:

y′=R(y,u,v,θ).

Una transformación incorrecta puede devolver cualquier vector unitario y pasar ese test.

Hay que verificar:

∥y′−\[y−versin(θ)(...)+sin(θ)(...)\]∥

contra referencia.

Mejor todavía:

R(θ)R(ϕ)y≈R(θ+ϕ)y

cuando se trata de la misma 2-plane rotation.

Y:

R(0)y=y.

Y:

R(θ)u=cosθu+sinθvR(θ)v=−sinθu+cosθv

según la convención elegida.

Esto sí valida la geometría.

# **ROUND 25 — EL TEST “20000 PASOS” NO PRUEBA COMPOSICIÓN GENERAL**

Se afirma:

```
\*\*\`1 paso grande vs 20000 pasos pequeños\`\*\*  
  
\*\*\`diff=8.916e-16\`\*\*
```

Muy buen test.

Pero sólo cubre una trayectoria.

Hay que variar:

N=1,2,10,100,1000,10000,20000,106

y:

θ/N

para diferentes θ.

Además:

R(θ/N)N

debe compararse con:

R(θ).

Y hacer esto para:

- random y/u/v

- casi alineados

- bases con tolerancia

- θ grande

- θ pequeño

- θ≈π

- θ≈2π.

# **ROUND 26 — FALTA LA PRUEBA DE θ≈π**

Las rotaciones geodésicas tienen un régimen numéricamente interesante alrededor de:

π.

No basta probar:

```
\*\*\`normal theta\`\*\*  
  
\*\*\`NaN\`\*\*  
  
\*\*\`Inf\`\*\*
```

Hay que probar:

π−ϵππ+ϵ.

Especialmente porque:

sinθ

cambia signo alrededor de π.

# **ROUND 27 — `project\\\_sphere` NECESITA DEFINIR QUÉ HACER CON y=0**

El API ofrece:

```
\*\*\`polydim\\\_project\\\_sphere\\\_f64\`\*\*
```

Pero la proyección:

P(y)=∥y∥y​

no está definida en:

y=0.

Existe:

```
\*\*\`POLYDIM\\\_ERR\\\_DEGENERATE\\\_NORM\`\*\*
```

pero el dossier no presenta el test.

Debe existir:

```
\*\*\`y = 0\`\*\*
```

y también:

∥y∥≈0

con comportamiento definido.

# **ROUND 28 — `NaN/Inf` EN TODOS LOS COMPONENTES NO ESTÁ CUBIERTO POR UN SOLO TEST**

El benchmark dice:

```
\*\*\`NaN en y rechazado\`\*\*
```

Pero necesitamos una matriz:

NaN/Inf

en:

- y

- u

- v

- X

- G

- output inicializado/no inicializado

- theta

- tau

- tolerance fields.

Y combinaciones:

```
\*\*\`+Inf\`\*\*  
  
\*\*\`-Inf\`\*\*  
  
\*\*\`qNaN\`\*\*  
  
\*\*\`sNaN\`\*\*
```

cuando la plataforma lo permita.

# **ROUND 29 — EL RUST `panic = "unwind"` NO “GARANTIZA MEMORY SAFETY FFI”**

Esta afirmación del dossier es demasiado fuerte:

> **`panic = "unwind"`** guaranteeing deterministic memory safety across FFI boundaries.

No.

**`panic = "unwind"`** sólo determina el comportamiento de panics en determinadas condiciones.

Para una frontera FFI robusta:

Rust↔C

debe garantizarse que:

panic

no atraviese una frontera incompatible.

Además:

```
\*\*\`catch\\\_unwind\`\*\*
```

debe rodear correctamente el código que puede panickear.

Y deben considerarse:

- C++ exceptions

- foreign exceptions

- abort

- unwinding

- ownership

- destructor execution

- thread boundary.

La afirmación correcta sería mucho más precisa:

> “La frontera FFI captura explícitamente los panics de Rust antes de que crucen la ABI, bajo el ABI configurado.”

Pero eso requiere ver el código que el ZIP **no contiene**.

**Estado:** 🔴 **CLAIM DE SEGURIDAD EXCESIVO.**

# **ROUND 30 — EL DOSSIER SE AUTOCERTIFICA**

Hay un problema metodológico.

El mismo documento contiene:

```
\*\*\`26/26 PASS\`\*\*  
  
\*\*\`8/8 PASS\`\*\*  
  
\*\*\`100% certified\`\*\*
```

y luego el tribunal compuesto por modelos externos concluye:

> “certifies unanimously”.

Pero los supuestos jueces no constituyen una certificación independiente si:

- reciben el mismo dossier,

- reciben las mismas premisas,

- no ejecutan el binario,

- no inspeccionan el código real,

- no reproducen benchmarks.

Eso es **evidence of review**, no independent certification.

Para llamarlo auditoría externa real:

source→independent build→independent tests​

debe estar separado del equipo que produjo los resultados.

# **EL RESULTADO DEL PRIMER ROUND**

Después de atravesar el dossier completo, mi estado provisional queda así:

| Área | Estado |
| :-: | :-: |
| Rodrigues algebra básica | 🟢 razonable |
| Normalización esfera | 🟢 razonable |
| Rechazo NaN/Inf | 🟢 diseñado correctamente |
| Cayley algebra | 🟢/🟠 |
| PMTP idea triple-buffer | 🟢 prometedora |
| Lock-free formal proof | 🔴 no demostrado |
| IPC raw pointers | 🔴 problema crítico |
| ABI buffer bounds | 🔴 problema crítico |
| 64ϵ independiente de D | 🔴 no demostrado |
| D=107 | 🔴 no validado |
| Betti-1 vía DSU | 🔴 matemáticamente insuficiente |
| DPI claim | 🔴 incorrecto |
| O(1) tensor transfer | 🟠 necesita redefinición |
| IEEE certification | 🟠 sobreafirmada |
| OpenBLAS comparison | 🟠 incompleta |
| Silicon certification | 🔴 sobreafirmada |
| FFI safety | 🔴 no demostrada |
| 26/26 tests | 🟢 como regresión; insuficiente como certificación |
| External AI tribunal | 🟠 no independiente en sentido experimental |


# **LA CORRECCIÓN MÁS IMPORTANTE**

No recomiendo “parchear” todavía los tests.

Primero hay que cambiar el **contrato de verdad** del proyecto.

Actualmente el dossier intenta demostrar:

POLYDIM es matemaˊticamente correcto + lock-free + memory-safe + asymptotically stable​

con tests relativamente pequeños.

Eso es demasiado grande para la evidencia.

La arquitectura correcta de certificación debería tener **cuatro capas independientes**:

### **Capa A — matemática**

Demostrar:

RTR=IR(y)∈SD−1R(θ+ϕ)=R(θ)R(ϕ)

bajo las hipótesis correspondientes.

Para Cayley:

QTQ=I

y demostrar las propiedades de retraction que realmente se necesitan.

### **Capa B — numerical analysis**

Determinar:

E(D,ϵ,θ,K,κ)

en lugar de declarar arbitrariamente:

E≤64ϵ.

### **Capa C — concurrency**

Demostrar formalmente:

linearizabilitymemoryorderingABA resistancelock−freestarvation/fairness

y después someterlo a stress.

### **Capa D — silicon**

Medir:

latencybandwidthcache missescyclesenergyscaling(D,K,T)

en una matriz de hardware.

## **Y hay una prioridad que cambia respecto de una auditoría convencional**

**Yo no empezaría corrigiendo Rodrigues.**

La parte matemática básica de Rodrigues está razonablemente planteada.

El siguiente ataque debe ir directamente al **PMTP/FFI/ownership/concurrency**, porque ahí puede existir una vulnerabilidad capaz de invalidar toda la tesis de:

> “zero-copy + lock-free + memory-safe + inter-agent native communication”.

Y después hay que atacar el claim numérico:

64ϵ∀D≤107

con análisis de error adversarial.

Finalmente hay que reconstruir la parte topológica, porque el uso de DSU para β1​ es actualmente el agujero matemático más evidente del dossier.

**Conclusión de este round:** V762 **no está todavía en condiciones de ser llamado “100% Silicon Certified”** sobre la evidencia contenida en este ZIP. Eso no significa que POLYDIM esté roto; significa que el dossier está haciendo afirmaciones bastante más fuertes que las pruebas que presenta. Y varias de esas afirmaciones pueden corregirse sin destruir la arquitectura.

El siguiente ataque lógico es **PMTP completo: modelo de memoria → secuencias → ABA → ownership → mmap entre procesos → handles → acquire/commit/validate → prueba de lock-free → stress adversarial**. Ahí es donde buscaría el próximo bug de nivel industrial.

Sí. Y esta vez voy a ser todavía más estricto con la palabra **“alucinación”**.

He vuelto a abrir el ZIP y a leer el contenido que realmente existe. Hay una constatación importante que debo corregir de forma explícita respecto de la entrega anterior:

> El dossier **afirma** que **`02\\\_ALL\\\_SOURCE\\\_SCRIPTS\\\_MONOLITH.md`** contiene el código completo, pero el archivo sólo contiene el header público y referencias **`file:///E:/...`** hacia fuentes externas. Los cuerpos C++/Rust/Dart/Python/Triton no están dentro del ZIP.

Por eso, **no voy a inventar líneas de implementación**. Lo que sí podemos auditar con certeza es el contrato, las propiedades matemáticas, las afirmaciones y los benchmarks. Para concurrencia, distinguiré entre **brecha demostrada en el contrato** y **bug potencial que requiere el cuerpo del código**.

Además, contrasté las cuestiones de sincronización con documentación actual: Linux confirma que un futex en memoria compartida puede estar en direcciones virtuales distintas en distintos procesos y aun referir al mismo almacenamiento compartido; GCC distingue explícitamente operaciones atómicas realmente lock-free de aquellas que pueden acabar en llamadas de biblioteca; OpenMP define explícitamente acquire/release y el modelo de memoria.

Así que sí: **las críticas que marco como DEMOSTRADAS no son inventadas**.

Ahora voy a hacer lo que pediste: **dos vías en paralelo y después continuar profundizando**.

# **CICLO 3 — DOS VÍAS SOTA**

## **VÍA A — CIERRE FORMAL**

Primero convertimos PMTP en un protocolo que pueda ser demostrado.

## **VÍA B — CIERRE DE SILICIO**

Después construimos el código defensivo que materializa esas propiedades.

No voy a sustituir A por B.

Porque:

coˊdigo que pasa tests=protocolo formalmente correcto​

y:

protocolo formalmente correcto=implementacioˊn correcta​

Necesitamos ambos.

# **3A — PRIMER HALLAZGO: EL CONTRATO PMTP NO DEFINE LA UNIDAD DE PUBLICACIÓN**

El header dice:

```
\*\*\`int32\\\_t polydim\\\_pmtp\\\_begin\\\_write(\`\*\*  
  
\`    \*\*PMTP\\\_Control\\\* c,\`\*\*  
  
\`    \*\*uint64\\\_t\\\* slot\\\_out);\`\*\*  
  
  
\*\*\`int32\\\_t polydim\\\_pmtp\\\_commit\\\_write(\`\*\*  
  
\`    \*\*PMTP\\\_Control\\\* c,\`\*\*  
  
\`    \*\*uint64\\\_t slot);\`\*\*
```

Pero no existe en el contrato público ninguna función equivalente a:

```
\*\*\`write\\\_payload()\`\*\*  
  
\*\*\`publish\\\_descriptor()\`\*\*
```

Eso significa que el protocolo depende implícitamente de que el consumidor sepa:

> qué parte del slot es válida y cuándo exactamente está publicada.

Éste es un punto crítico.

# **3B — EL PROTOCOLO NECESITA UNA LINEARIZATION POINT**

Para una publicación correcta debe existir un instante lógico:

Lp​

tal que:

t\<Lp​⇒payload no estaˊ publicado

y:

t≥Lp​⇒payload completamente publicado.

El **`commit\\\_write()`** debería ser ese punto.

Conceptualmente:

```
\*\*\`WRITING\`\*\*  
  
\`   \*\*|\`\*\*  
  
\`   \*\*| payload fully initialized\`\*\*  
  
\`   \*\*|\`\*\*  
  
\`   \*\*v\`\*\*  
  
\*\*\`COMMIT\`\*\*  
  
\`   \*\*|\`\*\*  
  
\`   \*\*| release publication\`\*\*  
  
\`   \*\*v\`\*\*  
  
\*\*\`READY\`\*\*
```

El reader:

```
\*\*\`READY\`\*\*  
  
\`   \*\*|\`\*\*  
  
\`   \*\*| acquire\`\*\*  
  
\`   \*\*v\`\*\*  
  
\*\*\`READING\`\*\*
```

No puede existir:

```
\*\*\`READY\`\*\*
```

antes de que termine la escritura del payload.

# **3C — CÓDIGO SOTA MÍNIMO**

Esto es **código de referencia**, no afirmación de que sea el código actual de V762.

```
\*\*\`\\\#include \\\<atomic\\\>\`\*\*  
  
\*\*\`\\\#include \\\<cstdint\\\>\`\*\*  
  
  
\*\*\`enum class SlotState : uint32\\\_t \\\{\`\*\*  
  
\`    \*\*FREE    = 0,\`\*\*  
  
\`    \*\*WRITING = 1,\`\*\*  
  
\`    \*\*READY   = 2\`\*\*  
  
\*\*\`\\\};\`\*\*  
  
  
\*\*\`struct alignas(64) PMTP\\\_SlotControl \\\{\`\*\*  
  
\`    \*\*std::atomic\\\<uint64\\\_t\\\> sequence\\\{0\\\};\`\*\*  
  
\`    \*\*std::atomic\\\<uint32\\\_t\\\> state\\\{static\\\_cast\\\<uint32\\\_t\\\>(SlotState::FREE)\\\};\`\*\*  
  
  
\`    \*\*uint32\\\_t reserved = 0;\`\*\*  
  
  
\`    \*\*uint64\\\_t generation = 0;\`\*\*  
  
\`    \*\*uint64\\\_t payload\\\_offset = 0;\`\*\*  
  
\`    \*\*uint64\\\_t payload\\\_bytes = 0;\`\*\*  
  
\`    \*\*uint64\\\_t checksum = 0;\`\*\*  
  
\*\*\`\\\};\`\*\*
```

Pero inmediatamente aparece un problema:

```
\*\*\`uint64\\\_t generation;\`\*\*
```

no puede ser leído concurrentemente mientras otro proceso lo modifica sin una sincronización adecuada.

Por tanto el descriptor debe tener una propiedad clara:

mutable metadata is atomic or protected by publication protocol​

# **3D — PUBLICACIÓN CORRECTA**

Un patrón conceptual:

```
\*\*\`bool publish(PMTP\\\_SlotControl& s,\`\*\*  
  
\`             \*\*uint64\\\_t generation,\`\*\*  
  
\`             \*\*uint64\\\_t offset,\`\*\*  
  
\`             \*\*uint64\\\_t bytes)\`\*\*  
  
\*\*\`\\\{\`\*\*  
  
\`    \*\*s.state.store(\`\*\*  
  
\`        \*\*static\\\_cast\\\<uint32\\\_t\\\>(SlotState::WRITING),\`\*\*  
  
\`        \*\*std::memory\\\_order\\\_relaxed\`\*\*  
  
\`    \*\*);\`\*\*  
  
  
\`    \*\*// Payload is written here.\`\*\*  
  
\`    \*\*// No reader is allowed to consume it yet.\`\*\*  
  
  
\`    \*\*s.payload\\\_offset = offset;\`\*\*  
  
\`    \*\*s.payload\\\_bytes  = bytes;\`\*\*  
  
\`    \*\*s.generation    = generation;\`\*\*  
  
  
\`    \*\*/\\\*\`\*\*  
  
\`     \*\*\\\* CRITICAL LINE:\`\*\*  
  
\`     \*\*\\\*\`\*\*  
  
\`     \*\*\\\* Everything before this release becomes visible\`\*\*  
  
\`     \*\*\\\* before READY is observed by an acquire reader.\`\*\*  
  
\`     \*\*\\\*/\`\*\*  
  
\`    \*\*s.state.store(\`\*\*  
  
\`        \*\*static\\\_cast\\\<uint32\\\_t\\\>(SlotState::READY),\`\*\*  
  
\`        \*\*std::memory\\\_order\\\_release\`\*\*  
  
\`    \*\*);\`\*\*  
  
  
\`    \*\*return true;\`\*\*  
  
\*\*\`\\\}\`\*\*
```

Reader:

```
\*\*\`bool acquire(const PMTP\\\_SlotControl& s,\`\*\*  
  
\`             \*\*uint64\\\_t& generation,\`\*\*  
  
\`             \*\*uint64\\\_t& offset,\`\*\*  
  
\`             \*\*uint64\\\_t& bytes)\`\*\*  
  
\*\*\`\\\{\`\*\*  
  
\`    \*\*uint32\\\_t state =\`\*\*  
  
\`        \*\*s.state.load(std::memory\\\_order\\\_acquire);\`\*\*  
  
  
\`    \*\*if (state != static\\\_cast\\\<uint32\\\_t\\\>(SlotState::READY))\`\*\*  
  
\`        \*\*return false;\`\*\*  
  
  
\`    \*\*generation = s.generation;\`\*\*  
  
\`    \*\*offset     = s.payload\\\_offset;\`\*\*  
  
\`    \*\*bytes      = s.payload\\\_bytes;\`\*\*  
  
  
\`    \*\*return true;\`\*\*  
  
\*\*\`\\\}\`\*\*
```

**Pero cuidado:** esto todavía **NO resuelve reclamación**.

Y ésa es precisamente la siguiente mordida.

# **3E — BUG CONCEPTUAL: PUBLICACIÓN ≠ LIFETIME**

Imaginemos:

```
\*\*\`slot 0\`\*\*  
  
\*\*\`generation 100\`\*\*  
  
\*\*\`READY\`\*\*
```

Reader:

```
\*\*\`acquire generation=100\`\*\*
```

Writer:

```
\*\*\`slot 0 → WRITING\`\*\*
```

Reader todavía está procesando:

80MB

El writer reutiliza:

```
\*\*\`slot 0 → generation=101\`\*\*
```

El reader original sigue accediendo al mismo almacenamiento.

Entonces tenemos:

publication correctness​

pero no:

lifetime correctness​

Esto es **una brecha real de arquitectura**, no una afirmación de que V762 necesariamente tenga un UAF.

# **3F — SOLUCIÓN SOTA 1: HAZARD POINTERS**

Cada reader publica qué generación está utilizando:

```
\*\*\`struct ReaderHazard \\\{\`\*\*  
  
\`    \*\*std::atomic\\\<uint64\\\_t\\\> generation\\\{\`\*\*  
  
\`        \*\*UINT64\\\_MAX\`\*\*  
  
\`    \*\*\\\};\`\*\*  
  
\*\*\`\\\};\`\*\*
```

Reader:

```
\*\*\`uint64\\\_t g =\`\*\*  
  
\`    \*\*slot.generation;\`\*\*  
  
  
\*\*\`hazard.generation.store(\`\*\*  
  
\`    \*\*g,\`\*\*  
  
\`    \*\*std::memory\\\_order\\\_release\`\*\*  
  
\*\*\`);\`\*\*  
  
  
\*\*\`/\\\* Safe payload processing \\\*/\`\*\*  
  
\*\*\`process\\\_payload(slot);\`\*\*  
  
  
\*\*\`/\\\* Release ownership \\\*/\`\*\*  
  
\*\*\`hazard.generation.store(\`\*\*  
  
\`    \*\*UINT64\\\_MAX,\`\*\*  
  
\`    \*\*std::memory\\\_order\\\_release\`\*\*  
  
\*\*\`);\`\*\*
```

Writer no recicla:

```
\*\*\`bool can\\\_reclaim(\`\*\*  
  
\`    \*\*uint64\\\_t generation,\`\*\*  
  
\`    \*\*const ReaderHazard\\\* hazards,\`\*\*  
  
\`    \*\*size\\\_t reader\\\_count)\`\*\*  
  
\*\*\`\\\{\`\*\*  
  
\`    \*\*for (size\\\_t i = 0; i \\\< reader\\\_count; ++i) \\\{\`\*\*  
  
\`        \*\*uint64\\\_t active =\`\*\*  
  
\`            \*\*hazards\\\[i\\\].generation.load(\`\*\*  
  
\`                \*\*std::memory\\\_order\\\_acquire\`\*\*  
  
\`            \*\*);\`\*\*  
  
  
\`        \*\*if (active == generation)\`\*\*  
  
\`            \*\*return false;\`\*\*  
  
\`    \*\*\\\}\`\*\*  
  
  
\`    \*\*return true;\`\*\*  
  
\*\*\`\\\}\`\*\*
```

Esto cambia fundamentalmente la seguridad.

# **3G — SOLUCIÓN SOTA 2: EPOCH-BASED RECLAMATION**

Para POLYDIM, incluso me interesa más estudiar **epoch-based reclamation / RCU-like reclamation** porque tenemos un flujo de tensores potencialmente enorme.

Conceptualmente:

```
\*\*\`global\\\_epoch = 500\`\*\*  
  
  
\*\*\`Reader A:\`\*\*  
  
\`    \*\*active\\\_epoch = 500\`\*\*  
  
  
\*\*\`Reader B:\`\*\*  
  
\`    \*\*active\\\_epoch = 501\`\*\*  
  
  
\*\*\`Writer:\`\*\*  
  
\`    \*\*retires generation 499\`\*\*
```

Sólo cuando:

min(active\_epochs)\>499

se puede reciclar esa generación.

Entonces:

publish=retire=reclaim​

Tres estados distintos.

Ésta es una mejora SOTA mucho más importante que añadir simplemente otro buffer.

# **3H — EL TRIPLE BUFFER DE V762 NO ES AUTOMÁTICAMENTE INCORRECTO**

Esto es importante para no sobreatacar.

Triple buffering puede ser perfectamente válido si el protocolo tiene una garantía adicional:

un slot no se recicla mientras exista un reader que pueda acceder a eˊl​

Si esa propiedad está implementada mediante el mecanismo real de V762, entonces mi crítica anterior se convierte en:

> **“hay que demostrar esa propiedad”**

y no:

> “V762 tiene un UAF”.

Como el cuerpo no está en el ZIP, **no puedo afirmar el bug**.

Eso es precisamente distinguir red-team de alucinación.

# **3I — ABA: AHORA SÍ PODEMOS CONSTRUIR EL TEST CORRECTO**

Código de stress:

```
\*\*\`struct TestToken \\\{\`\*\*  
  
\`    \*\*uint64\\\_t generation;\`\*\*  
  
\`    \*\*uint64\\\_t sequence;\`\*\*  
  
\*\*\`\\\};\`\*\*  
  
  
\*\*\`static void force\\\_aba\\\_pattern()\`\*\*  
  
\*\*\`\\\{\`\*\*  
  
\`    \*\*TestToken reader\\\_token\\\{\\\};\`\*\*  
  
  
\`    \*\*// Reader observes A.\`\*\*  
  
\`    \*\*reader\\\_token.generation = 100;\`\*\*  
  
\`    \*\*reader\\\_token.sequence   = 1000;\`\*\*  
  
  
\`    \*\*// Writer recycles:\`\*\*  
  
\`    \*\*// A -\\\> B -\\\> A\`\*\*  
  
\`    \*\*const uint64\\\_t generation\\\_after\\\_wrap = 102;\`\*\*  
  
  
\`    \*\*// A correct protocol must NOT accept this\`\*\*  
  
\`    \*\*// as the original generation 100.\`\*\*  
  
\`    \*\*assert(\`\*\*  
  
\`        \*\*generation\\\_after\\\_wrap !=\`\*\*  
  
\`        \*\*reader\\\_token.generation\`\*\*  
  
\`    \*\*);\`\*\*  
  
\*\*\`\\\}\`\*\*
```

Eso es sólo el modelo mínimo.

El test real debe hacer:

```
\*\*\`A\`\*\*  
  
\*\*\`B\`\*\*  
  
\*\*\`A\`\*\*  
  
\*\*\`B\`\*\*  
  
\*\*\`A\`\*\*  
  
\*\*\`B\`\*\*  
  
\*\*\`...\`\*\*
```

millones de veces.

Y poner:

generation

dentro del payload mismo.

# **3J — TEST DE “STALE READ”**

Este test me parece obligatorio para V763:

```
\*\*\`struct PayloadMarker \\\{\`\*\*  
  
\`    \*\*uint64\\\_t generation;\`\*\*  
  
\`    \*\*uint64\\\_t sequence;\`\*\*  
  
\`    \*\*uint64\\\_t magic;\`\*\*  
  
\*\*\`\\\};\`\*\*  
  
  
\*\*\`static constexpr uint64\\\_t MAGIC =\`\*\*  
  
\`    \*\*0x504F4C5944494DULL; // "POLYDIM"\`\*\*
```

El writer:

```
\*\*\`PayloadMarker marker\\\{\`\*\*  
  
\`    \*\*generation,\`\*\*  
  
\`    \*\*sequence,\`\*\*  
  
\`    \*\*MAGIC\`\*\*  
  
\*\*\`\\\};\`\*\*
```

El reader verifica:

```
\*\*\`bool validate\\\_marker(\`\*\*  
  
\`    \*\*const PayloadMarker& p,\`\*\*  
  
\`    \*\*uint64\\\_t expected\\\_generation,\`\*\*  
  
\`    \*\*uint64\\\_t expected\\\_sequence)\`\*\*  
  
\*\*\`\\\{\`\*\*  
  
\`    \*\*return\`\*\*  
  
\`        \*\*p.magic == MAGIC &&\`\*\*  
  
\`        \*\*p.generation == expected\\\_generation &&\`\*\*  
  
\`        \*\*p.sequence == expected\\\_sequence;\`\*\*  
  
\*\*\`\\\}\`\*\*
```

Así podemos distinguir:

```
\*\*\`tear\`\*\*  
  
\*\*\`stale\`\*\*  
  
\*\*\`ABA\`\*\*  
  
\*\*\`corruption\`\*\*  
  
\*\*\`wrong slot\`\*\*  
  
\*\*\`wrong generation\`\*\*
```

en lugar de meter todo dentro de:

```
\*\*\`SEQLOCK\\\_RACE\`\*\*
```

# **3K — NUEVO PROBLEMA: EL ERROR `-6` ESTÁ DEMASIADO GENERALIZADO**

Actualmente:

```
\*\*\`POLYDIM\\\_ERR\\\_SEQLOCK\\\_RACE = -6\`\*\*
```

puede significar muchas cosas.

Necesitamos distinguir:

```
\*\*\`RETRY\`\*\*  
  
\*\*\`STALE\`\*\*  
  
\*\*\`ABA\`\*\*  
  
\*\*\`INVALID\\\_SLOT\`\*\*  
  
\*\*\`RECLAIMED\`\*\*  
  
\*\*\`CORRUPT\`\*\*  
  
\*\*\`WRITER\\\_BUSY\`\*\*
```

No necesariamente como 6 códigos públicos inmediatamente.

Pero internamente sí.

Por ejemplo:

```
\*\*\`enum class PMTPFailure \\\{\`\*\*  
  
\`    \*\*Retry,\`\*\*  
  
\`    \*\*StaleGeneration,\`\*\*  
  
\`    \*\*ABA,\`\*\*  
  
\`    \*\*InvalidSlot,\`\*\*  
  
\`    \*\*CorruptMetadata,\`\*\*  
  
\`    \*\*WriterBusy\`\*\*  
  
\*\*\`\\\};\`\*\*
```

Y al exterior:

```
\*\*\`POLYDIM\\\_ERR\\\_SEQLOCK\\\_RACE\`\*\*
```

si se quiere mantener ABI estable.

Esto mejora enormemente el diagnóstico.

# **3L — SEGUNDO ATAQUE: “LOCK-FREE” TIENE QUE SER MEDIDO A NIVEL HARDWARE**

GCC permite comprobar si una operación concreta es realmente lock-free con mecanismos como **`\\\_\\\_atomic\\\_always\\\_lock\\\_free`** / **`\\\_\\\_atomic\\\_is\\\_lock\\\_free`**; no basta asumirlo por el tipo **`uint64\\\_t`**.

Por ejemplo:

```
\*\*\`static\\\_assert(\`\*\*  
  
\`    \*\*std::atomic\\\<uint64\\\_t\\\>::is\\\_always\\\_lock\\\_free,\`\*\*  
  
\`    \*\*"PMTP requires lock-free uint64 atomics"\`\*\*  
  
\*\*\`);\`\*\*
```

y además runtime:

```
\*\*\`bool runtime\\\_lock\\\_free()\`\*\*  
  
\*\*\`\\\{\`\*\*  
  
\`    \*\*std::atomic\\\<uint64\\\_t\\\> x\\\{0\\\};\`\*\*  
  
\`    \*\*return x.is\\\_lock\\\_free();\`\*\*  
  
\*\*\`\\\}\`\*\*
```

Pero aquí aparece una cuestión muy importante:

thread−lock−free=process−sharedprotocolcorrectness​

Son propiedades diferentes.

# **3M — NUEVO TEST: LOCK-FREE NO DEBE SER UNA FRASE**

El self-test debe imprimir:

```
\*\*\`atomic\\\<uint32\\\_t\\\>: always\\\_lock\\\_free = 1\`\*\*  
  
\*\*\`atomic\\\<uint64\\\_t\\\>: always\\\_lock\\\_free = 1\`\*\*  
  
\*\*\`atomic\\\<uintptr\\\_t\\\>: always\\\_lock\\\_free = 1\`\*\*
```

y el CI debe **fallar** si la plataforma objetivo no cumple el requisito.

Código:

```
\*\*\`bool verify\\\_atomic\\\_contract()\`\*\*  
  
\*\*\`\\\{\`\*\*  
  
\`    \*\*if (!std::atomic\\\<uint64\\\_t\\\>::is\\\_always\\\_lock\\\_free)\`\*\*  
  
\`        \*\*return false;\`\*\*  
  
  
\`    \*\*std::atomic\\\<uint64\\\_t\\\> probe\\\{0\\\};\`\*\*  
  
  
\`    \*\*if (!probe.is\\\_lock\\\_free())\`\*\*  
  
\`        \*\*return false;\`\*\*  
  
  
\`    \*\*return true;\`\*\*  
  
\*\*\`\\\}\`\*\*
```

Esto sí convierte:

> “creemos que es lock-free”

en:

> “la plataforma declara esta operación lock-free”.

# **3N — PERO HAY UNA TRAMPA: LOCK-FREE ATOMIC ≠ LOCK-FREE ALGORITHM**

Aunque:

```
\*\*\`atomic\\\<uint64\\\_t\\\> = lock-free\`\*\*
```

sea verdadero, todavía podemos tener:

```
\*\*\`CAS loop\`\*\*  
  
\*\*\`CAS loop\`\*\*  
  
\*\*\`CAS loop\`\*\*  
  
\*\*\`CAS loop\`\*\*  
  
\*\*\`...\`\*\*
```

sin progreso individual.

La propiedad del algoritmo debe demostrar que:

∀infinite contention,

algún participante progresa.

Por eso quiero **dos certificados distintos**:

```
\*\*\`ATOMIC\\\_LOCK\\\_FREE\`\*\*  
  
\*\*\`ALGORITHM\\\_LOCK\\\_FREE\`\*\*
```

Nunca fusionarlos.

# **3O — TERCER ATAQUE: MULTI-PROCESO REAL**

El benchmark actual habla de:

> multi-threaded stress

Eso no demuestra:

process A↔process B.

Para PMTP real necesitamos:

```
\*\*\`process A\`\*\*  
  
\`    \*\*mmap(shared segment)\`\*\*  
  
\`       \*\*|\`\*\*  
  
\`       \*\*v\`\*\*  
  
\`    \*\*process B\`\*\*
```

y no sólo:

```
\*\*\`thread A\`\*\*  
  
\*\*\`thread B\`\*\*
```

Esto es especialmente importante porque Linux documenta explícitamente que un futex compartido entre procesos puede tener direcciones virtuales distintas en cada proceso.

# **3P — TEST QUE FALTA**

Proceso A:

```
\*\*\`int fd = shm\\\_open(\`\*\*  
  
\`    \*\*"/polydim\\\_test",\`\*\*  
  
\`    \*\*O\\\_CREAT | O\\\_RDWR,\`\*\*  
  
\`    \*\*0600\`\*\*  
  
\*\*\`);\`\*\*  
  
  
\*\*\`ftruncate(fd, shared\\\_size);\`\*\*  
  
  
\*\*\`void\\\* base = mmap(\`\*\*  
  
\`    \*\*nullptr,\`\*\*  
  
\`    \*\*shared\\\_size,\`\*\*  
  
\`    \*\*PROT\\\_READ | PROT\\\_WRITE,\`\*\*  
  
\`    \*\*MAP\\\_SHARED,\`\*\*  
  
\`    \*\*fd,\`\*\*  
  
\`    \*\*0\`\*\*  
  
\*\*\`);\`\*\*
```

Proceso B hace otro:

```
\*\*\`void\\\* base = mmap(\`\*\*  
  
\`    \*\*nullptr,\`\*\*  
  
\`    \*\*shared\\\_size,\`\*\*  
  
\`    \*\*PROT\\\_READ | PROT\\\_WRITE,\`\*\*  
  
\`    \*\*MAP\\\_SHARED,\`\*\*  
  
\`    \*\*fd,\`\*\*  
  
\`    \*\*0\`\*\*  
  
\*\*\`);\`\*\*
```

Y verificamos:

```
\*\*\`base\\\_A != base\\\_B\`\*\*
```

pero:

```
\*\*\`same shared offset\`\*\*
```

debe acceder al mismo objeto lógico.

Esto es precisamente donde el diseño:

```
\*\*\`pointer\`\*\*
```

se rompe.

Y:

```
\*\*\`offset + length + generation\`\*\*
```

sobrevive.

# **3Q — SOLUCIÓN CONCRETA: NO TRANSMITIR POINTERS**

La documentación de V762 dice:

> “Pointers are transferred via 64-bit packed atomic sequence tags”.

Ésta es una frase que **quiero corregir**, aunque el código real podría estar haciendo algo diferente.

Un sequence tag **no debe ser descrito como pointer**.

La API correcta conceptualmente es:

```
\*\*\`typedef struct \\\{\`\*\*  
  
\`    \*\*uint32\\\_t segment\\\_id;\`\*\*  
  
\`    \*\*uint32\\\_t generation\\\_hi;\`\*\*  
  
  
\`    \*\*uint64\\\_t generation\\\_lo;\`\*\*  
  
  
\`    \*\*uint64\\\_t offset\\\_bytes;\`\*\*  
  
\`    \*\*uint64\\\_t length\\\_bytes;\`\*\*  
  
  
\`    \*\*uint32\\\_t dtype;\`\*\*  
  
\`    \*\*uint32\\\_t rank;\`\*\*  
  
\*\*\`\\\} PMTP\\\_Handle;\`\*\*
```

El consumidor calcula:

```
\*\*\`void\\\* ptr =\`\*\*  
  
\`    \*\*(uint8\\\_t\\\*)local\\\_segment\\\_base +\`\*\*  
  
\`    \*\*handle.offset\\\_bytes;\`\*\*
```

No:

```
\*\*\`void\\\* ptr = handle.raw\\\_pointer;\`\*\*
```

# **3R — MEJOR TODAVÍA: CAPABILITY HANDLE**

Yo llevaría el diseño a:

```
\*\*\`typedef struct \\\{\`\*\*  
  
\`    \*\*uint32\\\_t segment\\\_id;\`\*\*  
  
\`    \*\*uint32\\\_t flags;\`\*\*  
  
  
\`    \*\*uint64\\\_t offset\\\_bytes;\`\*\*  
  
\`    \*\*uint64\\\_t length\\\_bytes;\`\*\*  
  
  
\`    \*\*uint64\\\_t generation;\`\*\*  
  
\`    \*\*uint64\\\_t sequence;\`\*\*  
  
  
\`    \*\*uint32\\\_t dtype;\`\*\*  
  
\`    \*\*uint32\\\_t rank;\`\*\*  
  
\*\*\`\\\} PMTP\\\_Handle;\`\*\*
```

y exigir:

```
\*\*\`segment\\\_id válido\`\*\*  
  
\*\*\`offset alineado\`\*\*  
  
\*\*\`length dentro del segmento\`\*\*  
  
\*\*\`generation vigente\`\*\*  
  
\*\*\`sequence vigente\`\*\*  
  
\*\*\`dtype permitido\`\*\*  
  
\*\*\`rank válido\`\*\*
```

antes de devolver un puntero local.

# **3S — BOUNDS CHECK REAL**

El API actual:

```
\*\*\`const double\\\* y,\`\*\*  
  
\*\*\`...\`\*\*  
  
\*\*\`uint64\\\_t D\`\*\*
```

no contiene:

```
\*\*\`y\\\_capacity\`\*\*
```

Esto sigue siendo una brecha real del contrato.

Código defensivo:

```
\*\*\`typedef struct \\\{\`\*\*  
  
\`    \*\*const void\\\* data;\`\*\*  
  
\`    \*\*uint64\\\_t bytes;\`\*\*  
  
\*\*\`\\\} PolydimConstBuffer;\`\*\*  
  
  
\*\*\`typedef struct \\\{\`\*\*  
  
\`    \*\*void\\\* data;\`\*\*  
  
\`    \*\*uint64\\\_t bytes;\`\*\*  
  
\*\*\`\\\} PolydimBuffer;\`\*\*
```

Entonces:

```
\*\*\`static int check\\\_vector(\`\*\*  
  
\`    \*\*const PolydimConstBuffer\\\* b,\`\*\*  
  
\`    \*\*uint64\\\_t D,\`\*\*  
  
\`    \*\*uint64\\\_t elem\\\_size)\`\*\*  
  
\*\*\`\\\{\`\*\*  
  
\`    \*\*if (!b || !b-\\\>data)\`\*\*  
  
\`        \*\*return POLYDIM\\\_ERR\\\_NULL\\\_POINTER;\`\*\*  
  
  
\`    \*\*if (D \\\> UINT64\\\_MAX / elem\\\_size)\`\*\*  
  
\`        \*\*return POLYDIM\\\_ERR\\\_BUFFER\\\_OVERFLOW;\`\*\*  
  
  
\`    \*\*uint64\\\_t required =\`\*\*  
  
\`        \*\*D \\\* elem\\\_size;\`\*\*  
  
  
\`    \*\*if (b-\\\>bytes \\\< required)\`\*\*  
  
\`        \*\*return POLYDIM\\\_ERR\\\_BUFFER\\\_OVERFLOW;\`\*\*  
  
  
\`    \*\*return POLYDIM\\\_SUCCESS;\`\*\*  
  
\*\*\`\\\}\`\*\*
```

Esto cierra una clase completa de errores:

D→bytes→overflow→OOB.

# **3T — ALIASING TAMBIÉN DEBE COMPROBARSE ARITMÉTICAMENTE**

No:

```
\*\*\`if (y == y\\\_out)\`\*\*
```

solamente.

Porque:

```
\*\*\`y       = \\\[1000,2000)\`\*\*  
  
\*\*\`y\\\_out   = \\\[1500,2500)\`\*\*
```

tiene:

y=yout​

pero se solapan.

La comprobación correcta requiere intervalos:

```
\*\*\`struct ByteRange \\\{\`\*\*  
  
\`    \*\*uintptr\\\_t begin;\`\*\*  
  
\`    \*\*uintptr\\\_t end;\`\*\*  
  
\*\*\`\\\};\`\*\*  
  
  
\*\*\`static bool overlaps(\`\*\*  
  
\`    \*\*ByteRange a,\`\*\*  
  
\`    \*\*ByteRange b)\`\*\*  
  
\*\*\`\\\{\`\*\*  
  
\`    \*\*return a.begin \\\< b.end &&\`\*\*  
  
\`           \*\*b.begin \\\< a.end;\`\*\*  
  
\*\*\`\\\}\`\*\*
```

y antes:

```
\*\*\`uintptr\\\_t y\\\_end =\`\*\*  
  
\`    \*\*y\\\_begin + bytes;\`\*\*
```

con overflow checking.

# **3U — AHORA VIENE UNA BRECHA TODAVÍA MÁS SUTIL: INTEGER OVERFLOW EN RANGOS**

Esto:

```
\*\*\`uintptr\\\_t end = begin + bytes;\`\*\*
```

puede desbordar.

Correcto:

```
\*\*\`static bool checked\\\_add(\`\*\*  
  
\`    \*\*uintptr\\\_t a,\`\*\*  
  
\`    \*\*uintptr\\\_t b,\`\*\*  
  
\`    \*\*uintptr\\\_t\\\* out)\`\*\*  
  
\*\*\`\\\{\`\*\*  
  
\`    \*\*if (b \\\> UINTPTR\\\_MAX - a)\`\*\*  
  
\`        \*\*return false;\`\*\*  
  
  
\`    \*\*\\\*out = a + b;\`\*\*  
  
\`    \*\*return true;\`\*\*  
  
\*\*\`\\\}\`\*\*
```

Parece microdetalle.

No lo es.

Una API HPC de memoria segura debe asumir:

input adversarial.

# **3V — TEST ADVERSARIAL QUE DEBE ENTRAR EN LOS 26**

```
\*\*\`TEST(buffer\\\_overflow)\`\*\*  
  
\*\*\`\\\{\`\*\*  
  
\`    \*\*double x\\\[8\\\]\\\{\\\};\`\*\*  
  
\`    \*\*double y\\\[8\\\]\\\{\\\};\`\*\*  
  
  
\`    \*\*PolydimBuffer in\\\{\`\*\*  
  
\`        \*\*x,\`\*\*  
  
\`        \*\*sizeof(x)\`\*\*  
  
\`    \*\*\\\};\`\*\*  
  
  
\`    \*\*int rc = check\\\_vector(\`\*\*  
  
\`        \*\*reinterpret\\\_cast\\\<\`\*\*  
  
\`            \*\*const PolydimConstBuffer\\\*\`\*\*  
  
\`        \*\*\\\>(&in),\`\*\*  
  
\`        \*\*UINT64\\\_C(1000000000000000000),\`\*\*  
  
\`        \*\*sizeof(double)\`\*\*  
  
\`    \*\*);\`\*\*  
  
  
\`    \*\*ASSERT\\\_EQ(\`\*\*  
  
\`        \*\*rc,\`\*\*  
  
\`        \*\*POLYDIM\\\_ERR\\\_BUFFER\\\_OVERFLOW\`\*\*  
  
\`    \*\*);\`\*\*  
  
\*\*\`\\\}\`\*\*
```

Y también:

```
\*\*\`D = UINT64\\\_MAX\`\*\*

\*\*\`D = SIZE\\\_MAX / 8 + 1\`\*\*
```

No necesitamos ejecutar la operación; necesitamos demostrar que **rechaza antes de tocar memoria**.

# **3W — CUARTO ATAQUE: CRASH CONSISTENCY**

Este problema no estaba suficientemente tratado en V762.

Supongamos:

```
\*\*\`writer\`\*\*  
  
\`  \*\*begin\\\_write(slot=1)\`\*\*  
  
\`  \*\*write 30 MB\`\*\*  
  
\`  \*\*PROCESS CRASH\`\*\*
```

El sistema se reinicia.

¿Qué estado tiene slot 1?

Debe ser imposible interpretar:

```
\*\*\`WRITING\`\*\*
```

como:

```
\*\*\`READY\`\*\*
```

### **Header mínimo:**

```
\*\*\`enum PMTP\\\_State \\\{\`\*\*  
  
\`    \*\*PMTP\\\_FREE    = 0,\`\*\*  
  
\`    \*\*PMTP\\\_WRITING = 1,\`\*\*  
  
\`    \*\*PMTP\\\_READY   = 2,\`\*\*  
  
\`    \*\*PMTP\\\_RETIRED = 3\`\*\*  
  
\*\*\`\\\};\`\*\*
```

Y la única transición válida:

```
\*\*\`FREE\`\*\*  
  
\`  ↓\`  
  
\*\*\`WRITING\`\*\*  
  
\`  ↓\`  
  
\*\*\`READY\`\*\*  
  
\`  ↓\`  
  
\*\*\`RETIRED\`\*\*  
  
\`  ↓\`  
  
\*\*\`FREE\`\*\*
```

No:

```
\*\*\`FREE → READY\`\*\*
```

ni:

```
\*\*\`WRITING → FREE\`\*\*
```

sin protocolo explícito.

# **3X — MODELO FORMAL DE TRANSICIONES**

Ésta es la primera de las **dos opciones que me pediste**.

El modelo que propondría para TLA+/equivalente:

```
\*\*\`VARIABLES\`\*\*  
  
\`    \*\*state,\`\*\*  
  
\`    \*\*sequence,\`\*\*  
  
\`    \*\*generation,\`\*\*  
  
\`    \*\*readers,\`\*\*  
  
\`    \*\*payload\\\_generation\`\*\*
```

Invariantes:

I1​:state=READY⇒payload\_generation=generationI2​:state=WRITING⇒¬ReaderMayConsumeI3​:ReaderOwns(s,g)⇒slot.generation=gI4​:Reclaim(s,g)⇒∀r:r.active\_generation=gI5​:sequencenew​=sequenceold​

dentro de la ventana anti-ABA.

Liveness:

WriterEnabled⇒◊Published

y para readers:

ReaderEnabled⇒◊Acquired

bajo las hipótesis de scheduling declaradas.

# **3Y — SEGUNDA OPCIÓN: IMPLEMENTACIÓN CONCRETA**

Si queremos mantener la arquitectura de triple buffer, mi versión endurecida empezaría así:

```
\*\*\`struct alignas(64) PMTP\\\_Slot \\\{\`\*\*  
  
\`    \*\*std::atomic\\\<uint64\\\_t\\\> sequence\\\{0\\\};\`\*\*  
  
\`    \*\*std::atomic\\\<uint64\\\_t\\\> generation\\\{0\\\};\`\*\*  
  
\`    \*\*std::atomic\\\<uint32\\\_t\\\> state\\\{\`\*\*  
  
\`        \*\*PMTP\\\_FREE\`\*\*  
  
\`    \*\*\\\};\`\*\*  
  
  
\`    \*\*uint32\\\_t reserved0\\\{0\\\};\`\*\*  
  
  
\`    \*\*uint64\\\_t payload\\\_offset\\\{0\\\};\`\*\*  
  
\`    \*\*uint64\\\_t payload\\\_bytes\\\{0\\\};\`\*\*  
  
  
\`    \*\*uint64\\\_t checksum\\\{0\\\};\`\*\*  
  
\*\*\`\\\};\`\*\*
```

Y un descriptor global:

```
\*\*\`struct alignas(64) PMTP\\\_Control \\\{\`\*\*  
  
\`    \*\*uint64\\\_t magic;\`\*\*  
  
\`    \*\*uint32\\\_t abi\\\_major;\`\*\*  
  
\`    \*\*uint32\\\_t abi\\\_minor;\`\*\*  
  
  
\`    \*\*uint64\\\_t segment\\\_bytes;\`\*\*  
  
\`    \*\*uint64\\\_t slot\\\_count;\`\*\*  
  
  
\`    \*\*PMTP\\\_Slot slots\\\[3\\\];\`\*\*  
  
\*\*\`\\\};\`\*\*
```

Pero:

> **No recomiendo adoptar esto literalmente todavía.**

Primero hay que adaptar el modelo al verdadero algoritmo de V762 cuando tengamos el **`.cpp`**.

# **3Z — NUEVA BRECHA: ABI VERSIONING**

Esto sí lo puedo declarar **demostrado como ausencia documental**, porque el header visible no expone:

```
\*\*\`magic\`\*\*  
  
\*\*\`abi\\\_major\`\*\*  
  
\*\*\`abi\\\_minor\`\*\*  
  
\*\*\`struct\\\_size\`\*\*
```

Necesitamos:

```
\*\*\`\\\#define POLYDIM\\\_PMTP\\\_ABI\\\_MAJOR 1\`\*\*  
  
\*\*\`\\\#define POLYDIM\\\_PMTP\\\_ABI\\\_MINOR 0\`\*\*  
  
  
\*\*\`typedef struct \\\{\`\*\*  
  
\`    \*\*uint64\\\_t magic;\`\*\*  
  
  
\`    \*\*uint32\\\_t abi\\\_major;\`\*\*  
  
\`    \*\*uint32\\\_t abi\\\_minor;\`\*\*  
  
  
\`    \*\*uint64\\\_t struct\\\_size;\`\*\*  
  
\`    \*\*uint64\\\_t segment\\\_size;\`\*\*  
  
  
\`    \*\*uint64\\\_t features;\`\*\*  
  
\*\*\`\\\} PMTP\\\_ABI\\\_Header;\`\*\*
```

Y:

```
\*\*\`bool validate\\\_header(\`\*\*  
  
\`    \*\*const PMTP\\\_ABI\\\_Header& h,\`\*\*  
  
\`    \*\*uint64\\\_t mapped\\\_size)\`\*\*  
  
\*\*\`\\\{\`\*\*  
  
\`    \*\*if (h.magic != PMTP\\\_MAGIC)\`\*\*  
  
\`        \*\*return false;\`\*\*  
  
  
\`    \*\*if (h.abi\\\_major !=\`\*\*  
  
\`        \*\*POLYDIM\\\_PMTP\\\_ABI\\\_MAJOR)\`\*\*  
  
\`        \*\*return false;\`\*\*  
  
  
\`    \*\*if (h.struct\\\_size \\\> mapped\\\_size)\`\*\*  
  
\`        \*\*return false;\`\*\*  
  
  
\`    \*\*if (h.segment\\\_size \\\> mapped\\\_size)\`\*\*  
  
\`        \*\*return false;\`\*\*  
  
  
\`    \*\*return true;\`\*\*  
  
\*\*\`\\\}\`\*\*
```

Esto es obligatorio si el shared memory puede sobrevivir al proceso que lo creó.

# **4A — VAMOS AHORA A NUMÉRICA: HAY UNA AUTOCERTIFICACIÓN CIRCULAR**

El dossier dice:

```
\*\*\`\\\[cota certificada\\\]\`\*\*
```

y Rust:

```
\*\*\`cota\\\_no\\\_escala\\\_con\\\_d ... ok\`\*\*
```

Pero si el test está construido para verificar:

```
\*\*\`error \\\<= 64 \\\* EPSILON\`\*\*
```

no demuestra que:

64ϵ

sea una cota matemática.

Demuestra:

implementation passes chosen test cases.

Esto es una distinción fundamental.

# **4B — EL TEST CORRECTO NO DEBE CONOCER EL BOUND**

El test debería obtener una referencia independiente:

yref​

con:

MPFR

o una precisión suficientemente mayor.

Entonces:

```
\*\*\`long double / MPFR reference\`\*\*
```

y:

```
\*\*\`double polydim\`\*\*
```

comparados.

El test **no debe contener**:

```
\*\*\`expected\\\_bound = 64 \\\* epsilon;\`\*\*
```

como única autoridad.

Debe calcular:

```
\*\*\`observed\\\_error\`\*\*
```

y después un auditor externo decide:

max(error)/ϵ.

# **4C — TEST ADVERSARIAL DE θ**

Código:

```
\*\*\`const double thetas\\\[\\\] = \\\{\`\*\*  
  
\`    \*\*1e-1,\`\*\*  
  
\`    \*\*1e-4,\`\*\*  
  
\`    \*\*1e-8,\`\*\*  
  
\`    \*\*1e-12,\`\*\*  
  
\`    \*\*1e-16,\`\*\*  
  
\`    \*\*1e-20,\`\*\*  
  
\`    \*\*1e-100,\`\*\*  
  
\`    \*\*3.14159265358979323846,\`\*\*  
  
\`    \*\*3.14159265358979323846 - 1e-12,\`\*\*  
  
\`    \*\*3.14159265358979323846 + 1e-12,\`\*\*  
  
\`    \*\*2.0 \\\* 3.14159265358979323846\`\*\*  
  
\*\*\`\\\};\`\*\*
```

Y para cada:

```
\*\*\`POLYDIM\`\*\*  
  
\*\*\`vs\`\*\*  
  
\*\*\`high precision reference\`\*\*
```

No sólo:

```
\*\*\`norm(output)\`\*\*
```

sino:

```
\*\*\`vector\\\_error\`\*\*  
  
\*\*\`angle\\\_error\`\*\*  
  
\*\*\`inner\\\_product\\\_error\`\*\*  
  
\*\*\`norm\\\_error\`\*\*
```

# **4D — TEST DE ISOMETRÍA**

Código:

```
\*\*\`double d0 =\`\*\*  
  
\`    \*\*norm\\\_difference(y1, y2);\`\*\*  
  
  
\*\*\`rodrigues(y1, ..., r1);\`\*\*  
  
\*\*\`rodrigues(y2, ..., r2);\`\*\*  
  
  
\*\*\`double d1 =\`\*\*  
  
\`    \*\*norm\\\_difference(r1, r2);\`\*\*  
  
  
\*\*\`double err =\`\*\*  
  
\`    \*\*std::abs(d1 - d0);\`\*\*
```

Propiedad:

∥R(y1​)−R(y2​)∥=∥y1​−y2​∥​

Esto es mucho más fuerte que:

∣∥Ry∥−1∣.

# **4E — TEST DE EQUIVARIANZA**

Para Q∈O(D):

R(Qy,Qu,Qv,θ)≈QR(y,u,v,θ).

Esto es una prueba geométrica de alto nivel.

Código conceptual:

```
\*\*\`rodrigues(\`\*\*  
  
\`    \*\*Qy, Qu, Qv,\`\*\*  
  
\`    \*\*lhs,\`\*\*  
  
\`    \*\*theta\`\*\*  
  
\*\*\`);\`\*\*  
  
  
\*\*\`rodrigues(\`\*\*  
  
\`    \*\*y, u, v,\`\*\*  
  
\`    \*\*tmp,\`\*\*  
  
\`    \*\*theta\`\*\*  
  
\*\*\`);\`\*\*  
  
  
\*\*\`apply\\\_Q(tmp, rhs);\`\*\*  
  
  
\*\*\`error = max\\\_abs\\\_diff(lhs, rhs);\`\*\*
```

Si falla, puedes tener:

- signo incorrecto,

- índices incorrectos,

- reducción incorrecta,

- componente paralela mal tratada.

# **4F — TEST DE INVERSA**

R−θ​Rθ​=I.

Código:

```
\*\*\`rodrigues(\`\*\*  
  
\`    \*\*y,\`\*\*  
  
\`    \*\*u,\`\*\*  
  
\`    \*\*v,\`\*\*  
  
\`    \*\*y1,\`\*\*  
  
\`    \*\*theta\`\*\*  
  
\*\*\`);\`\*\*  
  
  
\*\*\`rodrigues(\`\*\*  
  
\`    \*\*y1,\`\*\*  
  
\`    \*\*u,\`\*\*  
  
\`    \*\*v,\`\*\*  
  
\`    \*\*y2,\`\*\*  
  
\`    \*\*-theta\`\*\*  
  
\*\*\`);\`\*\*  
  
  
\*\*\`double err =\`\*\*  
  
\`    \*\*max\\\_abs\\\_diff(y, y2);\`\*\*
```

Esto debe entrar en la suite.

# **4G — STIEFEL: OTRO ERROR DE VALIDACIÓN**

El benchmark actual comprueba:

```
\*\*\`max|YtY-I|\`\*\*
```

Eso es necesario.

No suficiente.

Necesitamos además:

retraction property​

y:

backward error​

# **4H — TEST DE RETRACTION**

Para:

RX​(τG)

debe verificarse:

RX​(0)=X.

Código:

```
\*\*\`stiefel\\\_cayley(\`\*\*  
  
\`    \*\*X,\`\*\*  
  
\`    \*\*G,\`\*\*  
  
\`    \*\*Y,\`\*\*  
  
\`    \*\*D,\`\*\*  
  
\`    \*\*K,\`\*\*  
  
\`    \*\*0.0,\`\*\*  
  
\`    \*\*...\`\*\*  
  
\*\*\`);\`\*\*  
  
  
\*\*\`assert(\`\*\*  
  
\`    \*\*max\\\_abs\\\_diff(X, Y)\`\*\*  
  
\`    \*\*\\\<= tol\`\*\*  
  
\*\*\`);\`\*\*
```

Después:

hRX​(hG)−X​

debe aproximarse al vector tangente correspondiente.

# **4I — TEST DE RESIDUAL SMW**

Si:

MZ=B

entonces:

```
\*\*\`residual =\`\*\*  
  
\`    \*\*norm(M \\\* Z - B) /\`\*\*  
  
\`    \*\*(norm(M) \\\* norm(Z) + norm(B));\`\*\*
```

El benchmark actual muestra:

```
\*\*\`pivot = 1.000e+00\`\*\*
```

pero eso no demuestra:

∥MZ−B∥

pequeño.

Este test debe añadirse.

# **4J — PUNTO MUY IMPORTANTE SOBRE LA FÓRMULA DE FLOPS**

La afirmación:

3K2D→2K2D

puede ser razonable como conteo simplificado si se explota estructura/simetría, pero **no debe presentarse como coste total del kernel**.

Hay que descomponer:

T=TGram​+Tfactor​+TSMW​+Treconstruct​+Tvalidation​.

Y medir cada uno.

Entonces sí sabremos dónde está realmente el speedup.

# **4K — PERFORMANCE SOTA: ROOFTOP MODEL**

Para cada kernel quiero:

AI=BytesFLOPs​.

Luego:

Pachievable​≤min(Pcompute​,BWmemory​×AI).

Esto nos permite saber si estamos:

```
\*\*\`memory bound\`\*\*
```

o:

```
\*\*\`compute bound.\`\*\*
```

Entonces optimizamos donde realmente importa.

No a ciegas.

# **4L — BENCHMARK QUE FALTA: THREAD SCALING**

La tabla actual tiene:

```
\*\*\`hilos=2\`\*\*
```

Esto es insuficiente para una reivindicación industrial HPC.

Necesitamos:

```
\*\*\`threads = 1\`\*\*  
  
\*\*\`2\`\*\*  
  
\*\*\`4\`\*\*  
  
\*\*\`8\`\*\*  
  
\*\*\`16\`\*\*  
  
\*\*\`32\`\*\*  
  
\*\*\`...\`\*\*
```

hasta los cores físicos.

Y:

S(N)=T1​/TN​E(N)=S(N)/N.

Esto también descubrirá:

- false sharing,

- NUMA,

- OpenMP overhead,

- saturation,

- memory bandwidth ceiling.

# **4M — BENCHMARK QUE FALTA: NUMA**

Necesitamos:

```
\*\*\`local → local\`\*\*  
  
\*\*\`local → remote\`\*\*  
  
\*\*\`remote → local\`\*\*  
  
\*\*\`remote → remote\`\*\*
```

con:

```
\*\*\`numactl\`\*\*
```

y hardware counters.

Porque para:

80MB

por vector, NUMA puede dominar.

# **4N — BENCHMARK QUE FALTA: PAGE SIZE**

Comparar:

```
\*\*\`4 KiB\`\*\*  
  
\*\*\`2 MiB huge pages\`\*\*
```

cuando la plataforma lo permita.

Medir:

DTLB missespage walksGB/s.

No asumir que huge pages siempre ganan.

**Medir.**

# **4O — BENCHMARK QUE FALTA: ISA DISPATCH**

Compilar:

```
\*\*\`generic\`\*\*  
  
\*\*\`AVX2\`\*\*  
  
\*\*\`AVX-512\`\*\*
```

y, si procede:

```
\*\*\`SVE/SVE2\`\*\*
```

en hardware ARM.

No quiero que el documento diga:

> “full SIMD auto-vectorization”

sin mostrar el assembly.

Necesitamos:

```
\*\*\`objdump -d libpolydim.so\`\*\*
```

y/o:

```
\*\*\`gcc -fopt-info-vec-optimized\`\*\*
```

y correlacionarlo con:

FLOP/s

y:

GB/s.

# **4P — Y AQUÍ ENCUENTRO OTRA COSA QUE NO QUIERO DEJAR PASAR**

El dossier declara:

```
\*\*\`D \\\>= 10^6\`\*\*
```

como parte de la pregunta central.

Pero el benchmark Rodrigues visible sólo llega a:

D=106.

No:

D=107.

Por tanto:

objetivo declarado=dominio validado​

Esto no es una opinión.

Es directamente observable en el benchmark suministrado.

Para cerrar el claim hay que ejecutar:

D=107

y medir memoria real.

# **4Q — Y HAY UNA SEGUNDA INCONSISTENCIA DOCUMENTAL CONFIRMADA**

El README dice:

> “The 5 inner products”

pero enumera:

⟨y,y⟩⟨y,u⟩⟨y,v⟩⟨u,u⟩⟨v,v⟩⟨u,v⟩.

Eso son:

6​

No 5.

No afecta al algoritmo.

Pero en un documento de certificación matemática debe corregirse.

# **4R — OTRA AFIRMACIÓN QUE DEBEMOS CAMBIAR**

Actualmente:

> “guaranteeing deterministic memory safety across FFI boundaries.”

No está justificado sólo por:

```
\*\*\`Rust 2024\`\*\*  
  
\*\*\`panic = unwind\`\*\*  
  
\*\*\`\\\#\\\[unsafe(no\\\_mangle)\\\]\`\*\*
```

La frontera FFI requiere demostrar:

```
\*\*\`ownership\`\*\*  
  
\*\*\`lifetime\`\*\*  
  
\*\*\`nullability\`\*\*  
  
\*\*\`alignment\`\*\*  
  
\*\*\`size\`\*\*  
  
\*\*\`ABI\`\*\*  
  
\*\*\`panic behavior\`\*\*  
  
\*\*\`threading\`\*\*  
  
\*\*\`allocator compatibility\`\*\*
```

Por tanto la frase debería convertirse en:

> “The Rust layer provides an FFI safety boundary subject to the documented ownership, ABI, panic-containment and buffer-validity contracts.”

Hasta inspeccionar **`lib.rs`**, **no debemos afirmar más**.

# **4S — EL SIGUIENTE SALTO: SANITIZERS**

Quiero añadir cuatro builds:

```
\*\*\`ASan\`\*\*  
  
\*\*\`UBSan\`\*\*  
  
\*\*\`TSan\`\*\*  
  
\*\*\`Debug\`\*\*
```

Concretamente:

```
\*\*\`-fsanitize=address,undefined\`\*\*
```

y, en una build separada:

```
\*\*\`-fsanitize=thread\`\*\*
```

No mezclar necesariamente todos los sanitizers.

### **ASan**

Detecta:

```
\*\*\`OOB\`\*\*  
  
\*\*\`use-after-free\`\*\*  
  
\*\*\`double-free\`\*\*
```

### **UBSan**

Detecta varias clases de:

```
\*\*\`undefined behavior\`\*\*
```

### **TSan**

Busca:

```
\*\*\`data races\`\*\*
```

Pero:

> TSan no sustituye la prueba formal del algoritmo.

Es otro detector.

# **4T — TSan + SHARED MEMORY MULTI-PROCESS TIENE UNA LIMITACIÓN**

Esto es importante para no vender humo.

TSan es extremadamente útil para concurrencia dentro del proceso.

Pero no lo debemos presentar como:

certificador universal de IPC

entre procesos.

Para IPC real necesitamos además:

```
\*\*\`fork/exec\`\*\*  
  
\*\*\`mmap\`\*\*  
  
\*\*\`shared segment\`\*\*  
  
\*\*\`process kill\`\*\*  
  
\*\*\`restart\`\*\*
```

y tests de protocolo.

# **4U — NUEVO OBJETIVO: FAULT INJECTION**

Esto es verdaderamente industrial.

Durante:

```
\*\*\`WRITING\`\*\*
```

forzar:

```
\*\*\`SIGKILL\`\*\*
```

del writer.

Durante:

```
\*\*\`READING\`\*\*
```

forzar:

```
\*\*\`SIGSTOP\`\*\*
```

del reader.

Durante:

```
\*\*\`COMMIT\`\*\*
```

matar proceso.

Luego comprobar:

last valid generation survives.

Esto es mucho más poderoso que 8 millones de iteraciones limpias.

# **4V — MATRIZ DE FAULT INJECTION**

Quiero:

| Evento | Reader | Writer | Resultado esperado |
| :-: | :-: | :-: | :-: |
| crash antes write | alive | dead | último READY |
| crash durante write | alive | dead | WRITING descartado |
| crash antes commit | alive | dead | no publicación |
| crash después commit | alive | dead | publicación válida |
| reader stop | stopped | alive | writer no corrompe |
| reader crash | dead | alive | slot eventualmente reciclable |


Esto sí acerca POLYDIM a:

industrial​

# **4W — CIERRE DE ESTE CICLO: QUÉ ES HECHO, QUÉ ES HIPÓTESIS**

## 🔴 **DEMOSTRADO**

1. El ZIP no contiene los cuerpos de implementación.

2. El benchmark Rodrigues llega a 106, no 107.

3. El contrato público no expone buffer lengths.

4. El contrato público no expone versionado PMTP.

5. El documento llama “5” a seis productos internos.

6. **`lock-free`** no queda demostrado por los números de stress publicados.

7. **`64ε`** no queda demostrado como teorema por los tests publicados.

8. **`zero-copy`** no queda demostrado mediante una medición de bytes/copias.

9. **`Silicon Certified`** es una conclusión más fuerte que la evidencia presentada.

10. La afirmación de seguridad FFI es más fuerte que lo que el material visible permite demostrar.

## 🟠 **HIPÓTESIS QUE NECESITAN EL CÓDIGO REAL**

1. ABA real.

2. use-after-reuse real.

3. incorrect memory\_order.

4. false sharing real.

5. raw pointers reales dentro de PMTP.

6. crash inconsistency real.

7. integer overflow real en implementación.

8. data race real.

9. allocator mismatch real.

10. panic crossing FFI real.

No voy a convertir esos 10 puntos en “bugs encontrados” hasta tener el código.

# **Y ÉSTE ES EL CAMINO QUE PROPONGO PARA LOS SIGUIENTES CICLOS**

Vamos a mantener el bucle que pediste:

AUDIT→COUNTEREXAMPLE→SOLUTION→TEST→FORMAL PROOF→SILICON TEST→NEXT BUG​

en lugar de:

AUDIT→lista de problemas→fin.

### **Próximo anillo, en este orden:**

**Ciclo 4 — PMTP real**

- **`memory\\\_order`**

- CAS loops

- sequence protocol

- ABA

- lifetime

- process-shared mmap

- crash recovery

- cache lines

- NUMA

- TLB

- multi-process stress.

**Ciclo 5 — ABI/FFI**

- C ↔ C++

- C ↔ Rust

- Dart FFI

- ownership

- allocator

- alignment

- ABI versioning

- panic/unwind

- malformed handles

- fuzzing.

**Ciclo 6 — Numerical Red Team**

- MPFR reference

- 10−100≤θ≤π+ϵ

- adversarial cancellation

- D=107

- reproducibility

- backward error

- condition numbers.

**Ciclo 7 — Stiefel**

- retraction axioms

- tangent projection

- Cayley algebra

- SMW residual

- singular/near-singular cases

- K→512

- D×K scaling.

**Ciclo 8 — Performance/Silicon**

- roofline

- cache

- SIMD

- AVX2/AVX-512/SVE

- OpenMP scaling

- NUMA

- huge pages

- memory bandwidth

- energy.

**Ciclo 9 — GPU/Triton**

- numerical parity CPU/GPU

- FP32/FP64

- warp divergence

- occupancy

- memory coalescing

- PCIe/NVLink

- zero-copy realmente medido.

**Ciclo 10 — RDMA/MIR-Wire**

- Write-With-Immediate

- ordering

- completion semantics

- remote memory lifetime

- NIC/CPU coherence

- retry/failure

- packet loss / transport assumptions.

Y sólo después de eso:

“industrialmente aceptable”​

## **Mi veredicto sobre tu pregunta “¿son alucinaciones?”**

**No, los hallazgos que marqué como 🔴 DEMOSTRADOS no son alucinaciones.** Están sustentados directamente por el dossier o por propiedades técnicas verificables.

Y donde **no puedo demostrar el bug sin el `.cpp`/`.rs` real**, lo he marcado explícitamente como **HIPÓTESIS**, no como hallazgo.

Ésa será la regla para todos los rounds siguientes.

Y una corrección especialmente importante respecto de mi propio análisis anterior: **no voy a mantener como bug la supuesta necesidad de que G sea tangente para que W=GXT−XGT sea antisimétrica**. Esa objeción queda retirada. El siguiente problema legítimo es demostrar que la operación resultante satisface las propiedades de **retraction**, no simplemente que conserva ortogonalidad.

La mejora SOTA más importante que emerge ahora no es otro microparche numérico: es convertir PMTP de **“triple buffer que pasó un stress test”** a un **protocolo formal de publicación + generación + reclamación + ABI + crash recovery**, y luego demostrar que la implementación satisface ese protocolo. Eso sí puede llevarnos del estado actual hacia una certificación de silicio defendible.

tu dices que emerge ahora. profundiza

Sí. Y aquí conviene precisar qué quise decir con **“emerge ahora”**: no significa que el problema haya aparecido mágicamente en V762. Significa que **al cerrar capas anteriores del análisis, ahora queda expuesta una clase de problemas de segundo/tercer orden que antes estaba oculta por problemas más superficiales**.

Voy a profundizar precisamente ahí: **PMTP/IPC como sistema concurrente real**, no como API que pasa los tests.

## **1. El salto conceptual: de “el algoritmo funciona” a “el sistema puede demostrar que funciona”**

En el dossier tenemos:

- 452.583 escrituras.

- 1.098 lecturas coherentes.

- 82.548 carreras detectadas.

- 7.845.655 casos “sin novedad”.

- 0 lecturas rasgadas entre las 1.098 validadas.

Eso es evidencia útil.

Pero **no demuestra todavía la propiedad industrial completa**.

El motivo es que hay varias propiedades distintas:

integridad del dato=orden de publicacioˊn=visibilidad=lifetime=reclamacioˊn/reutilizacioˊn=recuperacioˊn ante crash​

Y aquí está la emergencia real.

# **CICLO PROFUNDO — PMTP**

## **2. Problema emergente \#1: el seqlock demuestra coherencia, no necesariamente existencia válida**

Supongamos:

```
\*\*\`WRITER\`\*\*  
  
  
\*\*\`slot = FREE\`\*\*  
  
\`       ↓\`  
  
\`    \*\*WRITING\`\*\*  
  
\`       ↓\`  
  
\`     \*\*datos\`\*\*  
  
\`       ↓\`  
  
\`     \*\*READY\`\*\*
```

y:

```
\*\*\`READER\`\*\*  
  
  
\*\*\`READY\`\*\*  
  
\` ↓\`  
  
\*\*\`lee metadata\`\*\*  
  
\` ↓\`  
  
\*\*\`lee payload\`\*\*  
  
\` ↓\`  
  
\*\*\`vuelve a leer metadata\`\*\*  
  
\` ↓\`  
  
\*\*\`igual → acepta\`\*\*
```

Esto puede detectar:

- escritura concurrente;

- modificación durante lectura;

- torn reads;

- determinadas carreras.

Pero aparece una pregunta mucho más profunda:

> **¿Quién garantiza que el objeto que el reader está leyendo sigue teniendo lifetime válido durante TODA la ventana de lectura?**

Ese problema es diferente.

### **Ejemplo**

Reader:

```
\*\*\`R:\`\*\*  
  
\`  \*\*acquire(slot)\`\*\*  
  
\`  ────────────────────────────────\`  
  
\`          \*\*está leyendo payload\`\*\*  
  
\`  ────────────────────────────────\`
```

Mientras tanto:

```
\*\*\`W:\`\*\*  
  
\`  \*\*detecta slot disponible\`\*\*  
  
\`  \*\*reutiliza slot\`\*\*  
  
\`  \*\*escribe nueva generación\`\*\*
```

El seqlock puede detectar modificaciones.

Pero si además existe una operación de:

```
\*\*\`RETIRE\`\*\*  
  
\*\*\`FREE\`\*\*  
  
\*\*\`REUSE\`\*\*
```

entonces ya no estamos hablando únicamente de consistencia.

Estamos hablando de:

reclamation safety​

Es decir:

> **¿Puede el writer reutilizar físicamente el almacenamiento mientras existe un reader que todavía puede tocarlo?**

Esto **no está demostrado por el stress test del dossier**.

Y no afirmo que esté roto.

### **Clasificación**

**DETECTADO COMO BRECHA DE DEMOSTRACIÓN.**

No como bug confirmado.

# **3. Aquí aparece el verdadero enemigo: ABA**

Ahora vamos un nivel más abajo.

Supongamos que el reader observa:

```
\*\*\`generation = 100\`\*\*  
  
\*\*\`state = READY\`\*\*
```

Lee.

El writer hace:

```
\*\*\`100 READY\`\*\*  
  
\`↓\`  
  
\*\*\`101 WRITING\`\*\*  
  
\`↓\`  
  
\*\*\`101 READY\`\*\*
```

Eso es detectable.

Pero imagine un contador finito:

```
\*\*\`generation = 255\`\*\*
```

y posteriormente:

```
\*\*\`0\`\*\*
```

o, más generalmente, que el identificador reutilizable vuelva a un estado previamente observado.

Entonces:

```
\*\*\`A\`\*\*  
  
\`↓\`  
  
\*\*\`B\`\*\*  
  
\`↓\`  
  
\*\*\`A\`\*\*
```

Eso es la estructura clásica de:

ABA​

Por eso un simple:

```
\*\*\`if (seq\\\_begin == seq\\\_end)\`\*\*  
  
\`    \*\*accept();\`\*\*
```

no constituye por sí mismo una demostración universal de ausencia de ABA.

### **Solución SOTA**

Separar:

```
\*\*\`slot identity\`\*\*  
  
\*\*\`generation\`\*\*  
  
\*\*\`publication sequence\`\*\*  
  
\*\*\`payload validity\`\*\*  
  
\*\*\`reader ownership\`\*\*
```

Por ejemplo:

```
\*\*\`struct SlotMarker \\\{\`\*\*  
  
\`    \*\*uint64\\\_t generation;\`\*\*  
  
\`    \*\*uint64\\\_t sequence;\`\*\*  
  
\`    \*\*uint32\\\_t state;\`\*\*  
  
\`    \*\*uint32\\\_t checksum;\`\*\*  
  
\*\*\`\\\};\`\*\*
```

Y conceptualmente:

identity=(slot\_id,generation)

no:

identity=slot\_id

# **4. Pero hay algo todavía peor: generación no equivale a reclamación**

Aquí es donde el análisis empieza a ponerse realmente serio.

Incluso:

```
\*\*\`generation++\`\*\*
```

no resuelve:

> “¿Puede el escritor reutilizar este slot ahora?”

Porque la pregunta correcta es:

∃Ri​:Ri​ todavıˊa posee una referencia al slot

Si la respuesta es sí:

```
\*\*\`NO REUSE\`\*\*
```

aunque:

```
\*\*\`generation != old\\\_generation\`\*\*
```

Por eso propuse separar:

### **Publicación**

```
\*\*\`WRITING → READY\`\*\*
```

de:

### **Reclamación**

```
\*\*\`READY → RETIRED → FREE\`\*\*
```

Son problemas diferentes.

# **5. El modelo que yo exigiría a POLYDIM**

No:

```
\*\*\`FREE\`\*\*  
  
\*\*\`WRITING\`\*\*  
  
\*\*\`READY\`\*\*  
  
\*\*\`FREE\`\*\*
```

sino:

```
\`              ┌──────────────┐\`  
  
\`              │              │\`  
  
\`              ▼              │\`  
  
\`            \*\*FREE             │\`\*\*  
  
\`              │              │\`  
  
\`              ▼              │\`  
  
\`           \*\*WRITING           │\`\*\*  
  
\`              │              │\`  
  
\`              ▼              │\`  
  
\`            \*\*READY            │\`\*\*  
  
\`              │              │\`  
  
\`              ▼              │\`  
  
\`           \*\*RETIRED           │\`\*\*  
  
\`              │              │\`  
  
\`              ▼              │\`  
  
\`            \*\*FREE ────────────┘\`\*\*
```

Con una condición crítica:

READY→RETIRED no significa RETired→FREE​

hasta que:

readers\_active(slot)=0​

o hasta que un mecanismo equivalente de reclamación lo demuestre.

# **6. ¿Hazard pointers o epochs?**

Aquí no conviene meter tecnología porque sí.

Hay dos familias razonables.

### **Opción A — Hazard pointers**

Cada reader anuncia:

```
\*\*\`I am using slot X / generation G\`\*\*
```

Entonces el writer no puede reciclarlo.

Formalmente:

H=\{(sloti​,generationi​)\}

y:

(slot,g)∈H⇒¬FREE(slot,g)

Ventaja:

- reclamación precisa.

Coste:

- publicación/lectura de hazards;

- más tráfico de metadata;

- más complejidad.

### **Opción B — Epoch based reclamation**

Reader entra:

```
\*\*\`epoch = E\`\*\*
```

Writer retira:

```
\*\*\`slot → retired(E)\`\*\*
```

y solamente libera cuando:

Eglobal​\>Eretired​

para todos los readers pertinentes.

Para PMTP probablemente sea especialmente interesante si el patrón real es:

```
\*\*\`muchos readers\`\*\*  
  
\*\*\`pocos writers\`\*\*
```

pero **no voy a declarar cuál es superior sin conocer el patrón real de concurrencia**.

Eso sería inventar.

# **7. Segunda brecha emergente: SPMC no significa automáticamente IPC seguro**

El dossier habla de:

> triple-buffer SPMC

y el stress test parece orientado a threads.

Pero el objetivo arquitectónico de POLYDIM es mucho más ambicioso:

```
\*\*\`agent A\`\*\*  
  
\`   │\`  
  
\`   ▼\`  
  
\*\*\`shared memory\`\*\*  
  
\`   │\`  
  
\`   ├── \*\*agent B\`\*\*  
  
\`   ├── \*\*agent C\`\*\*  
  
\`   └── \*\*agent D\`\*\*
```

Eso significa que hay que demostrar:

thread-shared=process-shared​

Aunque utilicen el mismo hardware de memoria.

Linux sí permite compartir futexes mediante memoria compartida, y explícitamente reconoce que la misma palabra puede tener **distintas direcciones virtuales en distintos procesos**.

Esto tiene una consecuencia arquitectónica importante.

# **8. Raw pointer dentro de shared memory: aquí hay una trampa**

Supongamos:

Proceso A:

```
\*\*\`mapping base = 0x700000000000\`\*\*  
  
\*\*\`payload = 0x700000001000\`\*\*
```

Proceso B:

```
\*\*\`mapping base = 0x550000000000\`\*\*
```

El mismo objeto físico puede ser:

```
\*\*\`A: 0x700000001000\`\*\*  
  
\*\*\`B: 0x550000001000\`\*\*
```

Por tanto:

ptrA​=ptrB​

aunque:

objectA​=objectB​

Esto está documentado explícitamente en la semántica de memoria compartida de Linux.

Por eso para IPC industrial yo no aceptaría:

```
\*\*\`struct PayloadRef \\\{\`\*\*  
  
\`    \*\*void\\\* ptr;\`\*\*  
  
\*\*\`\\\};\`\*\*
```

como representación persistente dentro del segmento compartido.

Aceptaría:

```
\*\*\`struct SharedRef \\\{\`\*\*  
  
\`    \*\*uint64\\\_t segment\\\_id;\`\*\*  
  
\`    \*\*uint64\\\_t offset;\`\*\*  
  
\`    \*\*uint64\\\_t length;\`\*\*  
  
\`    \*\*uint64\\\_t generation;\`\*\*  
  
\*\*\`\\\};\`\*\*
```

y localmente:

```
\*\*\`ptr = local\\\_base + offset;\`\*\*
```

con:

```
\*\*\`offset \\\<= segment\\\_size\`\*\*  
  
\*\*\`length \\\<= segment\\\_size - offset\`\*\*
```

Eso transforma:

pointer identity

en:

shared-object identity​

Mucho más robusto.

# **9. Tercera brecha: el contrato actual no expresa capacidad**

Esto sí lo considero una brecha objetiva del header visible.

Por ejemplo:

```
\*\*\`polydim\\\_rodrigues\\\_geodesic\\\_f64(\`\*\*  
  
\`    \*\*y,\`\*\*  
  
\`    \*\*u,\`\*\*  
  
\`    \*\*v,\`\*\*  
  
\`    \*\*y\\\_out,\`\*\*  
  
\`    \*\*theta,\`\*\*  
  
\`    \*\*D,\`\*\*  
  
\`    \*\*tol,\`\*\*  
  
\`    \*\*report\`\*\*  
  
\*\*\`);\`\*\*
```

El contrato conoce:

```
\*\*\`D\`\*\*
```

pero no vemos explícitamente:

```
\*\*\`y\\\_capacity\`\*\*  
  
\*\*\`u\\\_capacity\`\*\*  
  
\*\*\`v\\\_capacity\`\*\*  
  
\*\*\`y\\\_out\\\_capacity\`\*\*
```

Entonces la función puede *matemáticamente* saber que necesita:

D⋅sizeof(double)

pero la interfaz no proporciona al callee una prueba directa de que el buffer realmente tiene ese tamaño.

Eso no significa:

> “el código hace overflow”.

No podemos afirmarlo.

Significa:

la seguridad de bounds depende de precondiciones externas​

y no está encapsulada en el ABI.

# **10. Solución: convertir tamaño implícito en contrato explícito**

Por ejemplo:

```
\*\*\`struct PolydimBufferF64 \\\{\`\*\*  
  
\`    \*\*double\\\* ptr;\`\*\*  
  
\`    \*\*uint64\\\_t len;\`\*\*  
  
\*\*\`\\\};\`\*\*
```

y:

```
\*\*\`struct PolydimConstBufferF64 \\\{\`\*\*  
  
\`    \*\*const double\\\* ptr;\`\*\*  
  
\`    \*\*uint64\\\_t len;\`\*\*  
  
\*\*\`\\\};\`\*\*
```

Entonces:

```
\*\*\`polydim\\\_rodrigues\\\_geodesic\\\_f64(\`\*\*  
  
\`    \*\*y,\`\*\*  
  
\`    \*\*u,\`\*\*  
  
\`    \*\*v,\`\*\*  
  
\`    \*\*y\\\_out,\`\*\*  
  
\`    \*\*theta,\`\*\*  
  
\`    \*\*D,\`\*\*  
  
\`    \*\*tol,\`\*\*  
  
\`    \*\*report\`\*\*  
  
\*\*\`);\`\*\*
```

pasa conceptualmente a:

```
\*\*\`polydim\\\_rodrigues\\\_geodesic\\\_f64(\`\*\*  
  
\`    \*\*y,\`\*\*  
  
\`    \*\*u,\`\*\*  
  
\`    \*\*v,\`\*\*  
  
\`    \*\*y\\\_out,\`\*\*  
  
\`    \*\*theta,\`\*\*  
  
\`    \*\*D,\`\*\*  
  
\`    \*\*tol,\`\*\*  
  
\`    \*\*report\`\*\*  
  
\*\*\`);\`\*\*
```

donde cada buffer tiene contrato:

len≥D

y antes de cualquier acceso:

```
\*\*\`if (y.len \\\< D) return BUFFER\\\_OVERFLOW;\`\*\*
```

Para operaciones multidimensionales:

D⋅K

no se calcula ingenuamente:

```
\*\*\`size\\\_t bytes = D \\\* K \\\* sizeof(double);\`\*\*
```

sino:

```
\*\*\`if (K != 0 && D \\\> SIZE\\\_MAX / K)\`\*\*  
  
\`    \*\*return BUFFER\\\_OVERFLOW;\`\*\*  
  
  
\*\*\`size\\\_t elements = D \\\* K;\`\*\*  
  
  
\*\*\`if (elements \\\> SIZE\\\_MAX / sizeof(double))\`\*\*  
  
\`    \*\*return BUFFER\\\_OVERFLOW;\`\*\*
```

Eso elimina una clase completa de overflow aritmético.

# **11. Cuarta brecha: ALIASED\_BUFFERS puede ser mucho más difícil de lo que parece**

El header tiene:

```
\*\*\`POLYDIM\\\_STATUS\\\_ALIASED\\\_BUFFERS\`\*\*
```

Eso es bueno.

Pero la pregunta profunda es:

> ¿Qué significa exactamente aliasing?

Esto:

```
\*\*\`y == y\\\_out\`\*\*
```

detecta únicamente alias exacto.

Pero esto:

```
\*\*\`y       = \\\[1000 ... 1999\\\]\`\*\*  
  
\*\*\`y\\\_out   = \\\[1500 ... 2499\\\]\`\*\*
```

tiene:

y∩yout​=∅

aunque:

y=yout​

Por tanto:

```
\*\*\`if (a == b)\`\*\*
```

no basta.

Para intervalos contiguos:

```
\*\*\`\\\[a, a+n)\`\*\*  
  
\*\*\`\\\[b, b+m)\`\*\*
```

hay solapamiento si:

a\<b+m∧b\<a+n

pero incluso aquí hay que evitar overflow en:

```
\*\*\`b + m\`\*\*
```

Por tanto, la versión robusta usa comparaciones basadas en diferencias/rangos representables.

### **Esto es una brecha de contrato, no un bug confirmado.**

Necesitamos ver la implementación para saber si V762 ya lo hace.

# **12. Quinta brecha: “lock-free” tiene dos significados distintos**

Esto es importantísimo para POLYDIM.

Podemos tener:

### **Hardware lock-free**

La operación atómica no usa un lock interno.

vs.

### **Algoritmo lock-free**

El sistema garantiza progreso global bajo determinadas condiciones.

No son equivalentes.

Una operación puede tener implementación que no sea realmente lock-free en determinado tipo/tamaño.

Los mecanismos estándar de C/C++ contemplan precisamente consultas de lock-freedom, y el soporte puede depender del tipo y plataforma.

Por eso no aceptaría:

```
\*\*\`PMTP = lock-free\`\*\*
```

solo porque usa:

```
\*\*\`std::atomic\`\*\*
```

Hay que medir/verificar:

```
\*\*\`static\\\_assert(std::atomic\\\<uint64\\\_t\\\>::is\\\_always\\\_lock\\\_free);\`\*\*
```

y cuando corresponda:

```
\*\*\`a.is\\\_lock\\\_free()\`\*\*
```

Además:

atomic lock−free⇒algorithm lock−free​

# **13. Sexta brecha: el problema más peligroso puede ser el crash**

Ahora entramos en un nivel que los tests normales prácticamente nunca cubren.

Writer:

```
\*\*\`WRITING\`\*\*  
  
\`   ↓\`  
  
\*\*\`escribe payload\`\*\*  
  
\`   ↓\`  
  
\*\*\`CRASH\`\*\*
```

¿Qué encuentra el siguiente proceso?

Si el protocolo sólo conoce:

```
\*\*\`FREE\`\*\*  
  
\*\*\`WRITING\`\*\*  
  
\*\*\`READY\`\*\*
```

puede quedar:

```
\*\*\`WRITING\`\*\*
```

para siempre.

Entonces tenemos:

liveness failure​

No corrupción.

No necesariamente data race.

Simplemente:

> **el sistema deja de progresar después de la muerte de un participante.**

Y esto es particularmente importante si POLYDIM pretende ser infraestructura de agentes.

# **14. El estado debería incorporar ownership/recovery**

Una posible estructura:

```
\*\*\`enum class State : uint32\\\_t \\\{\`\*\*  
  
\`    \*\*FREE,\`\*\*  
  
\`    \*\*WRITING,\`\*\*  
  
\`    \*\*READY,\`\*\*  
  
\`    \*\*RETIRED,\`\*\*  
  
\`    \*\*RECOVERABLE\`\*\*  
  
\*\*\`\\\};\`\*\*
```

y:

```
\*\*\`struct SlotHeader \\\{\`\*\*  
  
\`    \*\*uint64\\\_t generation;\`\*\*  
  
\`    \*\*uint64\\\_t owner\\\_id;\`\*\*  
  
\`    \*\*uint64\\\_t lease\\\_epoch;\`\*\*  
  
\`    \*\*uint64\\\_t publish\\\_seq;\`\*\*  
  
\`    \*\*uint32\\\_t state;\`\*\*  
  
\`    \*\*uint32\\\_t payload\\\_bytes;\`\*\*  
  
\*\*\`\\\};\`\*\*
```

Entonces:

```
\*\*\`WRITING\`\*\*
```

no significa simplemente:

> alguien está escribiendo.

Significa:

> writer X posee el derecho de publicación bajo generación G y lease E.

Si X muere:

```
\*\*\`lease expired\`\*\*
```

puede existir recuperación controlada.

# **15. Pero aquí aparece otro enemigo: false recovery**

No podemos simplemente decir:

```
\*\*\`if timeout \\\> 1ms\`\*\*  
  
\`    \*\*writer dead\`\*\*
```

porque:

```
\*\*\`descheduling\`\*\*  
  
\*\*\`page fault\`\*\*  
  
\*\*\`NUMA stall\`\*\*  
  
\*\*\`preemption\`\*\*  
  
\*\*\`thermal throttling\`\*\*  
  
\*\*\`OS noise\`\*\*
```

pueden producir latencias largas sin que el writer haya muerto.

Por tanto:

timeout=proof of death

Una recuperación segura necesita identidad/epoch/heartbeat o una estrategia externa de ownership.

Esto es precisamente el tipo de detalle que **emerge cuando pasamos de “stress test” a “sistema que debe sobrevivir a fallos reales”.**

# **16. Séptima brecha: el benchmark actual no prueba el escenario objetivo**

Esto también es importante.

El dossier da:

D=106

para Rodrigues.

Pero el objetivo declarado llega a:

D=107

Entonces:

106→107

es un factor:

10×

No podemos extrapolar linealidad sólo porque una prueba funcione en 106.

Hay que probar:

```
\*\*\`D = 10^3\`\*\*  
  
\*\*\`10^4\`\*\*  
  
\*\*\`10^5\`\*\*  
  
\*\*\`10^6\`\*\*  
  
\*\*\`10^7\`\*\*
```

y medir:

T(D)

además de:

BW(D)=T(D)8D​

para un vector f64.

Pero aún falta:

BWmemory​

del sistema.

Si POLYDIM consume aproximadamente varios streams de D doubles, el límite físico puede ser:

T≥memory bandwidthbytes moved​

y ahí podemos determinar si una optimización matemática tiene alguna posibilidad física.

# **17. Octava brecha: el “zero-copy” debe convertirse en una propiedad verificable**

Decir:

```
\*\*\`SharedMemory\`\*\*
```

no demuestra:

```
\*\*\`zero-copy\`\*\*
```

Una ruta puede ser:

```
\*\*\`producer\`\*\*  
  
\`→ \*\*shared memory\`\*\*  
  
\`→ \*\*consumer\`\*\*
```

y ser zero-copy.

Pero también puede existir:

```
\*\*\`producer\`\*\*  
  
\`→ \*\*shared memory\`\*\*  
  
\`→ \*\*temporary\`\*\*  
  
\`→ \*\*FFI conversion\`\*\*  
  
\`→ \*\*tensor\`\*\*  
  
\`→ \*\*consumer\`\*\*
```

con varias copias.

Por eso necesitamos instrumentación.

Idealmente:

Ncopies​=0

para el payload.

Y separar:

metadata copies

de:

payload copies

Porque copiar 64 bytes de metadata no invalida una arquitectura zero-copy del tensor de 80 MB.

# **18. Novena brecha: la verdadera unidad de prueba no es el slot**

Yo subiría la unidad de prueba a:

message lifecycle​

Es decir:

```
\*\*\`ALLOC\`\*\*  
  
\` ↓\`  
  
\*\*\`WRITE\`\*\*  
  
\` ↓\`  
  
\*\*\`PUBLISH\`\*\*  
  
\` ↓\`  
  
\*\*\`ACQUIRE\`\*\*  
  
\` ↓\`  
  
\*\*\`READ\`\*\*  
  
\` ↓\`  
  
\*\*\`VALIDATE\`\*\*  
  
\` ↓\`  
  
\*\*\`RELEASE\`\*\*  
  
\` ↓\`  
  
\*\*\`RETIRE\`\*\*  
  
\` ↓\`  
  
\*\*\`RECLAIM\`\*\*  
  
\` ↓\`  
  
\*\*\`REUSE\`\*\*
```

Y probaría cada transición bajo:

```
\*\*\`normal\`\*\*  
  
\*\*\`race\`\*\*  
  
\*\*\`delay\`\*\*  
  
\*\*\`preemption\`\*\*  
  
\*\*\`crash\`\*\*  
  
\*\*\`restart\`\*\*  
  
\*\*\`wraparound\`\*\*  
  
\*\*\`corruption\`\*\*  
  
\*\*\`duplicate\`\*\*  
  
\*\*\`reordering\`\*\*
```

Esto es mucho más fuerte que:

```
\*\*\`26 tests pass\`\*\*
```

porque prueba el **protocolo como máquina de estados**.

# **19. Décima brecha: necesitamos invariantes formales**

Aquí está probablemente la mejora más importante del ciclo.

No quiero que POLYDIM diga simplemente:

> “los tests pasan”.

Quiero invariantes.

### **Invariante P1 — publicación**

Si:

state=READY

entonces:

payload

está completamente escrito antes de la publicación.

### **P2 — estabilidad**

Si:

reader\_owns(slot,g)

entonces el payload correspondiente a:

(slot,g)

no puede ser reclamado.

### **P3 — generación**

Nunca se debe aceptar:

(slot,g1​)

cuando el reader adquirió:

(slot,g0​)

y:

g1​=g0​

### **P4 — reclamación**

FREE⇒no active reader

### **P5 — bounds**

Para cualquier acceso:

0≤offset

y:

length≤capacity−offset

### **P6 — publicación monotónica**

Si el protocolo exige orden:

seqn+1​\>seqn​

sin ambigüedad de wraparound.

# **20. Y aquí encuentro una cuestión todavía más profunda**

La arquitectura tiene que decidir explícitamente qué semántica quiere:

### **Modelo A**

```
\*\*\`latest-value\`\*\*
```

El reader sólo necesita el estado más reciente.

### **Modelo B**

```
\*\*\`reliable-message\`\*\*
```

Cada mensaje debe ser consumido.

### **Modelo C**

```
\*\*\`snapshot\`\*\*
```

El reader necesita una versión consistente completa.

### **Modelo D**

```
\*\*\`stream\`\*\*
```

No se puede perder ninguna transición.

Un triple buffer es naturalmente compatible con ciertos modelos de **latest-value/snapshot**, pero no es automáticamente equivalente a una cola fiable.

Por eso hay una pregunta arquitectónica fundamental:

¿QueˊsemaˊnticatieneexactamenteunmensajeMorpho?​

Esto cambia completamente:

- reclamación;

- backpressure;

- secuencias;

- pérdida;

- retransmisión;

- RDMA;

- persistencia;

- recovery.

No voy a inventar la respuesta: **el dossier no la formaliza con suficiente precisión**.

# **21. Y esto conecta directamente con MIR-Wire/RDMA**

Aquí la brecha se vuelve todavía más grande.

En shared memory:

```
\*\*\`CPU writes\`\*\*  
  
\`↓\`  
  
\*\*\`cache coherence\`\*\*  
  
\`↓\`  
  
\*\*\`reader\`\*\*
```

En RDMA:

```
\*\*\`NIC\`\*\*  
  
\`↓\`  
  
\*\*\`remote memory\`\*\*
```

La semántica de:

```
\*\*\`publication\`\*\*  
  
\*\*\`ordering\`\*\*  
  
\*\*\`visibility\`\*\*  
  
\*\*\`completion\`\*\*  
  
\*\*\`ownership\`\*\*
```

no puede simplemente asumirse igual.

Por eso Morpho necesita un **modelo de memoria de protocolo**, no sólo una implementación PMTP.

Yo lo formalizaría:

MorphoMemoryConsistencyModel​

con una tabla explícita:

| Operación | Antes | Después | Garantía |
| :-: | :-: | :-: | :-: |
| WRITE | WRITING | WRITING | payload privado |
| COMMIT | WRITING | READY | publicación |
| ACQUIRE | READY | READER | snapshot válido |
| RELEASE | READER | RETIRED | fin de uso |
| RECLAIM | RETIRED | FREE | reutilizable |


Y luego definir cómo se implementa en:

```
\*\*\`shared memory\`\*\*  
  
\*\*\`CUDA IPC\`\*\*  
  
\*\*\`NVLink\`\*\*  
  
\*\*\`RDMA\`\*\*  
  
\*\*\`MIR-Wire\`\*\*
```

sin cambiar la semántica lógica.

# **22. Entonces: ¿qué “emerge ahora”?**

Ahora sí puedo responder con precisión.

No emerge un bug mágico.

Emergen **dependencias que sólo aparecen cuando se intenta cerrar la demostración industrial**:

```
\*\*\`matemática\`\*\*  
  
\`   ↓\`  
  
\*\*\`algoritmo\`\*\*  
  
\`   ↓\`  
  
\*\*\`implementación\`\*\*  
  
\`   ↓\`  
  
\*\*\`concurrencia\`\*\*  
  
\`   ↓\`  
  
\*\*\`memoria\`\*\*  
  
\`   ↓\`  
  
\*\*\`IPC\`\*\*  
  
\`   ↓\`  
  
\*\*\`lifetime\`\*\*  
  
\`   ↓\`  
  
\*\*\`reclamation\`\*\*  
  
\`   ↓\`  
  
\*\*\`crash recovery\`\*\*  
  
\`   ↓\`  
  
\*\*\`ABI\`\*\*  
  
\`   ↓\`  
  
\*\*\`silicon\`\*\*
```

V762 ya cerró una cantidad importante de problemas numéricos/documentados.

Ahora el cuello de botella de rigor se desplaza hacia:

concurrency correctness+lifetime correctness+IPC semantics+fault recovery​

Y **ésta es una categoría completamente distinta de auditoría**.

## **Estado de severidad que puedo sostener ahora**

| Hallazgo | Estado |
| :-: | :-: |
| Tests PMTP demuestran que detecta carreras observadas | **DEMOSTRADO** |
| 0 torn reads en los 1.098 reads validados | **DEMOSTRADO según dossier** |
| Seqlock por sí solo prueba lifetime safety | **NO** |
| Seqlock por sí solo elimina ABA | **NO demostrado** |
| Triple buffer + stress ⇒ lock-free industrial | **NO demostrado** |
| Thread stress ⇒ process-shared IPC correcto | **NO** |
| Raw pointer es una representación IPC portable | **NO** |
| ABI visible demuestra bounds safety | **NO** |
| Crash recovery está formalmente demostrado | **NO** |
| Zero-copy está físicamente demostrado | **NO** |
| V762 tiene necesariamente esos bugs | **NO demostrado** |
| Existen esas **brechas de demostración** | **SÍ** |


Esto último es fundamental para no caer en el error contrario: **no voy a convertir una ausencia de evidencia en un bug inventado**.

La siguiente mordida, y aquí es donde yo seguiría, es todavía más profunda: **reconstruir PMTP como un protocolo formal de transición de estados y buscar interleavings exhaustivos**. Ahí podemos atacar casos como:

W1​→R1​→W2​→R2​

incluyendo:

- wraparound de secuencias,

- reader preempted,

- writer muerto,

- reader muerto,

- dos writers accidentales,

- reuso prematuro,

- reorderings acquire/release,

- alias parcial,

- overflow,

- proceso que remapea el segmento,

- y recuperación después de crash.

Eso ya no es “buscar otro bug”: es intentar **romper matemáticamente el protocolo de concurrencia**.


