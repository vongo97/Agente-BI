import streamlit as st

def apply_custom_styles():
    """
    Aplica los estilos CSS personalizados para una estética premium.
    """
    st.markdown("""
        <style>
        .main {
            background-color: #0e1117;
        }
        .stButton>button {
            width: 100%;
            border-radius: 5px;
            height: 3em;
            background-color: #262730;
            color: white;
            border: 1px solid #4B4B4B;
        }
        .stButton>button:hover {
            border-color: #FF4B4B;
            color: #FF4B4B;
        }
        .stInfo {
            background-color: #1e2630;
            border-left-color: #FF4B4B;
        }
        </style>
        """, unsafe_allow_html=True)
