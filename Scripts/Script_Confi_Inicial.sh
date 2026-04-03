cluster1@cluster1:~/Conf_Inicial$ cat configuracion.sh
#!/bin/bash

# 1. Validar argumentos de entrada
if [ "$#" -lt 3 ]; then
    echo "❌ Error: Faltan argumentos."
    echo "Uso: sudo $0 <RANGO_RED> <INDICE_IP> <NUMERO_NODO> [LLAVE_PUBLICA_SSH_MAESTRO]"
    echo "Ejemplo: sudo $0 10.4.8 11 1 'ssh-ed25519 AAA... cluster0@manager'"
    exit 1
fi

RANGO=$1
INDICE_IP=$2
NUMERO_NODO=$3
LLAVE_SSH=$4  # Opcional pero recomendado

IP="${RANGO}.${INDICE_IP}"
GATEWAY="${RANGO}.1"
SUBRED="${RANGO}.0/24"

# 2. Configurar el Hostname (ej: cluster1)
HOSTNAME="cluster${NUMERO_NODO}"
hostnamectl set-hostname $HOSTNAME
echo "=========================================="
echo "🚀 Iniciando configuración de: $HOSTNAME"
echo "🌐 IP asignada: $IP"
echo "=========================================="

# 3. Detectar la tarjeta de red (excluyendo 'lo')
INTERFACE=$(ip -o link show | awk -F': ' '{print $2}' | grep -v lo | head -n 1)

if [ -z "$INTERFACE" ]; then
    echo "❌ Error: No se pudo detectar la interfaz de red."
    exit 1
fi
echo "✅ Interfaz detectada: $INTERFACE."

# 4. Deshabilitar cloud-init
touch /etc/cloud/cloud-init.disabled
if ! grep -q "disable_cloud_init: true" /etc/cloud/cloud.cfg; then
    echo "disable_cloud_init: true" >> /etc/cloud/cloud.cfg
fi
echo "✅ Cloud-init deshabilitado."

# 5. Configurar Netplan
rm -f /etc/netplan/50-cloud-init.yaml 2>/dev/null
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
echo "✅ Netplan configurado y aplicado."

# 6. Instalar herramientas base
echo "⏳ Actualizando repositorios e instalando herramientas base..."
apt-get update -y > /dev/null
apt-get install -y ethtool python3-pip ufw > /dev/null

# 7. Obtener MAC y Configurar Wake-on-LAN
MAC=$(cat /sys/class/net/$INTERFACE/address)
echo "✅ La dirección MAC de $INTERFACE es: $MAC"
ethtool -s $INTERFACE wol g
echo "✅ Wake-on-LAN configurado para Magic Packet."

# 8. CONFIGURACIÓN DE FIREWALL (UFW)
echo "⏳ Configurando Firewall (UFW)..."
ufw --force reset > /dev/null
ufw default deny incoming > /dev/null
ufw default allow outgoing > /dev/null

# Permitir SSH
ufw allow ssh > /dev/null
# Permitir todo el tráfico interno entre los nodos de la subred
ufw allow from $SUBRED to any > /dev/null
# Puertos de Ray explícitos por seguridad
ufw allow 6379/tcp > /dev/null
ufw allow 8265/tcp > /dev/null
ufw allow 10000:10100/tcp > /dev/null

ufw --force enable > /dev/null
echo "✅ Firewall configurado y activado."

# 9. INYECCIÓN DE LLAVE SSH DEL MAESTRO
if [ -n "$LLAVE_SSH" ]; then
    echo "⏳ Configurando acceso SSH sin contraseña..."

    # Detecta el usuario real que ejecutó el comando sudo
    USUARIO_NODO="${SUDO_USER:-$USER}"
    HOME_DIR=$(eval echo ~$USUARIO_NODO)

    mkdir -p $HOME_DIR/.ssh
    echo "$LLAVE_SSH" >> $HOME_DIR/.ssh/authorized_keys

    # Ajustar permisos estrictos (SSH es muy delicado con esto)
    chmod 700 $HOME_DIR/.ssh
    chmod 600 $HOME_DIR/.ssh/authorized_keys
    chown -R $USUARIO_NODO:$USUARIO_NODO $HOME_DIR/.ssh

    echo "✅ Llave SSH agregada con éxito para el usuario $USUARIO_NODO."
else
    echo "⚠️ No se proporcionó llave SSH. Omitiendo este paso."
fi

# 10. Instalar Ansible y Ray
echo "⏳ Instalando Ansible y Ray (Esto puede tardar un par de minutos)..."
pip3 install ansible-core==2.15.8 ray==2.9.3 --break-system-packages

echo "=========================================="
echo "🎉 ¡Configuración del nodo $HOSTNAME completada al 100%! 🎉"
echo "=========================================="
