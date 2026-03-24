# Instalación del Sistema Operativo: Ubuntu Server

Para la infraestructura de este clúster Beowulf, se ha seleccionado **Ubuntu Server 22.04.5 LTS** (Long Term Support). Esta decisión arquitectónica se fundamenta en su soporte extendido de 5 años y su alta compatibilidad con el ecosistema de software científico. Al carecer de entorno gráfico (GUI), el sistema operativo libera valiosos recursos de CPU y memoria RAM, dejándolos a disposición exclusiva del procesamiento en segundo plano. Ubuntu Server es de código abierto, ligero, eficiente y ofrece seguridad avanzada frente a vulnerabilidades.

## 1. Preparación del Medio de Arranque (Rufus)
La creación del medio de instalación USB (mínimo 4 GB) se realiza mediante la utilidad Rufus, configurando los parámetros según la arquitectura de cada nodo:

* **Para Nodos Workers (HP Probook - Hardware antiguo):**
  * **Esquema de partición:** MBR (Master Boot Record).
  * **Sistema de destino:** BIOS (Legacy).
  * **Sistema de archivos:** FAT32.
* **Para el Nodo Maestro (Hardware moderno):**
  * **Esquema de partición:** GPT (GUID Partition Table).
  * **Sistema de destino:** UEFI.
  * **Sistema de archivos:** FAT32.

## 2. Configuración de Firmware (BIOS/UEFI)
El acceso a la BIOS se realiza presionando teclas específicas durante el arranque, como F10 para equipos HP o F2/DEL para otras marcas. En la sección *Boot Options*, se debe establecer la configuración correspondiente al esquema de partición elegido:
* **Legacy Support:** Debe establecerse en `Enabled` para sistemas que utilizan esquemas MBR.
* **Secure Boot:** Debe establecerse en `Enabled` para sistemas UEFI con particiones GPT.

## 3. Proceso de Instalación del Sistema
Al arrancar desde el medio USB, se deben seguir estos parámetros técnicos durante el asistente de instalación:

* **Selección de Paquetes:** Elegir la versión estándar `Ubuntu Server` e incluir la opción `Search for third-party drivers`. Esto asegura la correcta instalación de controladores propietarios, como los adaptadores de red.
* **Gestión de Red:** Las interfaces (Ethernet/Wi-Fi) se pueden dejar temporalmente por defecto (mediante DHCP) durante este paso.
* **Servicios Adicionales:** Es vital seleccionar la instalación de `OpenSSH` para permitir la administración remota futura. Se recomienda estrictamente **no instalar** servicios adicionales (snaps) en este punto para evitar interferencias y mantener el entorno limpio.

## 4. Particionamiento Avanzado con LVM
Para garantizar la escalabilidad y flexibilidad en la gestión del disco, se selecciona la opción de almacenamiento guiado utilizando **LVM (Logical Volume Manager)**. El esquema de particionado manual recomendado es el siguiente:

* **Partición `/boot` (Arranque):** Asignar **250 MB**. Contiene el kernel del sistema operativo y los archivos críticos del proceso de arranque.
* **Partición `Swap` (Memoria Virtual):** Fundamental para evitar caídas del sistema bajo carga extrema. Para nuestros nodos con 8 GB de RAM, se exige un mínimo de **4 GB de espacio swap**.
* **Partición `/` (Root):** Asignar un mínimo de **5 GB** para una instalación completa. Aquí se almacenan la mayoría de los archivos del sistema, librerías base y ejecutables.
* **Partición `/home` (Datos de Usuario):** Asignar un mínimo de **100 MB**. Aislar esta partición permite mantener a salvo los datos del usuario de forma independiente del sistema.

# **SI REQUIERE MAYOR INFORMACIÓN, A CONTINUACIÓN ENCONTRARA UN MANUAL DE MI AUTORÍA PARA AYUDARLE EN EL PROCESO**

**[Ver el Manual de Instalación de Ubuntu Server (PDF)](https://github.com/JhonathanBaron/Cluster-Basado-en-Green-Computing/blob/9bcf15b2dcebcc01cdbf5904be05dbe153f4dc9b/Documentos/Instalaci%C3%B3n_Ubuntu_Server.pdf)**
