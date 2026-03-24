# Configuración del Nodo Maestro y Automatización de Red

El Nodo Maestro (Intel Core i5-4590S, 8 GB RAM, 512 GB SSD) actúa como el director de orquesta del clúster Beowulf. Su configuración inicial es crítica para garantizar el enrutamiento adecuado hacia los nodos trabajadores a través del switch 3Com en topología de estrella.

Para estandarizar y agilizar el despliegue tanto del maestro como de los nodos esclavos (HP Probook), se ha desarrollado un script de automatización en Bash. Este script configura el nombre del equipo, la red estática y las credenciales de acceso remoto de forma desatendida.

## Script de Configuración Base (`config_nodo.sh`)

## 1. ¿Qué hace este script?
Al ejecutarse, el script realiza las siguientes operaciones a nivel de sistema:
1. **Detección de Hardware:** Identifica la interfaz de red física conectada al switch 3Com.
2. **Asignación de Identidad:** Cambia el *hostname* del equipo.
3. **Bloqueo de Cloud-Init:** Crea el archivo `/etc/cloud/cloud-init.disabled` para evitar la sobrescritura de la red en cada reinicio.
4. **Configuración de Netplan:** Aplica una IP estática, puerta de enlace y DNS.
5. **Seguridad y Acceso:** Genera claves SSH (Ed25519) sin contraseña para la orquestación remota.

---

## 2. Instrucciones de Ejecución Paso a Paso

Para implementar esta configuración en el Nodo Maestro o en los Workers, siga estrictamente estos pasos en la terminal del servidor:

### Paso 1: Crear el archivo ejecutable
Abra el editor de texto integrado `nano` creando un archivo llamado `config_nodo.sh`

### Paso 2: Asignar permisos de ejecución
El sistema requiere permisos explícitos para tratar el archivo de texto como un programa. Ejecute:
`chmod +x config_nodo.sh`

### Paso 3: Ejecutar el script (Ejemplo para el Maestro)
Ejecute el script con privilegios de administrador (sudo), pasando los tres argumentos requeridos en el siguiente orden: nombre del equipo, IP del gateway, y la IP estática del nodo.

Para el Nodo Maestro, el comando exacto (En mi caso, que difiere probablemente de tu configuración de red, y equipos) es:

`sudo ./config_nodo.sh nodo-maestro 10.4.8.1 10.4.8.75/24`

El script, se encuentra a continuación: 

```bash
nano config_nodo.sh

```bash
#!/bin/bash

# ==============================================================================
# Script de Auto-Configuracion de Nodos - Clúster Beowulf I2E UPTC
# Proposito: Configurar hostname, deshabilitar cloud-init, aplicar IP estatica
#            mediante Netplan y generar claves SSH asimetricas.
# ==============================================================================

# 1. Validar que el usuario sea root (necesario para modificar /etc/)
if [ "$EUID" -ne 0 ]; then
  echo "Error: Este script modifica archivos del sistema. Ejecutar con sudo."
  exit 1
fi

# 2. Validar el ingreso estricto de los 3 argumentos requeridos
if [ "$#" -lt 3 ]; then
  echo "Uso: $0 <nombre_nodo> <ip_gateway> <ip_nodo_con_mascara>"
  echo "Ejemplo: $0 nodo-maestro 10.4.8.1 10.4.8.75/24"
  exit 1
fi

# Asignacion de los parametros ingresados por el usuario a variables legibles
NOMBRE_NODO=$1
GATEWAY=$2
IP_NODO=$3

# 3. Deteccion automatica de la interfaz de red principal
# 'ip route' muestra la tabla de ruteo. Filtramos la ruta por defecto (default).
# 'awk' extrae la quinta columna (el nombre de la interfaz, ej. eno1, eth0).
# 'head' asegura que tomemos solo el primer resultado si hay multiples interfaces.
INTERFAZ=$(ip -o -4 route show to default | awk '{print $5}' | head -n 1)

# Validar que se encontro una tarjeta de red conectada
if [ -z "$INTERFAZ" ]; then
  echo "Error: No se detecto una interfaz de red activa. Revise la conexion al switch 3Com."
  exit 1
fi

echo "Iniciando configuracion para el nodo: $NOMBRE_NODO sobre la interfaz: $INTERFAZ"

# 4. Establecer el nombre del equipo en la red (Hostname)
hostnamectl set-hostname "$NOMBRE_NODO"

# 5. Deshabilitar cloud-init
# Al crear este archivo vacio, evitamos que cloud-init sobrescriba Netplan en el proximo reinicio.
touch /etc/cloud/cloud-init.disabled

# 6. Generar el archivo YAML para Netplan
ARCHIVO_NETPLAN="/etc/netplan/01-config-red.yaml"

# Se utiliza cat con EOF (End of File) para inyectar el texto respetando los espacios del YAML
cat <<EOF > $ARCHIVO_NETPLAN
network:
  version: 2
  ethernets:
    $INTERFAZ:
      dhcp4: no
      addresses:
        - $IP_NODO
      routes:
        - to: default
          via: $GATEWAY
      nameservers:
        addresses: [8.8.8.8, 8.8.4.4] # Servidores DNS publicos de Google
EOF

# Aplicar las reglas de red inmediatamente al kernel
netplan apply

# 7. Generacion de Claves SSH
# Obtenemos el nombre del usuario original (no root) que ejecuto sudo
USUARIO_REAL=${SUDO_USER:-$USER}
RUTA_SSH="/home/$USUARIO_REAL/.ssh/id_ed25519"

# Si la clave no existe, se crea una nueva usando el algoritmo ed25519 (mas rapido y seguro que RSA)
if [ ! -f "$RUTA_SSH" ]; then
  # 'sudo -u' ejecuta el comando como el usuario normal para que sea el propietario de la clave
  # '-N ""' establece que la clave no tendra contraseña (vital para automatizacion)
  sudo -u "$USUARIO_REAL" ssh-keygen -t ed25519 -C "$NOMBRE_NODO@cluster-i2e" -f "$RUTA_SSH" -N ""
fi

echo "Proceso finalizado con exito."

```
## 4. Orquestación y Automatización con Ansible

Dado que el clúster Beowulf del I2E cuenta con múltiples nodos trabajadores, la administración manual de cada equipo es ineficiente. Para solucionar esto, el Nodo Maestro, y también como una recomendación, usaremos **Ansible**, una herramienta de orquestación *agentless* (sin agentes) que utiliza las claves SSH que generamos en el paso anterior para ejecutar comandos o instalar software (como Ray, librerias de python).

### ¿Qué hace esta configuración?
1. **Instala Ansible** en el Nodo Maestro.
2. **Crea un Inventario (`hosts.ini`)**: Un archivo que le dice al Maestro cuáles son las direcciones IP de sus nodos trabajadores y cómo agruparlos.
3. **Distribuye las Claves SSH**: Envía la clave pública del Maestro a los workers para que Ansible pueda entrar sin pedir contraseña; para esto revisa el Conf_Nodos_Trabajadores.md (https://github.com/JhonathanBaron/Cluster-Basado-en-Green-Computing/blob/35e28c9a3949be37878c054fb63bb2fca6689c79/Conf_Nodos_Trabajadores.md).

### Instrucciones de Ejecución Paso a Paso

#### Paso 1: Instalar Ansible en el Maestro
Ejecute los siguientes comandos en la terminal del Nodo Maestro para actualizar los repositorios e instalar la herramienta:
```bash
sudo apt update
sudo apt install ansible -y
```
### Paso 2: Crear el Archivo de Inventario

Es una buena práctica de ingeniería mantener los archivos de configuración del clúster organizados. Crearemos un directorio específico y un archivo de inventario.

Bash
mkdir -p ~/`Nombre_Carpeta`
nano ~/`Nombre_Carpeta`/hosts.ini
Copie y pegue la siguiente estructura lógica dentro del archivo (ajuste las IPs según la cantidad de workers que tenga y sus direcciones ip, esto es despues de ejecutar los pasos en la guía de Conf_Nodos_Trabajadores.md):

```bash
[maestro]
Ip_nodo_maestro ansible_connection=local
#ejemplo:
#10.4.8.75 ansible_connection=local

[workers]
Ips_Nodos_Workers
#10.4.8.20
#10.4.8.21
#10.4.8.22
#10.4.8.23

[cluster:children]
maestro
workers

[cluster:vars]
ansible_user=worker  # Cambie 'worker' por el nombre de usuario real de sus equipos
ansible_ssh_private_key_file=~/.ssh/id_ed25519
```
### Paso 3: Prueba de Conectividad (El "Ping" del Clúster)
Una vez distribuidas las claves, verifique que el Maestro tiene control total sobre el clúster enviando un comando de prueba (ping) a todos los nodos mediante Ansible (Ejecute en la carpeta donde tenga el host.ini):

```Bash
ansible all -i ~/cluster-config/hosts.ini -m ping
```
