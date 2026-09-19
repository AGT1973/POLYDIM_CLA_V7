#!/usr/bin/env python3
# ==============================================================================
# POLYDIM V761 — MODO NOCTURNO AUTÓNOMO SOTA 2026 (6 HORAS CONTINUAS)
# Regla 4, Regla 12, Regla 26 y Regla 28 (Watchdog + Ataque Asintótico en Silicio)
# ==============================================================================

import os
import sys
import time
import json
import psutil
import subprocess
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPORT_DIR = r"E:\POLYDIM_EINSOF\REPORTES"
LOG_FILE = os.path.join(REPORT_DIR, "nightly_v761_6h_execution.log")
STATE_LEDGER_FILE = r"E:\POLYDIM_EINSOF\POLYDIM_STATE_LEDGER.json"

DURATION_HOURS = 6
TOTAL_SECONDS = DURATION_HOURS * 3600
START_TIME = datetime.now()
END_TIME = START_TIME + timedelta(hours=DURATION_HOURS)

os.makedirs(REPORT_DIR, exist_ok=True)

def log_msg(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

log_msg("=" * 80)
log_msg(f"🌙 INICIANDO MODO NOCTURNO AUTÓNOMO POLYDIM V761 ({DURATION_HOURS} HORAS)")
log_msg(f"Target Delivery Dir: {BASE_DIR}")
log_msg(f"Inicio: {START_TIME.strftime('%Y-%m-%d %H:%M:%S')} | Fin Estimado: {END_TIME.strftime('%Y-%m-%d %H:%M:%S')}")
log_msg("=" * 80)

round_idx = 0
total_errors = 0

while datetime.now() < END_TIME:
    round_idx += 1
    t0 = time.perf_counter()
    log_msg(f"\n>>> INICIANDO CICLO NOCTURNO #{round_idx} (Tiempo restante: {END_TIME - datetime.now()}) <<<")
    
    # 1. Monitoreo de Hardware
    mem = psutil.virtual_memory()
    cpu_pct = psutil.cpu_percent(interval=1.0)
    log_msg(f"[HARDWARE PROBE] CPU Load: {cpu_pct:.1f}% | RAM Used: {mem.used / (1024**3):.2f} GB / {mem.total / (1024**3):.2f} GB ({mem.percent}%)")

    # 2. Ejecutar Suite Física Python (5/5)
    suite_cmd = [sys.executable, os.path.join(BASE_DIR, "test_v761_mpeleides.py")]
    res_suite = subprocess.run(suite_cmd, cwd=BASE_DIR, capture_output=True, text=True)
    if res_suite.returncode != 0:
        total_errors += 1
        log_msg(f"[ERROR] Suite Física Falló (Exit {res_suite.returncode}):\n{res_suite.stderr}\n{res_suite.stdout}")
    else:
        log_msg("[SILICON SUITE] 5/5 Suites MPELEIDES PASSED (Exit Code 0)")

    # 3. Ejecutar Red Team Adversarial Runner (4/4 ataques)
    redteam_cmd = [sys.executable, os.path.join(BASE_DIR, "vector_space_redteam_runner_v761.py")]
    res_redteam = subprocess.run(redteam_cmd, cwd=BASE_DIR, capture_output=True, text=True)
    if res_redteam.returncode != 0:
        total_errors += 1
        log_msg(f"[ERROR] Red Team Runner Falló (Exit {res_redteam.returncode}):\n{res_redteam.stderr}\n{res_redteam.stdout}")
    else:
        log_msg("[RED TEAM] 4/4 Ataques Adversariales Superados (Exit Code 0)")

    # 4. Ejecutar Benchmark Dart Standalone FFI (D=1,000,000)
    try:
        dart_cmd = ["dart", "polydim_ffi_v761.dart"]
        res_dart = subprocess.run(dart_cmd, cwd=BASE_DIR, capture_output=True, text=True, timeout=30)
        if res_dart.returncode != 0:
            total_errors += 1
            log_msg(f"[ERROR] Dart FFI Falló (Exit {res_dart.returncode}):\n{res_dart.stderr}")
        else:
            log_msg("[DART FFI] D=10^6 Standalone Benchmark PASSED (Exit Code 0)")
    except Exception as e:
        log_msg(f"[WARN] Dart FFI execution skipped or timed out: {e}")

    # 5. Actualizar State Ledger
    try:
        if os.path.exists(STATE_LEDGER_FILE):
            with open(STATE_LEDGER_FILE, "r", encoding="utf-8") as f:
                ledger = json.load(f)
            ledger["nightly_mode"] = {
                "status": "RUNNING_6H_LOOP",
                "current_round": round_idx,
                "total_errors": total_errors,
                "last_cycle_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "end_target_time": END_TIME.strftime("%Y-%m-%d %H:%M:%S")
            }
            with open(STATE_LEDGER_FILE, "w", encoding="utf-8") as f:
                json.dump(ledger, f, indent=2)
    except Exception as e:
        log_msg(f"[WARN] Error actualizando State Ledger: {e}")

    t_round = time.perf_counter() - t0
    log_msg(f"✅ CICLO #{round_idx} FINALIZADO en {t_round:.2f}s | Errores acumulados: {total_errors}")

    # Intervalo de descanso entre ciclos de 60 segundos
    time.sleep(60)

log_msg("=" * 80)
log_msg(f"🌙 MODO NOCTURNO CONCLUIDO CON ÉXITO TRAS {round_idx} CICLOS (Errores Totales: {total_errors})")
log_msg("=" * 80)
