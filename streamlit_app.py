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

# --- DATABASE ---
def init_db():
    conn = sqlite3.connect('sistema.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS escalas (posto TEXT PRIMARY KEY, nome TEXT, telefone TEXT, email TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS configuracao_turnos (posto TEXT PRIMARY KEY)')
    c.execute('CREATE TABLE IF NOT EXISTS clientes (email TEXT PRIMARY KEY, senha TEXT, nome TEXT)')
    conn.commit()
    conn.close()

def enviar_email(dest, nome, posto, teste=False):
    assunto = "Teste de Configuração de E-mail" if teste else "Confirmação de Turno"
    corpo = f"Olá {nome}, este é um e-mail de teste." if teste else f"Olá {nome}, o seu turno foi confirmado: {posto}"
    try:
        msg = MIMEText(corpo)
        msg['Subject'] = assunto
        msg['From'] = EMAIL_USER
        msg['To'] = dest
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)
        return True
    except Exception as e:
        st.error(f"Erro SMTP: {e}")
        return False

def enviar_sms(numero, mensagem):
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        client.messages.create(body=mensagem, from_=TWILIO_NUMBER, to=numero)
    except: pass

st.set_page_config(page_title="Gestão de Segurança", layout="wide")
init_db()

# --- CSS BACKGROUND ---
st.markdown(f"""
    <style>
    .stApp {{ background: linear-gradient(rgba(0,0,0,0.7), rgba(0,0,0,0.7)), url("{BG_IMG}"); background-size: cover; }}
    .admin-btn {{ position: fixed; bottom: 10px; right: 10px; opacity: 0.1; cursor: pointer; font-size: 20px; z-index: 1000; }}
    </style>
""", unsafe_allow_html=True)

# --- NAVEGAÇÃO ---
with st.sidebar:
    st.title("🛡️ Portal")
    menu = st.radio("Ir para:", ["Reserva de Turnos", "Área de Cliente", "Criar Conta"])
    st.divider()
    if st.markdown('<div class="admin-btn">🔒</div>', unsafe_allow_html=True):
        if st.button("Painel Admin"):
            st.session_state.admin_mode = not st.session_state.get('admin_mode', False)

# --- MODO ADMIN ---
if st.session_state.get('admin_mode', False):
    st.header("🛠️ Administração")
    pwd = st.text_input("Senha Admin", type="password")
    if pwd == ADMIN_PASSWORD:
        t1, t2, t3 = st.tabs(["Gerar Turnos", "Gestão Inscrições", "Ferramentas"])
        
        with t1:
            st.subheader("Processar Texto Bruto")
            txt = st.text_area("Cole o texto aqui:", height=200)
            col_a, col_b = st.columns(2)
            if col_a.button("Gerar Turnos"):
                linhas = txt.split('\n')
                loc, dat = "", ""
                for l in linhas:
                    l = l.strip()
                    if not l or any(x in l.upper() for x in ["FOGO", "PSG"]): continue
                    if l.isupper() and len(l) > 3 and "DIA" not in l: loc = l
                    dm = re.search(r"(DIA \d+|\b\d{2}\b)", l, re.IGNORECASE)
                    if dm and not re.search(r"\d+h", l): dat = dm.group(1).upper()
                    hm = re.search(r"(Das \d{1,2}h as \d{1,2}h.*)", l, re.IGNORECASE)
                    if hm and loc:
                        p_fin = f"{loc} ({dat}) | {hm.group(1)}"
                        conn = sqlite3.connect('sistema.db')
                        conn.execute("INSERT OR IGNORE INTO configuracao_turnos VALUES (?)", (p_fin,))
                        conn.commit(); conn.close()
                st.rerun()
            
            if col_b.button("🗑️ Limpar Todos os Postos"):
                conn = sqlite3.connect('sistema.db')
                conn.execute("DELETE FROM configuracao_turnos")
                conn.execute("DELETE FROM escalas")
                conn.commit(); conn.close()
                st.warning("Sistema reiniciado.")
                st.rerun()

        with t3:
            st.subheader("Teste de Comunicações")
            if st.button("📧 Enviar E-mail de Teste"):
                if enviar_email(EMAIL_USER, "Admin", "Teste", teste=True):
                    st.success(f"E-mail enviado para {EMAIL_USER}")

# --- RESERVA DE TURNOS ---
if menu == "Reserva de Turnos":
    st.title("🎆 Reserva de Turnos")
    conn = sqlite3.connect('sistema.db')
    postos = [r[0] for r in conn.execute("SELECT posto FROM configuracao_turnos").fetchall()]
    dados = conn.execute("SELECT posto, nome, telefone FROM escalas").fetchall()
    ocupados = {r[0]: r[1] for r in dados}
    reg_nome = [r[1].upper() for r in dados]
    reg_tel = [r[2] for r in dados]
    conn.close()

    if postos:
        with st.form("reserva"):
            c1, c2 = st.columns(2)
            nome = c1.text_input("Nome")
            tel = c1.text_input("Telemóvel")
            mail = c2.text_input("Email")
            escolha = c2.selectbox("Turno", postos)
            q_sms = st.checkbox("Confirmar por SMS (Opcional)")
            if st.form_submit_button("Confirmar"):
                if not (nome and tel and mail): st.error("Faltam dados.")
                elif nome.upper() in reg_nome or tel in reg_tel: st.warning("Já tem um turno.")
                elif escolha in ocupados: st.error("Ocupado.")
                else:
                    conn = sqlite3.connect('sistema.db')
                    conn.execute("INSERT INTO escalas VALUES (?,?,?,?)", (escolha, nome, tel, mail))
                    conn.commit(); conn.close()
                    enviar_email(mail, nome, escolha)
                    if q_sms: enviar_sms(tel, f"Confirmado: {escolha}")
                    enviar_sms(ADMIN_PHONE, f"Novo: {nome} - {escolha}")
                    st.success("Registado!")
                    st.rerun()
        
        # Mapa de postos
        cols = st.columns(2)
        for i, p in enumerate(postos):
            with cols[i%2]:
                if p in ocupados: st.error(f"❌ {p} ({ocupados[p]})")
                else: st.success(f"✅ {p}")
    else: st.info("Sem postos.")

# --- CRIAR CONTA E LOGIN ---
elif menu == "Criar Conta":
    with st.form("c_conta"):
        n, e, s = st.text_input("Nome"), st.text_input("Email"), st.text_input("Senha", type="password")
        if st.form_submit_button("Criar"):
            conn = sqlite3.connect('sistema.db')
            try:
                conn.execute("INSERT INTO clientes VALUES (?,?,?)", (e, s, n))
                conn.commit(); st.success("Conta criada.")
            except: st.error("Email existe.")
            conn.close()

elif menu == "Área de Cliente":
    e, s = st.text_input("Email"), st.text_input("Senha", type="password")
    if st.button("Login"):
        conn = sqlite3.connect('sistema.db')
        u = conn.execute("SELECT nome FROM clientes WHERE email=? AND senha=?", (e, s)).fetchone()
        if u:
            st.success(f"Olá, {u[0]}")
            t = conn.execute("SELECT posto FROM escalas WHERE email=?", (e,)).fetchone()
            if t: st.info(f"O seu turno: {t[0]}")
            else: st.write("Sem turnos.")
        else: st.error("Falhou login.")
        conn.close()
