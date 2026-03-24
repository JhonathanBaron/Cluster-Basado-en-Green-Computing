# Sobre el Clúster I2E - UPTC 

Proyecto desarrollado en la **Universidad Pedagógica y Tecnológica de Colombia (UPTC)** por el Grupo de Investigación en Ingeniería Electrónica (I2E).

## Especificaciones de Hardware💻🖥

* **Nodo Maestro:** Torre con procesador Intel Core i5-4590S, 8 GB RAM DDR3, 512 GB SSD.
  
* **Nodos Workers (7x):** Placas base reutilizadas de portátiles HP Probook. Procesadores Intel Core i7-3612QM (4 núcleos, 8 hilos, 3.10 GHz) y entre 8 y 16 GB de RAM, 500 GB HDD.

* **Red:** Topología de estrella. Switch Gigabit Ethernet 3Com Baseline 2952-SFPPLUS (1000 Mbps) y cableado UTP Cat 5e.

## Infraestructura Física y Refrigeración

* **Gabinete Modular:** Se uso un rack antiguo el cual fue adecuado para manejar en su interior 8 placas (nodos workers)

  <div align="center">
  <img src="https://github.com/JhonathanBaron/Cluster-Basado-en-Green-Computing/blob/c2328b879854251a6d23df77120bc214fd764223/Imagenes/gabinete.jpeg" width="50%" alt="Gabinete">
  <br>
  <em>Gabinete .</em>
</div>
* **Sistema de Refrigeración Inteligente:** El microcontrolador usado para el manejo de la temperatura de mi cluster se basa en un arduino Nano, que usando lectura serial toma en cuenta los sensores digitales DS18B20 (12 bits). Monitorea temperaturas entre 15 °C y 70 °C, ajustando ventiladores por PWM basado en zonificación de entrada de aire frío y extracción de calor y buscando retroalimentación del nodo maestro.
  
* **Mantenimiento Riguroso:** Se recomienda antes de implementar hacer una limpieza con alcohol isopropílico, cepillos antiestáticos y reemplazo de pasta térmica cada dos años para evitar el "golpe térmico".

<div align="center">
  <img src="https://github.com/JhonathanBaron/Cluster-Basado-en-Green-Computing/blob/df3fd0cf60699b7d1c7fc6ec3505d5c50a6306ae/Imagenes/limpieza.jpg" width="50%" alt="Limpieza de las placas">
  <br>
  <em>Limpieza pasta térmica antigua .</em>
</div>
