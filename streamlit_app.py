from datetime import date, datetime, timezone
import json
import os
import urllib.parse
import urllib.request
import uuid
from google import genai
from google.genai import types
import streamlit as st

st.set_page_config(
    page_title="Sistema Clínico SOAP IA",
    page_icon="🩺",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# --- ESTILO MÉDICO LIMPIO ORIGINAL ---
st.markdown(
    """
    <style>
    .stApp {
        background-color: #F4F8FB !important;
        color: #111827 !important;
    }
    .stApp p, .stApp li, .stApp span, .stApp label, .stApp h1, .stApp h2, .stApp h3, .stApp h4 {
        color: #111827 !important;
    }
    .stTextArea textarea, .stTextInput input {
        background-color: #FFFFFF !important;
        color: #111827 !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 10px !important;
    }
    .soap-header {
        background: linear-gradient(135deg, #0D47A1 0%, #1976D2 100%);
        padding: 1.4rem;
        border-radius: 14px;
        text-align: center;
        margin-bottom: 1.2rem;
        box-shadow: 0 4px 12px rgba(13, 71, 161, 0.15);
    }
    .soap-header h1 {
        color: #FFFFFF !important;
        font-size: 1.65rem;
        margin: 0;
    }
    .soap-header p {
        color: #E3F2FD !important;
        font-size: 0.95rem;
        margin-top: 0.35rem;
        margin-bottom: 0;
    }
    .soap-card {
        background-color: #FFFFFF !important;
        color: #111827 !important;
        padding: 1.25rem;
        border-radius: 12px;
        border-left: 5px solid #1976D2;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
        margin-top: 1rem;
    }
    div.stButton > button:first-child {
        width: 100%;
        border-radius: 10px;
        font-weight: 600;
        padding: 0.65rem 1rem;
        background-color: #C62828 !important;
        color: #FFFFFF !important;
        border: none !important;
    }
    div.stButton > button:first-child p {
        color: #FFFFFF !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- CONEXIÓN A SUPABASE (CONTROL DE LICENCIAS POR USUARIO) ---
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "").strip().rstrip("/")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "").strip()


def supabase_request(method, path, payload=None):
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    if SUPABASE_KEY.startswith("eyJ"):
        headers["Authorization"] = f"Bearer {SUPABASE_KEY}"
    data = json.dumps(payload).encode("utf-8") if payload else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=10) as resp:
        body = resp.read().decode("utf-8")
        return json.loads(body) if body else []


def validar_licencia(codigo):
    codigo_limpio = codigo.strip()
    clave_maestra = st.secrets.get("APP_PASSWORD", "SOAP2026")

    if not SUPABASE_URL or not SUPABASE_KEY:
        if codigo_limpio == clave_maestra:
            return True, "Usuario Administrador", "local"
        return False, "Código incorrecto.", None

    try:
        encoded = urllib.parse.quote(codigo_limpio)
        filas = supabase_request("GET", f"licencias?codigo_licencia=eq.{encoded}&select=*")
        if not filas:
            if codigo_limpio == clave_maestra:
                return True, "Usuario Administrador", "local"
            return False, "Código de licencia no encontrado.", None

        lic = filas[0]
        if not lic.get("activo"):
            return False, "Esta licencia está suspendida o inactiva. Contacta al administrador.", None

        vence = lic.get("fecha_vencimiento")
        if vence and date.fromisoformat(vence) < date.today():
            return False, f"Tu licencia venció el {vence}. Renueva tu suscripción.", None

        token = str(uuid.uuid4())
        ahora = datetime.now(timezone.utc).isoformat()
        supabase_request(
            "PATCH",
            f"licencias?id=eq.{lic['id']}",
            {"sesion_actual": token, "ultimo_acceso": ahora},
        )
        return True, lic.get("medico_nombre", "Médico Autorizado"), token

    except Exception:
        if codigo_limpio == clave_maestra:
            return True, "Usuario Administrador", "local"
        return False, "No se pudo verificar la licencia. Intenta nuevamente.", None


def verificar_sesion_unica(codigo, token):
    if not SUPABASE_URL or not SUPABASE_KEY or token == "local":
        return True
    try:
        encoded = urllib.parse.quote(codigo.strip())
        filas = supabase_request(
            "GET", f"licencias?codigo_licencia=eq.{encoded}&select=activo,sesion_actual"
        )
        if not filas or not filas[0].get("activo"):
            return False
        return filas[0].get("sesion_actual") == token
    except Exception:
        return True


if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
    st.session_state.medico_nombre = ""
    st.session_state.codigo_licencia = ""
    st.session_state.sesion_token = ""

if st.session_state.autenticado:
    if not verificar_sesion_unica(
        st.session_state.codigo_licencia, st.session_state.sesion_token
    ):
        st.session_state.autenticado = False
        st.warning("Se inició sesión con esta licencia en otro dispositivo. Vuelve a ingresar.")

if not st.session_state.autenticado:
    st.markdown(
        """
        <div class="soap-header">
            <h1>🔒 Sistema Clínico SOAP IA</h1>
            <p>Acceso exclusivo para personal médico autorizado</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    clave_ingresada = st.text_input("Ingresa tu código de acceso:", type="password")
    if st.button("🔓 Ingresar al Sistema", type="primary"):
        ok, msg, token = validar_licencia(clave_ingresada)
        if ok:
            st.session_state.autenticado = True
            st.session_state.medico_nombre = msg
            st.session_state.codigo_licencia = clave_ingresada.strip()
            st.session_state.sesion_token = token
            st.rerun()
        else:
            st.error(msg)
    st.stop()
# -------------------------------------------------------------

st.markdown(
    """
    <div class="soap-header">
        <h1>🩺 Sistema Clínico SOAP Inteligente</h1>
        <p>Asistente de documentación clínica por voz y texto</p>
    </div>
    """,
    unsafe_allow_html=True,
)

api_key = os.getenv("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY")
if not api_key:
    st.error("Falta configurar GEMINI_API_KEY en Secrets.")
    st.stop()

client = genai.Client(vertexai=True, api_key=api_key)
MODEL_NAME = "gemini-3.5-flash-lite"

PROMPT_SOAP = (
    "Actúa como un médico especialista y asistente clínico experto. Transforma la consulta "
    "en una nota estructurada estrictamente en formato SOAP (Subjetivo, Objetivo, Análisis, Plan), "
    "incluyendo posibles diagnósticos diferenciales y códigos CIE-10 orientativos al final del Análisis. "
    "Responde en español latinoamericano profesional y claro."
)

st.subheader("🎙️ Dictado de Consulta")
audio_dictado = st.audio_input("Toca el micrófono para grabar:")
consulta_texto = st.text_area(
    "📝 Notas escritas de la consulta (Opcional):",
    placeholder="Escribe aquí los síntomas, signos vitales, laboratorios o evolución...",
    height=130,
)

if "reporte_soap" not in st.session_state:
    st.session_state.reporte_soap = ""

if st.button("⚡ GENERAR REPORTE CLÍNICO SOAP", type="primary"):
    if audio_dictado is not None:
        with st.spinner("Analizando audio clínico y redactando nota SOAP..."):
            try:
                audio_bytes = audio_dictado.getvalue()
                mime_type = audio_dictado.type or "audio/wav"
                response = client.models.generate_content(
                    model=MODEL_NAME,
                    contents=[
                        types.Part.from_bytes(data=audio_bytes, mime_type=mime_type),
                        PROMPT_SOAP,
                    ],
                )
                st.session_state.reporte_soap = response.text or ""
                st.success("¡Reporte SOAP generado!")
            except Exception as e:
                st.error(f"Error con la IA: {e}")
    elif consulta_texto.strip():
        with st.spinner("Procesando nota clínica..."):
            try:
                response = client.models.generate_content(
                    model=MODEL_NAME,
                    contents=f"{PROMPT_SOAP}\n\nConsulta:\n{consulta_texto}",
                )
                st.session_state.reporte_soap = response.text or ""
                st.success("¡Reporte SOAP generado!")
            except Exception as e:
                st.error(f"Error con la IA: {e}")
    else:
        st.warning("Graba un audio o escribe una nota clínica primero.")

if st.session_state.reporte_soap:
    st.markdown('<div class="soap-card">', unsafe_allow_html=True)
    st.markdown("### 📋 Reporte SOAP Generado")
    st.markdown(st.session_state.reporte_soap)
    st.markdown("</div>", unsafe_allow_html=True)
    st.caption("Copia rápida con un toque:")
    st.code(st.session_state.reporte_soap, language=None)
