from flask import (Flask, render_template, request, jsonify,
                   session, redirect, url_for)
from functools import wraps
import subprocess
import os
import glob
import re
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'i2e_cluster_beowulf_2024'  # Cambiar por clave segura en produccion

ANSIBLE_DIR = "/home/cluster0/ansible-cluster"
INVENTORY   = f"{ANSIBLE_DIR}/hosts"
MAC_SCRIPT  = "/home/cluster0/Mac/Mac.sh"

USUARIOS_VALIDOS = {
    "Cluster0": "oxoCluster0"
}

MAC_ADDRESSES = {
    "10.4.8.11": "b4:b5:2f:81:ab:2b",
    "10.4.8.12": "b4:b5:2f:81:b3:5d",
    "10.4.8.13": "b4:b5:2f:81:ab:56",
    "10.4.8.14": "8c:dc:d4:cb:43:de",
    "10.4.8.15": "b4:b5:2f:81:95:cf",
    "10.4.8.16": "8c:dc:d4:cb:44:00",
    "10.4.8.17": "8c:dc:d4:cb:44:5c",
    "10.4.8.18": "14:58:d0:19:24:95",
    "10.4.8.21": None,
    "10.4.8.10": None,
}

# ── AUTENTICACION ─────────────────────────────────────────────
def requiere_login(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('usuario'):
            if request.is_json:
                return jsonify({"status": "error", "output": "Sesion expirada."}), 401
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        usuario  = request.form.get('usuario', '').strip()
        password = request.form.get('password', '')
        if USUARIOS_VALIDOS.get(usuario) == password:
            session['usuario'] = usuario
            return redirect(url_for('index'))
        error = 'Usuario o contraseña incorrectos.'
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ── RUTAS PRINCIPALES ─────────────────────────────────────────
@app.route('/')
@requiere_login
def index():
    return render_template('index.html', usuario=session.get('usuario'))

@app.route('/lite')
@requiere_login
def lite():
    return render_template('lite.html', usuario=session.get('usuario'))

# ── HELPERS DE PLAYBOOKS ──────────────────────────────────────
def _parsear_playbook(path):
    nombre      = os.path.basename(path)
    descripcion = ''
    hosts       = ''
    try:
        ctime = os.path.getctime(path)
        fecha_creacion = datetime.fromtimestamp(ctime).strftime('%Y-%m-%d %H:%M')
    except:
        fecha_creacion = '(desconocida)'

    try:
        with open(path, 'r') as f:
            lineas = f.readlines()

        desc_lines = []
        in_comments = True
        for linea in lineas:
            stripped = linea.strip()
            if stripped.startswith('#'):
                texto = stripped.lstrip('#').strip()
                if texto.lower().startswith('desc:'):
                    desc_lines.append(texto[5:].strip())
                else:
                    desc_lines.append(texto)
                in_comments = True
            elif in_comments and stripped == '':
                break
            elif not stripped.startswith('#'):
                in_comments = False
            m = re.match(r'^\s*hosts\s*:\s*(.+)', linea)
            if m and not hosts:
                hosts = m.group(1).strip()

        if desc_lines:
            descripcion = ' '.join(desc_lines)
        else:
            descripcion = '(sin descripcion)'
    except Exception:
        pass

    return {
        "nombre":      nombre,
        "descripcion": descripcion,
        "hosts":       hosts if hosts else '(no especificado)',
        "fecha":       fecha_creacion,
        "path":        path
    }

# ── API: PLAYBOOKS ────────────────────────────────────────────
@app.route('/api/playbooks', methods=['GET'])
@requiere_login
def listar_playbooks():
    archivos = sorted(glob.glob(f"{ANSIBLE_DIR}/*.yml") +
                      glob.glob(f"{ANSIBLE_DIR}/*.yaml"))
    lista = [_parsear_playbook(p) for p in archivos]
    return jsonify({"status": "success", "playbooks": lista})

@app.route('/api/playbooks/leer', methods=['POST'])
@requiere_login
def leer_playbook():
    nombre = request.json.get('nombre', '')
    if not nombre or '/' in nombre or '..' in nombre:
        return jsonify({"status": "error", "output": "Nombre de archivo no valido."})
    path = os.path.join(ANSIBLE_DIR, nombre)
    if not os.path.isfile(path):
        return jsonify({"status": "error", "output": "Archivo no encontrado."})
    try:
        with open(path, 'r') as f:
            contenido = f.read()
        return jsonify({"status": "success", "contenido": contenido})
    except Exception as e:
        return jsonify({"status": "error", "output": str(e)})

@app.route('/api/playbooks/guardar', methods=['POST'])
@requiere_login
def guardar_playbook():
    data      = request.json
    nombre    = data.get('nombre', '').strip()
    contenido = data.get('contenido', '')

    if not nombre:
        return jsonify({"status": "error", "output": "El nombre del archivo es obligatorio."})
    if '/' in nombre or '..' in nombre:
        return jsonify({"status": "error", "output": "Nombre de archivo no valido."})
    if not nombre.endswith(('.yml', '.yaml')):
        nombre += '.yml'

    path = os.path.join(ANSIBLE_DIR, nombre)
    try:
        with open(path, 'w') as f:
            f.write(contenido)
        return jsonify({"status": "success",
                        "output": f"Playbook guardado: {nombre}"})
    except Exception as e:
        return jsonify({"status": "error", "output": str(e)})

@app.route('/api/playbooks/ejecutar', methods=['POST'])
@requiere_login
def ejecutar_playbook():
    nombre = request.json.get('nombre', '')
    if not nombre or '/' in nombre or '..' in nombre:
        return jsonify({"status": "error", "output": "Nombre de archivo no válido."})
    path = os.path.join(ANSIBLE_DIR, nombre)
    if not os.path.isfile(path):
        return jsonify({"status": "error", "output": "Playbook no encontrado."})
    try:
        # Ejecutar dentro del directorio ANSIBLE_DIR
        cmd = ["ansible-playbook", "-i", INVENTORY, path]
        res = subprocess.run(cmd, cwd=ANSIBLE_DIR, capture_output=True, text=True, timeout=300)
        salida = res.stdout + "\n" + res.stderr
        return jsonify({"status": "success" if res.returncode == 0 else "error",
                        "output": salida.strip()})
    except subprocess.TimeoutExpired:
        return jsonify({"status": "error", "output": "Playbook interrumpido por tiempo (300s)."})
    except Exception as e:
        return jsonify({"status": "error", "output": str(e)})

@app.route('/api/playbooks/borrar', methods=['POST'])
@requiere_login
def borrar_playbook():
    nombre = request.json.get('nombre', '')
    if not nombre or '/' in nombre or '..' in nombre:
        return jsonify({"status": "error", "output": "Nombre no válido."})
    path = os.path.join(ANSIBLE_DIR, nombre)
    if not os.path.isfile(path):
        return jsonify({"status": "error", "output": "Archivo no encontrado."})
    try:
        os.remove(path)
        return jsonify({"status": "success", "output": f"Playbook {nombre} eliminado."})
    except Exception as e:
        return jsonify({"status": "error", "output": str(e)})

# ── API: ESTADO DE NODOS (ping rapido) ────────────────────────
@app.route('/api/estado_nodos', methods=['GET'])
@requiere_login
def estado_nodos():
    nodos = {
        "10.4.8.10": "manager",
        "10.4.8.11": "worker1",
        "10.4.8.12": "worker2",
        "10.4.8.13": "worker3",
        "10.4.8.14": "worker4",
        "10.4.8.15": "worker5",
        "10.4.8.16": "worker6",
        "10.4.8.17": "worker7",
        "10.4.8.18": "worker8",
        "10.4.8.21": "canelita",
    }
    resultado = {}
    for ip, nombre in nodos.items():
        res = subprocess.run(
            f"ping -c 1 -W 1 {ip}",
            shell=True, capture_output=True
        )
        resultado[ip] = {
            "nombre": nombre,
            "online": res.returncode == 0
        }
    return jsonify({"status": "success", "nodos": resultado})

# ── API: ACCIONES GENERALES ───────────────────────────────────
@app.route('/api/ejecutar', methods=['POST'])
@requiere_login
def ejecutar():
    data     = request.json
    accion   = data.get('accion')
    objetivo = data.get('objetivo', 'all')
    extra    = data.get('extra', '').strip()
    cmd      = ""

    # ---- NUEVAS ACCIONES ----
    if accion == 'local_shell':
        if not extra:
            return jsonify({"status": "error", "output": "Comando vacío."})
        try:
            res = subprocess.run(extra, shell=True, capture_output=True, text=True, timeout=60)
            salida = res.stdout + "\n" + res.stderr
            return jsonify({"status": "success" if res.returncode == 0 else "error",
                            "output": salida.strip()})
        except subprocess.TimeoutExpired:
            return jsonify({"status": "error", "output": "Comando local interrumpido (60s)."})

    elif accion == 'ansible_adhoc':
        if not extra or '|' not in extra:
            return jsonify({"status": "error",
                            "output": "Formato: modulo|argumentos   (ej: shell|ls -la)"})
        modulo, args = extra.split('|', 1)
        modulo = modulo.strip()
        args = args.strip()
        if not modulo or not args:
            return jsonify({"status": "error", "output": "Módulo y argumentos obligatorios."})
        cmd = f"ansible {objetivo} -i {INVENTORY} -m {modulo} -a '{args}'"

    # ---- DIAGNOSTICO ----
    elif accion == 'ping':
        cmd = f"ansible {objetivo} -i {INVENTORY} -m ping"
    elif accion == 'recursos':
        cmd = f"ansible {objetivo} -i {INVENTORY} -m command -a 'free -h'"
    elif accion == 'uso_cpu':
        cmd = f"ansible {objetivo} -i {INVENTORY} -m shell -a 'top -bn1 | grep \"Cpu(s)\"'"
    elif accion == 'espacio_disco':
        cmd = f"ansible {objetivo} -i {INVENTORY} -m command -a 'df -h /'"
    elif accion == 'uptime':
        cmd = f"ansible {objetivo} -i {INVENTORY} -m command -a 'uptime'"
    elif accion == 'procesos':
        cmd = f"ansible {objetivo} -i {INVENTORY} -m shell -a 'ps aux --sort=-%cpu | head -10'"
    elif accion == 'temperatura':
        cmd = (f"ansible {objetivo} -i {INVENTORY} -m shell "
               f"-a 'cat /sys/class/thermal/thermal_zone*/temp 2>/dev/null "
               f"| awk \"{{print \\$1/1000 \\\" C\\\"}}\" || echo \"No disponible\"'")
    elif accion == 'usuarios':
        cmd = f"ansible {objetivo} -i {INVENTORY} -m shell -a 'who -u'"
    elif accion == 'terminar_sesion':
        if not extra:
            return jsonify({"status": "error", "output": "Falta usuario y terminal."})
        partes = extra.split()
        if len(partes) < 2:
            return jsonify({"status": "error",
                            "output": "Formato: usuario terminal  (ej: cluster1 pts/1)"})
        terminal = partes[1]
        cmd = f"ansible {objetivo} -i {INVENTORY} -b -m shell -a 'pkill -t {terminal} || true'"

    # ---- WAKE-ON-LAN ----
    elif accion == 'wakeonlan':
        if objetivo in ('all', 'workers'):
            res = subprocess.run(f"bash {MAC_SCRIPT}",
                                 shell=True, capture_output=True, text=True)
            return jsonify({"status": "success",
                            "output": (res.stdout + res.stderr).strip()})
        mac = MAC_ADDRESSES.get(objetivo)
        if not mac:
            return jsonify({"status": "error",
                            "output": f"No hay MAC registrada para {objetivo}."})
        res = subprocess.run(f"wakeonlan {mac}",
                             shell=True, capture_output=True, text=True)
        return jsonify({
            "status": "success" if res.returncode == 0 else "error",
            "output": f"WOL enviado a {objetivo} ({mac}).\n{(res.stdout+res.stderr).strip()}"
        })

    # ---- ENERGIA ----
    elif accion == 'reboot':
        cmd = f"ansible {objetivo} -i {INVENTORY} -b -m reboot"
    elif accion == 'poweroff':
        cmd = f"ansible {objetivo} -i {INVENTORY} -b -m command -a 'poweroff'"

    # ---- PIP ----
    elif accion == 'instalar_pip':
        if not extra:
            return jsonify({"status": "error", "output": "Falta el nombre de la libreria."})
        cmd = f"ansible {objetivo} -i {INVENTORY} -m shell -a 'pip3 install {extra} 2>&1'"
    elif accion == 'desinstalar_pip':
        if not extra:
            return jsonify({"status": "error", "output": "Falta el nombre de la libreria."})
        cmd = f"ansible {objetivo} -i {INVENTORY} -m shell -a 'pip3 uninstall -y {extra} 2>&1'"
    elif accion == 'version_pip':
        if not extra:
            return jsonify({"status": "error", "output": "Falta el nombre de la libreria."})
        cmd = (f"ansible {objetivo} -i {INVENTORY} -m shell "
               f"-a 'pip3 show {extra} 2>&1 | grep -E \"^(Name|Version|Location)\"'")
    elif accion == 'listar_pip':
        cmd = f"ansible {objetivo} -i {INVENTORY} -m shell -a 'pip3 list 2>&1'"

    # ---- APT ----
    elif accion == 'instalar_apt':
        if not extra:
            return jsonify({"status": "error", "output": "Falta el nombre del programa."})
        cmd = (f"ansible {objetivo} -i {INVENTORY} -b -m apt "
               f"-a 'name={extra} state=present update_cache=yes'")
    elif accion == 'desinstalar_apt':
        if not extra:
            return jsonify({"status": "error", "output": "Falta el nombre del programa."})
        cmd = (f"ansible {objetivo} -i {INVENTORY} -b -m apt "
               f"-a 'name={extra} state=absent autoremove=yes'")
    elif accion == 'version_apt':
        if not extra:
            return jsonify({"status": "error", "output": "Falta el nombre del programa."})
        cmd = (f"ansible {objetivo} -i {INVENTORY} -m shell "
               f"-a 'dpkg -l {extra} 2>&1 | grep ^ii || echo \"No instalado\"'")
    elif accion == 'actualizar_apt':
        cmd = (f"ansible {objetivo} -i {INVENTORY} -b -m apt "
               f"-a 'update_cache=yes upgrade=dist'")

    # ---- COMANDO LIBRE ----
    elif accion == 'comando_libre':
        if not extra:
            return jsonify({"status": "error", "output": "Falta el comando."})
        cmd = f"ansible {objetivo} -i {INVENTORY} -m shell -a '{extra}'"

    # ---- RAY ----
    elif accion == 'iniciar_ray':
        cmd = f"ansible-playbook -i {INVENTORY} {ANSIBLE_DIR}/ray2.yml"
    elif accion == 'detener_ray':
        cmd = f"ansible-playbook -i {INVENTORY} {ANSIBLE_DIR}/Detener_Ray.yml"
    elif accion == 'estado_ray':
        cmd = (f"ansible manager -i {INVENTORY} -m shell "
               f"-a 'ray status 2>&1 || echo \"Ray no esta corriendo\"'")

    # ---- JUPYTER ----
    elif accion == 'iniciar_jupyter':
        os.system("nohup jupyter notebook --ip=0.0.0.0 --port=8888 --no-browser "
                  "> /tmp/jupyter.log 2>&1 &")
        return jsonify({"status": "success",
                        "output": "Jupyter iniciado en segundo plano (puerto 8888)."})
    elif accion == 'detener_jupyter':
        subprocess.run("pkill -f 'jupyter.*notebook' || true",
                       shell=True, capture_output=True)
        return jsonify({"status": "success", "output": "Jupyter detenido."})
    elif accion == 'log_jupyter':
        res = subprocess.run("tail -30 /tmp/jupyter.log",
                             shell=True, capture_output=True, text=True)
        return jsonify({"status": "success",
                        "output": res.stdout or "(sin log aun)"})

    else:
        return jsonify({"status": "error",
                        "output": f"Accion no reconocida: {accion}"})

    # Ejecutar comando generado (para los casos que no retornaron antes)
    if cmd:
        try:
            resultado = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
            salida = resultado.stdout + "\n" + resultado.stderr
            return jsonify({"status": "success" if resultado.returncode == 0 else "error",
                            "output": salida.strip()})
        except subprocess.TimeoutExpired:
            return jsonify({"status": "error", "output": "Comando interrumpido por tiempo (120s)."})
    else:
        return jsonify({"status": "error", "output": "No se generó ningún comando."})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=7000)
