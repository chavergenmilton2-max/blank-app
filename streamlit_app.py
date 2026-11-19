import os
from datetime import datetime
from google import genai
from google.genai import types
import streamlit as st

st.set_page_config(
    page_title="Sistema Clínico SOAP IA",
    page_icon="🩺",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# --- ESTILO VISUAL MÉDICO PROFESIONAL ---
st.markdown(
    """
    <style>
    .stApp {
        background-color: #F4F8FB;
    }
    .soap-header {
        background: linear-gradient(135deg, #0D47A1 0%, #1976D2 100%);
        padding: 1.4rem;
        border-radius: 14px;
        color: white;
        text-align: center;
        margin-bottom: 1.2rem;
        box-shadow: 0 4px 12px rgba(13, 71, 161, 0.15);
    }
    .soap-header h1 {
        color: white;
        font-size: 1.65rem;
        margin: 0;
    }
    .soap-header p {
        color: #E3F2FD;
        font-size: 0.95rem;
        margin-top: 0.35rem;
        margin-bottom: 0;
    }
    .soap-card {
        background-color: #FFFFFF;
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
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- BLOQUEO POR CONTRASEÑA ---
CLAVE_ACCESO = st.secrets.get("APP_PASSWORD", "SOAP2026")

if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

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
        if clave_ingresada == CLAVE_ACCESO:
            st.session_state.autenticado = True
            st.rerun()
        else:
            st.error("Código incorrecto. Verifica e intenta de nuevo.")
    st.stop()
# ------------------------------

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

client = genai.Client(api_key=api_key)
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

    fecha_archivo = datetime.now().strftime("%Y%m%d_%H%M")
    st.download_button(
        label="📥 Descargar Nota SOAP (.txt)",
        data=st.session_state.reporte_soap,
        file_name=f"Nota_SOAP_{fecha_archivo}.txt",
        mime="text/plain",
    )