## Prerrequisitos
- **Ansible** instalado en el nodo controlador (`cluster0@cluster0:~/ansible-cluster$`).
- Inventario (`hosts`) configurado con los grupos `manager` y `workers`.
- Python 3 y `pip3` en todos los nodos.
- Acceso SSH sin contraseña desde el controlador a todos los nodos.
- Firewall UFW (o el que prefieras) disponible en los nodos.

## 1. Instalación de Ray en todos los nodos
```bash
ansible all -i hosts -m shell -a "pip3 install 'ray[default]==x.y.z'"
```
reemplaza x.y.z por la versión deseada (por ejemplo 2.53.0).

## 2. Configuración del Firewall (UFW)
Deshabilitamos temporalmente UFW o abrimos explícitamente el rango de puertos que usan los Workers de Ray para comunicarse:

```
# Opción A: Deshabilitar el firewall
ansible all -i hosts -b -m ufw -a "state=disabled"
```
Abrimos el rango de puertos que utilizará Ray:
```
# Opción B: Habilitar rango de puertos específicos de Ray
ansible all -i hosts -m shell -a "ufw allow 10010:10110/tcp" --become -K
```
## 3. Verificación de la instalación
Comprobamos que las versiones coincidan en todo el clúster:
```
ansible all -i hosts -m shell -a "python3 --version && ray --version"
```
## 4. Playbook: Despliegue del Clúster Ray (ray.yml)

Este Playbook orquesta el despliegue completo: limpia procesos y sesiones huérfanas, inicializa el Head Node en el manager y conecta los Workers.
Cree el archivo ray.yml en su directorio ansible-cluster con el siguiente contenido:
```
---
- name: Deploy and Clean Ray Cluster
  hosts: all
  become: yes
  vars:
    manager_cpus: 0
    worker_cpus: 8
    ray_tmp_dir: /tmp/ray
    ray_head_port: 6379
    ray_dashboard_host: 0.0.0.0
    ray_dashboard_port: 8265
    ray_client_port: 10001

  pre_tasks:
    - name: Ensure Ray temp directory exists
      file:
        path: "{{ ray_tmp_dir }}"
        state: directory
        owner: "{{ ansible_user }}"
        group: "{{ ansible_user }}"
        mode: '0777'

    - name: Stop and clean existing Ray processes and sessions
      shell: |
        ray stop --force || true
        rm -rf {{ ray_tmp_dir }} || true
        mkdir -p {{ ray_tmp_dir }}
        chown -R {{ ansible_user }}:{{ ansible_user }} {{ ray_tmp_dir }}
      ignore_errors: yes

    - name: Flush Redis DB on manager (clean GCS state)
      when: "'manager' in group_names"
      shell: redis-cli -p {{ ray_head_port }} FLUSHALL || true
      ignore_errors: yes

  tasks:
    - name: Start Ray head on the manager
      when: "'manager' in group_names"
      become: no
      async: 30
      poll: 0
      shell: |
        export PATH="$HOME/.local/bin:$PATH"
        nohup ray start \
          --head \
          --port={{ ray_head_port }} \
          --dashboard-host={{ ray_dashboard_host }} \
          --dashboard-port={{ ray_dashboard_port }} \
          --ray-client-server-port={{ ray_client_port }} \
          --node-ip-address={{ inventory_hostname }} \
          --node-name={{ ansible_hostname }} \
          --min-worker-port=10010 \
          --max-worker-port=10110 \
          --num-cpus={{ manager_cpus }} > /tmp/ray_head.log 2>&1 &

    - name: Wait 10 seconds for the Ray Head to fully initialize
      pause:
        seconds: 10
      run_once: true

    - name: Start Ray worker on the workers
      when: "'workers' in group_names"
      become: no
      async: 30
      poll: 0
      shell: |
        export PATH="$HOME/.local/bin:$PATH"
        nohup ray start \
          --address={{ hostvars[groups['manager'][0]].inventory_hostname }}:{{ ray_head_port }} \
          --node-ip-address={{ inventory_hostname }} \
          --node-name={{ ansible_hostname }} \
          --min-worker-port=10010 \
          --max-worker-port=10110 \
          --num-cpus={{ worker_cpus }} > /tmp/ray_worker.log 2>&1 &

    - name: Wait 5 seconds for workers to establish connection
      pause:
        seconds: 5
      run_once: true

    - name: Show Ray status for debugging
      become: no
      when: "'manager' in group_names"
      shell: |
        export PATH="$HOME/.local/bin:$PATH"
        ray status || true
      register: ray_status
      ignore_errors: yes

    - name: Display Ray status output
      when: "'manager' in group_names"
      debug:
        var: ray_status.stdout_lines

  post_tasks:
    - name: Ensure Ray temp directory ownership
      file:
        path: "{{ ray_tmp_dir }}"
        state: directory
        recurse: yes
        owner: "{{ ansible_user }}"
        group: "{{ ansible_user }}"
```
Ejecución del Playbook:
```
ansible-playbook -i hosts ray.yml
```
## 5. Playbook: Detener y Limpiar Ray (stop_ray_cluster.yml)
Para liberar recursos (especialmente la memoria compartida /dev/shm), debemos apagar Ray correctamente.
De igual manera en el directorio de ansible que tenga cree su Stop_Ray.yml (los nombres son a su elección).
```
---
- name: Stop and Clean Ray Cluster
  hosts: all
  become: yes
  tasks:
    - name: Detener Ray (head o worker)
      shell: ray stop --force
      ignore_errors: yes

    - name: Matar procesos raylet, gcs_server y monitor.py
      shell: |
        pkill -9 -f raylet       || true
        pkill -9 -f gcs_server   || true
        pkill -9 -f monitor.py   || true
        pkill -9 -f dashboard    || true
      ignore_errors: yes

    - name: Quitar sockets y datos temporales de Ray
      file:
        path: /tmp/ray
        state: absent
      ignore_errors: yes

    - name: Quitar stores de plasma en shm (si existe)
      file:
        path: /dev/shm/plasma_store*
        state: absent
      ignore_errors: yes

    - name: Confirmar limpieza final
      shell: |
        echo "Procesos Ray restantes:" && pgrep -a ray || echo "OK: ninguno"
        echo "Sesiones /tmp/ray:" && [ -d /tmp/ray ] && echo "DIRECTORIO EXISTE" || echo "OK: eliminado"
      register: cleanup_check
      changed_when: false

    - name: Mostrar resultados de la limpieza
      debug:
        var: cleanup_check.stdout_lines
```
Y para ejecutar en el directorio donde tenga ansible y su archivo host.
```
ansible-playbook -i hosts stop_ray_cluster.yml
```
## 6.Troubleshooting: Cómo Ver los Logs de Ray con Ansible
Si nota que algún nodo trabajador no se vincula correctamente al Head Node, puede utilizar Ansible para leer los logs de inicialización en tiempo real sin tener que ingresar por SSH a cada equipo.

Para revisar los logs del Maestro (manager):
```
ansible manager -i hosts -m shell -a "tail -n 25 /tmp/ray_head.log"
```

Para revisar posibles errores en todos los Trabajadores (workers):
```
ansible workers -i hosts -m shell -a "tail -n 25 /tmp/ray_worker.log"
```
