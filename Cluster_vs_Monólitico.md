## Resultados de Benchmark: Rendimiento del Clúster Green Computing

A continuación se presentan los resultados de las pruebas de rendimiento realizadas al clúster. Se comparan dos tipos de ejecución:

- **Monolítico**: un solo nodo trabajando solo (línea base).
- **Clúster**: todos los nodos trabajando juntos mediante **Ray**.

Los scripts utilizados están en el repositorio:

- [`bench01_monolithic.py`](https://github.com/JhonathanBaron/Cluster-Basado-en-Green-Computing/blob/96baf8fd1e68411b84226c5fce9a7903a6e35328/Benchmarks/bench01_monolithic.py) → mide el rendimiento de un nodo individual.
- [`bench01_Cluster.py`](https://github.com/JhonathanBaron/Cluster-Basado-en-Green-Computing/blob/0fff2927770769228145e47afa2bee76a10a7001/Benchmarks/bench01_Cluster.py) → mide el rendimiento agregado de todo el clúster.

---

### 1. ¿Qué significan estas métricas?

- **GFLOP/s** (Giga Floating Point Operations per second):  
  Capacidad de hacer cálculos matemáticos (multiplicaciones, sumas) por segundo. A mayor número, más rápido se procesan simulaciones, matrices, etc.

- **GB/s** (Gigabytes por segundo):  
  Velocidad a la que la CPU lee o escribe datos en la memoria RAM. Importante para manejar grandes volúmenes de datos (vídeo, bases de datos, machine learning).

- **Latencia (ns)**:  
  Tiempo que tarda la memoria en responder a una petición aleatoria. A menor latencia, más rápida es la reacción del sistema.

---

### 2. Resultados obtenidos

#### Cómputo (DGEMM – multiplicación de matrices)

| Tipo de ejecución | GFLOP/s (agregado) | ¿Qué significa? |
|------------------|-------------------|------------------|
| **Clúster** (todos los nodos) | **895.4** | El clúster puede hacer 895 mil millones de operaciones matemáticas por segundo. |
| Monolítico (nodo más rápido) | 134.9 | Un solo nodo potente se queda en 134.9 GFLOP/s. |

> **Conclusión práctica**: El clúster es **6.6 veces más potente** en cálculos pesados que el mejor nodo por separado. Ideal para simulaciones científicas, análisis de datos masivos o entrenamiento de modelos de IA (si el problema se puede dividir).

#### Memoria (STREAM Triad – operación lectura+escritura)

| Tipo de ejecución | GB/s (agregado) | ¿Qué significa? |
|------------------|----------------|------------------|
| **Clúster** | **99.5** | El clúster mueve 99.5 GB por segundo entre CPU y RAM. |
| Monolítico (nodo típico) | ~5 | Un nodo solo apenas alcanza 5 GB/s. |

> **Conclusión práctica**: El clúster es **20 veces más rápido** moviendo datos. Esto es clave para procesar **grandes archivos, bases de datos en memoria, o flujos de vídeo** donde el cuello de botella suele ser la RAM.

#### Latencia de memoria

| Tipo de ejecución | Latencia media (ns) | Interpretación |
|------------------|---------------------|----------------|
| Clúster | 531 ns | Un poco alta debido a que algunos nodos usaron memoria virtual (swap) por falta de RAM. |
| Monolítico (normal) | 220‑280 ns | Latencia típica de RAM DDR3/DDR4. |

> **A tener en cuenta**: Para aplicaciones que acceden a memoria de forma aleatoria (bases de datos, listas enlazadas), una latencia baja es importante. Si se libera RAM en los nodos (cerrar programas pesados), la latencia del clúster mejorará.

---

### 3. ¿Para qué sirve este rendimiento en la práctica?

Con estos números, tu clúster **Green Computing** es especialmente bueno para:

| Tipo de tarea | Ejemplo concreto | Por qué funciona bien |
|---------------|------------------|----------------------|
| **Procesamiento por lotes** | Limpiar y transformar 1 TB de datos CSV | Cada nodo procesa un trozo independiente → el ancho de banda agregado acelera la lectura/escritura. |
| **Machine Learning con datos particionados** | Entrenar 100 modelos pequeños en paralelo | No hay intercambio constante de datos entre nodos → se aprovecha la suma de GFLOP/s. |
| **Renderizado o simulaciones** | Calcular trayectorias de partículas en paralelo | Cada worker calcula su parte sin depender de los demás. |
| **Servidor de archivos o caché distribuida** | Almacenar objetos en RAM entre nodos | La suma de GB/s permite servir contenido muy rápido a muchos clientes. |

> **Limitación**: Para una sola tarea que requiera comunicación constante entre nodos (ej. multiplicar dos matrices enormes de forma distribuida), la sobrecarga de red reduce la eficiencia. En ese caso, un nodo individual potente puede ser mejor. Pero para el 80% de las tareas académicas de procesamiento de datos, el clúster gana.

---

### 4. Resumen práctico

- ✅ **Ventaja principal**: Suma de ancho de banda de memoria (99.5 GB/s) → ideal para mover grandes volúmenes de datos.
- ✅ **Cómputo agregado**: 895 GFLOP/s → 6.6 veces más que un nodo solo.
- ⚠️ **Latencia** mejorable si se libera RAM en todos los nodos.
- 💡 **Casos de uso recomendados**: Procesamiento por lotes, entrenamiento paralelo de modelos pequeños, caché distribuida, simulaciones independientes.

*Los números son reales, medidos en el clúster con 72 CPUs lógicas. Puedes reproducir las pruebas ejecutando los scripts enlazados.*

#### 📊 Comparativa visual de GFLOPs (escala lineal)

```plaintext
RENDIMIENTO DGEMM (GFLOPs)
======================================================================
Clúster Distribuido (Suma Real)      | ██████████████████████████████████████████ 895.39
cluster0 (i5-4590S)                  | ██████ 134.89
DESKTOP-TK3VOIK (i5-1035G1)          | █████ 121.05
DESKTOP-AJJ2N9U (i5-1035G1)          | ███ 78.55
DESKTOP-HEJLCP1 (Ryzen 5)            | ██ 67.82
cluster1 (i7-3612QM)                 | █ 33.65
