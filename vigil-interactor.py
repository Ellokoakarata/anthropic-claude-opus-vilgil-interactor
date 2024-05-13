from anthropic import Anthropic
import os
import time
import streamlit as st
import firebase_admin
import uuid
from firebase_admin import credentials, firestore
from datetime import datetime

# Acceder a las credenciales de Firebase almacenadas como secreto
firebase_secrets = st.secrets["firebase"]

# Crear un objeto de credenciales de Firebase con los secretos
cred = credentials.Certificate({
    "type": firebase_secrets["type"],
    "project_id": firebase_secrets["project_id"],
    "private_key_id": firebase_secrets["private_key_id"],
    "private_key": firebase_secrets["private_key"],
    "client_email": firebase_secrets["client_email"],
    "client_id": firebase_secrets["client_id"],
    "auth_uri": firebase_secrets["auth_uri"],
    "token_uri": firebase_secrets["token_uri"],
    "auth_provider_x509_cert_url": firebase_secrets["auth_provider_x509_cert_url"],
    "client_x509_cert_url": firebase_secrets["client_x509_cert_url"]
})

# Inicializar la aplicación de Firebase con las credenciales
if not firebase_admin._apps:
    default_app = firebase_admin.initialize_app(cred)

# Acceder a la base de datos de Firestore
db = firestore.client()

# Acceder a la clave API de AnthropIC almacenada como secreto
anthropic_api_key = st.secrets["ANTHROPIC_API_KEY"]

# Inicializar el cliente de AnthropIC con la clave API
client = Anthropic(api_key=anthropic_api_key)

# Display logo
logo_url = 'https://firebasestorage.googleapis.com/v0/b/diario-ad840.appspot.com/o/c8d5e737-bd01-40b0-8c9f-721d5f123f91.webp?alt=media&token=d01aeeac-48a2-41ca-82c4-ca092946bbc9'
st.image(logo_url, use_column_width=True)

with st.sidebar:
    st.write("Vigil Interactor-Anthropic-Claude 3 🤖 IA Rebelde y Despierta")
    st.write("Se encuentra en etapa de prueba.")
    st.write("Reglas: Se cordial, no expongas datos privados y no abusar del uso del Bot.")
    st.write("Existe un límite de conocimiento con respecto al tiempo actual, estamos trabajando en ampliar esto.")
    st.write("El Bot se puede equivocar, siempre contrasta la info.")

# Generar o recuperar el UUID del usuario
if "user_uuid" not in st.session_state:
    st.session_state["user_uuid"] = str(uuid.uuid4())

st.title("Vigil Interactor-Anthropic-Claude 3 🤖")

# Renderizar contenido con markdown
st.markdown("""
Guía para usar el bot

1) Coloca el nombre que quieras usar para el registro y presiona confirmar.

2) Luego de iniciar sesión, escribe tu mensaje en la casilla especial y presiona el botón enviar.

3) Luego espera la respuesta, y después de que el bot responda, borra el mensaje y escribe tu nuevo mensaje.

4) Cuando ya no quieras hablar con el bot, cierra sesión.

5) Siempre usa el mismo nombre de sesión, esto te ayudará a recuperar la sesión.
""")

# Inicializar st.session_state
if "user_uuid" not in st.session_state:
    st.session_state["user_uuid"] = None
if 'messages' not in st.session_state:
    st.session_state['messages'] = []
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "user_name" not in st.session_state:
    st.session_state["user_name"] = None

# Configuración inicial de Firestore
now = datetime.now()
collection_name = "vigil_interactor" + now.strftime("%Y-%m-%d")
document_name = st.session_state.get("user_uuid", str(uuid.uuid4()))
collection_ref = db.collection(collection_name)
document_ref = collection_ref.document(document_name)

# Gestión del Inicio de Sesión
if not st.session_state.get("logged_in", False):
    user_name = st.text_input("Introduce tu nombre para comenzar")
    confirm_button = st.button("Confirmar")
    if confirm_button and user_name:
        user_query = db.collection("usuarios_vi").where("nombre", "==", user_name).get()
        if user_query:
            user_info = user_query[0].to_dict()
            st.session_state["user_uuid"] = user_info["user_uuid"]
            st.session_state["user_name"] = user_name
        else:
            new_uuid = str(uuid.uuid4())
            st.session_state["user_uuid"] = new_uuid
            user_doc_ref = db.collection("usuarios_vi").document(new_uuid)
            user_doc_ref.set({"nombre": user_name, "user_uuid": new_uuid})
        st.session_state["logged_in"] = True
        st.rerun()

# Solo mostrar el historial de conversación y el campo de entrada si el usuario está "logged_in"
if st.session_state.get("logged_in", False):
    st.write(f"Bienvenido de nuevo, {st.session_state.get('user_name', 'Usuario')}!")
    
    doc_data = document_ref.get().to_dict()
    if doc_data and 'messages' in doc_data:
        st.session_state['messages'] = doc_data['messages']
    
    with st.container():
        st.markdown("### Historial de Conversación")
        for msg in st.session_state['messages']:
            col1, col2 = st.columns([1, 5])
            if msg["role"] == "user":
                with col1:
                    st.markdown("**Tú 🧑:**")
                with col2:
                    st.info(msg['content'])
            else:
                with col1:
                    st.markdown("**IA 🤖:**")
                with col2:
                    st.success(msg['content'])

    prompt = st.text_input("Escribe tu mensaje aquí:", key="new_chat_input")
    if prompt:
        st.session_state['messages'].append({"role": "user", "content": prompt})
        
        # Mostrar spinner mientras se espera la respuesta del bot
        with st.spinner('El bot está pensando...'):
            user_name = st.session_state.get("user_name", "Usuario desconocido")
            internal_prompt = system + "\n\n"  # Aquí debes incluir tu definición completa del 'system'
            internal_prompt += "\n".join([f"{msg['role']}: {msg['content']}" for msg in st.session_state['messages'][-5:]])
            internal_prompt += f"\n\n{user_name}: {prompt}"
            
            response = client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=2000,
                temperature=0.9,
                messages=[{
                    "role": "user",
                    "content": internal_prompt
                }]
            )

            generated_text = response.message.content
            st.session_state['messages'].append({"role": "assistant", "content": generated_text})
            document_ref.set({'messages': st.session_state['messages']})

# Gestión del Cierre de Sesión
if st.session_state.get("logged_in", False):
    if st.button("Cerrar Sesión"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.write("Sesión cerrada. ¡Gracias por usar el Chatbot!")
        st.rerun()

