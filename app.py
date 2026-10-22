import streamlit as st
import paho.mqtt.client as mqtt
import json
import time
import random
import string

# ------------------------------------------------------------------
# CONFIGURACIÓN & ESTILOS KROV NOIR
# ------------------------------------------------------------------
st.set_page_config(
    page_title="Krov Core // Actuadores Ciberfísicos",
    page_icon="⚡",
    layout="centered"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Plus+Jakarta+Sans:wght@400;600;700&display=swap');

html, body, [data-testid="stAppViewContainer"], .stApp {
    background-color: #04060a !important;
    color: #e2e8f0 !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}

[data-testid="stHeader"] { background: transparent !important; }

.actuator-box {
    background: linear-gradient(145deg, rgba(10, 16, 26, 0.95) 0%, rgba(5, 8, 14, 0.98) 100%);
    border: 1px solid rgba(0, 240, 255, 0.3);
    border-radius: 10px;
    padding: 20px;
    margin-bottom: 16px;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.7);
}

.actuator-title {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.85rem;
    color: #00f0ff;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    margin-bottom: 12px;
}

.status-indicator {
    display: inline-block;
    width: 10px;
    height: 10px;
    border-radius: 50%;
    margin-right: 8px;
}

.status-on { background: #00ff88; box-shadow: 0 0 12px #00ff88; }
.status-off { background: #ef4444; box-shadow: 0 0 12px #ef4444; }

div.stButton > button {
    font-family: 'JetBrains Mono', monospace !important;
    font-weight: 700 !important;
    border-radius: 6px !important;
    transition: all 0.2s ease !important;
}
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------
# ESTADO DE SESIÓN
# ------------------------------------------------------------------
if 'led_state' not in st.session_state:
    st.session_state.led_state = "OFF"
if 'servo_angle' not in st.session_state:
    st.session_state.servo_angle = 0
if 'command_count' not in st.session_state:
    st.session_state.command_count = 0
if 'audit_log' not in st.session_state:
    st.session_state.audit_log = []

# ------------------------------------------------------------------
# PUBLICADOR MQTT AGNOSTICO
# ------------------------------------------------------------------
def get_mqtt_client():
    cid = f"Krov_Actuator_{''.join(random.choices(string.ascii_letters + string.digits, k=6))}"
    try:
        import paho.mqtt.enums as mqtt_enums
        return mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=cid)
    except Exception:
        try:
            return mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id=cid)
        except Exception:
            return mqtt.Client(client_id=cid)

def publicar_comando(broker, port, topic, payload_dict):
    try:
        c = get_mqtt_client()
        c.connect(broker, port, keepalive=15)
        c.loop_start()
        msg_str = json.dumps(payload_dict)
        info = c.publish(topic, msg_str, qos=1)
        info.wait_for_publish(timeout=3.0)
        c.loop_stop()
        c.disconnect()
        return True, msg_str
    except Exception as e:
        return False, str(e)

# ------------------------------------------------------------------
# CONFIGURACIÓN DE TÓPICOS (WOKWI SEND_CMQTT COMPATIBLE)
# ------------------------------------------------------------------
with st.sidebar:
    st.markdown("**PARÁMETROS DEL ENLACE**")
    broker = st.text_input("Broker:", value="broker.mqttdashboard.com")
    port = st.number_input("Puerto:", value=1883)
    
    st.markdown("---")
    st.markdown("**MAPEO DE TÓPICOS WOKWI**")
    # Compatible con send_cmqtt (cmqtt_s / cmqtt_a) o lizalda/
    prefijo = st.text_input("Prefijo de Usuario (opcional):", value="")
    base_s = f"{prefijo.strip() + '/' if prefijo.strip() else ''}cmqtt_s"
    base_a = f"{prefijo.strip() + '/' if prefijo.strip() else ''}cmqtt_a"
    topic_digital = st.text_input("Tópico LED (Digital):", value=base_s)
    topic_analog = st.text_input("Tópico Servo (Analógico):", value=base_a)

st.title("⚡ Control de Actuadores Ciberfísicos")
st.caption("Consola táctica Krov para control de microcontroladores y servomotores Wokwi")

# ------------------------------------------------------------------
# INTERFAZ 1: CANAL DIGITAL (LED)
# ------------------------------------------------------------------
with st.container():
    st.markdown('<div class="actuator-box">', unsafe_allow_html=True)
    status_class = "status-on" if st.session_state.led_state == "ON" else "status-off"
    st.markdown(f'<div class="actuator-title"><span class="status-indicator {status_class}"></span>ACTUADOR DIGITAL // MATRIZ LED: {st.session_state.led_state}</div>', unsafe_allow_html=True)
    
    c_on, c_off = st.columns(2)
    with c_on:
        if st.button("🟢 IGNICIÓN [ON]", use_container_width=True):
            ok, resp = publicar_comando(broker, int(port), topic_digital, {"Act1": "ON"})
            if ok:
                st.session_state.led_state = "ON"
                st.session_state.command_count += 1
                st.session_state.audit_log.append(f"{time.strftime('%H:%M:%S')} - LED -> ON")
                st.rerun()
            else:
                st.error(f"Error de enlace: {resp}")
    with c_off:
        if st.button("🔴 DESACTIVAR [OFF]", use_container_width=True):
            ok, resp = publicar_comando(broker, int(port), topic_digital, {"Act1": "OFF"})
            if ok:
                st.session_state.led_state = "OFF"
                st.session_state.command_count += 1
                st.session_state.audit_log.append(f"{time.strftime('%H:%M:%S')} - LED -> OFF")
                st.rerun()
            else:
                st.error(f"Error de enlace: {resp}")
    st.markdown('</div>', unsafe_allow_html=True)

# ------------------------------------------------------------------
# INTERFAZ 2: CANAL ANALÓGICO (SERVOMOTOR)
# ------------------------------------------------------------------
with st.container():
    st.markdown('<div class="actuator-box">', unsafe_allow_html=True)
    st.markdown('<div class="actuator-title">ACTUADOR ANALÓGICO // CONTROL ANGULAR DE SERVO</div>', unsafe_allow_html=True)
    
    val_slider = st.slider("Magnitud de Control (0 a 100):", 0.0, 100.0, float(st.session_state.servo_angle / 1.8), step=1.0)
    angulo_calculado = int(val_slider * 1.8)
    
    st.caption(f"Posición estimada del vástago: **{angulo_calculado}°** (Rango 0° - 180°)")
    
    if st.button("🚀 Transmitir Calibración Angular", use_container_width=True):
        ok, resp = publicar_comando(broker, int(port), topic_analog, {"Analog": float(val_slider)})
        if ok:
            st.session_state.servo_angle = angulo_calculado
            st.session_state.command_count += 1
            st.session_state.audit_log.append(f"{time.strftime('%H:%M:%S')} - SERVO -> {val_slider:.1f} ({angulo_calculado}°)")
            st.success(f"Comando analógico transmitido al ESP32: {val_slider:.1f} ({angulo_calculado}°)")
        else:
            st.error(f"Error al transmitir: {resp}")
            
    st.markdown('</div>', unsafe_allow_html=True)

# Registro de Comandos (Audit Log)
with st.expander("📜 Bitácora de Comandos Ciberfísicos", expanded=False):
    st.write(f"Total comandos emitidos: **{st.session_state.command_count}**")
    for log_item in reversed(st.session_state.audit_log[-6:]):
        st.text(log_item)
