## Resultados de Benchmark: Comparación con Arquitecturas Monolíticas

Para evaluar el rendimiento real del clúster frente a equipos individuales (arquitecturas monolíticas), se ejecutó la suite [`bench01_monolithic.py`](https://github.com/JhonathanBaron/Cluster-Basado-en-Green-Computing/blob/73612ae7a4956ad9814142d23e811e316145bb4f/Benchmarks/bench01_monolithic.py). en cada nodo y en el clúster completo gestionado con **Ray**. Las pruebas miden:

- **GFLOPs sostenidos** (operaciones de punto flotante) mediante multiplicación de matrices DGEMM.
- **Ancho de banda de memoria** (Triad, Copy) y **latencia** (pointer‑chase).
- **Rendimiento FFT** como métrica adicional de cómputo.

> Los valores del clúster se presentan en dos formas:  
> - **Teórico / Sin overhead**: suma de la potencia bruta de todos los nodos.  
> - **Real / Wall‑clock**: rendimiento medido durante una ejecución distribuida (con sobrecarga de red y scheduling).

---

### 1. Rendimiento de Cómputo (Fuerza Bruta de CPU)

| Entidad / Máquina                          | CPU (Núcleos/Hilos)      | GFLOPs (Pico) | GFLOPs (Mediana) | GFLOPs FFT |
|--------------------------------------------|--------------------------|---------------|------------------|------------|
| **Ray Cluster (Teórico / Sin overhead)**   | Varios (suma total)      | 587.58        | –                | –          |
| `cluster0`                                 | i5‑4590S (4C/4T)         | 134.89        | 134.19           | 1.775      |
| `DESKTOP-TK3VOIK`                          | i5‑1035G1 (4C/8T)        | 121.05        | 120.79           | 2.424      |
| **Ray Cluster (Real / Wall‑clock)**        | Varios (red activa)      | 86.60         | –                | 2.601      |
| `DESKTOP-AJJ2N9U`                          | i5‑1035G1 (4C/8T)        | 78.55         | 71.24            | 1.499      |
| `DESKTOP-HEJLCP1`                          | Ryzen 5 3500U (4C/8T)    | 67.82         | 63.12            | 2.201      |
| `cluster1`                                 | i7‑3612QM (4C/8T)        | 33.65         | 31.86            | 1.653      |

> **Observación**: La suma teórica supera los **587 GFLOP/s**, pero la sobrecarga de comunicación en el clúster reduce el rendimiento efectivo a ~86,6 GFLOP/s. Aun así, este valor es superior al de cualquier portátil individual de la lista, validando la utilidad del sistema para cargas de trabajo paralelizables.

---

### 2. Rendimiento de Memoria (Ancho de Banda y Latencia)

Una de las grandes ventajas de los clústeres **green computing** es **sumar el ancho de banda de memoria** de todos los nodos, ya que cada uno tiene su propio controlador de RAM.

| Entidad / Máquina          | Ancho de Banda Triad (GB/s) | Ancho de Banda Copy (GB/s) | Latencia RAM Media (ns) |
|----------------------------|-----------------------------|----------------------------|-------------------------|
| **Ray Cluster (Agregado)** | **54.32**                   | –                          | 280.4                   |
| `DESKTOP-HEJLCP1`          | 3.47                        | 19.85                      | 279.6                   |
| `DESKTOP-TK3VOIK`          | 3.75                        | 19.88                      | 240.2                   |
| `cluster0`                 | 6.10                        | 18.36                      | 223.4                   |
| `cluster1`                 | 5.85                        | 16.92                      | 272.9                   |
| `DESKTOP-AJJ2N9U`          | 1.84                        | 7.21                       | 267.7                   |

> **Conclusión**: Mientras una placa individual difícilmente supera los 6 GB/s en el test Triad, el clúster agregado alcanza **54,32 GB/s**. Para tareas de procesamiento por lotes (donde cada nodo trabaja sobre sus propios datos), esta capacidad combinada es una ventaja decisiva.

---

### 3. Representación Gráfica (GFLOPs Sostenidos)

Para una visualización rápida, aquí está la comparación de rendimiento DGEMM (valores pico) en formato ASCII:

```plaintext
RENDIMIENTO DGEMM (GFLOPs)
==============================================================
Ray Cluster (Teórico)  | ██████████████████████████████ 587.58
cluster0               | ███████ 134.89
DESKTOP-TK3VOIK        | ██████ 121.05
Ray Cluster (Real)     | ████ 86.60
DESKTOP-AJJ2N9U        | ████ 78.55
DESKTOP-HEJLCP1        | ███ 67.82
cluster1 (i7‑3612QM)   | █ 33.65
