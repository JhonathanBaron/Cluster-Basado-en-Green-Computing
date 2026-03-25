# Orquestación del Clúster con Ansible

Administrar distintos nodos (maestros y trabajadores) de forma individual a través de SSH resulta ineficiente y propenso a errores humanos. Para solucionar esto y garantizar que todo el clúster Beowulf mantenga la misma configuración de software, el Grupo de Investigación I2E utiliza **Ansible**.

Ansible es una herramienta de orquestación y automatización de TI de código abierto. Su principal ventaja en nuestra arquitectura "Green Computing" es que es *agentless* (no requiere instalar un software cliente en los nodos trabajadores); funciona enviando instrucciones directamente a través de las conexiones SSH previamente configuradas.

## 1. Instalación de Ansible (Solo en el Nodo Maestro)

Dado que el Maestro, en mi caso, es el `10.4.8.10`, es el orquestador central, es el único equipo que necesita tener Ansible instalado.

Ejecute los siguientes comandos en la terminal del Nodo Maestro:
```bash
sudo apt update
sudo apt install software-properties-common -y
sudo add-apt-repository --yes --update ppa:ansible/ansible
sudo apt install ansible -y
```
Con el host y la carpeta creados anteriormente en el archivo Conf_Nodo_Maestro.md, podemos ejecutar distintos comandos, para familiarizarnos con ansible por favor consulte la pequeña guía a continuación.

## 2.Uso de Ansible: Comandos Ad-Hoc y Parámetros

Antes de escribir Playbooks (scripts de automatización complejos), Ansible permite ejecutar tareas rápidas en uno o varios nodos al instante mediante comandos ad-hoc.

La estructura base de un comando en Ansible es la siguiente:

```ansible <patrón_de_hosts> [opciones]```

**2.1 Parámetros Principales (Banderas)**
De acuerdo a la documentación interna de la herramienta (ansible --help), estos son los parámetros más utilizados para la administración del clúster:

-i INVENTORY (--inventory): Especifica la ruta del archivo de inventario (en nuestro caso, hosts).

-m MODULE_NAME (--module-name): Define la acción a ejecutar. Los módulos más comunes son ping, shell, command, apt y pip.

-a MODULE_ARGS (--args): Pasa argumentos específicos al módulo seleccionado (ej. el comando de Linux exacto que se desea correr).

-b (--become): Ejecuta la operación con escalamiento de privilegios (sudo). No pedirá contraseña gracias a la variable configurada en el inventario.

-v (--verbose): Aumenta el nivel de detalle en la salida de la terminal. Útil para depurar errores de conexión (-vvv o -vvvv).

--list-hosts: No ejecuta ninguna acción, solo imprime en pantalla la lista de nodos que coinciden con el patrón seleccionado.

**2.2 Ejemplos Prácticos en el Clúster Beowulf**

Asegúrese de ejecutar estos comandos desde el directorio ~/ansible-cluster.

1. Prueba de Conectividad (Ping):
Verifica que el Maestro tiene acceso por SSH y que Python responde en todos los nodos (tanto el manager como los workers).

``ansible all -i hosts -m ping``

2. Listar los nodos de un grupo específico:
Si desea ver qué IPs componen el grupo de trabajadores antes de enviar una instrucción:

``ansible workers -i hosts --list-hosts``

3. Ejecutar comandos nativos de Linux (grep, ps, ls):
Utilizando el módulo shell, podemos consultar información en tiempo real de múltiples nodos. Por ejemplo, para ver el modelo de procesador de los workers:

``ansible workers -i hosts -m shell -a "grep -i 'model name' /proc/cpuinfo"``


(También puede usar esto para verificar procesos en ejecución, ej: -a "ps aux | grep python").

4. Instalación de librerías en paralelo:
   
Para instalar una librería de Python (ej. numpy) en todos los nodos workers simultáneamente, utilizando privilegios de administrador (-b):

``ansible workers -i hosts -b -m shell -a 'pip3 install numpy --break-system-packages'``

---

## 3. Comandos Ad-Hoc vs. Playbooks

Ansible ofrece dos formas principales de interactuar con el clúster Beowulf. Elegir la herramienta adecuada depende de la complejidad de la tarea y de si necesitamos que la acción sea repetible en el futuro.

### 3.1 Comandos Ad-Hoc (El "Destornillador")
Son instrucciones de una sola línea que se ejecutan directamente en la terminal, como los ejemplos vistos en la sección anterior.

* **Función:** Ejecutar tareas rápidas, de una sola vez, que rara vez se guardan para su uso futuro.
* **Ventajas:**
  * **Inmediatez:** No requieren crear ni dar formato a archivos YAML.
  * **Diagnóstico rápido:** Ideales para verificar el estado del sistema (ej. revisar uso de CPU, reiniciar un servicio o hacer ping).
  * **Flexibilidad:** Permiten interactuar en tiempo real para solucionar problemas específicos en uno o varios nodos simultáneamente.

### 3.2 Playbooks (La "Línea de Ensamblaje")
Son archivos de texto plano escritos en formato YAML (`.yml`) que contienen una lista ordenada de tareas (un "guion"). Representan el verdadero poder de la automatización como código (Infrastructure as Code - IaC).

* **Función:** Orquestar configuraciones complejas, instalaciones de software multicapa y despliegues de aplicaciones en todo el clúster.
* **Ventajas:**
  * **Idempotencia:** Se pueden ejecutar 100 veces y el resultado será el mismo; Ansible solo hace cambios si detecta que el sistema no está en el estado deseado.
  * **Control de Versiones:** Al ser archivos de texto, se suben a GitHub para llevar un historial de qué se instaló, cuándo y por quién.
  * **Lógica Compleja:** Permiten usar variables, bucles, condicionales y manejar reinicios automáticos si una instalación lo requiere.
  * **Legibilidad:** Están diseñados para que cualquier ingeniero pueda leerlos y entender exactamente qué hace la infraestructura, incluso si no sabe programar.

### 3.3 Tabla Comparativa

| Característica | Comandos Ad-Hoc | Playbooks |
| :--- | :--- | :--- |
| **Formato** | Línea de comandos (Bash) | Archivos estructurados (YAML) |
| **Uso Ideal** | Tareas rápidas, *troubleshooting* | Despliegues complejos, estandarización |
| **Repetibilidad** | Baja (hay que volver a escribir el comando) | Alta (se ejecuta el archivo .yml) |
| **Idempotencia** | Depende del comando de Linux usado | Alta (garantizada por los módulos de Ansible) |
| **Curva de Aprendizaje** | Baja | Media |

---

## 4. Playbooks de Automatización del I2E

*(Sección en construcción: En el siguiente apartado documentaremos la creación del archivo YAML maestro para el despliegue automático del entorno de Big Data (Ray), Python y otras dependencias en todo el clúster).*
