"""
================================================================================
EVALUACIÓN DE RENDIMIENTO DISTRIBUIDO (BENCHMARKING) VÍA RAY
================================================================================
Este script implementa una suite de pruebas de estrés computacional y de memoria
para evaluar la capacidad agregada de un clúster de computación distribuida.

Metodología:
  1. Cómputo Intensivo (DGEMM): Evalúa el rendimiento de la CPU en GFLOP/s.
  2. Memoria Secuencial (STREAM): Mide el ancho de banda de la RAM en GB/s.
  3. Memoria Aleatoria (Latencia): Evalúa el costo de los fallos de caché (cache misses).
  4. Procesamiento de Señales (FFT): Mide el rendimiento en transformadas rápidas de Fourier.
================================================================================
"""

import ray
import numpy as np
import time
import math
import psutil
from tabulate import tabulate

# ----------------------------------------------------------------------
# INICIALIZACIÓN DEL ORQUESTADOR DISTRIBUIDO
# ----------------------------------------------------------------------
# Conecta el script al nodo maestro (Head Node) de Ray. 
# 'auto' detecta la instancia activa en el sistema local o red.
ray.init(address='auto', ignore_reinit_error=True)

# ----------------------------------------------------------------------
# HIPERPARÁMETROS DEL BENCHMARK (Configuración de carga de trabajo)
# ----------------------------------------------------------------------
CONFIG = {
    "gemm_n": 4096,           # Dimensión N de las matrices cuadradas (N x N) para DGEMM.
    "stream_mb": 512,         # Huella de memoria (en Megabytes) por arreglo en el test STREAM.
    "fft_n": 2**24,           # Cantidad de puntos complejos para la Transformada de Fourier (~16.7 millones).
    "chase_mb": 64,           # Tamaño de la estructura de datos para forzar fallos de caché (Latencia).
    "repeats": 3,             # Número de iteraciones internas por tarea para obtener significancia estadística.
}

# ----------------------------------------------------------------------
# 1. DGEMM (Double-Precision General Matrix Multiplication)
# ----------------------------------------------------------------------
@ray.remote
def bench_gemm_worker(n: int, repeats: int) -> dict:
    """
    Ejecuta el benchmark DGEMM.
    La multiplicación de matrices cuadradas tiene una complejidad computacional de O(N^3).
    Se calculan los GFLOPs (Giga Floating-Point Operations per Second) basándose en 
    la fórmula: 2 * N^3 operaciones aritméticas.
    """
    flops_total = 2.0 * n**3
    
    # Fase de calentamiento (warmup) para inicializar cachés y estructuras de memoria
    A = np.random.rand(n, n).astype(np.float64)
    B = np.random.rand(n, n).astype(np.float64)
    _ = np.dot(A, B)
    
    times = []
    for _ in range(repeats):
        A = np.random.rand(n, n).astype(np.float64)
        B = np.random.rand(n, n).astype(np.float64)
        
        t0 = time.perf_counter() # Marca de tiempo inicial (alta precisión)
        C = np.dot(A, B)         # Multiplicación C = A * B
        t1 = time.perf_counter() # Marca de tiempo final
        
        times.append(t1 - t0)
        del C # Liberación explícita de memoria para evitar saturación (Out Of Memory)
        
    best_time = min(times) # Se toma el mejor tiempo para reflejar el pico de la CPU (Peak Performance)
    gflops = flops_total / best_time / 1e9
    return {"gflops_peak": gflops, "matrix_size": n}

# ----------------------------------------------------------------------
# 2. STREAM-like (Ancho de Banda de Memoria)
# ----------------------------------------------------------------------
@ray.remote
def bench_stream_worker(target_mb: float) -> dict:
    """
    Simula el benchmark STREAM estándar de la industria.
    Evalúa el ancho de banda de la memoria principal ejecutando 4 kernels vectoriales:
    Copy, Scale, Add y Triad. Se mide la transferencia de datos en GB/s.
    """
    s = 2.5 # Escalar arbitrario utilizado en los kernels Scale y Triad
    n = int(target_mb * 1e6 / 8) # Cantidad de elementos (float64 = 8 bytes) para alcanzar los MB objetivo
    
    A = np.random.rand(n).astype(np.float64)
    B = np.random.rand(n).astype(np.float64)
    C = np.random.rand(n).astype(np.float64)
    
    repeats = 5
    results = {}
    
    # Kernel COPY: C = A (Lectura de A, Escritura en C)
    times = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        C[:] = A
        t1 = time.perf_counter()
        times.append(t1 - t0)
    results["copy_gbs"] = (2 * n * 8) / np.median(times) / 1e9
    
    # Kernel SCALE: B = s * C (Lectura de C, Escritura en B)
    times = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        B[:] = s * C
        t1 = time.perf_counter()
        times.append(t1 - t0)
    results["scale_gbs"] = (2 * n * 8) / np.median(times) / 1e9
    
    # Kernel ADD: C = A + B (Lecturas de A y B, Escritura en C)
    times = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        C[:] = A + B
        t1 = time.perf_counter()
        times.append(t1 - t0)
    results["add_gbs"] = (3 * n * 8) / np.median(times) / 1e9
    
    # Kernel TRIAD: A = B + s * C (Lecturas de B y C, Escritura en A) - Operación más compleja
    times = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        A[:] = B + s * C
        t1 = time.perf_counter()
        times.append(t1 - t0)
    results["triad_gbs"] = (3 * n * 8) / np.median(times) / 1e9
    
    results["array_mb"] = target_mb
    return results

# ----------------------------------------------------------------------
# 3. LATENCIA DE MEMORIA (Pointer-Chasing)
# ----------------------------------------------------------------------
@ray.remote
def bench_latency_worker(chase_mb: float) -> dict:
    """
    Mide el tiempo de respuesta puro de la memoria RAM.
    Se utiliza la técnica 'Pointer-Chasing', la cual lee direcciones de memoria 
    aleatorias saltándose las líneas de caché L1/L2/L3 (stride > 64 bytes) para
    forzar la lectura directa desde la RAM (Cache Misses).
    """
    stride = 64 # Tamaño estándar de una línea de caché (Cache Line) en x86
    n_int = max((chase_mb * 1024 * 1024) // 8, 1024)
    
    # Construcción de un arreglo circular con punteros aleatorizados
    indices = np.arange(n_int, dtype=np.int64)
    np.random.shuffle(indices)
    chain = np.zeros(n_int, dtype=np.int64)
    
    for i in range(n_int - 1):
        chain[indices[i]] = indices[i + 1]
    chain[indices[-1]] = indices[0]
    
    steps = min(2_000_000, n_int * 5) # Limitar la cantidad de saltos para no prolongar el test excesivamente
    ptr = int(chain[0])
    
    # Recorrido de la cadena de punteros
    t0 = time.perf_counter()
    for _ in range(steps):
        ptr = int(chain[ptr])
    t1 = time.perf_counter()
    
    latency_ns = (t1 - t0) / steps * 1e9 # Cálculo de latencia promedio por salto en nanosegundos
    return {"latency_ns": latency_ns, "array_mb": chase_mb}

# ----------------------------------------------------------------------
# 4. FAST FOURIER TRANSFORM (FFT 1-D)
# ----------------------------------------------------------------------
@ray.remote
def bench_fft_worker(n: int, repeats: int) -> dict:
    """
    Benchmark matemático: Transformada Rápida de Fourier en 1 Dimensión.
    Complejidad algorítmica: O(N * log2(N)).
    La convención estándar asume 5 * N * log2(N) operaciones de punto flotante.
    """
    flops = 5 * n * math.log2(n)
    
    # Generación de una señal sintética de números complejos
    x = np.random.rand(n).astype(np.float64) + 1j * np.random.rand(n).astype(np.float64)
    
    np.fft.fft(x) # Warmup
    
    times = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        np.fft.fft(x)
        t1 = time.perf_counter()
        times.append(t1 - t0)
        
    best_time = min(times)
    gflops = flops / best_time / 1e9
    return {"gflops_peak": gflops, "n_points": n}

# ----------------------------------------------------------------------
# ORQUESTACIÓN PRINCIPAL Y AGREGACIÓN DE RESULTADOS
# ----------------------------------------------------------------------
def main():
    print("Iniciando suite de Benchmarking Distribuido (Ray)...")
    print(f"Parámetros configurados: {CONFIG}\n")
    
    # Obtención de recursos de hardware agregados en la red Ray
    total_cpus = int(ray.cluster_resources().get("CPU", 1))
    # Oversubscription: Se lanzan 2 tareas por hilo lógico para asegurar el uso al 100%
    num_tasks = total_cpus * 2  
    print(f"Recursos lógicos detectados: {total_cpus} CPUs. Instanciando {num_tasks} procesos distribuidos.\n")
    
    # ----- FASE 1: DGEMM -----
    print("[1/4] Fase de Cómputo (DGEMM)...")
    gemm_refs = [bench_gemm_worker.remote(CONFIG["gemm_n"], CONFIG["repeats"]) for _ in range(num_tasks)]
    gemm_results = ray.get(gemm_refs)
    gemm_aggr = sum(r["gflops_peak"] for r in gemm_results) # Agregación sumatoria (capacidad total del clúster)
    gemm_individuals = [r["gflops_peak"] for r in gemm_results]
    
    # ----- FASE 2: STREAM -----
    print("[2/4] Fase de Ancho de Banda (STREAM)...")
    stream_refs = [bench_stream_worker.remote(CONFIG["stream_mb"]) for _ in range(num_tasks)]
    stream_results = ray.get(stream_refs)
    stream_aggr = {
        "copy": sum(r["copy_gbs"] for r in stream_results),
        "scale": sum(r["scale_gbs"] for r in stream_results),
        "add": sum(r["add_gbs"] for r in stream_results),
        "triad": sum(r["triad_gbs"] for r in stream_results),
    }
    stream_sample = [(r["copy_gbs"], r["scale_gbs"], r["add_gbs"], r["triad_gbs"]) for r in stream_results[:5]]
    
    # ----- FASE 3: LATENCIA -----
    print("[3/4] Fase de Latencia de RAM (Pointer-Chasing)...")
    latency_refs = [bench_latency_worker.remote(CONFIG["chase_mb"]) for _ in range(num_tasks)]
    latency_results = ray.get(latency_refs)
    avg_latency = np.mean([r["latency_ns"] for r in latency_results]) # Agregación en promedio (la latencia no se suma)
    min_latency = min(r["latency_ns"] for r in latency_results)
    max_latency = max(r["latency_ns"] for r in latency_results)
    
    # ----- FASE 4: FFT -----
    print("[4/4] Fase de Procesamiento de Señales (FFT)...")
    fft_refs = [bench_fft_worker.remote(CONFIG["fft_n"], CONFIG["repeats"]) for _ in range(num_tasks)]
    fft_results = ray.get(fft_refs)
    fft_aggr = sum(r["gflops_peak"] for r in fft_results)
    fft_individuals = [r["gflops_peak"] for r in fft_results]
    
    # ------------------------------------------------------------------
    # GENERACIÓN DE REPORTE ACADÉMICO
    # ------------------------------------------------------------------
    print("\n" + "="*80)
    print("REPORTE DE RENDIMIENTO AGREGADO (SISTEMA DISTRIBUIDO)")
    print("="*80)
    
    tabla_resumen = [
        ["Métrica de Evaluación", "Rendimiento Agregado", "Unidad", "Descripción Metodológica"],
        ["DGEMM (Pico Computacional)", f"{gemm_aggr:.2f}", "GFLOP/s", "Suma del rendimiento aritmético (Nodos)"],
        ["STREAM Copy", f"{stream_aggr['copy']:.2f}", "GB/s", "Suma de transferencia RAM (R/W)"],
        ["STREAM Scale", f"{stream_aggr['scale']:.2f}", "GB/s", "Suma de transferencia RAM (Escalada)"],
        ["STREAM Add", f"{stream_aggr['add']:.2f}", "GB/s", "Suma de transferencia RAM (Adición)"],
        ["STREAM Triad", f"{stream_aggr['triad']:.2f}", "GB/s", "Suma de transferencia RAM (Vectorial Compleja)"],
        ["Latencia de Memoria", f"{avg_latency:.1f}", "ns", "Tiempo promedio de acceso a memoria no cacheada"],
        ["Transformada de Fourier", f"{fft_aggr:.2f}", "GFLOP/s", "Suma del procesamiento de señales complejas"],
    ]
    print(tabulate(tabla_resumen, headers="firstrow", tablefmt="github"))
    
    print("\n" + "-"*80)
    print("MUESTREO ESTADÍSTICO DE WORKERS (5 Primeras Tareas)")
    print("-"*80)
    print(f"Dispersión DGEMM (GFLOPs): {[round(x,1) for x in gemm_individuals[:5]]}")
    for i, vals in enumerate(stream_sample):
        print(f"  Worker {i+1} STREAM (GB/s): Copy={vals[0]:.2f}, Scale={vals[1]:.2f}, Add={vals[2]:.2f}, Triad={vals[3]:.2f}")
    print(f"Rango de Latencia: Mínimo={min_latency:.1f} ns, Máximo={max_latency:.1f} ns")
    print(f"Dispersión FFT (GFLOPs): {[round(x,2) for x in fft_individuals[:5]]}")
    
    print("\n" + "="*80)
    print("CONCLUSIONES DEL TEST")
    print("="*80)
    print("El diseño arquitectónico de este clúster basa su fortaleza computacional en la escalabilidad horizontal.")
    print("Mientras que la latencia (ns) permanece constante a los límites físicos del hardware individual (e-waste),")
    print("las capacidades de Ancho de Banda (GB/s) y Cómputo (GFLOP/s) exhiben un crecimiento sumatorio.")
    
    # ------------------------------------------------------------------
    # FINALIZACIÓN LIMPIA Y LIBERACIÓN DE RECURSOS
    # ------------------------------------------------------------------
    print("\nFinalizando procesos y desconectando del clúster Ray...")
    ray.shutdown()
    print("Orquestador apagado exitosamente.")

if __name__ == "__main__":
    main()
