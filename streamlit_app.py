import streamlit as st
import sqlite3
import re
import pandas as pd
import smtplib
import time
from email.mime.text import MIMEText
from twilio.rest import Client
from datetime import datetime

# --- CONFIGURAÇÕES DE API E SEGURANÇA ---
ADMIN_PASSWORD = "ADMIN"
EMAIL_USER = "silvafrederico280385@gmail.com"
EMAIL_PASS = "*.*Fr3d5ilv488" 
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
TWILIO_ACCOUNT_SID = 'AC0c0da7648d2ad34f5c2df4253e371910'
TWILIO_AUTH_TOKEN = 'a83cb0baf2dce52ba061171d3f69a9f9'
TWILIO_NUMBER = "+12402930627"

# --- INICIALIZAÇÃO DA BASE DE DADOS ---
def init_db():
    conn = sqlite3.connect('sistema.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS escalas 
                 (posto TEXT PRIMARY KEY, nome TEXT, telefone TEXT, email TEXT, data TEXT, 
                  status TEXT DEFAULT 'Pendente', pref_email INTEGER DEFAULT 0, pref_sms INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS configuracao_turnos 
                 (posto TEXT PRIMARY KEY, empresa TEXT, data TEXT, localizacao TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS empresas (nome TEXT PRIMARY KEY)''')
    c.execute('''CREATE TABLE IF NOT EXISTS clientes 
                 (email TEXT PRIMARY KEY, senha TEXT, nome TEXT, telefone TEXT, 
                  carta TEXT, viatura TEXT, cartoes TEXT, ranking INTEGER DEFAULT 5)''')
    conn.commit()
    conn.close()

# --- FUNÇÃO DE NOTIFICAÇÃO FILTRADA ---
def enviar_alerta(email_dest, tel_dest, nome, posto, p_mail, p_sms):
    msg = f"Ola {nome}, o seu turno no posto {posto} foi CONFIRMADO."
    if p_mail == 1:
        try:
            m = MIMEText(msg); m['Subject'] = "CONFIRMACAO DE TURNO"; m['From'] = EMAIL_USER; m['To'] = email_dest
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as s:
                s.starttls(); s.login(EMAIL_USER, EMAIL_PASS); s.send_message(m)
        except: pass
    if p_sms == 1:
        try:
            Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN).messages.create(body=msg, from_=TWILIO_NUMBER, to=tel_dest)
        except: pass

st.set_page_config(page_title="Gestão de Segurança v20.0", layout="wide")
init_db()

# --- LÓGICA DE TIMEOUT ADMIN (10 MINUTOS) ---
if st.session_state.get('admin_auth'):
    if 'last_activity' not in st.session_state: st.session_state.last_activity = time.time()
    if time.time() - st.session_state.last_activity > 600:
        st.session_state.admin_auth = False
        st.rerun()
    st.session_state.last_activity = time.time()

# --- SIDEBAR (CONTROLO DE ACESSO) ---
with st.sidebar:
    st.title("🛡️ Portal de Escalas")
    if st.button("🏠 REFRESH / HOME"): st.rerun()
    
    st.divider()
    if not st.session_state.get('admin_auth', False):
        st.subheader("⚙️ Acesso Admin")
        with st.form("login_admin"):
            p = st.text_input("Senha", type="password")
            if st.form_submit_button("🔓 Entrar"):
                if p == ADMIN_PASSWORD:
                    st.session_state.admin_auth = True
                    st.rerun()
                else: st.error("Senha Incorreta")
    else:
        st.success("Modo Admin Ativo")
        if st.button("🔒 Sair do Admin"):
            st.session_state.admin_auth = False
            st.rerun()

    st.divider()
    menu = st.radio("Navegação", ["Reserva de Turnos", "Área de Cliente", "Criar Conta"])

# --- INTERFACE ADMINISTRATIVA ---
if st.session_state.get('admin_auth'):
    st.header("🛠️ Painel Administrativo")
    t1, t2, t3 = st.tabs(["Gerar Postos", "Validar Colaboradores", "Limpeza"])

    with t1:
        emp = st.text_input("Empresa", "PSG-REAL")
        loc_gps = st.text_input("Link Localização (Maps)")
        txt_input = st.text_area("Texto Bruto (Dia, Local, Horário)", height=250)
        if st.button("🚀 Processar e Criar Postos"):
            linhas = txt_input.split('\n')
            local_ref, dia_ref = "Geral", "31"
            count = 0
            conn = sqlite3.connect('sistema.db')
            for l in linhas:
                l = l.strip()
                if not l or l == "-" or ("€" in l and "Das" not in l): continue
                if "DIA" in l.upper() or (l.isdigit() and len(l) <= 2):
                    dia_ref = l
                elif (l.isupper() or len(l) > 3) and "DAS" not in l.upper() and "FOGO" not in l.upper():
                    local_ref = l
                elif "Das" in l and "€" in l:
                    p_full = f"Dia {dia_ref} | {local_ref} | {l}"
                    conn.execute("INSERT OR IGNORE INTO configuracao_turnos VALUES (?,?,?,?)", (p_full, emp, "2025-12-31", loc_gps))
                    count += 1
            conn.commit(); conn.close()
            st.success(f"Criados {count} postos.")

    with t2:
        conn = sqlite3.connect('sistema.db')
        inscritos = conn.execute("SELECT * FROM escalas").fetchall()
        for r in inscritos:
            rank = conn.execute("SELECT ranking FROM clientes WHERE email=?", (r[3],)).fetchone()
            stars = "⭐" * (rank[0] if rank else 5)
            with st.expander(f"{stars} {r[1]} -> {r[0]} ({r[5]})"):
                if r[5] == 'Pendente' and st.button("Confirmar", key=f"conf_{r[0]}"):
                    conn.execute("UPDATE escalas SET status='Confirmado' WHERE posto=?", (r[0],))
                    conn.commit()
                    enviar_alerta(r[3], r[2], r[1], r[0], r[6], r[7])
                    st.rerun()
                if st.button("Remover", key=f"del_{r[0]}"):
                    conn.execute("DELETE FROM escalas WHERE posto=?", (r[0],)); conn.commit(); st.rerun()
        conn.close()

# --- RESERVA DE TURNOS ---
elif menu == "Reserva de Turnos":
    st.header("📅 Turnos Disponíveis")
    conn = sqlite3.connect('sistema.db')
    postos = conn.execute("SELECT posto, localizacao FROM configuracao_turnos").fetchall()
    ocupados = dict(conn.execute("SELECT posto, nome FROM escalas").fetchall())
    conn.close()

    if postos:
        st.caption("Previsualização do Local:")
        st.markdown(f'<iframe width="100%" height="150" src="https://maps.google.com/maps?q={postos[0][1]}&output=embed"></iframe>', unsafe_allow_html=True)
        
        cols = st.columns(2)
        for i, (p, _) in enumerate(postos):
            with cols[i%2]:
                if p in ocupados:
                    st.error(f"❌ {p}\n(Ocupado por {ocupados[p]})")
                else:
                    st.success(f"✅ {p}")
                    if st.session_state.get('user_email'):
                        with st.popover("Confirmar Reserva"):
                            e_not = st.checkbox("Notificar Email", True, key=f"e_{i}")
                            s_not = st.checkbox("Notificar SMS", key=f"s_{i}")
                            if st.button("Confirmar", key=f"btn_{i}"):
                                conn = sqlite3.connect('sistema.db')
                                u = conn.execute("SELECT nome, telefone, email FROM clientes WHERE email=?", (st.session_state.user_email,)).fetchone()
                                conn.execute("INSERT INTO escalas VALUES (?,?,?,?,?,?,?,?)", (p, u[0], u[1], u[2], "2025-12-31", 'Pendente', int(e_not), int(s_not)))
                                conn.commit(); conn.close(); st.rerun()
                    else: st.warning("Faça Login para reservar.")

# --- CRIAR CONTA ---
elif menu == "Criar Conta":
    st.header("👤 Novo Registo")
    with st.form("reg_user"):
        n, e, t, s = st.text_input("Nome"), st.text_input("Email"), st.text_input("Telemóvel"), st.text_input("Senha", type="password")
        if st.form_submit_button("Criar Conta"):
            conn = sqlite3.connect('sistema.db')
            try:
                conn.execute("INSERT INTO clientes VALUES (?,?,?,?,?,?,?,?)", (e, s, n, t, "Sim", "Sim", "VIG", 5))
                conn.commit(); st.session_state.user_email = e; st.success("Registado!"); st.rerun()
            except: st.error("Email já existe.")
            finally: conn.close()

# --- ÁREA DE CLIENTE ---
elif menu == "Área de Cliente":
    if st.session_state.get('user_email'):
        conn = sqlite3.connect('sistema.db')
        u = conn.execute("SELECT nome, ranking FROM clientes WHERE email=?", (st.session_state.user_email,)).fetchone()
        st.subheader(f"Olá {u[0]} | Ranking: {'⭐' * u[1]}")
        meus = conn.execute("SELECT posto, status FROM escalas WHERE email=?", (st.session_state.user_email,)).fetchall()
        for p, s in meus:
            st.info(f"Posto: {p} | Status: {s}")
        if st.button("Logout"): st.session_state.user_email = None; st.rerun()
        conn.close()
    else:
        with st.form("login_u"):
            e = st.text_input("Email")
            s = st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar"):
                conn = sqlite3.connect('sistema.db')
                if conn.execute("SELECT 1 FROM clientes WHERE email=? AND senha=?", (e,s)).fetchone():
                    st.session_state.user_email = e; st.rerun()
                else: st.error("Dados Inválidos")
                conn.close()
