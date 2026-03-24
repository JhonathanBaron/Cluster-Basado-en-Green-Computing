# Conceptos Previos 🐱‍🐉
Para empezar, se debe tener claridad en varios aspectos para embarcarse en el reto de implementar un clúster, 
primeramente, se debe comprender que un clúster Beowulf es un conjunto de computadoras interconectadas entre sí 
en una red local; esto para que trabajen en conjunto como si fueran una sola unidad de procesamiento, además se 
caracterizan por estar construidas con hardware convencional y basadas en software libre.

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


Este proyecto se fundamenta en la necesidad de superar las limitaciones de procesamiento de arquitecturas monolíticas en robótica de exploración espacial.

* **Green Computing y Economía Circular:** Reutilización de hardware en desuso para reducir la huella de carbono tecnológica, maximizando el ciclo de vida de los componentes.
* **Arquitectura Beowulf:** Un clúster multicomputador construido con hardware comercial estandarizado (COTS), conectado mediante una red local para procesamiento paralelo.
* **Procesamiento de Datos LiDAR:** Manejo masivo de nubes de puntos (Big Data) provenientes de los sensores del Rover de Exploración Espacial Terrestre (SGI 3863).
* **SLAM (Simultaneous Localization and Mapping):** Algoritmos críticos que requieren bajas latencias para cerrar lazos de control a frecuencias superiores a 10 Hz.
* **ROS2 DDS:** Middleware de comunicación en tiempo real utilizado para la transmisión de datos entre el Rover y el clúster.
