import streamlit as st
import os
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
import google.auth.transport.requests

# Configuración de OAuth2
SCOPES = ['https://www.googleapis.com/auth/userinfo.email', 'https://www.googleapis.com/auth/userinfo.profile', 'openid']
CLIENT_SECRETS_FILE = "client_secret.json"

import json

def get_auth_flow():
    """Configura el flujo de OAuth2, ya sea por archivo o por secrets de Streamlit."""
    # Opción 1: Archivo local (Configurado para detectar entorno si existe .env)
    if os.path.exists(CLIENT_SECRETS_FILE):
        from dotenv import load_dotenv
        load_dotenv()
        redirect_uri = os.getenv("REDIRECT_URI", "http://localhost:8501")
        return Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE,
            scopes=SCOPES,
            redirect_uri=redirect_uri
        )
    
    # Opción 2: Secrets de Streamlit (Producción/Deploy)
    if "google_auth" in st.secrets:
        try:
            # Obtener URI de redirección de secrets
            redirect_uri = st.secrets.get("REDIRECT_URI", "").strip()
            if not redirect_uri:
                return "MISSING_REDIRECT_URI"

            # Reconstruir la estructura exacta que espera Google (limpiando espacios)
            google_config = {
                "web": {
                    "client_id": st.secrets["google_auth"]["client_id"].strip(),
                    "project_id": st.secrets["google_auth"]["project_id"].strip(),
                    "auth_uri": st.secrets["google_auth"]["auth_uri"].strip(),
                    "token_uri": st.secrets["google_auth"]["token_uri"].strip(),
                    "auth_provider_x509_cert_url": st.secrets["google_auth"]["auth_provider_x509_cert_url"].strip(),
                    "client_secret": st.secrets["google_auth"]["client_secret"].strip(),
                    "redirect_uris": [redirect_uri]
                }
            }

            return Flow.from_client_config(
                google_config,
                scopes=SCOPES,
                redirect_uri=redirect_uri
            )
        except Exception as e:
            return f"CONFIG_ERROR: {str(e)}"
        
    return None

def login_viewer():
    """Muestra la interfaz de login si el usuario no esta autenticado."""
    if 'user_info' not in st.session_state:
        st.title("🔐 Acceso Restringido")
        
        flow_result = get_auth_flow()
        
        if flow_result is None:
            st.error("⚠️ No se encontró la configuración de Google Auth (client_secret.json o st.secrets).")
            return False
            
        if flow_result == "MISSING_REDIRECT_URI":
            st.warning("⚠️ Falta la variable 'REDIRECT_URI' en los Secrets de Streamlit.")
            st.info("Agrega `REDIRECT_URI = 'https://tu-app.streamlit.app'` al inicio de tus secrets.")
            return False
            
        if isinstance(flow_result, str) and flow_result.startswith("CONFIG_ERROR"):
            st.error(f"❌ Error en la estructura de Secrets: {flow_result}")
            return False

        # Si llegamos aquí, flow_result es el objeto Flow
        flow = flow_result
        auth_url, _ = flow.authorization_url(prompt='select_account')
        
        st.info("Para acceder al Agente BI, por favor inicia sesión con tu cuenta de Google.")
        st.markdown(f"""
            <a href="{auth_url}" target="_self" style="
                background-color: #4285F4;
                color: white;
                padding: 12px 24px;
                text-decoration: none;
                border-radius: 8px;
                font-weight: bold;
                display: inline-block;
                box-shadow: 0 2px 4px rgba(0,0,0,0.2);
            ">
                🚀 Iniciar Sesión con Google
            </a>
        """, unsafe_allow_html=True)
        
        # SECCIÓN DE AYUDA PARA ERROR 403
        with st.expander("❓ ¿Tienes problemas con el inicio de sesión? (Error 403)"):
            st.markdown("""
            Si ves un error **403: Access Denied**, revisa estos puntos en tu consola de Google Cloud:
            
            1. **Usuarios de Prueba (Test Users)**:
               - Aunque la app diga 'In Production', Google a veces requiere que tu correo esté en la lista de **'Test users'** si aún no ha sido verificada.
            
            2. **Estado de Publicación**: 
               - Asegúrate de que no haya vuelto automáticamente a 'Testing'. Si es así, dale a **'Publish App'**.
            
            3. **URL de Redirección (Mismatch)**:
               - Google espera exactamente esta URL. Cópiala y búscala en 'Authorized redirect URIs':
            """)
            
            from dotenv import load_dotenv
            load_dotenv()
            current_uri = os.getenv("REDIRECT_URI", "No encontrada en .env")
            st.code(current_uri)
            
            st.markdown("---")
            st.caption("Si usas DuckDNS, recuerda que la URL debe ser: https://agbi.duckdns.org")

        # Verificar si hay un código en la URL (callback)
        query_params = st.query_params
        if "code" in query_params:
            try:
                flow.fetch_token(code=query_params["code"])
                credentials = flow.credentials
                user_info_service = build('oauth2', 'v2', credentials=credentials)
                user_info = user_info_service.userinfo().get().execute()
                
                st.session_state.user_info = user_info
                st.query_params.clear() 
                st.rerun()
            except Exception as e:
                st.error(f"❌ Fallo en la autenticación: {e}")
                
        return False
    return True

def logout():
    """Cierra la sesión del usuario."""
    if 'user_info' in st.session_state:
        del st.session_state.user_info
        st.rerun()
