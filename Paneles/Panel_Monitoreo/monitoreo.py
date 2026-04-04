import subprocess
import serial
import time
import threading
import urllib.request
import urllib.parse
import re
from flask import Flask, jsonify, request, render_template
from collections import deque

app = Flask(__name__)

# --- CONFIGURACIÓN ---
ANSIBLE_HOSTS = "/home/cluster0/Temperatura/hosts"
ARDUINO_PORT = "/dev/ttyUSB0"
BAUD_RATE = 9600
NODOS_EXCLUIDOS = ["10.4.8.10", "cluster0"]

# Lista completa de nodos del clúster (según tu inventario)
NODOS_CONOCIDOS = [
    "10.4.8.11", "10.4.8.12", "10.4.8.13", "10.4.8.14",
    "10.4.8.15", "10.4.8.16", "10.4.8.17", "10.4.8.18",
    "10.4.8.21"
]

WA_PHONE = "#Número_de_celular" #Cambiar estos dos según su número y token
WA_APIKEY = "#Api"
TEMP_ALARMA = 60.0
COOLDOWN_ALARMA = 1800
MAX_FALLOS_RED = 3
# ------------------------------

# Estado inicial
estado = {
    "modo": "auto",
    "nodos": {ip: {"temp": 0.0, "cpu": 0.0} for ip in NODOS_CONOCIDOS},
    "promedios": {"temp": 0.0, "cpu": 0.0},
    "temp_max": 0.0,
    "ultimo_aviso": 0,
    "estado_nodos": {ip: True for ip in NODOS_CONOCIDOS},   # Asumimos online hasta que fallen
    "fallos_nodos": {ip: 0 for ip in NODOS_CONOCIDOS},
    "pines": {
        "11": {"nombre": "Ventilador 1", "valor": 0, "tipo": "pwm"},
        "10": {"nombre": "Ventilador 2", "valor": 0, "tipo": "pwm"},
        "6":  {"nombre": "Ventilador 3", "valor": 0, "tipo": "pwm"},
        "5":  {"nombre": "Ventilador 4", "valor": 0, "tipo": "pwm"},
        "9":  {"nombre": "Relé Principal", "valor": 0, "tipo": "digital"}
    }
}

# Histórico para gráficas (máximo 120 puntos = 20 minutos a 10s)
historico = {ip: deque(maxlen=120) for ip in NODOS_CONOCIDOS}

# Conexión Arduino
try:
    arduino = serial.Serial(ARDUINO_PORT, BAUD_RATE, timeout=1)
    time.sleep(2)
except Exception as e:
    print(f"Advertencia: No se pudo conectar al Arduino: {e}")
    arduino = None

def enviar_comando_arduino(pin, valor_logico):
    if arduino and arduino.is_open:
        valor_fisico = int(valor_logico)
        if pin in ["11", "10", "6", "5"]:
            valor_fisico = 255 - valor_fisico
        comando = f"{pin}:{valor_fisico}\n"
        arduino.write(comando.encode('utf-8'))

def enviar_alerta_whatsapp(mensaje):
    url = f"https://api.callmebot.com/whatsapp.php?phone={WA_PHONE}&text={urllib.parse.quote(mensaje)}&apikey={WA_APIKEY}"
    try:
        urllib.request.urlopen(url, timeout=5)
        print(f"✅ Notificación enviada.")
    except Exception as e:
        print(f"❌ Error enviando WhatsApp: {e}")

def parsear_cpu(linea):
    """
    Parsea una línea como:
    '%Cpu(s):  3,3 us,  1,7 sy,  0,0 ni, 95,0 id, ...'
    Retorna el porcentaje de CPU usado (us + sy + ni)
    """
    # Buscar números con coma decimal
    match_us = re.search(r'(\d+[,.]?\d*)\s*us', linea)
    match_sy = re.search(r'(\d+[,.]?\d*)\s*sy', linea)
    match_ni = re.search(r'(\d+[,.]?\d*)\s*ni', linea)
    
    def to_float(s):
        return float(s.replace(',', '.'))
    
    us = to_float(match_us.group(1)) if match_us else 0.0
    sy = to_float(match_sy.group(1)) if match_sy else 0.0
    ni = to_float(match_ni.group(1)) if match_ni else 0.0
    return us + sy + ni

def hilo_ansible_y_auto():
    # Inicializar pines
    for pin in ["11", "10", "6", "5", "9"]:
        enviar_comando_arduino(pin, estado["pines"][pin]["valor"])

    # Comando ANSIBLE que devuelve temperatura y la línea de CPU
    comando_shell = """
temp=$(cat /sys/class/thermal/thermal_zone0/temp 2>/dev/null || echo 0)
cpu_line=$(top -bn1 | grep 'Cpu(s)')
echo "$temp|$cpu_line"
"""
    while True:
        try:
            cmd = ["/usr/bin/ansible", "all", "-i", ANSIBLE_HOSTS, "-m", "shell", "-a", comando_shell]
            resultado = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            lineas = resultado.stdout.strip().split('\n')
            
            nodos_data = {}
            nodos_vistos = set()
            nodo_actual = None
            buffer_linea = ""
            
            for linea in lineas:
                # Detectar nodo unreachable
                if " | UNREACHABLE" in linea:
                    nodo = linea.split(" | ")[0].strip()
                    if nodo in NODOS_EXCLUIDOS:
                        continue
                    nodos_vistos.add(nodo)
                    estado["fallos_nodos"][nodo] = estado["fallos_nodos"].get(nodo, 0) + 1
                    if estado["fallos_nodos"][nodo] >= MAX_FALLOS_RED:
                        if estado["estado_nodos"].get(nodo, True):
                            enviar_alerta_whatsapp(f"⚠️ ALERTA DE RED\nEl nodo {nodo} se ha CAÍDO.")
                            estado["estado_nodos"][nodo] = False
                    nodo_actual = None
                    continue
                
                # Detectar nodo exitoso
                if " | SUCCESS" in linea or " | CHANGED" in linea:
                    nodo = linea.split(" | ")[0].strip()
                    if nodo in NODOS_EXCLUIDOS:
                        nodo_actual = None
                        continue
                    nodos_vistos.add(nodo)
                    nodo_actual = nodo
                    # Resetear fallos
                    estado["fallos_nodos"][nodo] = 0
                    if not estado["estado_nodos"].get(nodo, False):
                        enviar_alerta_whatsapp(f"✅ NODO RECUPERADO\nEl nodo {nodo} vuelve a estar ONLINE.")
                        estado["estado_nodos"][nodo] = True
                    continue
                
                # Procesar línea de datos (temp|linea_cpu)
                if nodo_actual and linea.strip():
                    partes = linea.split('|')
                    if len(partes) >= 2:
                        try:
                            temp_raw = partes[0].strip()
                            temp = int(temp_raw) / 1000.0 if temp_raw.isdigit() else 0.0
                            cpu_line = partes[1]
                            cpu = parsear_cpu(cpu_line)
                            nodos_data[nodo_actual] = {"temp": temp, "cpu": cpu}
                            # Guardar histórico
                            ts = time.time()
                            historico[nodo_actual].append((ts, temp, cpu))
                        except Exception as e:
                            print(f"Error parseando datos de {nodo_actual}: {e}")
                    nodo_actual = None
            
            # Asegurar que todos los nodos conocidos tengan entrada en nodos_data
            for nodo in NODOS_CONOCIDOS:
                if nodo not in nodos_data:
                    if nodo in estado["nodos"]:
                        nodos_data[nodo] = estado["nodos"][nodo]
                    else:
                        nodos_data[nodo] = {"temp": 0.0, "cpu": 0.0}
                    # Si no fue visto, incrementar fallos (ya se hizo arriba para unreachable, pero aquí también)
                    if nodo not in nodos_vistos:
                        estado["fallos_nodos"][nodo] = estado["fallos_nodos"].get(nodo, 0) + 1
                        if estado["fallos_nodos"][nodo] >= MAX_FALLOS_RED:
                            estado["estado_nodos"][nodo] = False
                else:
                    # Si fue visto y tiene datos, está online
                    estado["estado_nodos"][nodo] = True
            
            # Actualizar estado global
            estado["nodos"] = nodos_data
            temps = [d["temp"] for d in nodos_data.values() if d["temp"] > 0]
            cpus = [d["cpu"] for d in nodos_data.values() if d["cpu"] > 0]
            estado["temp_max"] = max(temps) if temps else 0
            estado["promedios"]["temp"] = sum(temps) / len(temps) if temps else 0
            estado["promedios"]["cpu"] = sum(cpus) / len(cpus) if cpus else 0
            
            # Alarma térmica
            if estado["temp_max"] >= TEMP_ALARMA:
                ahora = time.time()
                if ahora - estado["ultimo_aviso"] > COOLDOWN_ALARMA:
                    nodos_calientes = [n for n, d in nodos_data.items() if d["temp"] >= TEMP_ALARMA]
                    nodos_str = ", ".join(nodos_calientes)
                    enviar_alerta_whatsapp(f"🔥 ALERTA TÉRMICA 🔥\nTemp máxima: {estado['temp_max']:.1f}°C\nNodos: {nodos_str}")
                    estado["ultimo_aviso"] = ahora
            
            # Control automático de ventiladores
            if estado["modo"] == "auto":
                t_max = estado["temp_max"]
                if t_max < 40:
                    pwm_auto = 0
                elif t_max >= 75:
                    pwm_auto = 255
                else:
                    ratio = (t_max - 40) / 35.0
                    pwm_auto = int((ratio ** 2) * 255)
                for pin in ["11", "10", "6", "5"]:
                    estado["pines"][pin]["valor"] = pwm_auto
                    enviar_comando_arduino(pin, pwm_auto)
                    
        except Exception as e:
            print(f"Error en bucle principal: {e}")
        
        time.sleep(10)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/lite")
def lite():
    return render_template("lite.html")

@app.route("/api/estado", methods=["GET"])
def get_estado():
    return jsonify(estado)

@app.route("/api/historico/<nodo>", methods=["GET"])
def get_historico(nodo):
    if nodo in historico:
        data = [{"timestamp": t, "temp": temp, "cpu": cpu} for t, temp, cpu in historico[nodo]]
        return jsonify(data)
    return jsonify([])

@app.route("/api/modo", methods=["POST"])
def set_modo():
    data = request.json
    if "modo" in data and data["modo"] in ["auto", "manual"]:
        estado["modo"] = data["modo"]
    return jsonify({"status": "ok"})

@app.route("/api/comando", methods=["POST"])
def set_comando():
    data = request.json
    pin = str(data.get("pin"))
    valor = data.get("valor")
    if pin in estado["pines"]:
        if estado["modo"] == "auto" and estado["pines"][pin]["tipo"] == "pwm":
            return jsonify({"status": "bloqueado por modo auto"}), 403
        estado["pines"][pin]["valor"] = valor
        enviar_comando_arduino(pin, valor)
        return jsonify({"status": "ok"})
    return jsonify({"status": "error"}), 400

if __name__ == "__main__":
    hilo = threading.Thread(target=hilo_ansible_y_auto, daemon=True)
    hilo.start()
    print("\n[🚀] Servidor Térmico Iniciado (CPU parseada desde top -bn1)\n")
    app.run(host="0.0.0.0", port=9000)
