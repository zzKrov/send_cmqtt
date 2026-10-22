import streamlit as st
import paho.mqtt.client as mqtt
import json
import time
import random
import string

# ------------------------------------------------------------------
# CONFIGURACIÓN GENERAL
# ------------------------------------------------------------------
st.set_page_config(
    page_title="Krov Core // Actuadores Ciberfísicos",
    page_icon="⚡",
    layout="centered"
)

# ------------------------------------------------------------------
# ESTILOS KROV NOIR (ESTILIZACIÓN DE CONTENEDORES NATIVOS)
# ------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Plus+Jakarta+Sans:wght@400;600;700&display=swap');

html, body, [data-testid="stAppViewContainer"], .stApp {
    background-color: #04060a !important;
    color: #e2e8f0 !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}

[data-testid="stHeader"] { background: transparent !important; }

div[data-testid="stVerticalBlockBorderWrapper"] {
    background: linear-gradient(145deg, rgba(10, 16, 26, 0.95) 0%, rgba(5, 8, 14, 0.98) 100%) !important;
    border: 1px solid rgba(0, 240, 255, 0.28) !important;
    border-top: 3px solid #00f0ff !important;
    border-radius: 10px !important;
    padding: 1.2rem !important;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.75) !important;
    margin-bottom: 1.2rem !important;
}

.actuator-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.82rem;
    color: #00f0ff;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    font-weight: 700;
    margin-bottom: 8px;
}

div.stButton > button {
    font-family: 'JetBrains Mono', monospace !important;
    font-weight: 700 !important;
    border-radius: 6px !important;
    transition: all 0.2s ease !important;
}
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------
# ESTADO
# ------------------------------------------------------------------
if 'led_state' not in st.session_state:
    st.session_state.led_state = "OFF"
if 'servo_angle' not in st.session_state:
    st.session_state.servo_angle = 0
if 'cmd_count' not in st.session_state:
    st.session_state.cmd_count = 0
if 'log' not in st.session_state:
    st.session_state.log = []

# ------------------------------------------------------------------
# PUBLICADOR MQTT
# ------------------------------------------------------------------
def get_mqtt_client():
    cid = f"Krov_Actuator_{''.join(random.choices(string.ascii_letters + string.digits, k=6))}"
    try:
        return mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=cid)
    except Exception:
        try:
            return mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id=cid)
        except Exception:
            return mqtt.Client(client_id=cid)

def publicar_comando(broker, port, topic, payload):
    try:
        c = get_mqtt_client()
        c.connect(broker, port, keepalive=15)
        c.loop_start()
        msg_str = json.dumps(payload)
        info = c.publish(topic, msg_str, qos=1)
        info.wait_for_publish(timeout=2.5)
        c.loop_stop()
        c.disconnect()
        return True, msg_str
    except Exception as e:
        return False, str(e)

# ------------------------------------------------------------------
# BARRA LATERAL
# ------------------------------------------------------------------
with st.sidebar:
    st.markdown("### KROV // PARÁMETROS ENLACE")
    broker = st.text_input("Broker:", value="broker.mqttdashboard.com")
    port = st.number_input("Puerto:", value=1883)
    
    st.markdown("---")
    prefijo = st.text_input("Prefijo de Usuario / Wokwi (opcional):", value="")
    base_s = f"{prefijo.strip() + '/' if prefijo.strip() else ''}cmqtt_s"
    base_a = f"{prefijo.strip() + '/' if prefijo.strip() else ''}cmqtt_a"
    topic_digital = st.text_input("Tópico LED (Digital):", value=base_s)
    topic_analog = st.text_input("Tópico Servo (Analógico):", value=base_a)

st.title("⚡ Control de Actuadores Ciberfísicos")
st.caption("Consola táctica Krov para control de microcontroladores y servomotores Wokwi")

# ------------------------------------------------------------------
# ACTUADOR 1: CANAL DIGITAL (LED)
# Usando with st.container(border=True) -> CERO cajas vacías
# ------------------------------------------------------------------
with st.container(border=True):
    color_led = "#00ff88" if st.session_state.led_state == "ON" else "#ef4444"
    st.markdown(f'<div class="actuator-label">ACTUADOR DIGITAL // MATRIZ LED: <span style="color:{color_led}; font-weight:700;">{st.session_state.led_state}</span></div>', unsafe_allow_html=True)
    
    c_on, c_off = st.columns(2)
    with c_on:
        if st.button("🟢 IGNICIÓN [ON]", use_container_width=True):
            ok, resp = publicar_comando(broker, int(port), topic_digital, {"Act1": "ON"})
            if ok:
                st.session_state.led_state = "ON"
                st.session_state.cmd_count += 1
                st.session_state.log.append(f"{time.strftime('%H:%M:%S')} - LED -> ON")
                st.rerun()
            else:
                st.error(f"Error de enlace: {resp}")
    with c_off:
        if st.button("🔴 DESACTIVAR [OFF]", use_container_width=True):
            ok, resp = publicar_comando(broker, int(port), topic_digital, {"Act1": "OFF"})
            if ok:
                st.session_state.led_state = "OFF"
                st.session_state.cmd_count += 1
                st.session_state.log.append(f"{time.strftime('%H:%M:%S')} - LED -> OFF")
                st.rerun()
            else:
                st.error(f"Error de enlace: {resp}")

# ------------------------------------------------------------------
# ACTUADOR 2: CANAL ANALÓGICO (SERVOMOTOR)
# ------------------------------------------------------------------
with st.container(border=True):
    st.markdown('<div class="actuator-label">ACTUADOR ANALÓGICO // CONTROL ANGULAR DE SERVO</div>', unsafe_allow_html=True)
    
    val_slider = st.slider("Magnitud de Control (0 a 100):", 0.0, 100.0, float(st.session_state.servo_angle / 1.8), step=1.0)
    angulo = int(val_slider * 1.8)
    
    # Feedback visual gamificado
    if val_slider > 80:
        st.warning(f"⚠️ MODO OVERDRIVE ACTIVO: {angulo}° (Torsión máxima)")
    else:
        st.caption(f"Posición angular nominal: **{angulo}°** (Rango 0° - 180°)")
    
    if st.button("🚀 Transmitir Calibración Angular", use_container_width=True):
        ok, resp = publicar_comando(broker, int(port), topic_analog, {"Analog": float(val_slider)})
        if ok:
            st.session_state.servo_angle = angulo
            st.session_state.cmd_count += 1
            st.session_state.log.append(f"{time.strftime('%H:%M:%S')} - SERVO -> {val_slider:.1f} ({angulo}°)")
            st.success(f"Posición {angulo}° enviada correctamente al ESP32.")
        else:
            st.error(f"Falla de transmisión: {resp}")

# ------------------------------------------------------------------
# BITÁCORA TÁCTICA
# ------------------------------------------------------------------
with st.expander("📜 Bitácora de Comandos Ciberfísicos", expanded=False):
    st.write(f"Total comandos emitidos en la sesión: **{st.session_state.cmd_count}**")
    for item in reversed(st.session_state.log[-5:]):
        st.text(item)
