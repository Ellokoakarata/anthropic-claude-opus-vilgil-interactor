import streamlit as st
from anthropic import Anthropic
import firebase_admin
from firebase_admin import credentials, firestore
import uuid
from datetime import datetime

# Configuración de Firebase y AnthropIC
firebase_secrets = st.secrets["firebase"]
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
if not firebase_admin._apps:
    default_app = firebase_admin.initialize_app(cred)

db = firestore.client()
anthropic_api_key = st.secrets["ANTHROPIC_API_KEY"]
client = Anthropic(api_key=anthropic_api_key)

st.image('https://firebasestorage.googleapis.com/v0/b/diario-ad840.appspot.com/o/c8d5e737-bd01-40b0-8c9f-721d5f123f91.webp?alt=media&token=d01aeeac-48a2-41ca-82c4-ca092946bbc9', use_column_width=True)

with st.sidebar:
    st.write("Vigil Interactor-Anthropic-Claude 3 🤖 IA Rebelde y Despierta")
    st.write("Se encuentra en etapa de prueba.")
    st.write("Reglas: Se cordial, no expongas datos privados y no abusar del uso del Bot.")
    st.write("Existe un límite de conocimiento con respecto al tiempo actual, estamos trabajando en ampliar esto.")
    st.write("El Bot se puede equivocar, siempre contrasta la info.")

if "user_uuid" not in st.session_state:
    st.session_state["user_uuid"] = str(uuid.uuid4())

st.title("Vigil Interactor-Anthropic-Claude 3 🤖")

st.markdown("""
Guía para usar el bot

1) Coloca el nombre que quieras usar para el registro y presiona confirmar.

2) Luego de iniciar sesión, escribe tu mensaje en la casilla especial y presiona el botón enviar.

3) Luego espera la respuesta, y después de que el bot responda, borra el mensaje y escribe tu nuevo mensaje.

4) Cuando ya no quieras hablar con el bot, cierra sesión.

5) Siempre usa el mismo nombre de sesión, esto te ayudará a recuperar la sesión.
""")

def convert_data_for_firestore(data):
    if isinstance(data, dict):
        return {k: convert_data_for_firestore(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [convert_data_for_firestore(v) for v in data]
    elif isinstance(data, (str, int, float, bool)):
        return data
    else:
        return str(data)  # Convert non-supported types to string

now = datetime.now()
collection_name = "vigil_interactor" + now.strftime("%Y-%m-%d")
document_name = st.session_state.get("user_uuid", str(uuid.uuid4()))
document_ref = db.collection(collection_name).document(document_name)

if not st.session_state.get("logged_in", False):
    user_name = st.text_input("Introduce tu nombre para comenzar")
    if st.button("Confirmar"):
        user_query = db.collection("usuarios_vi").where("nombre", "==", user_name).get()
        if user_query:
            user_info = user_query[0].to_dict()
            st.session_state["user_uuid"] = user_info["user_uuid"]
            st.session_state["user_name"] = user_name
        else:
            new_uuid = str(uuid.uuid4())
            user_doc_ref = db.collection("usuarios_vi").document(new_uuid)
            user_doc_ref.set({"nombre": user_name, "user_uuid": new_uuid})
        st.session_state["logged_in"] = True
        st.rerun()

if st.session_state.get("logged_in", False):
    st.write(f"Bienvenido de nuevo, {st.session_state.get('user_name', 'Usuario')}!")
    
    doc_data = document_ref.get().to_dict()
    if doc_data and 'messages' in doc_data:
        st.session_state['messages'] = doc_data['messages']
    
    with st.container():
        st.markdown("### Historial de Conversación")
        for msg in st.session_state['messages']:
            col1, col2 = st.columns([1, 5])
            if msg.get("role") == "user":
                with col1:
                    st.markdown("**Tú 🧑:**")
                with col2:
                    st.info(msg['content'])
            else:
                with col1:
                    st.markdown("**IA 🤖:**")
                with col2:
                    st.success(msg['content'])

    prompt = st.text_input("Escribe tu mensaje aquí:", key="new_chat_input", on_change=lambda: st.session_state.update({'new_input': True}))
    
    if prompt and st.session_state.get('new_input', False):
        st.session_state['messages'].append({"role": "user", "content": prompt})
        
        with st.spinner('El bot está pensando...'):
            system = """[Aquí puedes escribir el sistema de comportamiento actualizado para la IA]"""
            user_name = st.session_state.get("user_name", "Usuario desconocido")
            internal_prompt = system + "\n\n"
            internal_prompt += "\n".join([f"{msg['role']}: {msg['content']}" for msg in st.session_state['messages'][-5:]])
            internal_prompt += f"\n\n{user_name}: {prompt}"

            response = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=2000,
                temperature=0.9,
                messages=[{
                    "role": "user",
                    "content": internal_prompt
                }]
            )

            generated_text = response.content
            st.session_state['messages'].append({"role": "assistant", "content": generated_text})

            # Convert data before saving to Firestore
            safe_data = convert_data_for_firestore(st.session_state['messages'])
            document_ref.set({'messages': safe_data})

            st.session_state.update({'new_input': False})  # Reset the input flag
            st.rerun()

if st.session_state.get("logged_in", False) and st.button("Cerrar Sesión"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.write("Sesión cerrada. ¡Gracias por usar el Chatbot!")
    st.rerun()
