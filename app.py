import streamlit as st
import paho.mqtt.client as mqtt
import json
import time
import threading

st.set_page_config(
    page_title="Control de Actuadores IoT",
    page_icon="⚡",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Plus+Jakarta+Sans:wght@400;600;700&display=swap');

html, body, [data-testid="stAppViewContainer"], .stApp {
    background-color: #060913 !important;
    color: #e2e8f0 !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}

[data-testid="stHeader"] { background: transparent !important; }
[data-testid="stSidebar"] { display: none !important; }

div[data-testid="stVerticalBlockBorderWrapper"] {
    background: linear-gradient(145deg, #0d152d 0%, #070d1e 100%) !important;
    border: 1px solid rgba(56, 189, 248, 0.25) !important;
    border-top: 3px solid #38bdf8 !important;
    border-radius: 10px !important;
    padding: 1.2rem !important;
    margin-bottom: 1.2rem !important;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5) !important;
}

.actuator-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8rem;
    color: #38bdf8;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    font-weight: 600;
    margin-bottom: 8px;
}

div.stButton > button {
    font-family: 'JetBrains Mono', monospace !important;
    font-weight: 600 !important;
    border-radius: 6px !important;
    transition: all 0.2s ease !important;
}
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# CLASE MONOLÍTICA: CONTROLADOR DE COMANDOS MQTT
# ==============================================================================
class IoTActuatorGateway:
    def __init__(self, broker: str = "broker.mqttdashboard.com", port: int = 1883, device_id: str = "esp32_main"):
        self.broker = broker
        self.port = port
        self.device_id = device_id
        self.topic_digital = f"devices/{device_id}/cmd/digital"
        self.topic_analog = f"devices/{device_id}/cmd/analog"

        self._lock = threading.Lock()
        self.connected = False
        self.history = []

        self._client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=f"Client_Actuators_{device_id}"
        )
        self._client.on_connect = lambda c, u, f, rc, p=None: setattr(self, 'connected', (rc == 0))
        self._client.on_disconnect = lambda c, u, f, rc, p=None: setattr(self, 'connected', False)
        
        try:
            self._client.connect(self.broker, self.port, keepalive=30)
            self._client.loop_start()
        except Exception:
            self.connected = False

    def send_digital(self, state: bool) -> bool:
        cmd_str = "ON" if state else "OFF"
        payload = json.dumps({"state": cmd_str})
        info = self._client.publish(self.topic_digital, payload, qos=1)
        with self._lock:
            self.history.append(f"{time.strftime('%H:%M:%S')} — ACTUADOR DIGITAL: {cmd_str}")
        return info.rc == mqtt.MQTT_ERR_SUCCESS

    def send_analog(self, angle: int) -> bool:
        angle = max(0, min(180, int(angle)))
        payload = json.dumps({"angle": angle})
        info = self._client.publish(self.topic_analog, payload, qos=1)
        with self._lock:
            self.history.append(f"{time.strftime('%H:%M:%S')} — ACTUADOR ANALÓGICO: {angle}°")
        return info.rc == mqtt.MQTT_ERR_SUCCESS

@st.cache_resource
def get_actuator_gateway() -> IoTActuatorGateway:
    return IoTActuatorGateway()

gateway = get_actuator_gateway()

# Estado local del UI
if 'led_state' not in st.session_state:
    st.session_state.led_state = False
if 'servo_angle' not in st.session_state:
    st.session_state.servo_angle = 0

st.title("⚡ Control de Actuadores")
st.caption(f"Dispositivo de destino: `{gateway.device_id}` | Socket persistente")

# 1. ACTUADOR DIGITAL
with st.container(border=True):
    color_led = "#2dd4bf" if st.session_state.led_state else "#94a3b8"
    str_led = "ACTIVADO [ON]" if st.session_state.led_state else "DESACTIVADO [OFF]"
    st.markdown(f'<div class="actuator-label">Canal Digital (LED / Relé): <span style="color:{color_led};">{str_led}</span></div>', unsafe_allow_html=True)
    
    c_on, c_off = st.columns(2)
    with c_on:
        if st.button("Activar [ON]", use_container_width=True):
            if gateway.send_digital(True):
                st.session_state.led_state = True
                st.rerun()
    with c_off:
        if st.button("Desactivar [OFF]", use_container_width=True):
            if gateway.send_digital(False):
                st.session_state.led_state = False
                st.rerun()

# 2. ACTUADOR ANALÓGICO
with st.container(border=True):
    st.markdown('<div class="actuator-label">Canal Analógico (Servomotor)</div>', unsafe_allow_html=True)
    
    val_deg = st.slider("Posición Angular (0° a 180°):", 0, 180, st.session_state.servo_angle, step=5)
    
    if st.button("Transmitir Calibración Angular", use_container_width=True):
        if gateway.send_analog(val_deg):
            st.session_state.servo_angle = val_deg
            st.success(f"Comando de posición ({val_deg}°) despachado al dispositivo.")

with st.expander("Registro de Órdenes Despachadas", expanded=False):
    for entry in reversed(gateway.history[-8:]):
        st.text(entry)
