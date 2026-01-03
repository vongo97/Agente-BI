import streamlit as st
import google.generativeai as genai
import os
from dotenv import load_dotenv
from src.ui.styles import apply_custom_styles
from src.connectors.data_connectors import load_file_data, get_sql_engine, get_db_schema, load_gsheets_data
from src.engine.bi_analyst import validate_api_key, analyze_with_gemini, execute_analysis, generate_report_narrative
from src.utils.exporter import to_excel, to_image
from src.utils.report_gen import generate_pdf_report

from src.utils.auth import login_viewer, logout

# Cargar variables de entorno desde .env si existe
load_dotenv()

# Configuración de página
st.set_page_config(page_title="Agente BI - Inteligencia de Datos", layout="wide")
apply_custom_styles()

# Inicializar historial de chat
if "messages" not in st.session_state:
    st.session_state.messages = []

def main():
    # 1. Verificación de Autenticación
    if not login_viewer():
        return # Detener ejecución si no hay login

    st.title("🤖 Agente BI: Analista de Precisión")
    st.subheader(f"Hola, {st.session_state.user_info.get('given_name', 'Analista')}! 👋")

    with st.sidebar:
        # Perfil del usuario
        st.markdown("---")
        col_img, col_txt = st.columns([1,3])
        if st.session_state.user_info.get("picture"):
            col_img.image(st.session_state.user_info["picture"], width=50)
        col_txt.write(f"**{st.session_state.user_info['name']}**")
        col_txt.caption(st.session_state.user_info["email"])
        
        if st.button("🚪 Cerrar Sesión"):
            logout()
            
        st.divider()
        st.header("⚙️ Configuración")
        
        # Intentar obtener la API Key del entorno
        default_key = os.getenv("GOOGLE_API_KEY", "")
        api_key = st.text_input("Ingresa tu Google API Key", value=default_key, type="password")
        
        if api_key:
            is_valid, error_msg = validate_api_key(api_key)
            if is_valid:
                os.environ["GOOGLE_API_KEY"] = api_key
                st.success("✅ Conexión con Gemini exitosa")
            else:
                st.error(f"❌ Error en API Key: {error_msg}")
        
        st.divider()
        source_type = st.radio("Selecciona la fuente de datos:", 
                              ["Archivo (CSV/Excel)", "Base de Datos SQL", "Google Sheets"])
        
        if st.button("🗑️ Borrar Memoria"):
            st.session_state.messages = []
            st.rerun()

    data_to_analyze = None
    analysis_mode = "file"
    exec_context = None

    # Lógica de Conectores
    if source_type == "Archivo (CSV/Excel)":
        uploaded_file = st.sidebar.file_uploader("Sube tu archivo", type=["csv", "xlsx"])
        if uploaded_file:
            try:
                data_to_analyze = load_file_data(uploaded_file)
                st.success(f"✅ Archivo cargado: {uploaded_file.name}")
                exec_context = data_to_analyze
            except Exception as e:
                st.error(f"Error: {e}")

    elif source_type == "Base de Datos SQL":
        db_url = st.sidebar.text_input("URL de conexión SQL", type="password")
        if db_url:
            try:
                engine = get_sql_engine(db_url)
                data_to_analyze = get_db_schema(engine)
                exec_context = engine
                analysis_mode = "sql"
                st.success("✅ Conectado a la Base de Datos")
            except Exception as e:
                st.error(f"Error SQL: {e}")

    elif source_type == "Google Sheets":
        gs_url = st.sidebar.text_input("URL de Google Sheets")
        if gs_url:
            try:
                data_to_analyze = load_gsheets_data(gs_url)
                exec_context = data_to_analyze
                st.success("✅ Google Sheets cargado")
            except Exception as e:
                st.error(f"Error Sheets: {e}")

    # Interfaz de Análisis
    if data_to_analyze is not None:
        if analysis_mode == "file":
            with st.expander("🔍 Explorar datos"):
                st.dataframe(data_to_analyze.head(10))
        
        st.divider()
        st.header("💬 Conversación con tu Analista")

        # Mostrar mensajes previos
        for i, message in enumerate(st.session_state.messages):
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                if "fig" in message:
                    st.plotly_chart(message["fig"], use_container_width=True)
                
                # Opciones de exportación para el último mensaje del asistente
                if i == len(st.session_state.messages) - 1 and message["role"] == "assistant":
                    col1, col2, col3 = st.columns(3)
                    if "fig" in message:
                        img_bytes = to_image(message["fig"])
                        if img_bytes:
                            col1.download_button("🖼️ Guardar Gráfico", img_bytes, "analisis.png", "image/png", key=f"dl_img_{i}")
                    
                    if analysis_mode == "file":
                         xlsx_data = to_excel(data_to_analyze)
                         col2.download_button("📂 Descargar Dataset", xlsx_data, "datos.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key=f"dl_xlsx_{i}")
                    
                    if col3.button("📄 Informe Ejecutivo", key=f"btn_report_{i}"):
                        with st.spinner("🖋️ Redactando informe de consultoría..."):
                            # Obtener imagen si existe
                            fig_img = None
                            if "fig" in message:
                                fig_img = to_image(message["fig"])
                            
                            narrative = generate_report_narrative(data_to_analyze, message["content"], mode=analysis_mode)
                            pdf_bytes = generate_pdf_report(narrative, message["content"], fig_image=fig_img)
                            
                            # Opción de descarga
                            st.download_button("💾 Descargar PDF Profesional", pdf_bytes, "Informe_Ejecutivo.pdf", "application/pdf")
                            
                            # NUEVO: Guardado automático opcional en carpeta local
                            try:
                                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                                filepath = f"exports/Reporte_{timestamp}.pdf"
                                with open(filepath, "wb") as f:
                                    f.write(pdf_bytes)
                                st.success(f"📂 Copia guardada localmente en: {filepath}")
                            except:
                                pass
                                
                            st.markdown("---")
                            st.markdown(f"### 📑 Vista Previa del Informe\n{narrative}")

        # Input de chat
        if query := st.chat_input("¿Qué quieres saber de tus datos?"):
            st.session_state.messages.append({"role": "user", "content": query})
            with st.chat_message("user"):
                st.markdown(query)

            if not api_key:
                st.warning("⚠️ Ingresa tu API Key en la barra lateral.")
            else:
                with st.chat_message("assistant"):
                    with st.spinner("🤖 Analizando y procesando resultados..."):
                        raw_response = analyze_with_gemini(
                            data_to_analyze, 
                            query, 
                            chat_history=st.session_state.messages[:-1],
                            mode=analysis_mode
                        )
                        var_name = 'df' if analysis_mode == "file" else 'engine'
                        output_text, fig = execute_analysis(exec_context, raw_response, var_name)
                        
                        if output_text:
                            st.markdown(output_text)
                        if fig:
                            st.plotly_chart(fig, use_container_width=True)
                        
                        with st.expander("🛠️ Ver código técnico"):
                            st.code(raw_response)
                        
                        assistant_msg = {
                            "role": "assistant", 
                            "content": output_text if output_text else "He generado el análisis visual solicitado."
                        }
                        if fig:
                            assistant_msg["fig"] = fig
                        st.session_state.messages.append(assistant_msg)
                        st.rerun()

    else:
        st.info("👋 Selecciona una fuente de datos en el panel lateral para comenzar.")

if __name__ == "__main__":
    main()
