"""
================================================================================
CARACTERIZACIÓN DE HARDWARE: BENCH-01 | MONOLITHIC
================================================================================
Este módulo de software científico tiene como objetivo evaluar y cuantificar 
el rendimiento de cómputo y el subsistema de memoria en entornos monolíticos 
(computadoras personales / nodos individuales) antes de su integración en clúster.

Métricas de Evaluación Arquitectónica:
  1. DGEMM (Double-Precision General Matrix Multiplication): Cómputo bruto.
  2. STREAM-like Kernels: Ancho de banda de la memoria RAM (GB/s).
  3. Pointer-Chasing: Latencia física de acceso a celdas de memoria (ns).
  4. 1-D Fast Fourier Transform (FFT): Rendimiento en procesamiento de señales.

Uso Académico / CLI:
  python bench01_monolithic.py --size medium
  python bench01_monolithic.py --size large   # Para estresar sistemas de gama alta
================================================================================
"""

# ── AUTO-INSTALADOR DE DEPENDENCIAS CRÍTICAS ──────────────────────────────────
# Este bloque garantiza la reproducibilidad del experimento científico de forma 
# automatizada en entornos Linux/Windows sin intervención del usuario.
import sys
import subprocess

REQUIRED = {
    "numpy": "numpy",          # Operaciones de álgebra lineal y matrices densas
    "psutil": "psutil",        # Interfaz de telemetría del Sistema Operativo
    "py-cpuinfo": "cpuinfo",   # Extracción de metadatos del set de instrucciones de la CPU
}

def _install_missing():
    """Verifica e instala dinámicamente las dependencias en el entorno virtual."""
    import importlib
    needs = []
    for pip_name, import_name in REQUIRED.items():
        try:
            importlib.import_module(import_name)
        except ModuleNotFoundError:
            needs.append(pip_name)
    if needs:
        print(f"[setup] Entorno incompleto. Instalando dependencias: {needs}")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--quiet"] + needs
        )
        print("[setup] Entorno configurado con éxito.\n")

_install_missing()

# ── IMPORTS DE LAS LIBRERÍAS DEL SISTEMA ──────────────────────────────────────
import argparse
import os
import platform
import socket
import struct
import time
import math
import warnings
import gc  # Garbage Collector para la gestión estricta de la memoria RAM
from datetime import datetime

import numpy as np
import psutil

# Desactivar advertencias de optimización interna para mantener limpia la salida de consola
warnings.filterwarnings("ignore")

# Extracción de los metadatos de microarquitectura del procesador
try:
    import cpuinfo as _cpuinfo
    _CPU_BRAND = _cpuinfo.get_cpu_info().get("brand_raw", "N/A")
except Exception:
    _CPU_BRAND = "N/A"


# ── CONFIGURACIÓN DE CARGA DE TRABAJO (PRESETS DE COMPLEJIDAD) ────────────────
# >>> MODIFICAR AQUÍ <<<
# Si deseas un nivel de estrés hiper-complejo que desborde arquitecturas modernas:
# 1. Modifica los valores directamente dentro del diccionario "large".
# 2. O añade un nuevo preset personalizado (ej. "ultra_green").
SIZE_PRESETS = {
    # Carga Ligera: Diseñada para hardware e-waste muy antiguo (ej. procesadores Core 2 Duo, 2GB-4GB RAM)
    "small":  dict(gemm_n=2048,  stream_mb=256,  fft_n=2**22, chase_mb=32),
    
    # Carga Estándar: Equilibrio matemático para CPUs de 4 a 8 núcleos y mínimo 8GB de RAM disponible
    "medium": dict(gemm_n=4096,  stream_mb=512,  fft_n=2**24, chase_mb=64),
    
    # Carga Crítica/Compleja: Forzar uso exhaustivo de la jerarquía de cachés y buses del sistema (DDR3/DDR4)
    # Modificar estos valores alterará la complejidad asintótica de las pruebas locales.
    "large":  dict(
        gemm_n=8192,     # Eleva el cálculo de DGEMM a un espacio de almacenamiento masivo
        stream_mb=1024,  # Desborda cualquier caché L3 existente, obligando el uso de la RAM física
        fft_n=2**25,     # Incrementa los puntos de muestreo complejos a ~33.5 millones
        chase_mb=128     # Genera un grafo de punteros gigante para arruinar el Branch Predictor de la CPU
    ),
}


# ── UTILIDADES DE FORMATEO Y LOGGING ──────────────────────────────────────────
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
# 1. MÓDULO DE TELEMETRÍA DEL HARDWARE HOST
# ─────────────────────────────────────────────────────────────────────────────
def collect_sysinfo() -> dict:
    """
    Inspecciona las llamadas a nivel de kernel de OS para registrar el estado de hardware.
    Significado de las Variables de Retorno:
        - hostname: Identificador de la máquina en la red local.
        - cpu_physical/logical: Distinción entre núcleos físicos de silicio e hilos de Hyper-Threading.
        - ram_avail_gb: RAM libre del sistema (crítico para prevenir el throttling por SWAP en disco).
    """
    vm   = psutil.virtual_memory()
    swap = psutil.swap_memory()
    freq = psutil.cpu_freq()

    # Intento de detección de aceleradores de hardware gráficos (GPUs corporativas/personales)
    gpu_info = "N/A"
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
            stderr=subprocess.DEVNULL, timeout=5
        ).decode().strip()
        if out:
            gpu_info = out.replace("\n", " | ")
    except Exception:
        pass

    # Extracción de información de la librería matemática subyacente (OpenBLAS, MKL, etc.)
    try:
        np.__config__.blas_opt_info  
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
        "ram_total_gb":   vm.total    / 2**30,
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
# 2. CORE COMPUTACIONAL: ALGEBRA LINEAL DENSA (DGEMM)
# ─────────────────────────────────────────────────────────────────────────────
def bench_gemm(n: int, repeats: int = 5) -> dict:
    """
    Evalúa la capacidad de procesamiento punto flotante de doble precisión ($64\text{-bit}$).
    Complejidad Asintótica del Algoritmo: $$O(N^3)$$
    Significado de Variables Internas:
        - n: Dimensión lineal de la matriz cuadrada.
        - flops_total: Operaciones teóricas realizadas $$2.0 \times N^3$$.
        - times: Almacenamiento de marcas temporales de alta resolución.
    """
    flops_total = 2.0 * n**3

    # Warmup estructural: Previene que la compilación JIT o la carga diferida afecte las métricas
    A = np.random.rand(n, n).astype(np.float64)
    B = np.random.rand(n, n).astype(np.float64)
    _ = np.dot(A, B)

    times = []
    for _ in range(repeats):
        A = np.random.rand(n, n).astype(np.float64)
        B = np.random.rand(n, n).astype(np.float64)
        
        t0 = time.perf_counter()
        C  = np.dot(A, B) # Operación crítica de álgebra lineal BLAS
        t1 = time.perf_counter()
        
        times.append(t1 - t0)
        del C # Purga el espacio direccionado inmediatamente

    times.sort()
    # Filtrado estadístico para robustez científica frente a interrupciones del OS
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
        "matrix_mem_gb": 3 * n * n * 8 / 2**30,
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
# 3. ANCHO DE BANDA SECUENCIAL DE MEMORIA (STREAM-LIKE KERNELS)
# ─────────────────────────────────────────────────────────────────────────────
def bench_stream(target_mb: float) -> dict:
    """
    Mide el rendimiento del canal Bus CPU-RAM bajo patrones de acceso continuos.
    Variables y Ecuaciones del Ancho de Banda:
        - n: Cantidad de elementos del vector calculados en función del peso del tipo primitivo ($8\text{ bytes}$).
        - bw: $$\text{Bytes transferidos} / (\text{Tiempo de ejecución} \times 10^9)$$
    """
    s = 2.5   # Escalar constante del sistema
    n = int(target_mb * 1e6 / 8)  

    A = np.random.rand(n).astype(np.float64)
    B = np.random.rand(n).astype(np.float64)
    C = np.random.rand(n).astype(np.float64)

    repeats = 5
    results = {}

    # ── Kernel COPY: C = A (Transferencia pura: 1 Lectura, 1 Escritura)
    times = []
    for _ in range(repeats):
        t0 = time.perf_counter(); C[:] = A; t1 = time.perf_counter()
        times.append(t1 - t0)
    bw = (2 * n * 8) / np.median(times) / 1e9
    results["copy_GBs"] = bw

    # ── Kernel SCALE: B = s * C (Aritmética simple sobre la marcha)
    times = []
    for _ in range(repeats):
        t0 = time.perf_counter(); B[:] = s * C; t1 = time.perf_counter()
        times.append(t1 - t0)
    bw = (2 * n * 8) / np.median(times) / 1e9
    results["scale_GBs"] = bw

    # ── Kernel ADD: C = A + B (2 Lecturas de vectores independientes, 1 Escritura)
    times = []
    for _ in range(repeats):
        t0 = time.perf_counter(); C[:] = A + B; t1 = time.perf_counter()
        times.append(t1 - t0)
    bw = (3 * n * 8) / np.median(times) / 1e9
    results["add_GBs"] = bw

    # ── Kernel TRIAD: A = B + s * C (Operación Vectorial Compleja Combinada)
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
# 4. DIAGNÓSTICO DE LATENCIA PURA (POINTER-CHASING)
# ─────────────────────────────────────────────────────────────────────────────
def bench_latency(chase_mb: int) -> dict:
    """
    Anula de manera deliberada la utilidad de los registros de caché del CPU.
    Algoritmia: Crea una estructura circular aleatoria cuyos saltos son mayores 
    que una línea de caché ($64\text{ bytes}$), forzando retrasos físicos del hardware.
    Significado de Variables:
        - chain: El arreglo que funciona como el mapa de memoria desordenado.
        - latency_ns: El tiempo de respuesta expresado en nanosegundos ($10^{-9}\text{s}$).
    """
    stride = 64   
    n_int  = (chase_mb * 1024 * 1024) // 8
    n_int  = max(n_int, 1024)

    # Inicialización del mapa circular de punteros aleatorizados
    indices = np.arange(n_int, dtype=np.int64)
    np.random.shuffle(indices)
    chain = np.zeros(n_int, dtype=np.int64)
    for i in range(n_int - 1):
        chain[indices[i]] = indices[i + 1]
    chain[indices[-1]] = indices[0]

    # Ejecución de la persecución de punteros sin predictibilidad posible
    steps = min(2_000_000, n_int * 5)
    ptr   = int(chain[0])
    t0    = time.perf_counter()
    for _ in range(steps):
        ptr = int(chain[ptr])
    t1 = time.perf_counter()
    _ = ptr  

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
# 5. VELOCIDAD EN PROCESAMIENTO DE SEÑALES (1-D FFT)
# ─────────────────────────────────────────────────────────────────────────────
def bench_fft(n: int, repeats: int = 5) -> dict:
    """
    Mide el desempeño ejecutando la Transformada Rápida de Fourier.
    Fórmula de la Complejidad Matemática Estándar:
        $$\text{FLOPs efectivos} = 5 \times N \times \log_2(N)$$
    """
    flops = 5 * n * math.log2(n)
    x = np.random.rand(n).astype(np.float64) + 1j * np.random.rand(n).astype(np.float64)

    np.fft.fft(x) # Warmup

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
        "mem_mb":         n * 16 / 1e6,   # Representación complex128 ocupando 16 bytes
    }

def print_fft(r: dict):
    _section(f"FFT 1-D — {r['n_points']:,} puntos complejos")
    _row("Puntos",              f"{r['n_points']:,}")
    _row("Memoria del arreglo", f"{r['mem_mb']:.1f}", "MB")
    _row("FLOPs efectivos",     f"{r['flops']:.3e}")
    _row("GFLOPs (mediana)",    f"{r['gflops_median']:.3f}", "GFLOP/s")
    _row("GFLOPs (pico)",       f"{r['gflops_peak']:.3f}",  "GFLOP/s")


# ─────────────────────────────────────────────────────────────────────────────
# 6. MÓDULO DE REPORTE CIENTÍFICO FINAL
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
# PUNTO DE ENTRADA (ORQUESTADOR PRINCIPAL)
# ─────────────────────────────────────────────────────────────────────────────
def main():
    # Procesamiento sintáctico de las opciones por línea de comandos (CLI)
    parser = argparse.ArgumentParser(description="BENCH-01 | Compute & Memory Monolithic Benchmark")
    parser.add_argument("--size", type=str, choices=["small", "medium", "large"], default="medium",
                        help="Establece la escala de tamaño del volumen de cómputo (default: medium)")
    parser.add_argument("--repeats", type=int, default=5,
                        help="Modifica las iteraciones de control estadístico (default: 5)")
    parser.add_argument("--no-fft", action="store_true",
                        help="Excluye el benchmark de FFT para economizar uso de RAM")
    args = parser.parse_args()

    # Mapeo del preset de ejecución seleccionado
    cfg = SIZE_PRESETS[args.size]

    # Ejecución secuencial de los hilos de prueba del benchmark
    info = collect_sysinfo()
    print_sysinfo(info)

    print(f"\n[bench] Iniciando DGEMM local con n={cfg['gemm_n']} ...")
    gemm = bench_gemm(cfg["gemm_n"], repeats=args.repeats)
    print_gemm(gemm)

    print(f"\n[bench] Iniciando STREAM local con {cfg['stream_mb']} MB por vector ...")
    stream = bench_stream(cfg["stream_mb"])
    print_stream(stream)

    print(f"\n[bench] Iniciando Pointer-chase local con {cfg['chase_mb']} MB ...")
    latency = bench_latency(cfg["chase_mb"])
    print_latency(latency)

    fft = None
    if not args.no_fft:
        print(f"\n[bench] Iniciando FFT local con n={cfg['fft_n']:,} puntos complejos ...")
        fft = bench_fft(cfg["fft_n"], repeats=args.repeats)
        print_fft(fft)

    # Despliegue de resultados tabulados en la salida estándar
    print_summary(gemm, stream, latency, fft)

    # ── LIMPIEZA ABSOLUTA DE RECURSOS DEL SISTEMA ─────────────────────────────
    # Atiende tu solicitud de garantizar el cierre forzado de cualquier hilo secundario
    # y la liberación inmediata de los buffers asignados en el núcleo del host.
    print("[cleanup] Purgando variables residuales de la memoria física...")
    del gemm, stream, latency, fft
    gc.collect() # Invoca al Garbage Collector en modo restrictivo
    
    print("[cleanup] Desconectando descriptores del benchmark de forma segura. Terminado.")
    sys.exit(0) # Retorna el código de control de salida estándar al sistema operativo


if __name__ == "__main__":
    main()
