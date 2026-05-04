
Para garantizar el manejo, procesamiento y análisis eficiente de los flujos masivos de datos provenientes de los vehículos teleoperados, la primera fase del diseño consistió en una revisión bibliográfica de las plataformas de computación distribuida existentes. Los criterios de selección establecidos incluyeron:

- compatibilidad con sistemas operativos basados en Linux,
- una curva de aprendizaje que permitiera el desarrollo ágil,
- la capacidad de integración con librerías de visión artificial y machine learning,
- el lenguaje de programación nativo y
- la eficiencia computacional (fundamental bajo el paradigma de Green Computing).

En la **Tabla** se presenta la matriz comparativa de los principales frameworks evaluados.

**Tabla. Comparativa de plataformas para procesamiento distribuido y Big Data.**

| Framework | Lenguaje Principal | Enfoque de Procesamiento | Curva de Aprendizaje | Principales usos | Documentación |
|-----------|-------------------|--------------------------|----------------------|------------------|---------------|
| OpenMPI | C / C++ / Fortran | Paso de mensajes a bajo nivel | Alta | Simulaciones científicas complejas, modelado climático, dinámica molecular y renderizado 3D | [https://www.open-mpi.org/](https://www.open-mpi.org/) |
| Dask | Python | Paralelización de arreglos (NumPy) y DataFrames (Pandas) | Baja | Procesamiento de Big Data, aprendizaje automático a gran escala y simulaciones científicas complejas | [https://dask.org/](https://dask.org/) |
| PySpark | Python / Scala / Java | Datos tabulares y procesamiento por lotes (Batch) | Media - Alta | Bases de datos relacionales y análisis estadístico | [https://spark.apache.org/](https://spark.apache.org/) |
| Ray | Python / C++ / Java | Modelo de computación distribuida flexible que rompe con el esquema tradicional de "paso de mensajes" o "MapReduce" | Baja - Media | Sobresaliente para Inteligencia Artificial, visión por computador y Reinforcement Learning. | [https://docs.ray.io/](https://docs.ray.io/) |


Tras la evaluación, las alternativas más viables fueron Apache PySpark y Ray, debido a su compatibilidad con Python (un lenguaje bastante técnico y sencillo) además de su facilidad de instalación. Sin embargo, procesar la telemetría y datos del rover requiere ejecutar múltiples tareas pequeñas de forma concurrente y casi instantánea (visión artificial, lectura de sensores, control de motores y lectura del LiDAR) para lograr una teleoperación fluida.

Al analizar ambas opciones, se encontró una diferencia fundamental en su funcionamiento:

- **Apache PySpark** está diseñado para procesar bloques masivos de datos históricos de una sola vez (procesamiento por lotes o Batch). Esto genera una sobrecarga computacional (conocida como *overhead*), es decir, el sistema invierte un tiempo considerable de preparación antes de ejecutar cada tarea pequeña, lo cual introduce retrasos inaceptables para el control en tiempo real.
- **Ray**, por el contrario, utiliza un modelo basado en **"actores"** (*Actors*). Los actores son entidades de software que se mantienen activas en la memoria RAM, listas para ejecutar funciones bajo demanda de manera asíncrona. Esto elimina los tiempos de preparación repetitivos, reduciendo drásticamente la latencia y optimizando el uso del procesador.

Para justificar esta selección con datos empíricos, se diseñaron pruebas de rendimiento (*benchmarks*) enfocadas en medir el tiempo de respuesta y el consumo de recursos de ambas herramientas en el clúster.

Para llevar a cabo estas métricas, se desarrollaron scripts de evaluación en Python, disponibles en el repositorio del proyecto ([`Benchmarks/`](https://github.com/JhonathanBaron/Cluster-Basado-en-Green-Computing/tree/main/Benchmarks)), ejecutados desde el nodo maestro, los cuales simularon las cargas de trabajo características de la telemetría del rover. La metodología de evaluación se dividió en tres escenarios controlados:

1. **Prueba de latencia (overhead):** se enviaron 10 000 micro-tareas vacías para medir exclusivamente el tiempo de comunicación y preparación del entorno.
2. **Monitorización de recursos en estado de reposo:** utilizando la librería `psutil` para capturar la huella de memoria RAM pasiva de cada framework.
3. **Prueba de estrés matemático intensivo:** distribuyendo millones de operaciones a través de todos los núcleos disponibles en el clúster para evaluar la capacidad de procesamiento en paralelo real.

Todas las ejecuciones se realizaron en igualdad de condiciones, aislando la red local de procesos externos para garantizar la fidelidad de los datos.

## Resultados y Justificación Técnica

Los resultados obtenidos consolidaron la decisión arquitectónica basándose en tres ejes técnicos fundamentales:

### 1. Latencia y Tiempo de Inicialización

La preparación del entorno en Ray tomó apenas **0.0599 segundos**, siendo significativamente más ágil que PySpark (**0.3144 segundos**). Asimismo, al evaluar la latencia o *overhead* (el tiempo que tarda el sistema en gestionar 10 000 tareas minúsculas sin carga matemática), Ray demostró un desempeño superior al ejecutar el bloque en **3.58 segundos** frente a los **3.87 segundos** de PySpark. Para el entorno de teleoperación del rover, donde se transmiten flujos continuos de pequeñas instrucciones, esta diferencia en la reducción de latencia es crítica para evitar un desfase temporal entre el operador y la respuesta de la máquina; en términos simples se trata de buscar la máxima eficiencia en los tiempos de comunicación entre todos los involucrados, nodo maestro-nodos worker-rover.

<div align="center">
  <img src="https://github.com/JhonathanBaron/Cluster-Basado-en-Green-Computing/blob/0bee51a72394c90eeb11015c2dd1299871f52849/Imagenes/bench1.png" width="50%" alt="Gráfica comparativa del tiempo de ejecución de 10 000 micro-tareas vacías (overhead) entre Ray y PySpark">
  <br>
  <em>Figura 1. Tiempo de ejecución para 10 000 micro-tareas (Overhead).</em>
</div>

### 2. Eficiencia de Recursos (Green Computing)

Un pilar fundamental de la topología desarrollada es la optimización de hardware con recursos limitados. En estado de reposo, el motor de PySpark exigió **17.64 MB** de memoria RAM en el sistema debido a la necesidad de mantener activa la Máquina Virtual de Java (JVM). Por el contrario, la arquitectura de Ray operó con un consumo base casi imperceptible de **0.46 MB**. Esta drástica reducción permite que los nodos trabajadores destinen la totalidad de su memoria al procesamiento real de visión artificial y no al mantenimiento del entorno.

<div align="center">
  <img src="[../Imagenes/bench2.png](https://github.com/JhonathanBaron/Cluster-Basado-en-Green-Computing/blob/8dd75fae020839d97d9e6e7b92a220fa5bbd572c/Imagenes/bench2.png)" width="50%" alt="Gráfica comparativa del consumo de memoria RAM en estado de reposo: Ray (0.46 MB) frente a PySpark (17.64 MB)">
  <br>
  <em>Figura 2. Consumo de memoria RAM base de los entornos de procesamiento.</em>
</div>

### 3. Evaluación de Aceleración Computacional (Speedup) y Ley de Amdahl

Para validar definitivamente la viabilidad de la arquitectura distribuida frente a un sistema tradicional, se ejecutó una prueba de estrés de Unidad de Procesamiento Central (CPU). El experimento consistió en procesar 64 tareas de alta complejidad matemática, simulando la carga computacional de la cinemática inversa (cálculos para el movimiento de las articulaciones) y los filtros de visión artificial del rover; claro está, utilizando modelos solo de ejemplo.

El análisis de rendimiento se fundamentó en dos conceptos clave de la computación paralela:

- **Aceleración (Speedup):** es un indicador que mide cuánto más rápido es un sistema paralelo frente a uno de un solo núcleo. Se calcula dividiendo el tiempo secuencial entre el tiempo paralelo.
- **Ley de Amdahl:** esta ley establece que la velocidad de un sistema distribuido no mejora infinitamente al añadir más computadores, ya que siempre habrá una parte del código (como la gestión de la red o el arranque del programa) que no se puede paralizar y debe ejecutarse en serie.

Al ejecutar la carga de prueba en un único núcleo (procesamiento secuencial), simulando un computador convencional, el sistema requirió **45.31 segundos** para finalizar. Posteriormente, al distribuir la misma carga utilizando toda la potencia del clúster (procesamiento paralelo), los tiempos se redujeron drásticamente: Ray finalizó en **5.78 segundos** y PySpark en **5.71 segundos**.

<div align="center">
  <img src="https://github.com/JhonathanBaron/Cluster-Basado-en-Green-Computing/blob/8dd75fae020839d97d9e6e7b92a220fa5bbd572c/Imagenes/tiempo.png" width="50%" alt="Gráfica comparativa de la prueba de estrés de CPU: tiempo secuencial (45.31 s) vs Ray (5.78 s) vs PySpark (5.71 s), con factor de aceleración">
  <br>
  <em>Figura 3. Prueba de estrés de CPU: Comparativa de tiempos de ejecución y factor de aceleración.</em>
</div>

Estos resultados arrojan un factor de aceleración (*Speedup*) de **7.84x** para Ray y **7.92x** para PySpark. Alcanzar una aceleración cercana a **8x** demuestra una alta eficiencia en la orquestación de la red, indicando que la sobrecarga de comunicación entre el nodo maestro y los esclavos es mínima.

## Conclusión y Decisión Final

Si bien PySpark presentó una ventaja marginal en la prueba de estrés de CPU (siendo 0.06 segundos más rápido al procesar grandes lotes matemáticos), esta mínima diferencia en fuerza bruta **no compensa sus deficiencias en los otros frentes críticos**. Al ponderar el mínimo consumo de memoria, la baja latencia de inicialización y la versatilidad de su modelo de actores, **Ray se consolida unánimemente como la plataforma idónea** para cumplir con los requerimientos operativos y energéticos del proyecto.

---

## Scripts de Referencia

Los scripts utilizados para ejecutar estas pruebas de rendimiento se encuentran en el repositorio del proyecto, en la carpeta [`Benchmarks/`](https://github.com/JhonathanBaron/Cluster-Basado-en-Green-Computing/tree/main/Benchmarks):

- [`Bench_Ray_vs_pyspark1.py`](https://github.com/JhonathanBaron/Cluster-Basado-en-Green-Computing/blob/main/Benchmarks/Bench_Ray_vs_pyspark1.py) – Prueba de overhead (10 000 micro-tareas vacías).
- [`Bench_Ray_vs_pyspark2.py`](https://github.com/JhonathanBaron/Cluster-Basado-en-Green-Computing/blob/main/Benchmarks/Bench_Ray_vs_pyspark2.py) – Prueba de estrés matemático intensivo y monitorización de recursos.
