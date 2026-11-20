import streamlit as st
import google.generativeai as genai
from supabase import create_client
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

st.set_page_config(page_title="Sistema Clínico SOAP", page_icon="🩺", layout="centered")

# --- ESTILO - SIN LETRAS NEGRAS, TODO AZUL Y BLANCO ---
st.markdown("""
<style>
* { color: #1A237E !important; }
p, div, span, label, textarea, input { color: #1A237E !important; }
.header-box {
    background: linear-gradient(90deg, #1565C0, #1E88E5);
    padding: 25px; border-radius: 12px; text-align: center; margin-bottom: 20px;
}
.header-box h1 { color: white !important; font-size: 24px; margin: 0; }
.header-box p { color: white !important; font-size: 13px; margin-top: 8px; }
h1, h2, h3 { color: #1565C0 !important; }
.btn-rojo button {
    background-color: #C62828 !important; color: white !important;
    width: 100%; height: 50px; font-weight: bold; border-radius: 8px; font-size: 14px;
}
.btn-rojo button p { color: white !important; }
textarea { background-color: #F5F8FF !important; font-size: 15px !important; }
</style>
""", unsafe_allow_html=True)

# --- 2. LOGO AZULITO COMO SU FOTO ---
st.markdown("""
<div class="header-box">
    <h1>🩺 Sistema Clínico<br>SOAP Inteligente</h1>
    <p>Asistente de documentación clínica por voz y texto</p>
</div>
""", unsafe_allow_html=True)

# --- SUPABASE - CLAVES 30 DIAS ---
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-3.8-flash")

# --- CLAVE MEDICO ---
st.subheader("🔑 Acceso Médico")
clave = st.text_input("Ingrese su clave de acceso:", type="password")
if not clave:
    st.warning("Ingrese su clave para continuar.")
    st.stop()
res = supabase.table("licencias").select("*").eq("clave", clave).execute()
if not res.data:
    st.error("❌ Clave no válida.")
    st.stop()
lic = res.data[0]
fecha_vence = datetime.fromisoformat(lic["fecha_vencimiento"].replace("Z", ""))
if datetime.now() > fecha_vence:
    st.error("❌ Su licencia venció.")
    st.stop()
if lic["estado_pago"] != "pagado":
    st.error("❌ Pago pendiente.")
    st.stop()
st.success(f"✅ Bienvenido Dr. {lic['nombre_medico']}")

# --- DICTADO ---
st.markdown("### 🎙️ Dictado de Consulta")
st.text_input("🎤 Grabación", placeholder="00:00 - Toque para grabar", label_visibility="collapsed")
st.markdown("📝 **Notas escritas de la consulta (Opcional):**")
notas = st.text_area("", value="Paciente femenina de 20 años con estupor superficial más glucemia de 400mg/dl", height=90, label_visibility="collapsed")

# --- BOTON ROJO ---
st.markdown('<div class="btn-rojo">', unsafe_allow_html=True)
generar = st.button("⚡ GENERAR REPORTE CLÍNICO SOAP")
st.markdown('</div>', unsafe_allow_html=True)

if generar:
    prompt = f"""
    Eres médico experto. Genera reporte SOAP completo en español.
    Notas: {notas}
    Estructura exacta:
    S - SUBJETIVO:
    O - OBJETIVO:
    A - ANÁLISIS:
    P - PLAN:
    Incluye diagnóstico, tratamiento.
    """
    with st.spinner("Generando reporte..."):
        try:
            resp = model.generate_content(prompt)
            st.session_state["reporte"] = resp.text
        except Exception as e:
            st.error(f"Error: {e}")

# --- 1. REPORTE QUE SI SE PUEDE ESCRIBIR / EDITAR ---
if "reporte" in st.session_state:
    st.markdown("---")
    st.markdown("### 📄 Reporte SOAP - Usted puede editar aquí")
    st.info("✏️ Toque el texto y escriba. Aquí el médico puede corregir Subjetivo, Objetivo, Análisis y Plan.")
    
    # AQUI ESTA EL CAMBIO: AHORA ES UN CUADRO PARA ESCRIBIR, NO SOLO LETRAS
    reporte_editado = st.text_area(
        "Reporte Editable:",
        value=st.session_state["reporte"],
        height=500,
        label_visibility="collapsed"
    )
    # Guardamos lo que el médico escribió
    st.session_state["reporte_final"] = reporte_editado

    st.markdown("---")
    col1, col2 = st.columns(2)
    # --- 3. GUARDAR EN GOOGLE SHEETS - QUE SALGA EL AVISO ---
    with col1:
        if st.button("📊 Guardar en Google Sheets", type="primary"):
            try:
                scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
                creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(st.secrets["GOOGLE_SHEETS_CREDS"]), scope)
                client = gspread.authorize(creds)
                sheet = client.open("Pacientes Clinica").sheet1
                ahora = datetime.now().strftime("%Y-%m-%d %H:%M")
                # Guardamos el reporte YA EDITADO por el médico
                sheet.append_row([ahora, lic['nombre_medico'], notas, st.session_state["reporte_final"]])
                st.success("✅ ¡Guardado en Google Sheets!")
                st.balloons()
            except Exception as e:
                st.error(f"No se pudo guardar: {e}")
    with col2:
        if st.button("📋 Copiar Rápido"):
            st.code(st.session_state["reporte_final"])
            st.info("Seleccione todo, copie y pegue en WhatsApp.")
