import streamlit as st
import sqlite3
import re
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from twilio.rest import Client
from datetime import datetime

# --- CONFIGURAÇÕES ---
ADMIN_PASSWORD = "ADMIN"
EMAIL_USER = "silvafrederico280385@gmail.com"
EMAIL_PASS = "*.*Fr3d5ilv488" 
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
TWILIO_ACCOUNT_SID = 'AC0c0da7648d2ad34f5c2df4253e371910'
TWILIO_AUTH_TOKEN = 'a83cb0baf2dce52ba061171d3f69a9f9'
TWILIO_NUMBER = "+12402930627"

BG_IMG = "https://images.unsplash.com/photo-1533174072545-7a4b6ad7a6c3?auto=format&fit=crop&q=80&w=1920"

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
                  carta TEXT, viatura TEXT, cartoes TEXT)''')
    conn.commit()
    conn.close()

def enviar_notificacao_filtrada(email_dest, tel_dest, nome, posto, p_mail, p_sms):
    mensagem = f"Ola {nome}, o seu turno no posto {posto} foi CONFIRMADO. Bom trabalho!"
    
    if p_mail == 1:
        try:
            msg = MIMEText(mensagem); msg['Subject'] = "CONFIRMACAO DE TURNO"
            msg['From'] = EMAIL_USER; msg['To'] = email_dest
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as s:
                s.starttls(); s.login(EMAIL_USER, EMAIL_PASS); s.send_message(msg)
        except: pass

    if p_sms == 1:
        try:
            client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
            client.messages.create(body=mensagem, from_=TWILIO_NUMBER, to=tel_dest)
        except: pass

st.set_page_config(page_title="Gestão de Segurança v12.0", layout="wide")
init_db()

st.markdown(f"""<style>.stApp {{ background: linear-gradient(rgba(0,0,0,0.7), rgba(0,0,0,0.7)), url("{BG_IMG}"); background-size: cover; }}</style>""", unsafe_allow_html=True)

if 'user_email' not in st.session_state: st.session_state.user_email = None

# --- SIDEBAR ---
with st.sidebar:
    if st.button("🏠 HOME / PORTAL", width='stretch'):
        st.session_state.user_email = None; st.rerun()
    st.divider()
    db_conn = sqlite3.connect('sistema.db')
    empresas = [r[0] for r in db_conn.execute("SELECT nome FROM empresas").fetchall()]
    db_conn.close()
    emp_filtro = st.selectbox("Empresa", ["Todas"] + empresas)
    data_filtro = st.date_input("Data", datetime.now())
    menu = st.radio("Menu:", ["Reserva de Turnos", "Área de Cliente", "Criar Conta"])
    st.divider()
    admin_check = st.checkbox("⚙️ Admin Mode")
    if admin_check:
        pwd = st.text_input("Senha", type="password")
        st.session_state.admin_auth = (pwd == ADMIN_PASSWORD)

# --- MODO ADMIN ---
if admin_check and st.session_state.get('admin_auth', False):
    st.header("🛠️ Administração")
    t1, t2 = st.tabs(["Gerar Postos", "Inscrições"])

    with t2:
        conn = sqlite3.connect('sistema.db')
        inscritos = conn.execute("SELECT posto, nome, status, telefone, email, pref_email, pref_sms FROM escalas").fetchall()
        for p, n, s, tel, mail, p_m, p_s in inscritos:
            with st.expander(f"{'✅' if s == 'Confirmado' else '⏳'} {n} - {p}"):
                st.write(f"Preferências: {'Email ' if p_m else ''}{'SMS' if p_s else ''}")
                if s == 'Pendente' and st.button("Confirmar e Notificar", key=f"adm_{p}"):
                    conn.execute("UPDATE escalas SET status='Confirmado' WHERE posto=?", (p,))
                    conn.commit()
                    enviar_notificacao_filtrada(mail, tel, n, p, p_m, p_s)
                    st.success("Confirmado conforme preferências."); st.rerun()
        conn.close()

    with t1:
        nova_emp = st.text_input("Empresa")
        local_geo = st.text_input("Localização")
        txt_bruto = st.text_area("Texto Bruto")
        if st.button("Gerar"):
            conn = sqlite3.connect('sistema.db')
            conn.execute("INSERT OR IGNORE INTO empresas VALUES (?)", (nova_emp.strip(),))
            local_f = "Geral"
            for l in txt_bruto.split('\n'):
                l = l.strip()
                if not l or any(x in l.upper() for x in ["FOGO", "PSG"]): continue
                if l.isupper() and len(l) > 3 and not re.search(r"\d+h", l): local_f = l
                else:
                    p_id = f"{local_f} | {l} ({data_filtro.strftime('%d/%m')})"
                    conn.execute("INSERT OR IGNORE INTO configuracao_turnos VALUES (?,?,?,?)", (p_id, nova_emp.strip(), data_filtro.strftime('%Y-%m-%d'), local_geo))
            conn.commit(); conn.close(); st.rerun()

# --- RESERVA DE TURNOS ---
elif menu == "Reserva de Turnos":
    st.title("📅 Reserva")
    conn = sqlite3.connect('sistema.db')
    postos = conn.execute("SELECT posto, localizacao FROM configuracao_turnos WHERE data=?", (data_filtro.strftime('%Y-%m-%d'),)).fetchall()
    ocupados = dict(conn.execute("SELECT posto, nome FROM escalas").fetchall())
    conn.close()

    if postos:
        st.markdown(f'<iframe width="100%" height="200" src="https://maps.google.com/maps?q={postos[0][1]}&output=embed"></iframe>', unsafe_allow_html=True)
        cols = st.columns(3)
        for i, (p, _) in enumerate(postos):
            with cols[i%3]:
                if p in ocupados: st.error(f"❌ {p}")
                else:
                    st.success(f"✅ {p}")
                    if st.session_state.user_email:
                        with st.popover("Reservar"):
                            m_ok = st.checkbox("Notificar por Email", key=f"m_{p}")
                            s_ok = st.checkbox("Notificar por SMS", key=f"s_{p}")
                            if st.button("Confirmar", key=f"btn_{p}"):
                                conn = sqlite3.connect('sistema.db')
                                u = conn.execute("SELECT nome, telefone, email FROM clientes WHERE email=?", (st.session_state.user_email,)).fetchone()
                                conn.execute("INSERT INTO escalas VALUES (?,?,?,?,?,?,?,?)", (p, u[0], u[1], u[2], data_filtro.strftime('%Y-%m-%d'), 'Pendente', int(m_ok), int(s_ok)))
                                conn.commit(); conn.close(); st.rerun()

# --- OUTROS MENUS ---
elif menu == "Criar Conta":
    with st.form("reg"):
        n, e, t, s = st.text_input("Nome"), st.text_input("Email"), st.text_input("Tel"), st.text_input("Senha", type="password")
        if st.form_submit_button("Criar"):
            conn = sqlite3.connect('sistema.db')
            conn.execute("INSERT INTO clientes VALUES (?,?,?,?,?,?,?)", (e, s, n, t, "Sim", "Sim", ""))
            conn.commit(); conn.close(); st.session_state.user_email = e; st.rerun()

elif menu == "Área de Cliente":
    if st.session_state.user_email:
        conn = sqlite3.connect('sistema.db')
        user = conn.execute("SELECT nome FROM clientes WHERE email=?", (st.session_state.user_email,)).fetchone()
        st.subheader(f"Olá {user[0]}")
        res = conn.execute("SELECT posto, status FROM escalas WHERE email=?", (st.session_state.user_email,)).fetchall()
        for p, s in res:
            st.info(f"📍 {p} | Status: {s}")
            if st.button("Desistir", key=f"c_{p}"):
                conn.execute("DELETE FROM escalas WHERE posto=?", (p,)); conn.commit(); st.rerun()
        if st.button("Sair"): st.session_state.user_email = None; st.rerun()
        conn.close()
    else:
        e, s = st.text_input("Email"), st.text_input("Senha", type="password")
        if st.button("Entrar"):
            conn = sqlite3.connect('sistema.db')
            if conn.execute("SELECT email FROM clientes WHERE email=? AND senha=?", (e, s)).fetchone():
                st.session_state.user_email = e; st.rerun()
