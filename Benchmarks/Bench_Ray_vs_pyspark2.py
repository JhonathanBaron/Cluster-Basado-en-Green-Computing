import time
import ray
from pyspark.sql import SparkSession
import math

print("="*60)
print(" BENCHMARK DE ACELERACIÓN (SPEEDUP): SECUENCIAL vs RAY vs SPARK")
print("="*60)

# ---------------------------------------------------------
# FUNCIÓN DE CARGA MATEMÁTICA (Simula visión artificial / cinemática)
# ---------------------------------------------------------
def calculo_pesado(iteraciones):
    resultado = 0
    # Un ciclo largo con operaciones trigonométricas para estresar la CPU
    for i in range(iteraciones):
        resultado += math.sin(i) * math.cos(i) 
    return resultado

# Parámetros de la prueba
iteraciones_por_tarea = 3_000_000 # Ajusta si tarda demasiado o muy poco
numero_de_tareas = 64             # Idealmente, igual o mayor al total de núcleos del clúster

# ---------------------------------------------------------
# 1. EJECUCIÓN SECUENCIAL (1 Solo Núcleo)
# ---------------------------------------------------------
print(f"\n[+] 1. Ejecutando {numero_de_tareas} tareas de forma secuencial...")
t0 = time.time()
# Ejecuta una tras otra en un solo hilo
[calculo_pesado(iteraciones_por_tarea) for _ in range(numero_de_tareas)]
tiempo_secuencial = time.time() - t0
print(f"    -> Finalizado en {tiempo_secuencial:.2f} segundos")

# ---------------------------------------------------------
# 2. EJECUCIÓN EN PARALELO CON RAY
# ---------------------------------------------------------
print(f"\n[+] 2. Ejecutando en paralelo con RAY...")
# Decorador para convertir la función en una tarea de Ray
@ray.remote
def calculo_pesado_ray(iteraciones):
    return calculo_pesado(iteraciones)

ray.init(ignore_reinit_error=True, log_to_driver=False)
t0 = time.time()
# Lanzamos todas las tareas al clúster simultáneamente
ray.get([calculo_pesado_ray.remote(iteraciones_por_tarea) for _ in range(numero_de_tareas)])
tiempo_ray = time.time() - t0
ray.shutdown()
print(f"    -> Finalizado en {tiempo_ray:.2f} segundos")

# ---------------------------------------------------------
# 3. EJECUCIÓN EN PARALELO CON PYSPARK
# ---------------------------------------------------------
# Damos un respiro a la RAM
time.sleep(3) 

print(f"\n[+] 3. Ejecutando en paralelo con PYSPARK...")
spark = SparkSession.builder \
    .appName("TelemetriaRoverSpark") \
    .master("spark://10.4.8.10:7077") \
    .getOrCreate()
sc = spark.sparkContext
sc.setLogLevel("ERROR")

t0 = time.time()
# Distribuimos un arreglo y aplicamos la función pesada a cada elemento
rdd = sc.parallelize(range(numero_de_tareas), numSlices=numero_de_tareas)
rdd.map(lambda x: calculo_pesado(iteraciones_por_tarea)).collect()
tiempo_spark = time.time() - t0
spark.stop()
print(f"    -> Finalizado en {tiempo_spark:.2f} segundos")

speedup_ray = tiempo_secuencial / tiempo_ray
speedup_spark = tiempo_secuencial / tiempo_spark

print("\n" + "="*60)
print(" RESULTADOS FINALES PARA ANÁLISIS:")
print("="*60)
print(f" - Tiempo Secuencial (1 Núcleo) : {tiempo_secuencial:.4f} segundos")
print(f" - Tiempo Paralelo (Ray)        : {tiempo_ray:.4f} segundos")
print(f" - Tiempo Paralelo (PySpark)    : {tiempo_spark:.4f} segundos")
print(f"")
print(f" - Aceleración Ray (Speedup)    : {speedup_ray:.2f}x")
print(f" - Aceleración PySpark (Speedup): {speedup_spark:.2f}x")
print("="*60)
