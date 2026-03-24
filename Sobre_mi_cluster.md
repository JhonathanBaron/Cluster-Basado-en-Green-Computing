# Sobre el Clúster I2E - UPTC

Proyecto desarrollado en la **Universidad Pedagógica y Tecnológica de Colombia (UPTC)** por el Grupo de Investigación en Ingeniería Electrónica (I2E).

**Autores:** Diego-Alejandro Bautista-López, Jhonathan-Duberney Barón-Hernández, Fabián-Rolando Jiménez-López.
**Asesora:** Jenny-Amparo Rosales-Agredo.

## Especificaciones de Hardware
* **Nodo Maestro:** Torre con procesador Intel Core i5-4590S, 8 GB RAM DDR3, 512 GB SSD.
* **Nodos Workers (7x):** Placas base reutilizadas de portátiles HP Probook 4420s. Procesadores Intel Core i5-560M (2 núcleos/4 hilos, 2.7-3.2 GHz), 8 GB RAM, 500 GB HDD.
* **Red:** Topología de estrella. Switch Gigabit Ethernet 3Com Baseline 2952-SFPPLUS (1000 Mbps) y cableado UTP Cat 5e.

## Infraestructura Física y Refrigeración
* **Gabinete Modular:** Sistema de potencia centralizado por breaker de protección.
* **Sistema de Refrigeración Inteligente:** Microcontrolador BluePill (STM32) con sensores digitales DS18B20 (12 bits). Monitorea temperaturas entre 15 °C y 70 °C, ajustando ventiladores por PWM basado en zonificación de entrada de aire frío y extracción de calor.
* **Mantenimiento Riguroso:** Limpieza con alcohol isopropílico, cepillos antiestáticos y reemplazo de pasta térmica cada dos años para evitar el "golpe térmico".
