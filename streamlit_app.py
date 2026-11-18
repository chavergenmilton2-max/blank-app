import os
from google import genai
from google.genai import types
import streamlit as st

st.set_page_config(page_title="Sistema SOAP IA", page_icon="🩺")
st.title("🩺 Sistema Clínico SOAP Inteligente")
st.write("Herramienta de automatización clínica para médicos.")
st.divider()

api_key = os.getenv("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY")

if not api_key:
    st.error("Falta configurar GEMINI_API_KEY en el entorno o en st.secrets.")
    st.stop()

client = genai.Client(api_key=api_key)
MODEL_NAME = "gemini-3.5-flash-lite"

PROMPT_SOAP = (
    "Actúa como un asistente médico experto. Transforma la consulta en una nota "
    "estructurada estrictamente en formato SOAP (Subjetivo, Objetivo, Análisis, Plan). "
    "Responde en español latinoamericano profesional."
)

st.subheader("🎙️ Grabación de Consulta Médica")
audio_dictado = st.audio_input("Graba tu voz aquí:")
consulta_texto = st.text_area("Notas escritas de la consulta (Opcional):", value="")
st.divider()

if "reporte_soap" not in st.session_state:
    st.session_state.reporte_soap = ""

if st.button("⚡ GENERAR REPORTE CLÍNICO SOAP"):
    if audio_dictado is not None:
        with st.spinner("Procesando el audio y generando el reporte SOAP..."):
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
                st.success("¡Reporte generado con éxito!")
            except Exception as e:
                st.error(f"Error con la IA: {e}")
    elif consulta_texto.strip():
        with st.spinner("Procesando la nota escrita..."):
            try:
                response = client.models.generate_content(
                    model=MODEL_NAME,
                    contents=f"{PROMPT_SOAP}\n\nConsulta:\n{consulta_texto}",
                )
                st.session_state.reporte_soap = response.text or ""
                st.success("¡Reporte generado con éxito!")
            except Exception as e:
                st.error(f"Error con la IA: {e}")
    else:
        st.warning("Por favor, graba un audio o escribe una nota clínica primero.")

if st.session_state.reporte_soap:
    st.markdown("### Reporte SOAP")
    st.markdown(st.session_state.reporte_soap)

st.divider()

if st.button("💾 GUARDAR E INTEGRAR EN GOOGLE SHEETS"):
    if not st.session_state.reporte_soap:
        st.warning("Genera un reporte SOAP antes de guardarlo.")
    else:
        st.balloons()
        st.success("¡Reporte listo para enviarse a Google Sheets!")