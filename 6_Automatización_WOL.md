## ¿Qué es una dirección MAC y cómo funciona Wake‑on‑LAN?

Cada tarjeta de red posee un identificador único de 48 bits denominado **dirección MAC** (Media Access Control). Esta dirección permite identificar de forma inequívoca un dispositivo dentro de una red local.

**Wake‑on‑LAN (WOL)** es un estándar que permite encender un ordenador apagado enviándole un paquete especial (paquete mágico) a través de la red. El paquete contiene la dirección MAC del equipo destino repetida 16 veces; si la placa base y el sistema operativo están correctamente configurados, la máquina se inicia.

### ¿Por qué necesitamos WOL en un clúster?

En un clúster orientado a la eficiencia energética, los nodos trabajadores se apagan cuando no hay carga de trabajo. Encenderlos manualmente uno a uno no es práctico. Con WOL podemos:

- Automatizar el arranque de todo el clúster desde el nodo maestro de forma simultánea.
- Integrar el encendido en scripts de planificación o en playbooks de Ansible.
- Reducir el consumo eléctrico y el desgaste físico de los equipos.

## Prerrequisitos

- **BIOS/UEFI**: Wake‑on‑LAN habilitado en cada nodo trabajador.
- **Sistema operativo**: el driver de red debe mantener la interfaz activa para escuchar paquetes WOL (ajústelo con `ethtool` si es necesario).
- **Red**: todos los nodos deben estar en la misma subred (el paquete mágico viaja por broadcast).
- **Ansible** funcionando en el nodo maestro, con inventario `hosts` que incluya los grupos `manager` y `workers`.

## 1. Playbook Interactivo: Generador Automático de Script Wake‑on‑LAN

El playbook `mac.yml` realiza dos fases:

1. **Recopilar las direcciones MAC** de todos los nodos trabajadores (necesitan estar encendidos y accesibles *al menos la primera vez*).
2. **Generar un script bash** en el nodo maestro que, al ejecutarlo, enviará los paquetes mágicos a los trabajadores. El playbook pregunta interactivamente la ruta y el nombre del script.

Cree el archivo `mac.yml` en su directorio de playbooks con el siguiente contenido:

```yaml
---
# ==============================================================================
# Playbook Interactivo: Generador Automático de Script Wake-on-LAN
# Archivo: mac.yml
# ==============================================================================

# Fase 1: Leer el hardware de las placas esclavas
- name: Recopilar direcciones MAC de los nodos trabajadores
  hosts: workers
  gather_facts: yes
  ignore_unreachable: yes  # Permite que el playbook continúe aunque un nodo falle

# Fase 2: Configurar el script en el maestro
- name: Generar script de encendido masivo en el Nodo Maestro
  hosts: manager
  gather_facts: no

  # === Bloque de preguntas interactivas ===
  vars_prompt:
    - name: "ruta_destino"
      prompt: "📂 Ingrese la ruta absoluta para guardar el script (ej. /home/cluster0/scripts_wol)"
      default: "/home/cluster0/cluster-utils"
      private: no

    - name: "nombre_archivo"
      prompt: "📄 Ingrese el nombre del archivo (ej. wake_workers.sh)"
      default: "encender_workers.sh"
      private: no
  # ===============================================

  tasks:
    - name: Asegurar que la herramienta 'wakeonlan' esté instalada
      apt:
        name: wakeonlan
        state: present
        update_cache: yes
      become: yes

    - name: Crear directorio destino si no existe
      file:
        path: "{{ ruta_destino }}"
        state: directory
        mode: '0755'

    - name: Generar script ejecutable con detalles de cada nodo
      copy:
        dest: "{{ ruta_destino }}/{{ nombre_archivo }}"
        mode: '0755'
        content: |
          #!/bin/bash
          # ==========================================================
          # Script de encendido masivo (WOL) - Clúster Beowulf I2E
          # Generado automáticamente por Ansible
          # ==========================================================

          echo "🚀 Enviando paquetes mágicos a los nodos trabajadores..."
          echo "----------------------------------------------------------"

          {% for host in groups['workers'] %}
          {% if 'ansible_default_ipv4' in hostvars[host] %}
          # 🖥️ IP: {{ host }} | Usuario Ansible: {{ hostvars[host]['ansible_user'] }} | Hostname: {{ hostvars[host]['ansible_hostname'] | default('Desconocido') }}
          echo "Encendiendo {{ hostvars[host]['ansible_hostname'] | default(host) }}..."
          wakeonlan {{ hostvars[host]['ansible_default_ipv4']['macaddress'] }} > /dev/null

          {% else %}
          # ⚠️ ADVERTENCIA: El nodo IP {{ host }} (Usuario: {{ hostvars[host]['ansible_user'] }}) estaba inalcanzable.
          echo "⚠️ Omitiendo {{ host }} - No se pudo obtener la MAC."

          {% endif %}
          {% endfor %}
          echo "----------------------------------------------------------"
          echo "✅ Todos los paquetes WOL han sido enviados."

   ```
