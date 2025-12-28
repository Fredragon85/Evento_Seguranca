import streamlit as st
import sqlite3
import re
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from twilio.rest import Client
from io import BytesIO

# --- CONFIGURAÇÕES ---
ADMIN_PASSWORD = "ADMIN"

# E-mail (Configuração Obrigatória)
EMAIL_USER = "silvafrederico280385@gmail.com"
EMAIL_PASS = "*.*Fr3d5ilv488" 
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# Twilio (Alerta Admin)
TWILIO_ACCOUNT_SID = 'AC0c0da7648d2ad34f5c2df4253e371910'
TWILIO_AUTH_TOKEN = 'a83cb0baf2dce52ba061171d3f69a9f9'
TWILIO_NUMBER = "+12402930627"
ADMIN_PHONE = "+351939227659"

# URL da imagem de fundo
BACKGROUND_IMAGE_URL = "https://i.imgur.com/G5qjO04.png" # Link da imagem

def init_db():
    conn = sqlite3.connect('turnos.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS escalas (posto TEXT PRIMARY KEY, nome TEXT, telefone TEXT, email TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS configuracao_turnos (posto TEXT PRIMARY KEY)')
    conn.commit()
    conn.close()

def enviar_confirmacao_email(destinatario, nome, posto):
    corpo = f"Ola {nome},\n\nO seu turno foi confirmado com sucesso!\n\nDetalhes: {posto}\n\nBom trabalho!"
    try:
        msg = MIMEText(corpo)
        msg['Subject'] = "Confirmacao de Turno"
        msg['From'] = EMAIL_USER
        msg['To'] = destinatario
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)
    except: pass

def alerta_admin_sms(mensagem):
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        client.messages.create(body=mensagem, from_=TWILIO_NUMBER, to=ADMIN_PHONE)
    except: pass

# --- CONFIGURAÇÃO DA PÁGINA COM BACKGROUND ---
st.set_page_config(page_title="Gestão de Eventos", layout="wide")

# CSS para a imagem de fundo
st.markdown(
    f"""
    <style>
    .stApp {{
        background-image: url({BACKGROUND_IMAGE_URL});
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: fixed; /* Fixa a imagem no scroll */
    }}
    /* Esconde o modo admin por toggle na sidebar */
    .st-emotion-cache-1pxazr7 {{ /* Esta classe pode mudar entre versões do Streamlit */
        visibility: hidden;
        height: 0px;
        position: absolute;
    }}
    /* Estilo para o botão invisível */
    .invisible-button {{
        background: transparent !important;
        border: none !important;
        color: transparent !important;
        cursor: pointer;
        padding: 0;
        margin: 0;
        position: fixed;
        bottom: 10px;
        right: 10px;
        width: 30px; /* Area clicavel */
        height: 30px; /* Area clicavel */
        z-index: 9999;
    }}
    /* Opcional: Icone de cadeado para o admin, apenas visível no canto */
    .admin-icon {{
        position: fixed;
        bottom: 10px;
        right: 10px;
        font-size: 24px;
        color: #fff; /* Cor do cadeado */
        cursor: pointer;
        z-index: 9998; /* Abaixo do botão invisível */
        text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
    }}
    </style>
    """,
    unsafe_allow_html=True
)


init_db()

# --- SIDEBAR (Modo Administrador visível apenas com o botão dissimulado) ---
with st.sidebar:
    st.title("⚙️ Painel")
    # Este toggle é o que controla o modo admin, mas será acionado pelo botão invisível
    # O CSS acima vai tornar este toggle (e sua label) invisível
    modo_admin = st.toggle("Ativar Painel de Gestão", key="admin_toggle_sidebar")
    
# --- Botão Dissimulado no Canto Inferior Direito ---
# Este botão simula o clique no toggle da sidebar
if st.markdown("""
    <div class="admin-icon">🔒</div>
    <button class="invisible-button" onclick="
        var toggle = document.querySelector('[data-testid=\"stSidebarUserContent\"] .st-emotion-cache-1pxazr7 input[type=\"checkbox\"]');
        if (toggle) {
            toggle.checked = !toggle.checked;
            toggle.dispatchEvent(new Event('change'));
        }
    "></button>
    """, unsafe_allow_html=True):
    pass # O clique é tratado via JavaScript

if modo_admin: # A lógica de admin é ativada se o toggle for true (via clique no botão invisível)
    st.sidebar.header("🛠️ Administração")
    senha = st.sidebar.text_input("Senha", type="password", key="admin_senha_sidebar")
    if senha == ADMIN_PASSWORD:
        st.sidebar.success("Acesso Admin Concedido!")
        
        # Botões de acesso no modo administrador
        if st.sidebar.button("➕ Gerar Turnos", key="btn_gerar_turnos"):
            st.session_state.admin_tab = "gerar_turnos"
        if st.sidebar.button("📋 Ver Inscrições", key="btn_ver_inscricoes"):
            st.session_state.admin_tab = "ver_inscricoes"
        if st.sidebar.button("📥 Exportar Excel", key="btn_exportar_excel"):
            st.session_state.admin_tab = "exportar_excel"

        if "admin_tab" not in st.session_state:
            st.session_state.admin_tab = "ver_inscricoes" # Default
        
        st.subheader("Painel de Administrador")
        if st.session_state.admin_tab == "gerar_turnos":
            st.subheader("Processamento Automático de Turnos")
            texto = st.text_area("Cole o texto bruto aqui:", height=250)
            if st.button("Processar e Criar Turnos"):
                linhas = texto.split('\n')
                local, data = "", ""
                for l in linhas:
                    l = l.strip()
                    if not l or any(x in l.upper() for x in ["FOGO", "PSG"]): continue
                    if l.isupper() and len(l) > 3 and "DIA" not in l: local = l
                    dm = re.search(r"(DIA \d+|\b\d{2}\b)", l, re.IGNORECASE)
                    if dm and not re
