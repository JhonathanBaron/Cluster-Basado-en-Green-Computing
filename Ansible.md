# Orquestación del Clúster con Ansible

Administrar distintos nodos (maestros y trabajadores) de forma individual a través de SSH resulta ineficiente y propenso a errores humanos. Para solucionar esto y garantizar que todo el clúster Beowulf mantenga la misma configuración de software, el Grupo de Investigación I2E utiliza **Ansible**.

Ansible es una herramienta de orquestación y automatización de TI de código abierto. Su principal ventaja en nuestra arquitectura "Green Computing" es que es *agentless* (no requiere instalar un software cliente en los nodos HP Probook); funciona enviando instrucciones directamente a través de las conexiones SSH previamente configuradas.

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

Bash
``ansible all -i hosts -m ping``

2. Listar los nodos de un grupo específico:
Si desea ver qué IPs componen el grupo de trabajadores antes de enviar una instrucción:

Bash
``ansible workers -i hosts --list-hosts``

3. Ejecutar comandos nativos de Linux (grep, ps, ls):
Utilizando el módulo shell, podemos consultar información en tiempo real de múltiples nodos. Por ejemplo, para ver el modelo de procesador de los workers:

Bash
``ansible workers -i hosts -m shell -a "grep -i 'model name' /proc/cpuinfo"``


(También puede usar esto para verificar procesos en ejecución, ej: -a "ps aux | grep python").

4. Instalación de librerías en paralelo:
   
Para instalar una librería de Python (ej. numpy) en todos los nodos workers simultáneamente, utilizando privilegios de administrador (-b):

Bash
``ansible workers -i hosts -b -m shell -a "pip3 install numpy --break-system-packages"``

