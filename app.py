import streamlit as st
import streamlit.components.v1 as components
import paho.mqtt.client as mqtt
import json
import time
import random

WOKWI_PROJECT_ID = "479234255516779521"

st.set_page_config(
    page_title="Control de Actuadores // Gemelo Digital",
    page_icon="⚡",
    layout="wide",
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

.block-container {
    max-width: 1400px !important;
    padding-top: 1.2rem !important;
    padding-bottom: 2rem !important;
}

.actuator-card {
    background: linear-gradient(145deg, #0d152d 0%, #070d1e 100%);
    border: 1px solid rgba(56, 189, 248, 0.25);
    border-top: 3px solid #38bdf8;
    border-radius: 10px;
    padding: 1.3rem;
    margin-bottom: 1.1rem;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
}

.actuator-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.78rem;
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
# GATEWAY DE ACTUADORES MQTT
# ==============================================================================
def create_mqtt_client(client_prefix: str) -> mqtt.Client:
    cid = f"{client_prefix}_{int(time.time())}_{random.randint(1000, 9999)}"
    try:
        return mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2, client_id=cid)
    except (AttributeError, TypeError):
        return mqtt.Client(client_id=cid, clean_session=True)

class IoTActuatorGateway:
    def __init__(self, broker: str = "broker.mqttdashboard.com", port: int = 1883, device_id: str = "esp32_main"):
        self.broker = broker
        self.port = port
        self.device_id = device_id
        self.topic_digital = f"devices/{device_id}/cmd/digital"
        self.topic_analog = f"devices/{device_id}/cmd/analog"
        self.history = []

        self._client = create_mqtt_client("Streamlit_Actuators")
        try:
            self._client.connect(self.broker, self.port, keepalive=30)
            self._client.loop_start()
        except Exception:
            pass

    def send_digital(self, state: bool) -> bool:
        cmd_str = "ON" if state else "OFF"
        info = self._client.publish(self.topic_digital, json.dumps({"state": cmd_str}), qos=1)
        self.history.append(f"{time.strftime('%H:%M:%S')} — ACTUADOR DIGITAL: {cmd_str}")
        return info.rc == mqtt.MQTT_ERR_SUCCESS

    def send_analog(self, angle: int) -> bool:
        angle = max(0, min(180, int(angle)))
        info = self._client.publish(self.topic_analog, json.dumps({"angle": angle}), qos=1)
        self.history.append(f"{time.strftime('%H:%M:%S')} — ACTUADOR ANALÓGICO: {angle}°")
        return info.rc == mqtt.MQTT_ERR_SUCCESS

@st.cache_resource
def get_actuator_gateway() -> IoTActuatorGateway:
    return IoTActuatorGateway()

gateway = get_actuator_gateway()

if 'led_state' not in st.session_state:
    st.session_state.led_state = False
if 'servo_angle' not in st.session_state:
    st.session_state.servo_angle = 0

# ==============================================================================
# ENCABEZADO Y PANTALLA DIVIDIDA
# ==============================================================================
st.title("⚡ Control de Actuadores // Gemelo Digital")
st.caption(f"Despacho directo de órdenes hacia `{gateway.device_id}` a través de socket persistente")

col_controls, col_twin = st.columns([1, 1.35], gap="large")

with col_controls:
    # 1. CANAL DIGITAL
    with st.container():
        color_led = "#2dd4bf" if st.session_state.led_state else "#94a3b8"
        str_led = "ACTIVADO [ON]" if st.session_state.led_state else "DESACTIVADO [OFF]"
        
        st.markdown(f"""
        <div class="actuator-card">
            <div class="actuator-label">Canal Digital (Matriz LED): <span style="color:{color_led}; font-weight:700;">{str_led}</span></div>
        </div>
        """, unsafe_allow_html=True)
        
        b1, b2 = st.columns(2)
        with b1:
            if st.button("🟢 Activar [ON]", use_container_width=True):
                if gateway.send_digital(True):
                    st.session_state.led_state = True
                    st.rerun()
        with b2:
            if st.button("🔴 Desactivar [OFF]", use_container_width=True):
                if gateway.send_digital(False):
                    st.session_state.led_state = False
                    st.rerun()

    # 2. CANAL ANALÓGICO
    with st.container():
        st.markdown("""
        <div class="actuator-card">
            <div class="actuator-label">Canal Analógico (Servomotor SG90)</div>
        </div>
        """, unsafe_allow_html=True)
        
        val_deg = st.slider("Posición Angular (0° a 180°):", 0, 180, st.session_state.servo_angle, step=5)
        if st.button("🚀 Transmitir Calibración Angular", use_container_width=True):
            if gateway.send_analog(val_deg):
                st.session_state.servo_angle = val_deg
                st.success(f"Servomotor comandado a {val_deg}°")

    with st.expander("Registro de Órdenes Despachadas", expanded=False):
        for entry in reversed(gateway.history[-6:]):
            st.text(entry)

with col_twin:
    components.html(
        f"""
        <div style="background: linear-gradient(145deg, #0d152d 0%, #080d1e 100%);
                    border: 1px solid rgba(56, 189, 248, 0.28);
                    border-top: 3px solid #38bdf8;
                    border-radius: 12px;
                    overflow: hidden;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.7), 0 0 20px rgba(56,189,248,0.12);">
            <div style="display: flex; justify-content: space-between; align-items: center;
                        padding: 10px 16px; background: rgba(6, 9, 19, 0.9);
                        border-bottom: 1px solid rgba(56, 189, 248, 0.2);
                        font-family: 'JetBrains Mono', monospace; font-size: 0.72rem;">
                <div style="color: #cbd5e1; display: flex; align-items: center; gap: 8px;">
                    <span style="color: #38bdf8;">✦</span> GEMELO DIGITAL // ESP32 WOKWI
                </div>
                <div style="color: #2dd4bf; display: flex; align-items: center; gap: 6px;">
                    <span style="display:inline-block; width:7px; height:7px; border-radius:50%; background:#2dd4bf; box-shadow:0 0 8px #2dd4bf;"></span>
                    CANAL ACTIVO
                </div>
            </div>
            <iframe 
                src="https://wokwi.com/projects/{WOKWI_PROJECT_ID}?embed=1&view=diagram" 
                width="100%" 
                height="530" 
                style="border: none; display: block; background: #0c1222;"
                allow="fullscreen; autoplay">
            </iframe>
        </div>
        """,
        height=580
    )
