# Conceptos Previos 🐱‍🐉
Para empezar, se debe tener claridad en varios aspectos para embarcarse en el reto de implementar un clúster, 
primeramente, se debe comprender que un clúster Beowulf es un conjunto de computadoras interconectadas entre sí 
en una red local; esto para que trabajen en conjunto como si fueran una sola unidad de procesamiento, además se 
caracterizan por estar construidas con hardware convencional y basadas en software libre.
<div align="center">
  <img src="https://raw.githubusercontent.com/JhonathanBaron/Cluster-Basado-en-Green-Computing/main/Imagenes/cluster_v2.jpeg" width="80%" alt="Proceso de acondicionamiento de placas HP Probook 4420s">
  <br>
  <em>Figura 1: Acondicionamiento de las Placas base reutilizadas. Se aprecia la limpieza y preparación antes del montaje en el rack modular.</em>
</div>
# Usos de un clúster Beowulf🐱‍💻
Las aplicaciones de esta tecnología son muy variadas, puesto que permiten resolver problemas que requieren gran 
capacidad como recursos de cómputo; por lo cual son útiles en: 

•	Simulaciones científicas. 
•	Renderizado de gráficos.
•	Procesamiento de datos masivos.
•	Inteligencia artificial y machine learning.
•	Educación e investigación en cómputo paralelo.
•	Prestación de servicios web.

Claramente cada una de estas aplicaciones requiere un hardware específico para desempeñar mejor las tareas, 
debido a que el principio de un clúster es dividir un trabajo grande en pequeñas tareas que se distribuyen en
varios nodos (computadores) para ser procesadas simultáneamente.

# ¿Qué es el Big Data?
Este término refiere al manejo de grandes conjuntos de datos. A medida que los datos se vuelven más masivos, se hacen más complejos para trabajar con herramientas convencionales, lo que crea la necesidad de tecnologías capaces de procesarlos y optimizar la velocidad. Además, la mayoría de los datos tienen múltiples formatos, lo cual es inherente a la necesidad de procesarlos en tiempo casi real; en este contexto los clústeres Beowulf pueden utilizarse como plataforma base para procesar Big Data utilizando frameworks como Hadoop o Spark, softwares especializados en usar los recursos distribuidos, disco duro o RAM, para procesar datos masivos.

# ¿Qué es procesamiento paralelo y distribuido?
•	Procesamiento paralelo: múltiples tareas se ejecutan al mismo tiempo en varios núcleos de una misma máquina o en distintas máquinas.

•	Procesamiento distribuido: tareas se dividen entre distintos nodos que se comunican a través de una red.
El clúster Beowulf combina ambas estrategias, permitiendo aprovechar tanto los núcleos de cada nodo como el conjunto de nodos interconectados.

# Nodo Maestro
Este es la unidad de cómputo (también conocida como nodo manager) que coordina el funcionamiento del clúster. Sus funciones son:
•	Distribuir tareas a los nodos trabajadores.
•	Monitorear el estado y recursos de los nodos.
•	Centralizar logs, datos y configuraciones.
Si es necesario también puede realizar tareas de procesamiento.
Nodos Trabajadores
Estas son las unidades que se encargan de ejecutar las tareas según son coordinadas por el nodo Maestro, y a diferencia de este, tienen menos responsabilidades y se centran en la ejecución de las tareas computacionales asignadas, sin registrar el comportamiento de otros nodos.

# Red Local
En el contexto de un clúster la red local es un componente muy importante, pues es esencialmente el medio en el que varias computadoras simulan ser una sola; la interconexión de los nodos a partir de red cableada mejora las velocidades de trasmisión como la estabilidad del sistema. Lo más común es usar una red Ethernet por su bajo costo y relativa facilidad de instalación y configuración (además es la que se usara en este manual), en clústeres pequeños o medianos lo usual es usar una topología de red tipo estrella (configuración para una red de área local (LAN) en la que cada uno de los nodos están conectados a un punto de conexión central), en este caso se utiliza un switch (Gigabit) para realizar este fin; continuamente se adjunta la topología de red utilizada en nuestro clúster.
