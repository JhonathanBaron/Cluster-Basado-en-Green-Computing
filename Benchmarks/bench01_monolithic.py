"""
================================================================================
BENCH-01 | MONOLITHIC — Compute & Memory Benchmark/para probar en computadoras personales
================================================================================
Mide:
  • GFLOPs sostenidos (DGEMM via NumPy/BLAS)
  • Ancho de banda de memoria (STREAM-like: copy, scale, add, triad)
  • Latencia de memoria (pointer-chase)
  • Rendimiento de FFT (GFLOPs efectivos)
  • Paralelismo disponible (threads BLAS, CPUs lógicos)

Uso:
  python bench01_monolithic.py
  python bench01_monolithic.py --size large   # matrices más grandes
  python bench01_monolithic.py --no-fft       # omitir FFT

Requisitos: se instalan automáticamente si faltan.
================================================================================
"""

# ── Auto-instalador ────────────────────────────────────────────────────────────
import sys
import subprocess

REQUIRED = {
    "numpy": "numpy",
    "psutil": "psutil",
    "py-cpuinfo": "cpuinfo",   # pip name : import name
}

def _install_missing():
    import importlib
    needs = []
    for pip_name, import_name in REQUIRED.items():
        try:
            importlib.import_module(import_name)
        except ModuleNotFoundError:
            needs.append(pip_name)
    if needs:
        print(f"[setup] Instalando dependencias faltantes: {needs}")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--quiet"] + needs
        )
        print("[setup] Listo.\n")

_install_missing()

# ── Imports principales ────────────────────────────────────────────────────────
import argparse
import os
import platform
import socket
import struct
import time
import math
import warnings
from datetime import datetime

import numpy as np
import psutil

warnings.filterwarnings("ignore")

try:
    import cpuinfo as _cpuinfo
    _CPU_BRAND = _cpuinfo.get_cpu_info().get("brand_raw", "N/A")
except Exception:
    _CPU_BRAND = "N/A"

# ── Configuración de tamaños ───────────────────────────────────────────────────
SIZE_PRESETS = {
    "small":  dict(gemm_n=2048,  stream_mb=256,  fft_n=2**22, chase_mb=32),
    "medium": dict(gemm_n=4096,  stream_mb=512,  fft_n=2**24, chase_mb=64),
    "large":  dict(gemm_n=8192,  stream_mb=1024, fft_n=2**25, chase_mb=128),
}

# ── Utilidades de formato ──────────────────────────────────────────────────────
SEP  = "─" * 72
SEP2 = "═" * 72

def _header(title: str):
    print(f"\n{SEP2}")
    print(f"  {title}")
    print(SEP2)

def _section(title: str):
    print(f"\n{SEP}")
    print(f"  {title}")
    print(SEP)

def _row(label: str, value, unit: str = ""):
    label_str = f"  {label:<38}"
    val_str   = f"{value}" if isinstance(value, str) else f"{value:>12}"
    print(f"{label_str} {val_str}  {unit}")

# ─────────────────────────────────────────────────────────────────────────────
# 1. INFORMACIÓN DEL SISTEMA
# ─────────────────────────────────────────────────────────────────────────────
def collect_sysinfo() -> dict:
    vm   = psutil.virtual_memory()
    swap = psutil.swap_memory()
    freq = psutil.cpu_freq()

    # Intentar detectar GPU (opcional, no falla si no existe)
    gpu_info = "N/A"
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=name,memory.total",
             "--format=csv,noheader,nounits"],
            stderr=subprocess.DEVNULL, timeout=5
        ).decode().strip()
        if out:
            gpu_info = out.replace("\n", " | ")
    except Exception:
        pass

    blas_info = np.show_config.__doc__ or ""
    try:
        np.__config__.blas_opt_info  # type: ignore
        blas = getattr(np.__config__, "blas_opt_info", {})
        blas_libs = blas.get("libraries", ["desconocido"])
    except Exception:
        blas_libs = ["desconocido"]

    return {
        "hostname":       socket.gethostname(),
        "os":             f"{platform.system()} {platform.release()}",
        "arch":           platform.machine(),
        "cpu_brand":      _CPU_BRAND,
        "cpu_physical":   psutil.cpu_count(logical=False),
        "cpu_logical":    psutil.cpu_count(logical=True),
        "cpu_freq_max":   f"{freq.max:.0f} MHz" if freq else "N/A",
        "ram_total_gb":   vm.total   / 2**30,
        "ram_avail_gb":   vm.available / 2**30,
        "swap_total_gb":  swap.total / 2**30,
        "python":         sys.version.split()[0],
        "numpy":          np.__version__,
        "blas":           ", ".join(blas_libs),
        "gpu":            gpu_info,
        "timestamp":      datetime.now().isoformat(timespec="seconds"),
    }

def print_sysinfo(info: dict):
    _header("BENCH-01 · MONOLÍTICO — Compute & Memory")
    _section("INFORMACIÓN DEL SISTEMA")
    _row("Host",              info["hostname"])
    _row("Sistema Operativo", info["os"])
    _row("Arquitectura",      info["arch"])
    _row("CPU",               info["cpu_brand"])
    _row("Núcleos físicos",   info["cpu_physical"])
    _row("Núcleos lógicos",   info["cpu_logical"])
    _row("Frecuencia máx.",   info["cpu_freq_max"])
    _row("RAM total",         f"{info['ram_total_gb']:.2f}", "GiB")
    _row("RAM disponible",    f"{info['ram_avail_gb']:.2f}", "GiB")
    _row("Swap total",        f"{info['swap_total_gb']:.2f}", "GiB")
    _row("Python",            info["python"])
    _row("NumPy",             info["numpy"])
    _row("BLAS detectado",    info["blas"])
    _row("GPU (si existe)",   info["gpu"])
    _row("Timestamp",         info["timestamp"])

# ─────────────────────────────────────────────────────────────────────────────
# 2. BENCHMARK GEMM (GFLOPs)
# ─────────────────────────────────────────────────────────────────────────────
def bench_gemm(n: int, repeats: int = 5) -> dict:
    """
    Multiplicación de matrices cuadradas float64: C = A @ B
    FLOPs = 2 * n^3  (n multiplicaciones + n sumas por elemento de C)
    """
    flops_total = 2.0 * n**3

    # Calentamiento
    A = np.random.rand(n, n).astype(np.float64)
    B = np.random.rand(n, n).astype(np.float64)
    _ = np.dot(A, B)

    times = []
    for _ in range(repeats):
        A = np.random.rand(n, n).astype(np.float64)
        B = np.random.rand(n, n).astype(np.float64)
        t0 = time.perf_counter()
        C  = np.dot(A, B)
        t1 = time.perf_counter()
        times.append(t1 - t0)
        del C

    times.sort()
    # Descartamos el más lento y el más rápido si hay suficientes muestras
    if repeats > 2:
        times = times[1:-1]

    t_med  = np.median(times)
    t_best = min(times)

    return {
        "matrix_size":   n,
        "repeats":       repeats,
        "flops_per_run": flops_total,
        "time_median_s": t_med,
        "time_best_s":   t_best,
        "gflops_median": flops_total / t_med  / 1e9,
        "gflops_peak":   flops_total / t_best / 1e9,
        "matrix_mem_gb": 3 * n * n * 8 / 2**30,  # A, B, C en float64
    }

def print_gemm(r: dict):
    _section(f"DGEMM — Multiplicación de matrices {r['matrix_size']}×{r['matrix_size']}")
    _row("Tamaño de matriz",        f"{r['matrix_size']}×{r['matrix_size']}")
    _row("Memoria total (A+B+C)",   f"{r['matrix_mem_gb']:.2f}", "GiB")
    _row("FLOPs por iteración",     f"{r['flops_per_run']:.3e}")
    _row("Repeticiones (netas)",    r["repeats"])
    _row("Tiempo mediano",          f"{r['time_median_s']:.4f}", "s")
    _row("Tiempo mínimo",           f"{r['time_best_s']:.4f}",  "s")
    _row("GFLOPs (mediana)",        f"{r['gflops_median']:.2f}", "GFLOP/s")
    _row("GFLOPs (pico)",           f"{r['gflops_peak']:.2f}",  "GFLOP/s  ← reportar este")

# ─────────────────────────────────────────────────────────────────────────────
# 3. BENCHMARK DE ANCHO DE BANDA DE MEMORIA (STREAM-like)
# ─────────────────────────────────────────────────────────────────────────────
def bench_stream(target_mb: float) -> dict:
    """
    Implementación inspirada en el benchmark STREAM.
    Kernels:
      Copy:  C = A
      Scale: B = s * C
      Add:   C = A + B
      Triad: A = B + s*C
    Ancho de banda = bytes_leídos+escritos / tiempo
    """
    s = 2.5   # escalar arbitrario
    n = int(target_mb * 1e6 / 8)   # elementos float64 para ~target_mb MB por array

    A = np.random.rand(n).astype(np.float64)
    B = np.random.rand(n).astype(np.float64)
    C = np.random.rand(n).astype(np.float64)

    repeats = 5
    results = {}

    # — Copy —
    times = []
    for _ in range(repeats):
        t0 = time.perf_counter(); C[:] = A; t1 = time.perf_counter()
        times.append(t1 - t0)
    # bytes: 1 read (A) + 1 write (C)
    bw = (2 * n * 8) / np.median(times) / 1e9
    results["copy_GBs"] = bw

    # — Scale —
    times = []
    for _ in range(repeats):
        t0 = time.perf_counter(); B[:] = s * C; t1 = time.perf_counter()
        times.append(t1 - t0)
    bw = (2 * n * 8) / np.median(times) / 1e9
    results["scale_GBs"] = bw

    # — Add —
    times = []
    for _ in range(repeats):
        t0 = time.perf_counter(); C[:] = A + B; t1 = time.perf_counter()
        times.append(t1 - t0)
    # 2 reads (A,B) + 1 write (C)
    bw = (3 * n * 8) / np.median(times) / 1e9
    results["add_GBs"] = bw

    # — Triad —
    times = []
    for _ in range(repeats):
        t0 = time.perf_counter(); A[:] = B + s * C; t1 = time.perf_counter()
        times.append(t1 - t0)
    bw = (3 * n * 8) / np.median(times) / 1e9
    results["triad_GBs"] = bw

    results["array_size_mb"] = n * 8 / 1e6
    results["n_elements"]    = n
    return results

def print_stream(r: dict):
    _section(f"STREAM-like — Ancho de banda de memoria ({r['array_size_mb']:.0f} MB por array)")
    _row("Elementos por array",  f"{r['n_elements']:,}")
    _row("Copy  (1R + 1W)",      f"{r['copy_GBs']:.2f}",  "GB/s")
    _row("Scale (1R + 1W)",      f"{r['scale_GBs']:.2f}", "GB/s")
    _row("Add   (2R + 1W)",      f"{r['add_GBs']:.2f}",   "GB/s")
    _row("Triad (2R + 1W)",      f"{r['triad_GBs']:.2f}", "GB/s  ← métrica principal")

# ─────────────────────────────────────────────────────────────────────────────
# 4. LATENCIA DE MEMORIA (pointer-chase)
# ─────────────────────────────────────────────────────────────────────────────
def bench_latency(chase_mb: int) -> dict:
    """
    Pointer-chase: acceso aleatorio a un arreglo grande para forzar cache misses.
    Mide latencia de RAM (no caché L1/L2).
    """
    stride = 64   # bytes — tamaño de línea de caché típico
    n_int  = (chase_mb * 1024 * 1024) // 8
    n_int  = max(n_int, 1024)

    # Construir cadena de punteros aleatoria
    indices = np.arange(n_int, dtype=np.int64)
    np.random.shuffle(indices)
    chain = np.zeros(n_int, dtype=np.int64)
    for i in range(n_int - 1):
        chain[indices[i]] = indices[i + 1]
    chain[indices[-1]] = indices[0]

    # Recorrer la cadena
    steps = min(2_000_000, n_int * 5)
    ptr   = int(chain[0])
    t0    = time.perf_counter()
    for _ in range(steps):
        ptr = int(chain[ptr])
    t1 = time.perf_counter()
    _ = ptr  # evitar optimización

    latency_ns = (t1 - t0) / steps * 1e9

    return {
        "array_size_mb": chase_mb,
        "steps":         steps,
        "latency_ns":    latency_ns,
    }

def print_latency(r: dict):
    _section(f"Latencia de memoria — arreglo de {r['array_size_mb']} MB")
    _row("Pasos realizados",        f"{r['steps']:,}")
    _row("Latencia media (RAM)",    f"{r['latency_ns']:.1f}", "ns")
    note = " (< 100 ns: caché; 60-200 ns: RAM típica; > 300 ns: NUMA/swap)"
    print(f"  {'Referencia':38} {note}")

# ─────────────────────────────────────────────────────────────────────────────
# 5. BENCHMARK FFT
# ─────────────────────────────────────────────────────────────────────────────
def bench_fft(n: int, repeats: int = 5) -> dict:
    """
    FFT 1-D de n puntos complejos (float64).
    FLOPs efectivos = 5 * n * log2(n)  (convención estándar)
    """
    flops = 5 * n * math.log2(n)
    x = np.random.rand(n).astype(np.float64) + 1j * np.random.rand(n).astype(np.float64)

    # Calentamiento
    np.fft.fft(x)

    times = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        np.fft.fft(x)
        t1 = time.perf_counter()
        times.append(t1 - t0)

    t_med  = np.median(times)
    t_best = min(times)

    return {
        "n_points":       n,
        "flops":          flops,
        "time_median_s":  t_med,
        "time_best_s":    t_best,
        "gflops_median":  flops / t_med  / 1e9,
        "gflops_peak":    flops / t_best / 1e9,
        "mem_mb":         n * 16 / 1e6,   # complex128 = 16 bytes
    }

def print_fft(r: dict):
    _section(f"FFT 1-D — {r['n_points']:,} puntos complejos")
    _row("Puntos",              f"{r['n_points']:,}")
    _row("Memoria del arreglo", f"{r['mem_mb']:.1f}", "MB")
    _row("FLOPs efectivos",     f"{r['flops']:.3e}")
    _row("GFLOPs (mediana)",    f"{r['gflops_median']:.3f}", "GFLOP/s")
    _row("GFLOPs (pico)",       f"{r['gflops_peak']:.3f}",  "GFLOP/s")

# ─────────────────────────────────────────────────────────────────────────────
# 6. RESUMEN FINAL
# ─────────────────────────────────────────────────────────────────────────────
def print_summary(gemm, stream, latency, fft=None):
    _header("RESUMEN — BENCH-01 MONOLÍTICO")
    _row("GFLOPs sostenidos (DGEMM pico)",    f"{gemm['gflops_peak']:.2f}",       "GFLOP/s")
    _row("GFLOPs sostenidos (DGEMM mediana)", f"{gemm['gflops_median']:.2f}",     "GFLOP/s")
    _row("Ancho de banda Triad",              f"{stream['triad_GBs']:.2f}",       "GB/s")
    _row("Ancho de banda Copy",               f"{stream['copy_GBs']:.2f}",        "GB/s")
    _row("Latencia RAM (pointer-chase)",      f"{latency['latency_ns']:.1f}",     "ns")
    if fft:
        _row("GFLOPs FFT (pico)",             f"{fft['gflops_peak']:.3f}",        "GFLOP/s")
    print(f"\n{SEP2}\n")

# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="BENCH-01 | Compute & Memory Benchmark")
    parser.add_argument("--size", type=str, choices=["small", "medium", "large"], default="medium",
                        help="Tamaño de los benchmarks (default: medium)")
    parser.add_argument("--repeats", type=int, default=5,
                        help="Número de repeticiones para DGEMM/FFT (default: 5)")
    parser.add_argument("--no-fft", action="store_true",
                        help="Omitir el benchmark de FFT")
    args = parser.parse_args()

    cfg = SIZE_PRESETS[args.size]

    # ── Sistema ────────────────────────────────────────────────────────────────
    info = collect_sysinfo()
    print_sysinfo(info)

    # ── GEMM ──────────────────────────────────────────────────────────────────
    print(f"\n[bench] DGEMM  n={cfg['gemm_n']} ...")
    gemm = bench_gemm(cfg["gemm_n"], repeats=args.repeats)
    print_gemm(gemm)

    # ── STREAM ────────────────────────────────────────────────────────────────
    print(f"\n[bench] STREAM  {cfg['stream_mb']} MB/array ...")
    stream = bench_stream(cfg["stream_mb"])
    print_stream(stream)

    # ── Latencia ──────────────────────────────────────────────────────────────
    print(f"\n[bench] Pointer-chase  {cfg['chase_mb']} MB ...")
    latency = bench_latency(cfg["chase_mb"])
    print_latency(latency)

    # ── FFT ───────────────────────────────────────────────────────────────────
    fft = None
    if not args.no_fft:
        print(f"\n[bench] FFT  n={cfg['fft_n']:,} ...")
        fft = bench_fft(cfg["fft_n"], repeats=args.repeats)
        print_fft(fft)

    # ── Resumen ───────────────────────────────────────────────────────────────
    print_summary(gemm, stream, latency, fft)


if __name__ == "__main__":
    main()
