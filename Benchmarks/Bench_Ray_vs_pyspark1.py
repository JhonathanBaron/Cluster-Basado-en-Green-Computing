import time
import psutil
import ray
from pyspark.sql import SparkSession
import os

def get_system_ram_mb():
    """Retorna la RAM usada del sistema en MB"""
    return psutil.virtual_memory().used / (1024 * 1024)

print("="*50)
print("INICIANDO BENCHMARKS: RAY vs PYSPARK")
print("="*50)

resultados = {}

# ---------------------------------------------------------
# 1. PRUEBAS CON RAY
# ---------------------------------------------------------
print("\n[+] Iniciando pruebas con Ray...")
ram_antes_ray = get_system_ram_mb()

# Prueba de tiempo de inicialización
t_inicio_ray = time.time()
ray.init(ignore_reinit_error=True, log_to_driver=False)
resultados['ray_startup_time'] = time.time() - t_inicio_ray
resultados['ray_ram_usada'] = get_system_ram_mb() - ram_antes_ray

@ray.remote
def tarea_vacia(x):
    return x

@ray.remote
def tarea_pesada(x):
    # Simulamos carga matemática de procesamiento
    return x ** 2.5

# Prueba 1: Overhead (10,000 tareas minúsculas)
print("    -> Ejecutando prueba de latencia (Overhead) en Ray...")
t0 = time.time()
ray.get([tarea_vacia.remote(i) for i in range(10000)])
resultados['ray_overhead_time'] = time.time() - t0

# Prueba 2: Volumen de datos (Procesar 1,000,000 de datos en lotes)
print("    -> Ejecutando prueba de volumen de datos en Ray...")
# Usamos lotes para no desbordar la memoria del nodo maestro gestionando un millón de promesas
lotes = 100
tamaño_lote = 10000
t0 = time.time()
for _ in range(lotes):
    ray.get([tarea_pesada.remote(i) for i in range(tamaño_lote)])
resultados['ray_volume_time'] = time.time() - t0

ray.shutdown()

# ---------------------------------------------------------
# 2. PRUEBAS CON PYSPARK
# ---------------------------------------------------------
# Pausa breve para liberar memoria del SO
time.sleep(3) 

print("\n[+] Iniciando pruebas con PySpark...")
ram_antes_spark = get_system_ram_mb()

# Prueba de tiempo de inicialización
t_inicio_spark = time.time()
spark = SparkSession.builder \
    .appName("TelemetriaRoverSpark") \
    .master("spark://10.4.8.10:7077") \
    .getOrCreate()
sc = spark.sparkContext
sc.setLogLevel("ERROR")
resultados['spark_startup_time'] = time.time() - t_inicio_spark
resultados['spark_ram_usada'] = get_system_ram_mb() - ram_antes_spark

# Prueba 1: Overhead (10,000 tareas minúsculas)
print("    -> Ejecutando prueba de latencia (Overhead) en Spark...")
t0 = time.time()
rdd_vacio = sc.parallelize(range(10000), numSlices=sc.defaultParallelism)
rdd_vacio.map(lambda x: x).collect()
resultados['spark_overhead_time'] = time.time() - t0

# Prueba 2: Volumen de datos (Procesar 1,000,000 de datos)
print("    -> Ejecutando prueba de volumen de datos en Spark...")
t0 = time.time()
rdd_pesado = sc.parallelize(range(1000000), numSlices=sc.defaultParallelism * 4)
rdd_pesado.map(lambda x: x ** 2.5).count() # Action que fuerza el computo
resultados['spark_volume_time'] = time.time() - t0

spark.stop()

# ---------------------------------------------------------
# 3. IMPRESIÓN DE RESULTADOS (COPIA ESTO Y PÁSAMELO)
# ---------------------------------------------------------
print("\n" + "="*50)
print(" RESULTADOS FINALES PARA ANÁLISIS (COPIAR ESTO):")
print("="*50)
print(f"RAY:")
print(f" - Tiempo Inicialización : {resultados['ray_startup_time']:.4f} segundos")
print(f" - Latencia (Overhead)   : {resultados['ray_overhead_time']:.4f} segundos")
print(f" - Volumen de Datos      : {resultados['ray_volume_time']:.4f} segundos")
print(f" - RAM Base Consumida    : {resultados['ray_ram_usada']:.2f} MB")

print(f"\nPYSPARK:")
print(f" - Tiempo Inicialización : {resultados['spark_startup_time']:.4f} segundos")
print(f" - Latencia (Overhead)   : {resultados['spark_overhead_time']:.4f} segundos")
print(f" - Volumen de Datos      : {resultados['spark_volume_time']:.4f} segundos")
print(f" - RAM Base Consumida    : {resultados['spark_ram_usada']:.2f} MB")
print("="*50)
