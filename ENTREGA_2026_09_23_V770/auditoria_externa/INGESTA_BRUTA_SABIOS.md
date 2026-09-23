# PROTOCOLO DE INGESTA — FASE 0 (Unión en Bruto)
**FECHA:** 2026-09-23
**VERSIÓN:** V770 (Post-Fase 1)

## 1. Estado del Bloqueo (Rule 19)
**VETO ACTIVADO:** La generación y modificación de código fuente C++/Rust/Python queda **ESTRICTAMENTE PROHIBIDA** hasta que se complete la Fase 1 (Evaluación y Adición) y el usuario autorice el desbloqueo.

## 2. Ingesta Bruta Recibida (Consolidación)

### 2.1 Origen: Cerebras WSE (mcp-cerebras)
**Resumen del Reporte:**
> The algebraic identity $G_{proj}^T G_{proj} = G^T G - S(X^T G) - (G^T X)S + S(X^T X)S$ is mathematically exact but numerically unstable.
> In floating-point arithmetic, the subtraction of two large, nearly equal matrices incurs **catastrophic cancellation**.
> The relative error bound explodes to $O(u D \sqrt{K})$, meaning hundreds of bits of error for $D=10^6$.
> The current implementation will catastrophically diverge, overflow RAM, and invoke undefined behavior on any realistic workload.

### 2.2 Origen: Kimi/Claude (Vía Ariel)
**Resumen del Reporte:**
> La contracción algebraica $Q = H - S C - (S C)^\top + S^2$ (donde $C=X^\top G, S=\text{sym}(C), H=G^\top G$) es matemáticamente correcta y representa la mejora de mayor impacto.
> Recomienda fuertemente el uso de BLAS-3 (SYRK/GEMM) en lugar de bucles C++ manuales para los bloques $K \times K$.
> Sugiere forzar simetría numérica al final: `Q = 0.5 * (Q + Q.transpose())` para mitigar asimetrías de coma flotante.
> Cuestiona el conteo de TFLOPs original, ajustando a $\sim 0.1$ GFLOP por evaluación para $D=10^7, K=512$, asumiendo que 160MB de DRAM y TFLOPs vienen de iteraciones de line-search o loops anidados.
> **Regla de oro:** No materializar $G_{proj}$ salvo que sea consumidor final.
> Disiente implícitamente con Cerebras: considera la contracción robusta conceptualmente si se usa álgebra de alta intensidad y se fuerza la simetría.

### 2.3 Orígenes Pendientes (DeepSeek, Qwen, Gemini)
*(Esperando confirmación final del usuario para cerrar la Fase 0 y pasar a Fase 1: Arbitraje sobre la Cancelación Catastrófica de Cerebras vs la Validación de Kimi).*

## 3. Próximo Paso (Fase 1)
Evaluación crítica (Red Team) de la aserción de Cerebras sobre la Cancelación Catastrófica en SMW. Si es cierto, la optimización $O(K^3)$ destruye la geometría de $S^{D-1}$ por precisión de coma flotante, refutando el "Exit Code 0" de juguete y exigiendo un rollback o algoritmo numéricamente estable.
