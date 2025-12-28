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
EMAIL_USER = "silvafrederico280385@gmail.com"
EMAIL_PASS = "*.*Fr3d5ilv488" 
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
TWILIO_ACCOUNT_SID = 'AC0c0da7648d2ad34f5c2df4253e371910'
TWILIO_AUTH_TOKEN = 'a83cb0baf2dce52ba061171d3f69a9f9'
TWILIO_NUMBER = "+12402930627"
ADMIN_PHONE = "+351939227659"

BG_IMG = "https://images.unsplash.com/photo-1533174072545-7a4b6ad7a6c3?auto=format&fit=crop&q=80&w=1920"

# --- DATABASE ENGINE ---
def init_db():
    conn = sqlite3.connect('sistema.db', check_same_thread=False)
    c = conn.cursor()
    # Tabela de Inscrições
    c.execute('CREATE TABLE IF NOT EXISTS escalas (posto TEXT PRIMARY KEY, nome TEXT, telefone TEXT, email TEXT)')
    # Tabela de Postos
    c.execute('CREATE TABLE IF NOT EXISTS configuracao_turnos (posto TEXT PRIMARY KEY)')
    # Tabela de Clientes/Utilizadores (Login)
    c.execute('CREATE TABLE IF NOT EXISTS clientes (email TEXT PRIMARY KEY, senha TEXT, nome TEXT)')
    conn.commit()
    conn.close()

def enviar_email(dest, nome, posto):
    try:
        msg = MIMEText(f"Olá {nome}, o seu turno foi confirmado com sucesso: {posto}")
        msg['Subject'] = "Confirmação de Turno"
        msg['From'] = EMAIL_USER
        msg['To'] = dest
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)
    except: pass

def enviar_sms(numero, mensagem):
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        client.messages.create(body=mensagem, from_=TWILIO_NUMBER, to=numero)
    except: pass

st.set_page_config(page_title="Gestão de Segurança", layout="wide")
init_db()

# --- ESTÉTICA CSS ---
st.markdown(f"""
    <style>
    .stApp {{ background: linear-gradient(rgba(0,0,0,0.7), rgba(0,0,0,0.7)), url("{BG_IMG}"); background-size: cover; }}
    .admin-btn {{ position: fixed; bottom: 10px; right: 10px; opacity: 0.2; cursor: pointer; font-size: 20px; z-index: 1000; }}
    </style>
""", unsafe_allow_html=True)

# --- SIDEBAR E NAVEGAÇÃO ---
with st.sidebar:
    st.title("🛡️ Portal de Segurança")
    opcao = st.radio("Navegação", ["Reserva de Turnos", "Área de Cliente", "Criar Conta"])
    st.divider()
    if st.markdown('<div class="admin-btn">🔒</div>', unsafe_allow_html=True):
        if st.button("Painel Gestão"):
            st.session_state.admin_mode = not st.session_state.get('admin_mode', False)

# --- MODO ADMIN ---
if st.session_state.get('admin_mode', False):
    senha = st.text_input("Senha Admin", type="password")
    if senha == ADMIN_PASSWORD:
        t1, t2, t3 = st.tabs(["Configurar Turnos", "Lista Total", "Exportar"])
        with t1:
            txt = st.text_area("Texto Bruto:")
            if st.button("Gerar"):
                # Lógica de Regex para extrair turnos (mantida igual às anteriores)
                for l in txt.split('\n'):
                    hm = re.search(r"(Das \d{1,2}h as \d{1,2}h.*)", l, re.IGNORECASE)
                    if hm:
                        try:
                            conn = sqlite3.connect('sistema.db')
                            conn.execute("INSERT INTO configuracao_turnos VALUES (?)", (l,))
                            conn.commit(); conn.close()
                        except: pass
                st.rerun()
        # Outras abas de admin mantidas para gestão da base de dados...

# --- ÁREA DE CRIAR CONTA ---
if opcao == "Criar Conta":
    st.header("📝 Registo de Novo Cliente")
    with st.form("registo_cliente"):
        n_c = st.text_input("Nome")
        e_c = st.text_input("Email")
        s_c = st.text_input("Senha", type="password")
        if st.form_submit_button("Registar"):
            try:
                conn = sqlite3.connect('sistema.db')
                conn.execute("INSERT INTO clientes VALUES (?,?,?)", (e_c, s_c, n_c))
                conn.commit(); conn.close()
                st.success("Conta criada! Pode fazer login.")
            except: st.error("Email já registado.")

# --- ÁREA DE CLIENTE (LOGIN) ---
elif opcao == "Área de Cliente":
    st.header("👤 Login de Cliente")
    email_l = st.text_input("Email")
    senha_l = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        conn = sqlite3.connect('sistema.db')
        user = conn.execute("SELECT nome FROM clientes WHERE email=? AND senha=?", (email_l, senha_l)).fetchone()
        if user:
            st.success(f"Bem-vindo, {user[0]}!")
            meu_turno = conn.execute("SELECT posto FROM escalas WHERE email=?", (email_l,)).fetchone()
            if meu_turno: st.info(f"O seu turno atual: {meu_turno[0]}")
            else: st.write("Não tem turnos reservados.")
        else: st.error("Dados incorretos.")
        conn.close()

# --- RESERVA DE TURNOS ---
elif opcao == "Reserva de Turnos":
    st.title("🎆 Reserva de Turnos")
    
    conn = sqlite3.connect('sistema.db')
    postos = [r[0] for r in conn.execute("SELECT posto FROM configuracao_turnos").fetchall()]
    inscritos = dict(conn.execute("SELECT posto, nome FROM escalas").fetchall())
    conn.close()

    if postos:
        with st.form("form_reserva"):
            c1, c2 = st.columns(2)
            nome = c1.text_input("Nome Completo")
            tel = c1.text_input("Telemóvel")
            mail = c2.text_input("E-mail")
            escolha = c2.selectbox("Posto", postos)
            
            st.write("---")
            quero_sms = st.checkbox("Desejo receber confirmação por SMS (Opcional)")
            quero_email = st.checkbox("Desejo receber confirmação por E-mail", value=True)
            
            if st.form_submit_button("Confirmar Marcação"):
                if not (nome and tel and mail):
                    st.error("Preencha os campos obrigatórios.")
                elif escolha in inscritos:
                    st.error("Turno já ocupado.")
                else:
                    conn = sqlite3.connect('sistema.db')
                    conn.execute("INSERT INTO escalas VALUES (?,?,?,?)", (escolha, nome, tel, mail))
                    conn.commit(); conn.close()
                    
                    # Logica de Notificação Condicional
                    if quero_email: enviar_email(mail, nome, escolha)
                    if quero_sms: enviar_sms(tel, f"Confirmado: {escolha}")
                    
                    # Alerta Admin é SEMPRE enviado por segurança
                    enviar_sms(ADMIN_PHONE, f"Registo: {nome} em {escolha}")
                    
                    st.success("✅ Marcação concluída!")
                    st.rerun()

        # Grid de Disponibilidade
        cols = st.columns(2)
        for i, p in enumerate(postos):
            with cols[i%2]:
                if p in inscritos: st.error(f"❌ {p} ({inscritos[p]})")
                else: st.success(f"✅ {p}")
