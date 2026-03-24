# Configuración de los Nodos Workers

Los nodos workers, son el músculo de procesamiento del clúster Beowulf. Su función exclusiva es ejecutar las cargas de trabajo intensivas (Big Data, procesamiento paralelo, entrenamiento de distintas sesiones de ia, etc) enviadas por el Nodo Maestro.

Para agilizar la integración de estos nodos al clúster, se ha diseñado un script en Bash que configura la red estática, habilita el encendido remoto (Wake-on-LAN), ajusta el firewall de seguridad e inyecta la llave SSH del maestro para permitir la orquestación remota sin intervención manual.

## 1. ¿Qué hace este script?
Al ejecutarse en un nodo worker recién instalado, el script realiza automáticamente lo siguiente:
1. **Asignación Dinámica de Identidad:** Configura el *hostname* (ej. `node-20`) basándose en el índice IP proporcionado.
2. **Configuración de Red Estática:** Detecta la tarjeta de red, desactiva `cloud-init` y aplica una IP estática en Netplan de acuerdo al rango del clúster.
3. **Activación de Wake-on-LAN:** Instala y configura `ethtool` para permitir que el Nodo Maestro encienda las placas HP remotamente.
4. **Seguridad Perimetral (UFW):** Reinicia y configura el firewall para bloquear tráfico externo, permitiendo únicamente conexiones SSH y tráfico interno desde la subred del clúster.
5. **Inyección de Llave SSH:** Si se provee la llave pública del Nodo Maestro como argumento, la agrega a `authorized_keys`, estableciendo el puente de confianza para futura automatización.

---

## 2. Instrucciones de Ejecución Paso a Paso

Para integrar un nuevo nodo worker al clúster, siga estos pasos en la terminal de la placa HP Probook:

### Paso 1: Crear el archivo ejecutable
Abra el editor de texto integrado `nano` creando un archivo llamado `config_worker.sh`:
```bash
nano config_worker.sh
```

### Paso 2: Asignar permisos de ejecución
El sistema requiere permisos explícitos para tratar el archivo de texto como un programa. Ejecute:
```bash
chmod +x config_worker.sh
```

### Paso 3: Ejecutar el script
Ejecute el script con privilegios de administrador (`sudo`), pasando el rango de red, el último octeto (índice) de la IP deseada, y (entre comillas) la llave pública SSH que generó previamente en el Nodo Maestro.

Por ejemplo, si su red es `10.4.8.X`, quiere asignar la IP terminada en `20`, y su llave pública es `ssh-ed25519 AAA... maestro@cluster-i2e`, el comando exacto será:
```bash
sudo ./config_worker.sh 10.4.8 20 "ssh-ed25519 AAAAC3Nz... maestro@cluster-i2e"
```

*(Nota: Repita este proceso iterando el índice para cada nodo. Ej: `21` para el worker 2, `22` para el worker 3, etc.)*

---

## 3. Código del Script de Automatización

A continuación, se presenta el código fuente que debe copiar e insertar en el archivo creado en el **Paso 1**:
```bash
#!/bin/bash

# ==============================================================================
# Script de Auto-Configuración de Nodos Workers - Clúster Beowulf I2E UPTC
# Propósito: Configurar red estática, firewall, Wake-on-LAN y acceso SSH.
# ==============================================================================

# 1. Validar argumentos de entrada
if [ "$#" -lt 2 ]; then
    echo "❌ Error: Faltan argumentos."
    echo "Uso: sudo $0 <RANGO_RED> <INDICE_IP> [LLAVE_PUBLICA_SSH_MAESTRO]"
    echo "Ejemplo: sudo $0 10.4.8 20 'ssh-ed25519 AAAAC3Nz... maestro@cluster-i2e'"
    exit 1
fi

RANGO=$1
INDICE=$2
LLAVE_SSH=$3  # Opcional
IP="${RANGO}.${INDICE}"
GATEWAY="${RANGO}.1"
SUBRED="${RANGO}.0/24"

# Configurar el Hostname para identificar fácilmente el nodo en Ray/Ansible
HOSTNAME="node-${INDICE}"
hostnamectl set-hostname $HOSTNAME
echo "✅ Hostname configurado como: $HOSTNAME"

# 2. Detectar la tarjeta de red (excluyendo 'lo')
INTERFACE=$(ip -o link show | awk -F': ' '{print $2}' | grep -v lo | head -n 1)

if [ -z "$INTERFACE" ]; then
    echo "❌ No se pudo detectar la interfaz."
    exit 1
fi
echo "✅ Interfaz detectada: $INTERFACE. Configurando IP: $IP..."

# 3. Deshabilitar cloud-init
touch /etc/cloud/cloud-init.disabled
if ! grep -q "disable_cloud_init: true" /etc/cloud/cloud.cfg; then
    echo "disable_cloud_init: true" >> /etc/cloud/cloud.cfg
fi

# 4. Configurar Netplan
rm -f /etc/netplan/50-cloud-init.yaml
rm -f /etc/netplan/01-netcfg.yaml 2>/dev/null

cat <<EOF > /etc/netplan/01-static-config.yaml
network:
  version: 2
  renderer: networkd
  ethernets:
    $INTERFACE:
      dhcp4: no
      addresses: [$IP/24]
      routes:
        - to: default
          via: $GATEWAY
      nameservers:
        addresses: [8.8.8.8, 8.8.4.4]
      wakeonlan: true
EOF

netplan apply
echo "✅ Netplan aplicado."

# 5. Instalar dependencias base y configurar Wake-on-LAN
apt-get update -y
apt-get install -y ethtool ufw

ethtool -s $INTERFACE wol g
echo "✅ Wake-on-LAN configurado."

# 6. CONFIGURACIÓN DE FIREWALL (UFW)
echo "⏳ Configurando Firewall..."
ufw --force reset
ufw default deny incoming
ufw default allow outgoing

# Permitir SSH desde cualquier lugar
ufw allow ssh

# Permitir todo el tráfico interno entre los nodos del clúster (Ansible, Ray, NFS, etc.)
ufw allow from $SUBRED to any

ufw --force enable
echo "✅ Firewall configurado y activado."

# 7. INYECCIÓN DE LLAVE SSH DEL MAESTRO
if [ -n "$LLAVE_SSH" ]; then
    echo "Configurando acceso SSH sin contraseña para el maestro..."
    
    # Capturar al usuario real que invocó sudo (para no inyectar en root)
    USUARIO_NODO=${SUDO_USER:-$USER}
    
    mkdir -p /home/$USUARIO_NODO/.ssh
    echo "$LLAVE_SSH" >> /home/$USUARIO_NODO/.ssh/authorized_keys
    chmod 700 /home/$USUARIO_NODO/.ssh
    chmod 600 /home/$USUARIO_NODO/.ssh/authorized_keys
    chown -R $USUARIO_NODO:$USUARIO_NODO /home/$USUARIO_NODO/.ssh
    
    echo "✅ Llave SSH agregada con éxito para el usuario: $USUARIO_NODO"
fi

echo "Configuración de $HOSTNAME completada con éxito."
```

** Una vez ejecutado en todos los nodos puede editar el Host.ini del Conf_Nodo_Maestro.md para acceder a los beneficios de usar ansible **
